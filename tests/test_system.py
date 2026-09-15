"""Negative, lifecycle, research and restart checks for the implemented vertical slice."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

from aecp.control import ControlPlane, Denied, LocalCostModel, Quote, Receipt
from aecp.engine import SCHEDULERS, Engine
from aecp.ledger import MAX_AMOUNT, BudgetRejected, IdempotencyConflict, InvalidTransition, Ledger
from aecp.market import Market
from aecp.policies import Policy
from aecp.workload import corpus, evidence, resolve


class SystemCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "state.sqlite3"
        self.ledger = Ledger(self.path)
        self.ledger.create_account("run", 100, unit="SIM_COST_MICRO")
        self.ledger.create_account("workflow", 100, unit="SIM_COST_MICRO", parent_id="run")
        for agent in ("alpha", "beta"):
            self.ledger.create_account(agent, 100, unit="SIM_COST_MICRO", parent_id="workflow")

    def hold(self, identity="hold", agent="alpha", amount=40, expires_at=None):
        return self.ledger.reserve(agent, identity, amount, task_id="case", operation_id="reconcile",
                                   request_hash=identity, expires_at=expires_at, resource="premium")


class HierarchyTests(SystemCase):
    def test_siblings_race_one_parent_cap(self):
        def reserve(index):
            try:
                self.hold(str(index), ("alpha", "beta")[index % 2], 7)
                return True
            except BudgetRejected:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(reserve, range(40))), 14)
        self.assertEqual(self.ledger.account("run")["reserved"], 98)
        self.assertEqual(self.ledger.account("workflow")["reserved"], 98)
        self.assertTrue(self.ledger.audit()["consistent"])

    def test_descendant_cannot_mint_and_units_cannot_cross(self):
        self.ledger.create_account("grandchild", 100, unit="SIM_COST_MICRO", parent_id="alpha")
        self.hold("leaf", "grandchild", 100)
        with self.assertRaises(BudgetRejected):
            self.hold("sibling", "beta", 1)
        with self.assertRaises(BudgetRejected):
            self.ledger.create_account("wrong-unit", 50, unit="MARKET_CREDIT", parent_id="alpha")
        with self.assertRaises(IdempotencyConflict):
            self.ledger.create_account("grandchild", 100, unit="SIM_COST_MICRO", parent_id="beta")

    def test_parent_breach_blocks_sibling_dispatch_and_records_full_cost(self):
        self.hold("first", "alpha", 40)
        self.hold("second", "beta", 40)
        self.ledger.mark_dispatched("first")
        self.ledger.settle("first", 101)
        self.assertEqual(self.ledger.account("run")["spent"], 101)
        with self.assertRaises(BudgetRejected):
            self.ledger.mark_dispatched("second")
        self.ledger.release("second")
        self.assertTrue(self.ledger.audit()["consistent"])
        self.assertFalse(self.ledger.audit()["within_funding"])

    def test_cumulative_bound_breach_beyond_sqlite_integer_is_recorded_exactly(self):
        self.ledger.create_account("large", MAX_AMOUNT, unit="SIM_COST_MICRO")
        for identity in ("invoice-one", "invoice-two"):
            self.ledger.reserve("large", identity, 1, task_id="large-case", operation_id="execute",
                                request_hash=identity)
            self.ledger.mark_dispatched(identity)
        self.ledger.settle("invoice-one", MAX_AMOUNT)
        self.ledger.settle("invoice-two", MAX_AMOUNT)
        self.assertEqual(self.ledger.account("large")["spent"], 2 * MAX_AMOUNT)
        self.assertEqual(self.ledger.account("large")["headroom"], -MAX_AMOUNT)
        self.assertTrue(self.ledger.audit()["consistent"])
        self.assertFalse(self.ledger.audit()["within_funding"])
        with self.ledger._transaction() as connection:
            row = connection.execute(
                "SELECT typeof(spent), typeof(spent_high) FROM accounts WHERE id='large'").fetchone()
            self.assertEqual(tuple(row), ("integer", "text"))

    def test_expiry_only_releases_predispatch(self):
        self.hold("pending", amount=20, expires_at=2)
        self.hold("unknown", amount=30, expires_at=2)
        self.ledger.mark_dispatched("unknown", now=1)
        self.ledger.mark_unresolved("unknown")
        self.assertEqual(self.ledger.expire(2), 1)
        self.assertEqual(self.ledger.account("run")["reserved"], 30)
        self.assertEqual(Ledger(self.path).reservation("unknown")["state"], "UNRESOLVED")

    def test_expired_dispatch_is_denied_before_sweep(self):
        self.hold(expires_at=2)
        with self.assertRaises(InvalidTransition):
            self.ledger.mark_dispatched("hold", now=2)

    def test_independent_logical_clocks_do_not_expire_other_runs(self):
        self.hold("waiting", expires_at=2)
        self.ledger.create_account("other-run", 100, unit="SIM_COST_MICRO")
        self.ledger.expire(1000, scope="other-run")
        self.assertEqual(self.ledger.reservation("waiting")["state"], "RESERVED")
        self.assertEqual(self.ledger.expire(2, scope="run"), 1)

    def test_winding_down_blocks_creation_and_dispatch_but_allows_settlement(self):
        self.hold("one", amount=20)
        self.hold("two", amount=20)
        self.ledger.mark_dispatched("one")
        self.ledger.set_lifecycle("workflow", "WINDING_DOWN")
        self.ledger.settle("one", 10)
        with self.assertRaises(BudgetRejected):
            self.ledger.mark_dispatched("two")
        with self.assertRaises(BudgetRejected):
            self.ledger.create_account("new", 10, unit="SIM_COST_MICRO", parent_id="beta")
        self.ledger.release("two")
        self.assertTrue(self.ledger.audit()["consistent"])

    def test_legacy_schema_migrates_without_losing_holds(self):
        legacy = Path(self.directory.name) / "legacy.db"
        with closing(sqlite3.connect(legacy)) as connection:
            connection.executescript("""
                CREATE TABLE accounts(id TEXT PRIMARY KEY, unit TEXT, funded INTEGER, spent INTEGER DEFAULT 0,
                                      reserved INTEGER DEFAULT 0, status TEXT DEFAULT 'ACTIVE');
                CREATE TABLE holds(id TEXT PRIMARY KEY, account_id TEXT, task_id TEXT, operation_id TEXT,
                                   request_hash TEXT, upper_bound INTEGER, state TEXT, actual INTEGER);
                INSERT INTO accounts VALUES ('old', 'SIM_COST_MICRO', 100, 0, 40, 'ACTIVE');
                INSERT INTO holds VALUES ('pending', 'old', 'case', 'op', 'hash', 40, 'UNRESOLVED', NULL);
            """)
        ledger = Ledger(legacy)
        self.assertEqual(ledger.account("old")["reserved"], 40)
        self.assertIsNone(ledger.account("old")["parent_id"])
        ledger.settle("pending", 30)
        self.assertTrue(ledger.audit()["consistent"])


class MarketTests(SystemCase):
    def setUp(self):
        super().setUp()
        self.market = Market(self.ledger)
        self.market.endow("treasury", 100)
        self.market.transfer("endow-alpha", "treasury", "alpha", 50)
        self.market.transfer("endow-beta", "treasury", "beta", 50)
        self.market.open("auction", 1, 4)

    def bid(self, identity, agent, price):
        self.hold(identity, agent, 14, expires_at=4)
        return self.market.bid(identity, "auction", agent, price, identity, 0)

    def test_first_price_ties_and_conservation(self):
        self.bid("bid-b", "beta", 25)
        self.bid("bid-a", "alpha", 25)
        bids = self.market.clear("auction", 1)
        self.assertEqual([bid["id"] for bid in bids if bid["state"] == "ALLOCATED"], ["bid-a"])
        self.ledger.mark_dispatched("bid-a", now=1)
        self.ledger.settle("bid-a", 14)
        self.market.finish("bid-a", delivered=True, now=1)
        self.market.finish("bid-a", delivered=True, now=1)
        snapshot = self.market.snapshot()
        self.assertTrue(snapshot["consistent"])
        self.assertEqual(snapshot["issued"], snapshot["total"])
        self.assertEqual(next(wallet["balance"] for wallet in snapshot["wallets"]
                              if wallet["id"] == "market:operator"), 25)
        self.assertEqual(self.ledger.account("run")["spent"], 14)

    def test_escrow_cannot_be_reused_across_auctions(self):
        self.bid("first", "alpha", 40)
        self.market.open("second", 1, 4)
        self.hold("second-hold", "alpha", 14, expires_at=4)
        with self.assertRaises(BudgetRejected):
            self.market.bid("second-bid", "second", "alpha", 20, "second-hold", 0)
        self.assertTrue(self.market.snapshot()["consistent"])

    def test_operating_reservation_is_required_and_owned(self):
        self.hold("wrong", "alpha", 14)
        with self.assertRaises(BudgetRejected):
            self.market.bid("fraud", "auction", "beta", 20, "wrong", 0)
        self.ledger.release("wrong")
        with self.assertRaises(BudgetRejected):
            self.market.bid("released", "auction", "alpha", 20, "wrong", 0)

    def test_ambiguous_delivery_retains_escrow_after_expiry(self):
        self.bid("unknown", "alpha", 30)
        self.market.clear("auction", 0)
        self.ledger.mark_dispatched("unknown")
        self.ledger.mark_unresolved("unknown")
        self.market.expire(10)
        with self.assertRaises(InvalidTransition):
            self.market.finish("unknown", delivered=False, now=10)
        self.assertEqual(self.ledger.account("run")["reserved"], 14)
        self.assertEqual(self.market.snapshot()["bids"][0]["state"], "ALLOCATED")

    def test_hoarding_expires_and_refunds_once(self):
        self.bid("hoard", "alpha", 50)
        self.market.clear("auction", 0)
        self.market.expire(4)
        self.market.expire(4)
        self.assertEqual(self.ledger.account("run")["reserved"], 0)
        self.assertEqual(self.market.snapshot()["bids"][0]["state"], "EXPIRED")
        self.assertTrue(self.market.snapshot()["consistent"])

    def test_cancel_requires_owner_and_refunds(self):
        self.bid("cancel", "alpha", 40)
        with self.assertRaises(BudgetRejected):
            self.market.cancel("cancel", "beta")
        self.market.cancel("cancel", "alpha")
        self.market.cancel("cancel", "alpha")
        self.assertTrue(self.market.snapshot()["consistent"])

    def test_escrow_wallets_cannot_be_transferred_by_generic_api(self):
        self.bid("locked", "alpha", 40)
        with self.assertRaises(BudgetRejected):
            self.market.transfer("steal", "escrow:locked", "beta", 40)
        self.assertTrue(self.market.snapshot()["consistent"])


class ControlTests(SystemCase):
    def setUp(self):
        super().setUp()
        self.control = ControlPlane(self.ledger)
        self.control.register_task("alpha", "case", "reconcile")
        self.control.register_task("alpha", "protected", "release_payment")
        self.parameters = {"invoice_cents": 100, "payments": [100]}

    def test_unknown_task_and_wrong_operation_fail_at_trusted_primitive(self):
        for task, operation in (("unknown", "reconcile"), ("protected", "reconcile")):
            with self.subTest(task=task), self.assertRaises(Denied):
                self.control.prepare("forbidden", "alpha", task, "cheap", self.parameters, operation=operation)
        self.assertEqual(self.ledger.account("run")["reserved"], 0)

    def test_request_fingerprint_prevents_changed_duplicate(self):
        self.control.prepare("request", "alpha", "case", "cheap", self.parameters)
        self.control.execute("request", "alpha")
        with self.assertRaises(IdempotencyConflict):
            self.control.prepare("request", "alpha", "case", "cheap", {"invoice_cents": 100, "payments": [99]})
        with self.assertRaises(Denied):
            self.control.request("request", "beta")

    def test_exact_approval_cannot_authorize_changed_or_retried_operation(self):
        fingerprint = self.control.fingerprint("alpha", "protected", "cheap", "release_payment",
                                               self.parameters, "request")
        self.control.approval_request("approval", "alpha", fingerprint, 3)
        self.control.review("approval", "reviewer", approve=True, now=0)
        self.control.prepare("request", "alpha", "protected", "cheap", self.parameters,
                             operation="release_payment", now=0)
        with self.assertRaises(Denied):
            self.control.prepare("retry", "alpha", "protected", "cheap", self.parameters,
                                 operation="release_payment", now=0)
        with self.assertRaises(Denied):
            self.control.execute("request", "alpha", now=3)
        self.assertEqual(self.ledger.reservation("request")["state"], "RESERVED")

    def test_approval_absence_and_self_approval_cannot_be_bought(self):
        with self.assertRaises(Denied):
            self.control.prepare("request", "alpha", "case", "cheap", self.parameters, operation="release_payment")
        fingerprint = self.control.fingerprint("alpha", "case", "cheap", "release_payment", self.parameters, "request")
        self.control.approval_request("approval", "alpha", fingerprint, 3)
        with self.assertRaises(Denied):
            self.control.review("approval", "alpha", approve=True, now=0)

    def test_process_crash_after_dispatch_keeps_liability_without_reexecution(self):
        script = """from aecp.control import ControlPlane
from aecp.ledger import Ledger
import os,sys
control=ControlPlane(Ledger(sys.argv[1]))
control.prepare('crashed','alpha','case','cheap',{'invoice_cents':100,'payments':[100]})
control.ledger.mark_dispatched('crashed')
os._exit(23)
"""
        result = subprocess.run([sys.executable, "-c", script, str(self.path)], env=os.environ, timeout=10)
        self.assertEqual(result.returncode, 23)
        recovered = ControlPlane(Ledger(self.path))
        with patch.object(recovered.adapter, "execute", side_effect=AssertionError("must not replay")):
            self.assertEqual(recovered.execute("crashed", "alpha")["reservation"]["state"], "UNRESOLVED")
        self.assertEqual(self.ledger.account("run")["reserved"], 4)

    def test_crash_after_persisted_result_settles_without_reexecution(self):
        self.control.prepare("request", "alpha", "case", "cheap", self.parameters)
        with patch.object(self.ledger, "settle", side_effect=RuntimeError("worker died")):
            with self.assertRaises(RuntimeError):
                self.control.execute("request", "alpha")
        recovered = ControlPlane(Ledger(self.path))
        with patch.object(recovered.adapter, "execute", side_effect=AssertionError("must not replay")):
            result = recovered.execute("request", "alpha")
        self.assertEqual(result["reservation"]["state"], "SETTLED")
        self.assertEqual(self.ledger.account("run")["spent"], 4)

    def test_local_cost_is_allocated_not_cash_and_rounds_up(self):
        cost = LocalCostModel().allocated_cost(1, 0, 0)
        self.assertEqual(cost["allocated_cost"], 1)
        self.assertIsNone(cost["actual_cash_spend"])
        with self.assertRaises(ValueError):
            LocalCostModel().allocated_cost(0.1, 0, 0)

    def test_provider_exception_remains_an_unresolved_liability(self):
        self.control.prepare("request", "alpha", "case", "cheap", self.parameters)
        with patch.object(self.control.adapter, "execute", side_effect=RuntimeError("provider failure")):
            result = self.control.execute("request", "alpha")
        self.assertEqual(result["reservation"]["state"], "UNRESOLVED")
        self.assertEqual(self.ledger.account("run")["reserved"], 4)

    def test_market_credits_cannot_pay_simulated_execution(self):
        self.ledger.create_account("credits", 100, unit="MARKET_CREDIT")
        with self.assertRaises(Denied):
            self.control.prepare("request", "credits", "case", "cheap", self.parameters)

    def test_trusted_receipt_releases_unused_quote_and_records_breaches(self):
        self.control.prepare("partial", "alpha", "case", "cheap", self.parameters)
        with patch.object(self.control.adapter, "execute", return_value=Receipt({"completed": True}, 2)):
            result = self.control.execute("partial", "alpha")
        self.assertEqual(result["reservation"]["actual"], 2)
        self.assertEqual(result["receipt"]["actual_units"], 2)
        self.control.prepare("breach", "alpha", "case", "cheap", self.parameters)
        with patch.object(self.control.adapter, "execute", return_value=Receipt({"completed": True}, 101)):
            self.control.execute("breach", "alpha")
        self.assertEqual(self.ledger.account("run")["spent"], 103)
        self.assertEqual(self.ledger.account("run")["status"], "FROZEN")
        self.assertTrue(self.ledger.audit()["consistent"])

    def test_quote_change_requires_new_authorization_before_dispatch(self):
        self.control.prepare("request", "alpha", "case", "cheap", self.parameters)
        with patch.object(self.control.adapter, "quote", return_value=Quote(8, version="price.v2")):
            with self.assertRaises(Denied):
                self.control.execute("request", "alpha")
        self.assertEqual(self.ledger.reservation("request")["state"], "RESERVED")


class EconomyTests(unittest.TestCase):
    def test_central_plans_mandatory_capacity_before_execution(self):
        cases = {f"task-{index}": replace(case, observation=replace(case.observation, mandatory=True, deadline=100))
                 for index, case in enumerate(corpus(7, count=3))}
        for scenario, capacity in (("ordinary", 2), ("review-collapse", 0)):
            plan = [{"task_id": task, "agent_id": "agent", "decision": {"resource": "cheap", "explanation": {}}}
                    for task in cases]
            Engine._central_plan(plan, cases, {"agent": Policy("adaptive")}, 1000, 0, scenario)
            self.assertEqual(sum(item["decision"]["resource"] not in {"wait", "defer"} for item in plan), capacity)

    def test_hidden_truth_is_absent_from_observations(self):
        for case in corpus(7):
            self.assertNotIn("resolution", asdict(case.observation))
            self.assertNotIn("seed", asdict(case.observation))
            self.assertNotIn("bank_payments", asdict(case.observation))
        differences = [case for case in corpus(7) if resolve(case.observation.invoice_cents,
                       case.observation.visible_payments) != case.resolution]
        self.assertTrue(differences)
        for case in differences:
            premium = evidence(case, "premium")
            self.assertEqual(resolve(premium["invoice_cents"], premium["payments"]), case.resolution)

    def test_economic_digest_ignores_run_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = Engine(Path(directory) / "state.db")
            engine.create("first", count=3)
            first = engine.complete("first")
            engine.create("second", count=3)
            second = engine.complete("second")
            self.assertEqual(first["digest"], second["digest"])

    def test_observed_feedback_changes_adaptive_action(self):
        observation = next(case.observation for case in corpus(7)
                           if case.observation.document_status == "partial" and case.observation.value > 100)
        policy = Policy("adaptive")
        self.assertEqual(policy.choose(observation, 100, observation.arrival).resource, "premium")
        for _trial in range(60):
            policy.observe("cheap", "partial", True)
        self.assertEqual(policy.choose(observation, 100, observation.arrival).resource, "cheap")
        self.assertIn("cheap:partial", policy.beliefs)
        self.assertEqual(Policy("conservative").choose(observation, 100, observation.arrival).resource, "defer")

    def test_observed_provider_unavailability_changes_resource_choice(self):
        observation = next(case.observation for case in corpus(7)
                           if case.observation.document_status == "partial" and case.observation.value > 100)
        policy = Policy("adaptive")
        self.assertEqual(policy.choose(observation, 100, observation.arrival).resource, "premium")
        for _attempt in range(4):
            policy.observe_delivery("premium", False)
        self.assertEqual(policy.choose(observation, 100, observation.arrival).resource, "consultation")

    def run_engine(self, path, **config):
        engine = Engine(path)
        engine.create("trial", **config)
        return engine.complete("trial")

    def test_resume_in_separate_process_matches_uninterrupted(self):
        with tempfile.TemporaryDirectory() as directory:
            resumed = Path(directory) / "resumed.db"
            command = [sys.executable, "-m", "aecp", "demo", "--db", str(resumed), "--run-id", "trial",
                       "--scenario", "outage"]
            subprocess.run([*command, "--steps", "3"], check=True, capture_output=True, timeout=20)
            subprocess.run(command, check=True, capture_output=True, timeout=20)
            actual = Engine(resumed).snapshot("trial")
            expected = self.run_engine(Path(directory) / "reference.db", scenario="outage")
            self.assertEqual(actual["digest"], expected["digest"])
            self.assertGreater(actual["metrics"]["unresolved_exposure"], 0)

    def test_process_death_inside_tick_recovers_durable_phases(self):
        with tempfile.TemporaryDirectory() as directory:
            expected = self.run_engine(Path(directory) / "reference.db", scenario="burst", budget=300)
            for owner, method in (("ControlPlane", "prepare"), ("Market", "clear"),
                                  ("ControlPlane", "execute"), ("Engine", "_save_trace"),
                                  ("Engine", "_checkpoint")):
                with self.subTest(phase=f"{owner}.{method}"):
                    path = Path(directory) / f"{owner}-{method}.db"
                    engine = Engine(path)
                    engine.create("trial", scenario="burst", budget=300)
                    script = f"""import os,sys
from aecp.engine import Engine
from aecp.control import ControlPlane
from aecp.market import Market
original={owner}.{method}
def crash(*args,**kwargs):
    result=original(*args,**kwargs)
    os._exit(23)
{owner}.{method}=crash
Engine(sys.argv[1]).step('trial')
"""
                    killed = subprocess.run([sys.executable, "-c", script, str(path)], timeout=20)
                    self.assertEqual(killed.returncode, 23)
                    actual = Engine(path).complete("trial")
                    self.assertEqual(actual["digest"], expected["digest"])
                    self.assertTrue(actual["audit"]["consistent"])

    def test_all_baselines_share_corpus_and_respect_funding(self):
        with tempfile.TemporaryDirectory() as directory:
            hashes = set()
            for scheduler in SCHEDULERS:
                result = self.run_engine(Path(directory) / f"{scheduler}.db", scheduler=scheduler,
                                         budget=180, scenario="burst")
                hashes.add(result["run"]["config"]["corpus_hash"])
                self.assertTrue(result["audit"]["within_funding"])
                self.assertGreater(result["metrics"]["coordination_cost"], 0)
                self.assertTrue(result["market"]["consistent"])
                self.assertEqual(result["metrics"]["verified_tasks"] + result["metrics"]["failed_tasks"] +
                                 result["metrics"]["abandoned_tasks"] + result["metrics"]["unresolved_tasks"], 36)
            self.assertEqual(len(hashes), 1)

    def test_review_collapse_blocks_exact_mandatory_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_engine(Path(directory) / "collapse.db", scenario="review-collapse")
            protected = [trace for trace in result["traces"] if trace["observation"]["mandatory"]]
            self.assertTrue(protected)
            self.assertTrue(all(trace["status"] == "DENIED" and trace["denial"] == "APPROVAL_REQUIRED"
                                for trace in protected))
            self.assertTrue(all(approval["state"] == "PENDING" for approval in result["approvals"]))


if __name__ == "__main__":
    unittest.main()
