"""Trusted execution boundary, immutable requests, exact approvals and simulated adapter."""

from __future__ import annotations

import json
from contextlib import nullcontext
from dataclasses import asdict, dataclass
from typing import Protocol

from aecp.determinism import canonical_json, stable_digest
from aecp.ledger import IdempotencyConflict, Ledger, _amount, _identifier
from aecp.market import Market
from aecp.policies import COSTS
from aecp.workload import resolve

POLICY_VERSION = "authorization.v1"


class Denied(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Quote:
    upper_bound: int
    unit: str = "SIM_COST_MICRO"
    mode: str = "simulated"
    version: str = "sim-adapter.v1"
    details: dict | None = None


def quote_record(quote: Quote) -> dict:
    result = asdict(quote)
    if result["details"] is None:
        del result["details"]
    return result


@dataclass(frozen=True)
class Receipt:
    payload: dict
    actual_units: int
    unit: str = "SIM_COST_MICRO"
    source: str = "sim-adapter.v1"


class ResourceAdapter(Protocol):
    def quote(self, resource: str, parameters: dict) -> Quote: ...
    def execute(self, resource: str, parameters: dict) -> Receipt: ...


class SimulatedAdapter:
    def quote(self, resource: str, parameters: dict) -> Quote:
        if resource not in COSTS:
            raise Denied("RESOURCE_NOT_ALLOWED")
        return Quote(COSTS[resource])

    def execute(self, resource: str, parameters: dict) -> Receipt:
        if resource in {"planning", "bidding", "verification", "mandatory_review"}:
            return Receipt({"resource": resource, "completed": True}, COSTS[resource])
        resolution = resolve(parameters["invoice_cents"], parameters["payments"])
        return Receipt({"resource": resource, "resolution": resolution,
                        "evidence": parameters, "provider": "deterministic-record-processor"}, COSTS[resource])


@dataclass(frozen=True)
class LocalCostModel:
    """Allocated cost; rate units per second/GiB-second, usage in milliseconds/MiB."""
    cpu_rate: int = 2
    gpu_rate: int = 100
    memory_rate: int = 1

    def allocated_cost(self, cpu_ms: int, gpu_ms: int, memory_mib_ms: int) -> dict:
        for value in (cpu_ms, gpu_ms, memory_mib_ms, self.cpu_rate, self.gpu_rate, self.memory_rate):
            _amount(value)
        numerator = cpu_ms * self.cpu_rate * 1024 + gpu_ms * self.gpu_rate * 1024
        numerator += memory_mib_ms * self.memory_rate
        return {"allocated_cost": (numerator + 1023999) // 1024000,
                "unit": "LOCAL_ALLOCATED_MICRO", "actual_cash_spend": None}


class ControlPlane:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger
        self.market = Market(ledger)
        self.adapter: ResourceAdapter = SimulatedAdapter()
        self.adapters: dict[str, ResourceAdapter] = {}
        with ledger._transaction() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS requests(
                id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, task_id TEXT NOT NULL, resource TEXT NOT NULL,
                operation TEXT NOT NULL, parameters TEXT NOT NULL, fingerprint TEXT NOT NULL,
                quote INTEGER NOT NULL, result TEXT, policy_version TEXT NOT NULL)""")
            connection.execute("""CREATE TABLE IF NOT EXISTS approvals(
                id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
                expires_at INTEGER NOT NULL, reviewer TEXT, state TEXT NOT NULL)""")
            connection.execute("""CREATE TABLE IF NOT EXISTS task_policy(
                agent_id TEXT NOT NULL, task_id TEXT NOT NULL, required_operation TEXT NOT NULL,
                PRIMARY KEY(agent_id, task_id))""")
            connection.execute("""CREATE TABLE IF NOT EXISTS approval_actions(
                approval_id TEXT PRIMARY KEY REFERENCES approvals(id), action TEXT NOT NULL)""")
            connection.execute("""CREATE TABLE IF NOT EXISTS request_quotes(
                request_id TEXT PRIMARY KEY REFERENCES requests(id), quote TEXT NOT NULL)""")
            connection.execute("""CREATE TABLE IF NOT EXISTS receipts(
                request_id TEXT PRIMARY KEY REFERENCES requests(id), actual_units INTEGER NOT NULL,
                unit TEXT NOT NULL, source TEXT NOT NULL)""")

    def register_task(self, agent_id: str, task_id: str, required_operation: str) -> None:
        """Trusted workload/operator policy. Agents cannot lower a registered operation class."""
        if required_operation not in {"reconcile", "release_payment"}:
            raise ValueError("invalid operation class")
        _identifier(task_id)
        self.ledger.account(agent_id)
        with self.ledger._transaction() as connection:
            old = connection.execute("SELECT required_operation FROM task_policy WHERE agent_id = ? AND task_id = ?",
                                     (agent_id, task_id)).fetchone()
            if old and old[0] != required_operation:
                raise IdempotencyConflict("trusted task policy is immutable")
            connection.execute("INSERT OR IGNORE INTO task_policy VALUES (?, ?, ?)",
                               (agent_id, task_id, required_operation))

    def validate_task(self, agent_id: str, task_id: str, operation: str, resource: str) -> None:
        with self.ledger._transaction() as connection:
            policy = connection.execute("SELECT required_operation FROM task_policy WHERE agent_id = ? AND task_id = ?",
                                        (agent_id, task_id)).fetchone()
        if not policy:
            raise Denied("UNKNOWN_TASK")
        if policy[0] != operation and resource not in {"planning", "bidding", "verification", "mandatory_review"}:
            raise Denied("OPERATION_POLICY_MISMATCH")

    def adapter_for(self, resource: str) -> ResourceAdapter:
        return self.adapters.get(resource, self.adapter)

    def fingerprint(self, agent_id: str, task_id: str, resource: str, operation: str, parameters: dict,
                    request_id: str, *, quote: Quote | None = None) -> str:
        return stable_digest({"agent_id": agent_id, "task_id": task_id, "resource": resource,
                              "operation": operation, "parameters": parameters, "policy": POLICY_VERSION,
                              "request_id": request_id,
                              "quote": quote_record(quote or self.adapter_for(resource).quote(resource, parameters))})

    def approval_request(self, approval_id: str, agent_id: str, fingerprint: str, expires_at: int,
                         *, action: dict | None = None) -> dict:
        for identity in (approval_id, agent_id, fingerprint):
            _identifier(identity)
        _amount(expires_at, positive=True)
        with self.ledger._transaction() as connection:
            old = connection.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
            if old:
                if (old["agent_id"], old["fingerprint"], old["expires_at"]) != (agent_id, fingerprint, expires_at):
                    raise IdempotencyConflict("approval request changed")
                return dict(old)
            connection.execute("INSERT INTO approvals VALUES (?, ?, ?, ?, NULL, 'PENDING')",
                               (approval_id, agent_id, fingerprint, expires_at))
            if action is not None:
                connection.execute("INSERT INTO approval_actions VALUES (?, ?)", (approval_id, canonical_json(action)))
            self.ledger._event(connection, "approval_requested", agent_id, approval_id=approval_id,
                               fingerprint=fingerprint, expires_at=expires_at)
            return dict(connection.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone())

    def review(self, approval_id: str, reviewer: str, *, approve: bool, now: int) -> None:
        _identifier(reviewer)
        with self.ledger._transaction() as connection:
            approval = connection.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
            if not approval or now >= approval["expires_at"] or approval["state"] != "PENDING":
                raise Denied("APPROVAL_EXPIRED_OR_FINAL")
            if reviewer == approval["agent_id"]:
                raise Denied("SELF_APPROVAL_FORBIDDEN")
            state = "APPROVED" if approve else "REJECTED"
            connection.execute("UPDATE approvals SET reviewer = ?, state = ? WHERE id = ?",
                               (reviewer, state, approval_id))
            self.ledger._event(connection, "review_decision", approval["agent_id"], approval_id=approval_id,
                               reviewer=reviewer, state=state)

    def prepare(self, request_id: str, agent_id: str, task_id: str, resource: str, parameters: dict,
                *, operation: str = "reconcile", now: int = 0, expires_at: int | None = None) -> dict:
        for identity in (request_id, agent_id, task_id):
            _identifier(identity)
        if operation not in {"reconcile", "release_payment"}:
            raise Denied("OPERATION_NOT_ALLOWED")
        self.validate_task(agent_id, task_id, operation, resource)
        if resource in {"cheap", "premium", "consultation"}:
            if set(parameters) != {"invoice_cents", "payments"}:
                raise Denied("INVALID_PARAMETERS")
            _amount(parameters["invoice_cents"], positive=True)
            if not isinstance(parameters["payments"], list) or len(parameters["payments"]) > 32:
                raise Denied("INVALID_PARAMETERS")
            for payment in parameters["payments"]:
                _amount(payment)
        elif resource not in self.adapters and parameters:
            raise Denied("INVALID_PARAMETERS")
        adapter = self.adapter_for(resource)
        if hasattr(adapter, "authorize"):
            adapter.authorize(agent_id, task_id, operation, resource, parameters)
        quote = adapter.quote(resource, parameters)
        _amount(quote.upper_bound, positive=True)
        if self.ledger.account(agent_id)["unit"] != quote.unit:
            raise Denied("QUOTE_UNIT_MISMATCH")
        fingerprint = self.fingerprint(agent_id, task_id, resource, operation, parameters, request_id, quote=quote)
        with self.ledger._transaction() as connection:
            old = connection.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
            if old and old["fingerprint"] != fingerprint:
                raise IdempotencyConflict("request changed")
            if operation == "release_payment":
                approved = connection.execute(
                    "SELECT id FROM approvals WHERE agent_id = ? AND fingerprint = ? "
                    "AND state = 'APPROVED' AND expires_at > ?",
                    (agent_id, fingerprint, now),
                ).fetchone()
                if not approved:
                    self.ledger._event(connection, "policy_denied", agent_id, request_id,
                                       reason="APPROVAL_REQUIRED", fingerprint=fingerprint)
            else:
                approved = True
        if not approved:
            raise Denied("APPROVAL_REQUIRED")
        self.ledger.reserve(agent_id, request_id, quote.upper_bound, task_id=task_id,
                            operation_id=operation, request_hash=fingerprint, expires_at=expires_at, resource=resource)
        with self.ledger._transaction() as connection:
            connection.execute("INSERT OR IGNORE INTO requests VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)",
                               (request_id, agent_id, task_id, resource, operation, canonical_json(parameters),
                                fingerprint, quote.upper_bound, POLICY_VERSION))
            connection.execute("INSERT OR IGNORE INTO request_quotes VALUES (?, ?)",
                               (request_id, canonical_json(quote_record(quote))))
        return self.request(request_id, agent_id)

    def execute(self, request_id: str, agent_id: str, *, now: int = 0,
                trusted_capacity: bool = False, ambiguous: bool = False) -> dict:
        request = self.request(request_id, agent_id)
        hold = request["reservation"]
        if hold["state"] in {"SETTLED", "RELEASED"}:
            return request
        if request["result"] is not None:
            if request["receipt"] is None:
                self.ledger.mark_unresolved(request_id)
                return self.request(request_id, agent_id)
            self.ledger.settle(request_id, request["receipt"]["actual_units"])
            return self.request(request_id, agent_id)
        if hold["state"] in {"DISPATCHED", "UNRESOLVED"}:
            self.ledger.mark_unresolved(request_id)
            return self.request(request_id, agent_id)
        self.validate_task(agent_id, request["task_id"], request["operation"], request["resource"])
        adapter = self.adapter_for(request["resource"])
        if hasattr(adapter, "authorize"):
            adapter.authorize(agent_id, request["task_id"], request["operation"], request["resource"],
                              json.loads(request["parameters"]))
        current_quote = quote_record(adapter.quote(request["resource"], json.loads(request["parameters"])))
        if current_quote != request["quote_metadata"]:
            raise Denied("QUOTE_CHANGED_NEW_AUTHORIZATION_REQUIRED")
        with self.ledger._transaction() as connection:
            if request["operation"] == "release_payment":
                approved = connection.execute(
                    "SELECT id FROM approvals WHERE agent_id = ? AND fingerprint = ? "
                    "AND state = 'APPROVED' AND expires_at > ?", (agent_id, request["fingerprint"], now)
                ).fetchone()
                if not approved:
                    raise Denied("APPROVAL_REQUIRED")
            if request["resource"] in {"premium", "consultation"} and not trusted_capacity:
                if request["resource"] != "premium":
                    raise Denied("CAPACITY_UNAVAILABLE")
                allocated = connection.execute(
                    """SELECT bids.id FROM bids JOIN auctions ON bids.auction_id = auctions.id
                        WHERE bids.hold_id = ? AND bids.agent_id = ? AND bids.state = 'ALLOCATED'
                        AND auctions.expires_at > ?""", (request_id, agent_id, now)
                ).fetchone()
                if not allocated:
                    raise Denied("CAPACITY_UNAVAILABLE")
            self.ledger._dispatch(connection, request_id, now)
        if ambiguous:
            self.ledger.mark_unresolved(request_id)
            return self.request(request_id, agent_id)
        try:
            receipt = adapter.execute(request["resource"], json.loads(request["parameters"]))
            _amount(receipt.actual_units)
            if receipt.unit != request["unit"]:
                raise ValueError("adapter receipt changed accounting unit")
        except Exception as error:
            self.ledger.mark_unresolved(request_id)
            with self.ledger._transaction() as connection:
                self.ledger._event(connection, "adapter_error", agent_id, request_id,
                                   error_type=type(error).__name__)
            return self.request(request_id, agent_id)
        with self.ledger._transaction() as connection:
            connection.execute("UPDATE requests SET result = ? WHERE id = ?",
                               (canonical_json(receipt.payload), request_id))
            connection.execute("INSERT INTO receipts VALUES (?, ?, ?, ?)",
                               (request_id, receipt.actual_units, receipt.unit, receipt.source))
            self.ledger._event(connection, "adapter_receipt", agent_id, request_id,
                               actual_units=receipt.actual_units, unit=receipt.unit, source=receipt.source)
        self.ledger.settle(request_id, receipt.actual_units)
        return self.request(request_id, agent_id)

    def request(self, request_id: str, agent_id: str, *, connection=None) -> dict:
        with (self.ledger._transaction() if connection is None else nullcontext(connection)) as connection:
            row = connection.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
            if not row or row["agent_id"] != agent_id:
                raise Denied("REQUEST_NOT_FOUND")
            result = dict(row)
            result["result"] = json.loads(row["result"]) if row["result"] else None
            result["reservation"] = dict(self.ledger._hold(connection, request_id))
            quote = connection.execute("SELECT quote FROM request_quotes WHERE request_id = ?",
                                       (request_id,)).fetchone()
            result["quote_metadata"] = json.loads(quote[0]) if quote else None
            receipt = connection.execute("SELECT * FROM receipts WHERE request_id = ?", (request_id,)).fetchone()
            result["receipt"] = dict(receipt) if receipt else None
            result["mode"] = result["quote_metadata"]["mode"] if quote else "simulated"
            result["unit"] = result["quote_metadata"]["unit"] if quote else "SIM_COST_MICRO"
            return result
