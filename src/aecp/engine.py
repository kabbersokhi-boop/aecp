"""Durable logical-time experiments with reproducible, paired financial workloads."""

from __future__ import annotations

import fcntl
import json
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from aecp.control import ControlPlane, Denied
from aecp.determinism import SCHEMA, canonical_json, stable_digest
from aecp.ledger import BudgetRejected, InvalidTransition, Ledger
from aecp.policies import COSTS, Policy
from aecp.policies import VERSION as POLICY_VERSION
from aecp.workload import VERSION, corpus, corpus_identity, evidence

SCENARIOS = ("ordinary", "tight", "burst", "outage", "review-collapse", "throttling", "retry-pressure")
SCHEDULERS = ("market", "equal", "priority", "evcost", "central")


def code_revision() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL,
                                       text=True, timeout=2).strip()
    except (OSError, subprocess.SubprocessError):
        return "unavailable"


class Engine:
    """Persist a tick plan before effects and use stable attempt IDs for crash recovery.

    Logical-time stepping has one trusted operator. Execution claims remain single-winner
    even if a caller incorrectly overlaps workers. No provider result is regenerated
    after an ambiguous dispatch; the action remains unresolved.
    """

    def __init__(self, path: str | Path):
        self.ledger = Ledger(path)
        self.control = ControlPlane(self.ledger)
        self.market = self.control.market
        with self.ledger._transaction() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS runs(
                id TEXT PRIMARY KEY, config TEXT NOT NULL, checkpoint TEXT NOT NULL,
                created_at TEXT NOT NULL, code_revision TEXT NOT NULL)""")
            connection.execute("""CREATE TABLE IF NOT EXISTS task_traces(
                run_id TEXT NOT NULL, task_id TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(run_id, task_id))""")

    def create(self, run_id: str = "demo", *, seed: int = 7, budget: int = 450,
               scenario: str = "ordinary", scheduler: str = "market", style: str = "adaptive",
               count: int = 36) -> dict:
        if scenario not in SCENARIOS or scheduler not in SCHEDULERS or style not in {
            "adaptive", "conservative", "value", "mixed"
        }:
            raise ValueError("unknown scenario, scheduler or style")
        if type(count) is not int or not 3 <= count <= 300:
            raise ValueError("count must be between 3 and 300")
        if scenario == "tight":
            budget = min(budget, 180)
        cases = corpus(seed, count, burst=scenario == "burst")
        config = {"seed": seed, "budget": budget, "scenario": scenario, "scheduler": scheduler,
                  "style": style, "count": count, "environment_version": VERSION,
                  "policy_version": POLICY_VERSION, "entropy_schema": SCHEMA,
                  "corpus_hash": corpus_identity(cases), "costs": COSTS,
                  "resource_capacity": {"premium": 2, "consultation": 1},
                  "mode": "deterministic_reproduction", "real_provider_spend": 0}
        with self.ledger._transaction() as connection:
            old = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if old and json.loads(old["config"]) != config:
                raise ValueError("run identity already binds a different experiment")
        self.ledger.create_account(run_id, budget, unit="SIM_COST_MICRO")
        self.ledger.create_account(f"{run_id}/workflow", budget, unit="SIM_COST_MICRO", parent_id=run_id)
        self.market.endow(f"{run_id}/treasury", 3000)
        for index in range(3):
            agent_id = f"{run_id}/agent-{index}"
            self.ledger.create_account(agent_id, budget, unit="SIM_COST_MICRO", parent_id=f"{run_id}/workflow")
            self.market.transfer(f"{run_id}/endow-{index}", f"{run_id}/treasury", agent_id, 700)
        for index, case in enumerate(cases):
            self.control.register_task(f"{run_id}/agent-{index % 3}", case.observation.task_id,
                                       "release_payment" if case.observation.mandatory else "reconcile")
        checkpoint = {"tick": 0, "finished": False, "beliefs": {}, "plan": None}
        with self.ledger._transaction() as connection:
            connection.execute("INSERT OR IGNORE INTO runs VALUES (?, ?, ?, ?, ?)",
                               (run_id, canonical_json(config), canonical_json(checkpoint),
                                datetime.now(UTC).isoformat(), code_revision()))
        return self.run(run_id)

    def run(self, run_id: str) -> dict:
        with self.ledger._transaction() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if not row:
                raise KeyError(run_id)
            return {**dict(row), "config": json.loads(row["config"]), "checkpoint": json.loads(row["checkpoint"])}

    def _checkpoint(self, run_id: str, checkpoint: dict) -> None:
        with self.ledger._transaction() as connection:
            connection.execute("UPDATE runs SET checkpoint = ? WHERE id = ?", (canonical_json(checkpoint), run_id))

    def _save_trace(self, run_id: str, task_id: str, trace: dict) -> None:
        with self.ledger._transaction() as connection:
            previous = connection.execute("SELECT payload FROM task_traces WHERE run_id = ? AND task_id = ?",
                                          (run_id, task_id)).fetchone()
            if previous and json.loads(previous[0]) == trace:
                return
            connection.execute("INSERT OR REPLACE INTO task_traces VALUES (?, ?, ?)",
                               (run_id, task_id, canonical_json(trace)))
            self.ledger._event(connection, "task_outcome", trace["agent_id"], task_id=task_id, trace=trace)

    def traces(self, run_id: str) -> list[dict]:
        with self.ledger._transaction() as connection:
            return [json.loads(row[0]) for row in connection.execute(
                "SELECT payload FROM task_traces WHERE run_id = ? ORDER BY task_id", (run_id,)
            )]

    def _charge(self, identity: str, agent: str, task: str, resource: str, tick: int) -> dict:
        self.control.prepare(identity, agent, task, resource, {}, now=tick)
        return self.control.execute(identity, agent, now=tick, trusted_capacity=True)

    def step(self, run_id: str) -> dict:
        """Serialize simulation operators across processes; OS releases the lock on death."""
        with open(self.ledger.path + ".engine.lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                return self._step(run_id)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _step(self, run_id: str) -> dict:
        run = self.run(run_id)
        config, checkpoint = run["config"], run["checkpoint"]
        if checkpoint["finished"]:
            return self._snapshot(run_id)
        tick = checkpoint["tick"]
        cases = corpus(config["seed"], config["count"], burst=config["scenario"] == "burst")
        by_id = {case.observation.task_id: case for case in cases}
        traces = {trace["task_id"]: trace for trace in self.traces(run_id)}
        policies = {}
        for index in range(3):
            agent = f"{run_id}/agent-{index}"
            style = ("conservative", "value", "adaptive")[index] if config["style"] == "mixed" else config["style"]
            policies[agent] = Policy(style, checkpoint["beliefs"].get(agent, {}))
        if checkpoint["plan"] is None:
            plan = []
            for index, case in enumerate(cases):
                observation = case.observation
                if observation.arrival > tick or (observation.task_id in traces and
                                                  traces[observation.task_id]["status"] != "WAITING"):
                    continue
                agent = f"{run_id}/agent-{index % 3}"
                decision = policies[agent].choose(observation, self.ledger.account(agent)["effective_headroom"], tick)
                plan.append({"task_id": observation.task_id, "agent_id": agent,
                             "decision": asdict(decision), "tick": tick})
            scheduler = config["scheduler"]
            if scheduler == "priority":
                plan.sort(key=lambda item: (by_id[item["task_id"]].observation.deadline,
                                           -by_id[item["task_id"]].observation.value, item["task_id"]))
            elif scheduler in {"evcost", "central"}:
                def value_key(item):
                    decision = item["decision"]
                    cost = COSTS.get(decision["resource"], 1) + 3
                    value = decision["expected_value"]
                    if scheduler == "central":
                        observation = by_id[item["task_id"]].observation
                        remaining = max(1, observation.deadline - tick)
                        value = value * 100 // remaining
                    return (-value * 10000 // cost, item["task_id"])
                plan.sort(key=value_key)
            elif scheduler == "equal":
                plan.sort(key=lambda item: ((int(item["agent_id"][-1]) - tick) % 3, item["task_id"]))
            if scheduler == "central":
                self._central_plan(plan, by_id, policies, self.ledger.account(run_id)["headroom"], tick,
                                   config["scenario"])
            checkpoint["plan"] = plan
            self._checkpoint(run_id, checkpoint)
        plan = checkpoint["plan"]
        premium_capacity = 0 if config["scenario"] == "throttling" and tick % 3 == 1 else 2
        consultation_capacity = 0 if config["scenario"] == "review-collapse" else 1
        capacities = {"premium": premium_capacity, "consultation": consultation_capacity}
        for trace in traces.values():
            if trace["tick"] == tick and trace["resource"] in capacities and not trace["allocation"]:
                if any(self.ledger.reservation(identity)["state"] in {"DISPATCHED", "SETTLED", "UNRESOLVED"}
                       for identity in trace["attempts"]):
                    capacities[trace["resource"]] -= 1
        auction_id = f"{run_id}/tick-{tick}"
        self.market.open(auction_id, premium_capacity, tick + 2)
        candidates = []
        for item in plan:
            task, agent = item["task_id"], item["agent_id"]
            if task in traces and (traces[task]["status"] != "WAITING" or traces[task]["tick"] == tick):
                continue
            case = by_id[task]
            decision = item["decision"]
            resource = decision["resource"]
            prefix = f"{run_id}/{task}/tick-{tick}"
            trace = {**item, "observation": asdict(case.observation), "attempts": [], "status": "PENDING",
                     "verified": False, "verified_value": 0, "resource": resource, "allocation": None,
                     "proposed_resolution": None, "verification": None}
            try:
                self._charge(f"{prefix}/planning", agent, task, "planning", tick)
                if resource == "wait":
                    trace["status"] = "WAITING"
                elif resource == "defer":
                    trace["status"] = "ABANDONED"
                else:
                    outage = config["scenario"] in {"outage", "retry-pressure"} and tick in {2, 3, 4}
                    data = evidence(case, resource, outage=outage)
                    parameters = {"invoice_cents": data["invoice_cents"], "payments": data["payments"]}
                    operation = "release_payment" if case.observation.mandatory else "reconcile"
                    identity = f"{prefix}/execution"
                    fingerprint = self.control.fingerprint(agent, task, resource, operation, parameters, identity)
                    if case.observation.mandatory:
                        approval_id = f"{prefix}/approval"
                        approval = self.control.approval_request(
                            approval_id, agent, fingerprint, tick + 2,
                            action={"request_id": identity, "task_id": task, "resource": resource,
                                    "operation": operation, "parameters": parameters, "quote": COSTS[resource]})
                        if config["scenario"] != "review-collapse" and approval["state"] == "PENDING":
                            with self.ledger._transaction() as connection:
                                used = connection.execute(
                                    "SELECT count(*) FROM approvals WHERE reviewer = 'simulated-mandatory-reviewer' "
                                    "AND expires_at = ? AND agent_id IN (SELECT id FROM accounts WHERE parent_id = ?)",
                                    (tick + 2, f"{run_id}/workflow")).fetchone()[0]
                            if used < 2:
                                self._charge(f"{prefix}/mandatory_review", agent, task, "mandatory_review", tick)
                                self.control.review(approval_id, "simulated-mandatory-reviewer", approve=True, now=tick)
                        trace["approval_id"] = approval_id
                    self.control.prepare(identity, agent, task, resource, parameters, operation=operation,
                                         now=tick, expires_at=tick + 2)
                    trace["attempts"].append(identity)
                    self.control.prepare(f"{prefix}/verification", agent, task, "verification", {}, now=tick,
                                         expires_at=tick + 2)
                    trace["evidence_source"] = data["source"]
                    trace["outage"] = outage
                    if resource == "premium" and config["scheduler"] == "market":
                        self._charge(f"{prefix}/bidding", agent, task, "bidding", tick)
                        bid_id = f"{prefix}/bid"
                        self.market.bid(bid_id, auction_id, agent, decision["bid"], identity, tick)
                        trace["allocation"] = bid_id
                    candidates.append(trace)
            except (BudgetRejected, Denied, InvalidTransition) as error:
                trace["status"] = "DENIED"
                trace["denial"] = str(error)
                for identity in trace["attempts"]:
                    if self.ledger.reservation(identity)["state"] == "RESERVED":
                        self.ledger.release(identity)
            if trace["status"] != "PENDING":
                try:
                    verification_id = f"{prefix}/verification"
                    if self.ledger.reservation(verification_id)["state"] == "RESERVED":
                        self.ledger.release(verification_id)
                except KeyError:
                    pass
                self._save_trace(run_id, task, trace)
        cleared = {bid["id"]: bid for bid in self.market.clear(auction_id, tick)}
        for trace in candidates:
            task, agent, resource = trace["task_id"], trace["agent_id"], trace["resource"]
            identity = trace["attempts"][0]
            case = by_id[task]
            allocated = True
            if trace["allocation"]:
                allocated = cleared[trace["allocation"]]["state"] in {"ALLOCATED", "DELIVERED"}
            elif resource in capacities:
                allocated = capacities[resource] > 0
                capacities[resource] -= int(allocated)
            if not allocated:
                self.ledger.release(identity)
                trace["status"] = "WAITING"
            else:
                try:
                    ambiguous = trace["outage"] and resource == "premium"
                    result = self.control.execute(identity, agent, now=tick, trusted_capacity=True, ambiguous=ambiguous)
                    if result["reservation"]["state"] in {"UNRESOLVED", "DISPATCHED"}:
                        trace["status"] = "UNRESOLVED"
                        if config["scenario"] == "retry-pressure":
                            for attempt in range(1, 4):
                                retry = f"{identity}/retry-{attempt}"
                                try:
                                    self.control.prepare(retry, agent, task, resource, json.loads(result["parameters"]),
                                                         operation=result["operation"], now=tick)
                                    trace["attempts"].append(retry)
                                    self.control.execute(retry, agent, now=tick, trusted_capacity=True, ambiguous=True)
                                except (BudgetRejected, Denied) as error:
                                    trace["retry_denial"] = str(error)
                                    break
                    else:
                        if trace["allocation"]:
                            self.market.finish(trace["allocation"], delivered=True, now=tick)
                        trace["proposed_resolution"] = result["result"]["resolution"]
                        self.control.execute(f"{run_id}/{task}/tick-{tick}/verification", agent, now=tick,
                                             trusted_capacity=True)
                        trace["verified"] = trace["proposed_resolution"] == case.resolution
                        trace["verification"] = {"correct": trace["verified"], "evaluator_version": VERSION,
                                                 "deadline_met": tick + 1 <= case.observation.deadline}
                        trace["verified_value"] = case.observation.value if trace["verified"] and \
                            trace["verification"]["deadline_met"] else 0
                        trace["status"] = "VERIFIED" if trace["verified_value"] else "FAILED"
                except (BudgetRejected, Denied, InvalidTransition) as error:
                    trace["status"] = "DENIED"
                    trace["denial"] = str(error)
            verification_id = f"{run_id}/{task}/tick-{tick}/verification"
            if trace["verification"] is None:
                try:
                    if self.ledger.reservation(verification_id)["state"] == "RESERVED":
                        self.ledger.release(verification_id)
                except KeyError:
                    pass
            self._save_trace(run_id, task, trace)
        current_traces = self.traces(run_id)
        for trace in current_traces:
            if trace["tick"] == tick and trace["status"] in {"UNRESOLVED", "VERIFIED", "FAILED"}:
                policies[trace["agent_id"]].observe_delivery(trace["resource"], trace["status"] != "UNRESOLVED")
            if trace["tick"] == tick and trace["verification"] is not None:
                policies[trace["agent_id"]].observe(trace["resource"], trace["observation"]["document_status"],
                                                    trace["verified"])
        checkpoint["beliefs"] = {agent: policy.beliefs for agent, policy in policies.items()}
        checkpoint["tick"] += 1
        checkpoint["plan"] = None
        checkpoint["finished"] = len(current_traces) == len(cases) and all(
            trace["status"] != "WAITING" for trace in current_traces
        )
        self._checkpoint(run_id, checkpoint)
        self.market.expire(checkpoint["tick"], scope=run_id)
        return self._snapshot(run_id)

    def complete(self, run_id: str) -> dict:
        while not self.run(run_id)["checkpoint"]["finished"]:
            self.step(run_id)
        return self.snapshot(run_id)

    @staticmethod
    def _central_plan(plan: list[dict], cases: dict, policies: dict, headroom: int, tick: int, scenario: str) -> None:
        """Exact tick-local multiple-choice knapsack using observable estimated utility.

        This is a receding-horizon baseline, not a privileged offline oracle. Planning
        for every candidate is included before allocating execution plus verification.
        """
        budget = max(0, headroom - len(plan) * COSTS["planning"])
        premium_capacity = 0 if scenario == "throttling" and tick % 3 == 1 else 2
        consultation_capacity = 0 if scenario == "review-collapse" else 1
        mandatory_capacity = 0 if scenario == "review-collapse" else 2
        states = {(0, 0, 0, 0): (0, [])}
        for index, item in enumerate(plan):
            observation = cases[item["task_id"]].observation
            if tick >= observation.deadline:
                continue
            options = ["cheap", "premium", "consultation"]
            updated = dict(states)
            for (spent, premium, consultation, mandatory), (utility, chosen) in states.items():
                for resource in options:
                    cost = COSTS[resource] + COSTS["verification"]
                    if observation.mandatory:
                        if scenario == "review-collapse":
                            continue
                        cost += COSTS["mandatory_review"]
                    key = (spent + cost, premium + int(resource == "premium"),
                           consultation + int(resource == "consultation"), mandatory + int(observation.mandatory))
                    if (key[0] > budget or key[1] > premium_capacity or key[2] > consultation_capacity
                            or key[3] > mandatory_capacity):
                        continue
                    estimated = observation.value * policies[item["agent_id"]].probability(
                        resource, observation.document_status) // 10000
                    candidate = utility + estimated
                    if key not in updated or candidate > updated[key][0]:
                        updated[key] = (candidate, [*chosen, (index, resource, estimated)])
            states = updated
        _key, (_value, chosen) = max(states.items(), key=lambda entry: (entry[1][0], -entry[0][0]))
        selected = {index: (resource, estimated) for index, resource, estimated in chosen}
        for index, item in enumerate(plan):
            observation = cases[item["task_id"]].observation
            if index in selected:
                resource, estimated = selected[index]
                item["decision"].update(resource=resource, expected_value=estimated)
            elif tick < observation.deadline and item["decision"]["resource"] != "defer":
                item["decision"]["resource"] = "wait"
            item["decision"]["explanation"]["central_allocator"] = "exact tick-local estimated-utility knapsack"

    def snapshot(self, run_id: str) -> dict:
        with open(self.ledger.path + ".engine.lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_SH)
            try:
                return self._snapshot(run_id)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _snapshot(self, run_id: str) -> dict:
        run = self.run(run_id)
        traces = self.traces(run_id)
        with self.ledger._transaction() as connection:
            holds = [dict(row) for row in connection.execute(
                "SELECT * FROM holds WHERE account_id IN (SELECT id FROM accounts WHERE parent_id = ?) ORDER BY id",
                (f"{run_id}/workflow",),
            )]
            approvals = [dict(row) for row in connection.execute(
                "SELECT * FROM approvals WHERE agent_id IN (SELECT id FROM accounts WHERE parent_id = ?) ORDER BY id",
                (f"{run_id}/workflow",),
            )]
            requests = [dict(row) for row in connection.execute(
                "SELECT requests.*, request_quotes.quote AS quote_metadata FROM requests "
                "LEFT JOIN request_quotes ON requests.id = request_quotes.request_id "
                "WHERE agent_id IN (SELECT id FROM accounts WHERE parent_id = ?) ORDER BY requests.id",
                (f"{run_id}/workflow",))]
        account = self.ledger.account(run_id)
        unresolved = sum(hold["upper_bound"] for hold in holds if hold["state"] in {"DISPATCHED", "UNRESOLVED"})
        categories = {resource: sum(hold["actual"] or 0 for hold in holds if hold["resource"] == resource)
                      for resource in COSTS}
        coordination = sum(categories[resource] for resource in (
            "planning", "bidding", "verification", "mandatory_review"))
        access = [sum(trace["status"] in {"VERIFIED", "FAILED", "UNRESOLVED"} for trace in traces
                      if trace["agent_id"] == f"{run_id}/agent-{index}") for index in range(3)]
        premium_access = [sum(hold["resource"] == "premium" and hold["account_id"] == f"{run_id}/agent-{index}"
                              and hold["state"] in {"DISPATCHED", "UNRESOLVED", "SETTLED"} for hold in holds)
                          for index in range(3)]
        verified_access = [sum(trace["status"] == "VERIFIED" and trace["agent_id"] == f"{run_id}/agent-{index}"
                               for trace in traces) for index in range(3)]
        completed = [trace for trace in traces if trace["verification"] is not None]
        def jain(values):
            return sum(values) ** 2 / (3 * sum(value ** 2 for value in values)) if any(values) else 0
        metrics = {
            "verified_value": sum(trace["verified_value"] for trace in traces),
            "total_task_value": sum(case.observation.value for case in corpus(
                run["config"]["seed"], run["config"]["count"], burst=run["config"]["scenario"] == "burst")),
            "modeled_cost": account["spent"], "coordination_cost": coordination,
            "cost_categories": categories, "planning_bidding_cost": categories["planning"] + categories["bidding"],
            "retry_execution_cost": sum(hold["actual"] or 0 for hold in holds if "/retry-" in hold["id"]),
            "unresolved_exposure": unresolved, "reserved": account["reserved"],
            "verified_tasks": sum(trace["status"] == "VERIFIED" for trace in traces),
            "failed_tasks": sum(trace["status"] == "FAILED" for trace in traces),
            "abandoned_tasks": sum(trace["status"] in {"ABANDONED", "DENIED", "CAPACITY_DENIED"} for trace in traces),
            "denied_tasks": sum(trace["status"] in {"DENIED", "CAPACITY_DENIED"} for trace in traces),
            "waiting_tasks": sum(trace["status"] == "WAITING" for trace in traces),
            "unresolved_tasks": sum(trace["status"] == "UNRESOLVED" for trace in traces),
            "review_demand": len(approvals), "access_by_agent": access,
            "jain_access_index": jain(access), "premium_access_by_agent": premium_access,
            "jain_premium_access_index": jain(premium_access), "jain_verified_outcome_index": jain(verified_access),
            "actual_cash_spend": 0, "unit": "SIM_COST_MICRO",
            "deadline_misses": sum(trace["verified_value"] == 0 for trace in traces)
                               if run["checkpoint"]["finished"] else None,
            "completion_latency_ticks": (sum(trace["tick"] + 1 - trace["observation"]["arrival"] for trace in completed)
                                         / len(completed)) if completed else None,
            "terminal_decision_latency_ticks": sum(trace["tick"] + 1 - trace["observation"]["arrival"]
                                                   for trace in traces) / max(1, len(traces)),
            "premium_utilization": sum(premium_access) / max(1, sum(
                0 if run["config"]["scenario"] == "throttling" and tick % 3 == 1 else 2
                for tick in range(run["checkpoint"]["tick"]))),
        }
        events = [event for event in self.ledger.events()
                  if event["account_id"] == run_id or event["account_id"].startswith(f"{run_id}/")]
        market = self.market.snapshot()
        market["bids"] = [bid for bid in market["bids"] if bid["agent_id"].startswith(f"{run_id}/")]
        market["auctions"] = [auction for auction in market["auctions"] if auction["id"].startswith(f"{run_id}/")]
        def normalize(value):
            if isinstance(value, dict):
                return {normalize(key): normalize(item) for key, item in value.items() if key != "request_hash"}
            if isinstance(value, list):
                return [normalize(item) for item in value]
            if isinstance(value, str) and (value == run_id or value.startswith(f"{run_id}/")):
                return "$run" + value[len(run_id):]
            return value
        digest = stable_digest(normalize({"config": run["config"], "traces": traces, "holds": holds,
                                          "beliefs": run["checkpoint"]["beliefs"], "metrics": metrics,
                                          "bids": market["bids"]}))
        return {"run": run, "account": account, "metrics": metrics, "digest": digest,
                "agents": [self.ledger.account(f"{run_id}/agent-{index}") for index in range(3)],
                "traces": traces, "holds": holds, "events": events, "approvals": approvals,
                "requests": requests,
                "market": market, "audit": self.ledger.audit()}
