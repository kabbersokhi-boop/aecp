"""Development-only tool, policy-boundary and multi-step recovery regressions."""

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from aecp.control import ControlPlane, Denied
from aecp.ledger import BudgetRejected, IdempotencyConflict, Ledger
from aecp.nim import NimAdapter
from aecp.semantic import SemanticTasks
from aecp.semantic_workload import corpus


class SemanticTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "state.db"
        self.control = ControlPlane(Ledger(self.path))
        self.control.ledger.create_account("agent", 10000, unit="SIM_COST_MICRO")
        self.registry = SemanticTasks(self.control)
        self.registry.register("agent", "development")

    def case(self, kind):
        return next(case for case in corpus("development") if case.truth["semantic_kind"] == kind)

    def act(self, case, action, identity="attempt", **values):
        return self.registry.action("agent", {"task_id": case.observation["task_id"], "request_id": identity,
                                              "action": action, "reason": "development fixture", **values})

    def test_fetch_reveals_only_purchased_documents_and_is_idempotent(self):
        case = self.case("fetch")
        before = self.registry.view("agent", case.observation["task_id"])
        result = self.act(case, "fetch", source="remittance")
        self.assertEqual(result, self.act(case, "fetch", source="remittance"))
        after = self.registry.view("agent", case.observation["task_id"])
        self.assertGreater(len(after["documents"]), len(before["documents"]))
        self.assertEqual(after["fetched_sources"], ["remittance"])
        self.assertEqual(self.control.ledger.account("agent")["spent"], 6)
        self.assertNotIn("truth", json.dumps(after))

    def test_context_mismatch_fails_in_control_plane_without_gateway(self):
        case = self.case("fetch")
        with self.assertRaises(Denied):
            self.control.prepare("malicious", "agent", case.observation["task_id"], "semantic_fetch",
                                 {"agent": "victim", "case": case.observation["task_id"], "source": "remittance"})
        self.assertEqual(self.control.ledger.account("agent")["reserved"], 0)

    def test_terminal_evaluation_failure_recovers_without_double_spend(self):
        case = self.case("direct")
        with patch.object(self.registry, "evaluate", side_effect=RuntimeError("controlled evaluator crash")):
            with self.assertRaises(RuntimeError):
                self.act(case, "finalize", payment_ids=case.truth["payment_ids"])
        spent = self.control.ledger.account("agent")["spent"]
        self.assertEqual(self.registry.view("agent", case.observation["task_id"])["status"], "OPEN")
        self.registry = SemanticTasks(ControlPlane(Ledger(self.path)))
        self.act(case, "finalize", payment_ids=case.truth["payment_ids"])
        self.assertEqual(self.control.ledger.account("agent")["spent"], spent)
        self.assertEqual(self.registry.view("agent", case.observation["task_id"])["status"], "FINALIZE")

    def test_oversized_composed_identity_does_not_leave_pending_work(self):
        case = self.case("direct")
        with self.assertRaises(ValueError):
            self.act(case, "check", identity="a" * 256, payment_ids=[])
        self.assertEqual(self.registry.view("agent", case.observation["task_id"])["steps_used"], 0)

    def test_stale_duplicate_cannot_downgrade_a_completed_workflow(self):
        case = self.case("direct")
        paused = threading.Event()
        release = threading.Event()
        execute = self.control.execute
        results = []

        def stale_execution(identity, agent):
            result = execute(identity, agent)
            if identity.endswith("/planning"):
                return result
            paused.set()
            if not release.wait(5):
                raise RuntimeError("test synchronization failed")
            return {**result, "result": None, "receipt": None,
                    "reservation": {**result["reservation"], "state": "DISPATCHED"}}

        body = {"request_id": "duplicate", "task_id": case.observation["task_id"], "action": "finalize",
                "reason": "Same immutable action", "payment_ids": case.truth["payment_ids"]}
        with patch.object(self.control, "execute", side_effect=stale_execution):
            thread = threading.Thread(target=lambda: results.append(self.registry.action("agent", body)))
            thread.start()
            try:
                self.assertTrue(paused.wait(5))
                independent = SemanticTasks(ControlPlane(Ledger(self.path)))
                completed = independent.action("agent", body)
            finally:
                release.set()
                thread.join(timeout=5)
        self.assertEqual(results, [completed])
        self.assertNotIn("unresolved", results[0])
        self.assertEqual(self.registry.view("agent", case.observation["task_id"])["status"], "FINALIZE")

    def test_arithmetic_correct_but_wrong_links_are_not_verified(self):
        case = self.case("replacement")
        target = case.truth["payment_ids"]
        amounts = {payment["id"]: payment["amount_cents"] for payment in case.observation["payments"]}
        alternative = next(identity for identity in amounts if identity not in target)
        replaced = next(identity for identity in target if amounts[identity] == amounts[alternative])
        wrong = [alternative if identity == replaced else identity for identity in target]
        self.act(case, "finalize", payment_ids=wrong)
        outcome = next(item["outcome"] for item in self.registry.snapshot()["cases"]
                       if item["task"] == case.observation["task_id"])
        self.assertTrue(outcome["resolution_correct"])
        self.assertFalse(outcome["linking_correct"])
        self.assertFalse(outcome["verified"])

    def test_optional_consultation_does_not_grant_mandatory_approval(self):
        case = self.case("conflict")
        result = self.act(case, "consult", "consult")
        self.assertFalse(result["resource_result"]["mandatory_approval_granted"])
        with self.assertRaises(Denied):
            self.act(case, "finalize", "forbidden", payment_ids=case.truth["payment_ids"])
        self.act(case, "escalate", "safe")
        self.assertEqual(self.registry.view("agent", case.observation["task_id"])["status"], "ESCALATE")

    def test_unfunded_consultation_does_not_consume_review_capacity(self):
        self.control.ledger.create_account("poor", 1, unit="SIM_COST_MICRO")
        self.registry.register("poor", "development")
        task = self.case("po_split").observation["task_id"]
        with self.assertRaises(BudgetRejected):
            self.registry.action("poor", {"task_id": task, "request_id": "poor", "action": "consult", "reason": "test"})
        self.assertEqual(self.registry.view("poor", task)["consultations_remaining"], 2)
        self.assertEqual(self.control.ledger.account("poor")["reserved"], 0)

    def test_changed_duplicate_never_changes_original_action(self):
        case = self.case("direct")
        original = self.act(case, "check", payment_ids=[])
        with self.assertRaises(IdempotencyConflict):
            self.act(case, "check", payment_ids=case.truth["payment_ids"])
        self.assertEqual(original, self.act(case, "check", payment_ids=[]))

    def test_crash_after_receipt_recovers_same_inference_context_once(self):
        from test_nim import FakeTransport
        transport = FakeTransport()
        transport.response["choices"][0]["message"]["content"] = json.dumps({"action": "abstain", "payment_ids": [],
            "source": "none", "confidence": "low", "reason": "insufficient evidence"})
        self.control.adapters["nim_chat"] = NimAdapter("configured-model", transport)
        case = self.case("po_split")
        settle = self.control.ledger.settle

        def fail_on_inference(identity, actual):
            if not identity.endswith("/planning"):
                raise RuntimeError("fixture process failure after durable receipt")
            return settle(identity, actual)

        with (patch.object(self.control.ledger, "settle", side_effect=fail_on_inference),
              self.assertRaises(RuntimeError)):
            self.act(case, "infer")
        recovered = ControlPlane(Ledger(self.path))
        recovered.adapters["nim_chat"] = NimAdapter("configured-model", transport)
        self.registry = SemanticTasks(recovered)
        result = self.act(case, "infer")
        self.assertEqual(result["reservation"]["state"], "SETTLED")
        self.assertEqual(transport.calls, 1)
