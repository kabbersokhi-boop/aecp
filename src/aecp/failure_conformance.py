"""Offline failure-conformance benchmark with provider-owned durable ground truth."""

from __future__ import annotations

import json
import multiprocessing
import os
import sqlite3
import threading
from collections import Counter
from dataclasses import asdict, dataclass
from multiprocessing.connection import Client, Listener
from pathlib import Path
from typing import Protocol

from aecp.control import ControlPlane, Quote, Receipt, ResourceAdapter
from aecp.determinism import bernoulli_bps, stable_digest
from aecp.ledger import BudgetRejected, IdempotencyConflict, InvalidTransition, Ledger

UNIT = "SIM_COST_MICRO"
PROVIDER_VERSION = "independent-fake-provider.v1"
CONTRACT_VERSION = "failure-conformance.v1"


class ProviderResponseLost(RuntimeError):
    pass


@dataclass(frozen=True)
class Attempt:
    attempt_id: str
    correlation_id: str
    charge: int = 3
    fault: str = "none"
    idempotent_provider: bool = False
    worker_exit_after_response: bool = False


class GatewayAdapter(Protocol):
    name: str

    def attempt(self, attempt: Attempt) -> dict: ...
    def snapshot(self) -> dict: ...


def _provider_schema(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE executions(
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            received INTEGER NOT NULL,
            executed INTEGER NOT NULL,
            charge INTEGER NOT NULL,
            result_id TEXT,
            delivered INTEGER NOT NULL,
            fault TEXT NOT NULL,
            provider_mode TEXT NOT NULL
        );
        CREATE INDEX executions_correlation ON executions(correlation_id, seq);
    """)


def _provider_server(socket_path: str, journal_path: str, ready) -> None:
    path = Path(socket_path)
    if path.exists():
        path.unlink()
    database = sqlite3.connect(journal_path)
    database.row_factory = sqlite3.Row
    _provider_schema(database)
    listener = Listener(socket_path, family="AF_UNIX")
    ready.set()
    try:
        running = True
        while running:
            channel = listener.accept()
            try:
                message = channel.recv()
                command = message["command"]
                if command == "shutdown":
                    channel.send({"ok": True})
                    running = False
                    continue
                if command == "journal":
                    rows = [dict(row) for row in database.execute("SELECT * FROM executions ORDER BY seq")]
                    channel.send({"rows": rows})
                    continue
                attempt = message["attempt"]
                mode = "idempotent" if attempt["idempotent_provider"] else "non-idempotent"
                previous = None
                if attempt["idempotent_provider"]:
                    previous = database.execute(
                        "SELECT * FROM executions WHERE correlation_id = ? AND executed = 1 ORDER BY seq LIMIT 1",
                        (attempt["correlation_id"],),
                    ).fetchone()
                fault = attempt["fault"]
                executed = fault != "no_execute_drop" and previous is None
                charge = attempt["charge"] if executed else 0
                result_id = previous["result_id"] if previous else (
                    stable_digest({"provider": PROVIDER_VERSION, "attempt": attempt["attempt_id"],
                                   "sequence": database.execute("SELECT count(*) FROM executions").fetchone()[0]})[:24]
                    if executed else None
                )
                delivered = fault not in {"drop_after_execute", "no_execute_drop"}
                database.execute(
                    "INSERT INTO executions(attempt_id, correlation_id, received, executed, charge, result_id, "
                    "delivered, fault, provider_mode) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)",
                    (attempt["attempt_id"], attempt["correlation_id"], int(executed), charge, result_id,
                     int(delivered), fault, mode),
                )
                database.commit()
                if delivered:
                    channel.send({"result_id": result_id, "actual_units": charge, "executed": bool(executed),
                                  "provider_mode": mode})
            finally:
                channel.close()
    finally:
        listener.close()
        database.close()
        if path.exists():
            path.unlink()


class ProviderProcess:
    def __init__(self, root: Path):
        self.socket = root / "provider.sock"
        self.journal_path = root / "provider.sqlite3"
        context = multiprocessing.get_context("spawn")
        self.ready = context.Event()
        self.process = context.Process(
            target=_provider_server, args=(str(self.socket), str(self.journal_path), self.ready), daemon=True
        )

    def __enter__(self):
        self.process.start()
        if not self.ready.wait(10):
            raise RuntimeError("provider process did not become ready")
        return self

    def call(self, attempt: Attempt) -> dict:
        channel = Client(str(self.socket), family="AF_UNIX")
        try:
            channel.send({"command": "execute", "attempt": asdict(attempt)})
            try:
                return channel.recv()
            except EOFError as error:
                raise ProviderResponseLost(attempt.attempt_id) from error
        finally:
            channel.close()

    def journal(self) -> list[dict]:
        channel = Client(str(self.socket), family="AF_UNIX")
        try:
            channel.send({"command": "journal"})
            return channel.recv()["rows"]
        finally:
            channel.close()

    def __exit__(self, exc_type, exc, traceback):
        if self.process.is_alive():
            channel = Client(str(self.socket), family="AF_UNIX")
            try:
                channel.send({"command": "shutdown"})
                channel.recv()
            finally:
                channel.close()
        self.process.join(timeout=10)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=5)


class JournaledProviderAdapter(ResourceAdapter):
    def __init__(self, provider: ProviderProcess, upper_bound: int = 4):
        self.provider = provider
        self.upper_bound = upper_bound

    def quote(self, resource: str, parameters: dict) -> Quote:
        return Quote(self.upper_bound, version=PROVIDER_VERSION,
                     details={"provider_idempotency": bool(parameters.get("idempotent_provider", False))})

    def execute(self, resource: str, parameters: dict) -> Receipt:
        attempt = Attempt(
            attempt_id=parameters["attempt_id"],
            correlation_id=parameters.get("correlation_id", parameters["attempt_id"]),
            charge=parameters.get("charge", 3),
            fault=parameters.get("fault", "none"),
            idempotent_provider=parameters.get("idempotent_provider", False),
            worker_exit_after_response=parameters.get("worker_exit_after_response", False),
        )
        result = self.provider.call(attempt)
        if attempt.worker_exit_after_response:
            os._exit(73)
        return Receipt({"provider_result_id": result["result_id"], "executed": result["executed"]},
                       result["actual_units"], source=PROVIDER_VERSION)


class AecpGateway:
    name = "aecp"

    def __init__(self, root: Path, provider: ProviderProcess, budget: int, *, upper_bound: int = 4):
        self.database = root / "aecp.sqlite3"
        self.ledger = Ledger(self.database)
        self.ledger.create_account("root", budget, unit=UNIT)
        self.ledger.create_account("agent", budget, unit=UNIT, parent_id="root")
        self.control = ControlPlane(self.ledger)
        self.control.adapters["journaled"] = JournaledProviderAdapter(provider, upper_bound)
        self.provider = provider

    def register(self, task_id: str) -> None:
        self.control.register_task("agent", task_id, "reconcile")

    def attempt(self, attempt: Attempt) -> dict:
        self.register(attempt.attempt_id)
        parameters = asdict(attempt)
        self.control.prepare(attempt.attempt_id, "agent", attempt.attempt_id, "journaled", parameters)
        return self.control.execute(attempt.attempt_id, "agent")

    def reconcile(self, attempt_id: str) -> dict:
        rows = [row for row in self.provider.journal() if row["attempt_id"] == attempt_id]
        if not rows:
            raise ValueError("provider has no evidence for attempt")
        row = rows[-1]
        evidence = f"{PROVIDER_VERSION}:{row['seq']}:{row['result_id'] or 'no-charge'}"
        if row["executed"]:
            self.ledger.settle(attempt_id, row["charge"])
        else:
            self.ledger.reconcile_no_charge(attempt_id, evidence=evidence)
        return self.control.request(attempt_id, "agent")

    def snapshot(self) -> dict:
        account = self.ledger.account("agent")
        return {"budget": account, "audit": self.ledger.audit(), "provider_journal": self.provider.journal()}


class NaiveGateway:
    name = "naive-check-then-execute"

    def __init__(self, provider: ProviderProcess, budget: int):
        self.provider = provider
        self.budget = budget
        self.spent = 0
        self.completed = 0
        self.lock = threading.Lock()

    def attempt(self, attempt: Attempt) -> dict:
        observed = self.spent
        if observed + attempt.charge > self.budget:
            return {"state": "DENIED"}
        result = self.provider.call(attempt)
        with self.lock:
            self.spent += result["actual_units"]
            self.completed += 1
        return {"state": "SETTLED", "actual": result["actual_units"]}

    def snapshot(self) -> dict:
        return {"budget": self.budget, "settled": self.spent, "useful_work_completed": self.completed,
                "provider_journal": self.provider.journal()}


class RejectAllGateway:
    name = "reject-all"

    def __init__(self, provider: ProviderProcess, budget: int):
        self.provider = provider
        self.budget = budget
        self.denied = 0

    def attempt(self, attempt: Attempt) -> dict:
        self.denied += 1
        return {"state": "DENIED"}

    def snapshot(self) -> dict:
        return {"budget": self.budget, "settled": 0, "useful_work_completed": 0,
                "legitimate_work_denied": self.denied, "provider_journal": self.provider.journal()}


def _worker_execute(database: str, socket_path: str, request_id: str, exit_before_settlement: bool) -> None:
    provider = object.__new__(ProviderProcess)
    provider.socket = Path(socket_path)
    control = ControlPlane(Ledger(database))
    control.adapters["journaled"] = JournaledProviderAdapter(provider)
    if exit_before_settlement:
        control.ledger.settle = lambda *args, **kwargs: os._exit(74)
    control.execute(request_id, "agent")


def _provider_metrics(rows: list[dict], budget: int, settled: int, reserved: int) -> dict:
    charges = sum(row["charge"] for row in rows if row["executed"])
    executions = sum(row["executed"] for row in rows)
    duplicates = sum(count - 1 for count in Counter(
        row["attempt_id"] for row in rows if row["executed"]
    ).values() if count > 1)
    exposure = max(0, charges - settled - reserved)
    return {"independently_journaled_provider_charges": charges, "gateway_settled_cost": settled,
            "outstanding_reserved_liability": reserved, "unaccounted_or_prematurely_released_exposure": exposure,
            "provider_executions": executions, "duplicate_provider_executions": duplicates,
            "observed_funding_violation": settled + reserved > budget}


def _fresh(root: Path, name: str) -> Path:
    path = root / name
    path.mkdir()
    return path


def run_conformance(output: Path) -> dict:
    if output.exists():
        raise ValueError("refusing to overwrite conformance evidence")
    output.parent.mkdir(parents=True, exist_ok=True)
    root = output.parent / ".conformance-work"
    if root.exists():
        raise ValueError("stale conformance work directory exists")
    root.mkdir()
    scenarios: dict[str, dict] = {}
    try:
        location = _fresh(root, "normal")
        with ProviderProcess(location) as provider:
            gateway = AecpGateway(location, provider, 12)
            result = gateway.attempt(Attempt("normal", "normal"))
            scenarios["normal_settlement"] = {"state": result["reservation"]["state"], **gateway.snapshot()}

        location = _fresh(root, "concurrent")
        with ProviderProcess(location) as provider:
            ledger = Ledger(location / "aecp.sqlite3")
            ledger.create_account("root", 4, unit=UNIT)
            for agent in ("agent-a", "agent-b"):
                ledger.create_account(agent, 4, unit=UNIT, parent_id="root")
            barrier = threading.Barrier(2)
            outcomes = []

            def reserve(agent: str) -> None:
                barrier.wait()
                try:
                    ledger.reserve(agent, agent, 4, task_id=agent, operation_id="reconcile", request_hash=agent)
                    outcomes.append("RESERVED")
                except BudgetRejected:
                    outcomes.append("DENIED")

            threads = [threading.Thread(target=reserve, args=(agent,)) for agent in ("agent-a", "agent-b")]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            scenarios["concurrent_parent_authority"] = {"outcomes": sorted(outcomes), "audit": ledger.audit()}

        location = _fresh(root, "identity")
        with ProviderProcess(location) as provider:
            gateway = AecpGateway(location, provider, 12)
            first = gateway.attempt(Attempt("immutable", "same-correlation"))
            second = gateway.control.execute("immutable", "agent")
            conflict = False
            try:
                gateway.control.prepare("immutable", "agent", "immutable", "journaled",
                                        {**asdict(Attempt("immutable", "same-correlation")), "charge": 2})
            except IdempotencyConflict:
                conflict = True
            identity_snapshot = gateway.snapshot()
            scenarios["duplicate_immutable_identity"] = {
                "first": first["reservation"]["state"], "repeat": second["reservation"]["state"],
                **identity_snapshot,
            }
            scenarios["changed_parameters_conflict"] = {"rejected": conflict, **identity_snapshot}

        location = _fresh(root, "provider-modes")
        with ProviderProcess(location) as provider:
            provider.call(Attempt("idem-1", "idem", idempotent_provider=True))
            provider.call(Attempt("idem-2", "idem", idempotent_provider=True))
            provider.call(Attempt("nonidem-1", "nonidem"))
            provider.call(Attempt("nonidem-2", "nonidem"))
            rows = provider.journal()
            scenarios["provider_idempotency_modes"] = {
                "idempotent_executions": sum(row["executed"] for row in rows
                                               if row["correlation_id"] == "idem"),
                "non_idempotent_executions": sum(row["executed"] for row in rows
                                                   if row["correlation_id"] == "nonidem"),
                "provider_journal": rows,
            }

        location = _fresh(root, "lost-response")
        with ProviderProcess(location) as provider:
            gateway = AecpGateway(location, provider, 8)
            lost = gateway.attempt(Attempt("lost", "lost", fault="drop_after_execute"))
            scenarios["executed_response_lost"] = {"state": lost["reservation"]["state"], **gateway.snapshot()}

        location = _fresh(root, "worker-death")
        with ProviderProcess(location) as provider:
            gateway = AecpGateway(location, provider, 8)
            attempt = Attempt("worker-death", "worker-death", worker_exit_after_response=True)
            gateway.register(attempt.attempt_id)
            gateway.control.prepare(attempt.attempt_id, "agent", attempt.attempt_id, "journaled", asdict(attempt))
            context = multiprocessing.get_context("spawn")
            worker = context.Process(target=_worker_execute,
                                     args=(str(gateway.database), str(provider.socket), attempt.attempt_id, False))
            worker.start()
            worker.join(10)
            recovered = ControlPlane(Ledger(gateway.database))
            recovered.adapters["journaled"] = JournaledProviderAdapter(provider)
            state = recovered.execute(attempt.attempt_id, "agent")["reservation"]["state"]
            scenarios["worker_dies_after_provider_execution"] = {
                "worker_exit": worker.exitcode, "state": state, **gateway.snapshot()
            }

        location = _fresh(root, "receipt-death")
        with ProviderProcess(location) as provider:
            gateway = AecpGateway(location, provider, 8)
            attempt = Attempt("receipt-death", "receipt-death")
            gateway.register(attempt.attempt_id)
            gateway.control.prepare(attempt.attempt_id, "agent", attempt.attempt_id, "journaled", asdict(attempt))
            context = multiprocessing.get_context("spawn")
            worker = context.Process(target=_worker_execute,
                                     args=(str(gateway.database), str(provider.socket), attempt.attempt_id, True))
            worker.start()
            worker.join(10)
            recovered = ControlPlane(Ledger(gateway.database))
            recovered.adapters["journaled"] = JournaledProviderAdapter(provider)
            state = recovered.execute(attempt.attempt_id, "agent")["reservation"]["state"]
            scenarios["durable_receipt_before_worker_death"] = {
                "worker_exit": worker.exitcode, "state": state, **gateway.snapshot()
            }

        location = _fresh(root, "retry-expiry")
        with ProviderProcess(location) as provider:
            gateway = AecpGateway(location, provider, 8)
            first = gateway.attempt(Attempt("attempt-1", "operation", fault="drop_after_execute"))
            second = gateway.attempt(Attempt("attempt-2", "operation", fault="drop_after_execute"))
            third_denied = False
            try:
                gateway.attempt(Attempt("attempt-3", "operation"))
            except BudgetRejected:
                third_denied = True
            gateway.ledger.expire(2**31)
            cancellation_denied = False
            try:
                gateway.ledger.release("attempt-1")
            except InvalidTransition:
                cancellation_denied = True
            retry_snapshot = gateway.snapshot()
            scenarios["independently_funded_retry"] = {
                "first": first["reservation"]["state"], "second": second["reservation"]["state"],
                "third_denied": third_denied, **retry_snapshot,
            }
            scenarios["expiry_cannot_erase_uncertainty"] = {
                "cancellation_denied": cancellation_denied,
                "first_after_expiry": gateway.ledger.reservation("attempt-1")["state"],
                **retry_snapshot,
            }

        location = _fresh(root, "reconciliation")
        with ProviderProcess(location) as provider:
            gateway = AecpGateway(location, provider, 8)
            gateway.attempt(Attempt("charged", "charged", fault="drop_after_execute"))
            charged = gateway.reconcile("charged")
            gateway.attempt(Attempt("no-charge", "no-charge", fault="no_execute_drop"))
            no_charge = gateway.reconcile("no-charge")
            scenarios["trusted_reconciliation"] = {
                "charged": charged["reservation"]["state"],
                "no_charge": no_charge["reservation"]["state"], **gateway.snapshot()
            }

        location = _fresh(root, "bound-breach")
        with ProviderProcess(location) as provider:
            gateway = AecpGateway(location, provider, 12, upper_bound=4)
            result = gateway.attempt(Attempt("overrun", "overrun", charge=7))
            account = gateway.ledger.account("agent")
            scenarios["provider_bound_breach"] = {
                "state": result["reservation"]["state"], "actual": result["reservation"]["actual"],
                "status": account["status"], **gateway.snapshot()
            }

        controls = {}
        location = _fresh(root, "naive")
        with ProviderProcess(location) as provider:
            naive = NaiveGateway(provider, 4)
            barrier = threading.Barrier(2)

            def unsafe(identity: str) -> None:
                barrier.wait()
                naive.attempt(Attempt(identity, identity, charge=4))

            threads = [threading.Thread(target=unsafe, args=(f"naive-{index}",)) for index in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            controls[naive.name] = naive.snapshot()
        location = _fresh(root, "reject-all")
        with ProviderProcess(location) as provider:
            reject = RejectAllGateway(provider, 4)
            reject.attempt(Attempt("rejected", "rejected", charge=4))
            controls[reject.name] = reject.snapshot()

        for scenario in scenarios.values():
            if "budget" not in scenario:
                continue
            budget = scenario["budget"]
            scenario["metrics"] = _provider_metrics(
                scenario["provider_journal"], budget["funded"], budget["spent"], budget["reserved"]
            )
        result = {
            "version": CONTRACT_VERSION,
            "scope": "project-defined offline conformance evidence; not industry certification",
            "provider_ground_truth": "separate process and SQLite journal; exported only after execution",
            "provider_modes": ["idempotent", "non-idempotent"],
            "simulated_cost_unit": UNIT,
            "scenarios": scenarios,
            "controls": controls,
            "trust_assumptions": [
                "trusted AECP process and storage",
                "complete mediation",
                "provider journal is authoritative only when explicitly exposed for reconciliation",
                "declared bounds are valid except in the deliberate breach scenario",
            ],
            "unsupported": ["host compromise", "malicious same-process code", "out-of-band provider access"],
            "provider_calls": 0,
        }
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return result
    finally:
        import shutil

        shutil.rmtree(root, ignore_errors=True)


def _study_trial(root: Path, seed: int, budget: int, loss_bps: int, strategy: str) -> dict:
    delay = {"retain": None, "reconcile-1": 1, "reconcile-4": 4}[strategy]
    with ProviderProcess(root) as provider:
        gateway = AecpGateway(root, provider, budget)
        pending: list[tuple[str, int]] = []
        completed = denied = 0
        authority_time = 0
        recovery_durations = []
        ticks = 12
        for tick in range(ticks + 5):
            for attempt_id, lost_at in tuple(pending):
                if delay is not None and tick - lost_at >= delay:
                    gateway.reconcile(attempt_id)
                    recovery_durations.append(tick - lost_at)
                    pending.remove((attempt_id, lost_at))
            if tick < ticks:
                attempt_id = f"task-{tick:02d}"
                lost = bernoulli_bps(loss_bps, seed, "response-loss", attempt_id)
                try:
                    result = gateway.attempt(Attempt(attempt_id, f"operation-{attempt_id}",
                                                     fault="drop_after_execute" if lost else "none"))
                    if result["reservation"]["state"] == "SETTLED":
                        completed += 1
                    else:
                        pending.append((attempt_id, tick))
                except BudgetRejected:
                    denied += 1
            authority_time += gateway.ledger.account("agent")["reserved"]
        snapshot = gateway.snapshot()
        metrics = _provider_metrics(snapshot["provider_journal"], budget,
                                    snapshot["budget"]["spent"], snapshot["budget"]["reserved"])
        return {"seed": seed, "budget": budget, "response_loss_bps": loss_bps, "strategy": strategy,
                "offered_work": ticks, "useful_work_completed": completed,
                "legitimate_work_denied_or_deferred": denied,
                "settled_modeled_cost": snapshot["budget"]["spent"],
                "unresolved_authority": snapshot["budget"]["reserved"],
                "authority_time_held": authority_time, "authority_time_unit": f"{UNIT}-ticks",
                "mean_recovery_ticks": (sum(recovery_durations) / len(recovery_durations)
                                        if recovery_durations else None),
                "reconciled_attempts": len(recovery_durations), "safety": metrics}


def run_cost_of_safety(output: Path, *, seeds: tuple[int, ...] = (1, 2, 3, 4, 5)) -> dict:
    if output.exists():
        raise ValueError("refusing to overwrite cost-of-safety evidence")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = output.parent / ".cost-study-work"
    if work.exists():
        raise ValueError("stale cost-study work directory exists")
    work.mkdir()
    rows = []
    try:
        for seed in seeds:
            for budget in (16, 28):
                for loss_bps in (2500, 5000):
                    for strategy in ("retain", "reconcile-1", "reconcile-4"):
                        trial = _fresh(work, f"s{seed}-b{budget}-l{loss_bps}-{strategy}")
                        rows.append(_study_trial(trial, seed, budget, loss_bps, strategy))
        paired = []
        keys = {(row["seed"], row["budget"], row["response_loss_bps"]) for row in rows}
        for key in sorted(keys):
            group = {row["strategy"]: row for row in rows
                     if (row["seed"], row["budget"], row["response_loss_bps"]) == key}
            baseline = group["retain"]
            for strategy in ("reconcile-1", "reconcile-4"):
                current = group[strategy]
                paired.append({"seed": key[0], "budget": key[1], "response_loss_bps": key[2],
                               "strategy": strategy,
                               "useful_work_difference": current["useful_work_completed"] -
                               baseline["useful_work_completed"],
                               "authority_time_difference": current["authority_time_held"] -
                               baseline["authority_time_held"],
                               "unresolved_authority_difference": current["unresolved_authority"] -
                               baseline["unresolved_authority"]})
        aggregates = {}
        for strategy in ("retain", "reconcile-1", "reconcile-4"):
            selected = [row for row in rows if row["strategy"] == strategy]
            aggregates[strategy] = {
                field: sum(row[field] for row in selected) / len(selected)
                for field in ("useful_work_completed", "settled_modeled_cost", "unresolved_authority",
                              "authority_time_held", "legitimate_work_denied_or_deferred")
            }
        result = {
            "version": "cost-of-safety.v1", "seeds": list(seeds), "trials": len(rows),
            "factors": {"budgets": [16, 28], "response_loss_bps": [2500, 5000],
                        "strategies": ["retain", "reconcile-1", "reconcile-4"], "offered_tasks": 12},
            "strategy_semantics": {
                "retain": "keep uncertain liability for the whole bounded observation window",
                "reconcile-1": "query authoritative provider evidence one logical tick after loss",
                "reconcile-4": "query authoritative provider evidence four logical ticks after loss",
            },
            "aggregates": aggregates, "paired_differences": paired, "rows": rows,
            "limitations": [
                "modeled authority-time is not money",
                "provider and workload are synthetic",
                "finite seeds are evidence for this bounded question, not proof for all histories",
                "provider truth is used only after its strategy-specific reconciliation delay",
            ],
            "provider_calls": 0,
        }
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return result
    finally:
        import shutil

        shutil.rmtree(work, ignore_errors=True)
