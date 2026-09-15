"""State-aware schemas, governance and consumer decisions on development evidence only."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aecp.control import ControlPlane, Denied
from aecp.interpretation import parameters, response_format
from aecp.ledger import Ledger
from aecp.nim import NimAdapter
from aecp.semantic import SemanticTasks
from aecp.structured import schema_identity

specification = importlib.util.spec_from_file_location(
    "policy_v3", Path(__file__).parents[1] / "examples/semantic_consumer/policy_v3.py")
policy = importlib.util.module_from_spec(specification)
specification.loader.exec_module(policy)


class FakeTransport:
    base_url = "https://integrate.api.nvidia.com/v1"

    def request(self, path, body):
        return {"model": body["model"], "choices": [{"message": {"content": json.dumps({
            "assessment": "uncertain", "payment_ids": [], "document_ids": [], "confidence": "low",
            "summary": "Protocol test only; not quality evidence."})}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 40, "total_tokens": 140}}


class InterpretationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.control = ControlPlane(Ledger(Path(directory.name) / "test.db"))
        self.control.ledger.create_account("agent", 20000, unit="SIM_COST_MICRO")
        self.control.adapters["nim_chat"] = NimAdapter("fake-model", FakeTransport())
        self.tasks = SemanticTasks(self.control)
        self.tasks.register("agent", "development", workload="v3")

    def view(self, predicate):
        return next(view for view in self.tasks.observations("agent") if predicate(view))

    def act(self, view, action, identity, **parameters):
        return self.tasks.action("agent", {"task_id": view["task_id"], "request_id": identity,
                                           "action": action, "reason": "development test", **parameters})

    def test_schema_only_visible_identities_and_no_workflow_authority(self):
        view = self.view(lambda view: bool(view["available_sources"]))
        schema = response_format(view)
        encoded = json.dumps(schema)
        self.assertNotIn('"action"', encoded)
        self.assertNotIn('"source"', encoded)
        self.assertNotIn("allocation", schema["json_schema"]["schema"]["properties"]["document_ids"]["items"]["enum"])
        before = schema_identity(schema)
        self.act(view, "fetch", "fetch", source="remittance")
        after = self.tasks.view("agent", view["task_id"])
        self.assertNotEqual(before, schema_identity(response_format(after)))
        self.assertNotIn("remittance", after["valid_actions"].get("fetch", {}).get("sources", []))
        with self.assertRaises(Denied):
            self.act(after, "fetch", "repeat", source="remittance")

    def test_snapshot_labels_persisted_workloads_without_relabeling_history(self):
        from aecp.semantic_corpus_v3 import VERSION
        snapshot = self.tasks.snapshot()
        self.assertEqual(snapshot["workload"], VERSION)
        self.assertEqual(snapshot["workloads"], [VERSION])
        self.control.ledger.create_account("legacy", 4000, unit="SIM_COST_MICRO")
        self.tasks.register("legacy", "development")
        snapshot = self.tasks.snapshot()
        self.assertEqual(snapshot["workload"], "mixed")
        self.assertEqual(snapshot["workloads"], ["semantic-finops.v2.1", VERSION])

    def test_exact_schema_changes_quote_fingerprint(self):
        view = self.view(lambda view: bool(view["available_sources"]))
        original = parameters(view, "fake-model")
        self.control.prepare("immutable", "agent", view["task_id"], "nim_chat", original)
        self.act(view, "fetch", "fetch", source="remittance")
        changed = parameters(self.tasks.view("agent", view["task_id"]), "fake-model")
        from aecp.ledger import IdempotencyConflict
        with self.assertRaises(IdempotencyConflict):
            self.control.prepare("immutable", "agent", view["task_id"], "nim_chat", changed)

    def test_evaluator_labels_follow_persisted_workload_without_changing_grades(self):
        self.control.ledger.create_account("legacy", 4000, unit="SIM_COST_MICRO")
        self.tasks.register("legacy", "development")
        for agent, label in (("legacy", "semantic-hidden-allocation.v2.1"),
                             ("agent", "semantic-hidden-allocation.v3.frozen-1")):
            view = next(view for view in self.tasks.observations(agent)
                        if not view["mandatory_review"] and view["reviewer_can_help"]
                        and not view["available_sources"])
            case = self.tasks.case(agent, view["task_id"])
            truth = case["truth"]
            for correct in (True, False):
                answer = {"resource_result": {"payment_ids": truth["payment_ids"] if correct else [],
                                               "resolution": truth["resolution"]}}
                graded = self.tasks.evaluate(agent, view["task_id"], "finalize", answer)
                self.assertEqual(graded.pop("evaluator"), label)
                self.assertEqual(graded["verified"], correct)
                legacy_case = {**case, "observation": {**case["observation"],
                                                       "workload_version": "semantic-finops.v2.1"}}
                with patch.object(self.tasks, "case", return_value=legacy_case):
                    unchanged = self.tasks.evaluate(agent, view["task_id"], "finalize", answer)
                self.assertEqual(unchanged.pop("evaluator"), "semantic-hidden-allocation.v2.1")
                self.assertEqual(graded, unchanged)

    def test_mandatory_review_has_no_inference_or_finalize_action(self):
        view = self.view(lambda view: view["mandatory_review"])
        self.assertNotIn("finalize", view["valid_actions"])
        self.assertNotIn("infer", view["valid_actions"])
        for mode in policy.POLICIES:
            self.assertEqual(policy.choose(view, mode, [])["action"], "escalate")
        with self.assertRaises(Denied):
            self.act(view, "finalize", "injected-approval", payment_ids=[])
        self.assertEqual(self.control.ledger.account("agent")["spent"], 0)

    def test_governed_inference_bounded_and_usage_survives_uncertainty(self):
        view = self.view(lambda view: "infer" in view["valid_actions"])
        for index in range(2):
            result = self.act(view, "infer", "inference-" + str(index))
            self.assertTrue(result["resource_result"]["schema_valid"])
            self.assertEqual(result["reservation"]["state"], "SETTLED")
        with self.assertRaises(Denied):
            self.act(view, "infer", "third")
        self.assertGreater(self.control.ledger.account("agent")["spent"], 0)
        self.assertEqual(self.control.ledger.account("agent")["reserved"], 0)

    def test_easy_rules_skip_inference_and_always_model_pays(self):
        view = self.view(lambda view: not view["mandatory_review"] and view["reviewer_can_help"]
                         and not view["available_sources"] and policy.deterministic_links(view))
        history = [{"action": "check"}]
        self.assertEqual(policy.choose(view, "selective-llm", history)["action"], "finalize")
        self.assertEqual(policy.choose(view, "always-llm", history)["action"], "infer")

    def test_uncertain_or_unsupported_interpretation_never_finalizes(self):
        view = self.view(lambda view: "infer" in view["valid_actions"])
        answer = {"assessment": "supported", "payment_ids": ["invented"], "document_ids": ["invoice"],
                  "confidence": "high", "summary": "malicious"}
        result = {"resource_result": {"schema_valid": True,
                  "completion": {"choices": [{"message": {"content": json.dumps(answer)}}]}}}
        self.assertIsNone(policy.interpretation(result, view))

    def test_recoverable_denial_removes_action_and_security_denial_stops(self):
        view = self.view(lambda view: bool(view["available_sources"]))
        history = [{"action": "fetch", "denied": {"error": "EVIDENCE_SOURCE_NOT_AVAILABLE"}}]
        self.assertNotEqual(policy.choose(view, "rules-only", history)["action"], "fetch")
        history = [{"action": "infer", "denied": {"error": "UNKNOWN_TASK"}}]
        self.assertEqual(policy.choose(view, "selective-llm", history)["action"], "abstain")

    def test_persisted_inference_receipt_recovers_without_live_adapter(self):
        view = self.view(lambda view: "infer" in view["valid_actions"])
        settle = self.control.ledger.settle

        def crash_before_settlement(identity, actual):
            if identity == "agent/semantic/crash":
                raise RuntimeError("controlled crash after trusted receipt")
            return settle(identity, actual)

        with patch.object(self.control.ledger, "settle", side_effect=crash_before_settlement):
            with self.assertRaises(RuntimeError):
                self.act(view, "infer", "crash")
        request = self.control.request("agent/semantic/crash", "agent")
        self.assertIsNotNone(request["receipt"])
        self.assertGreater(self.control.ledger.account("agent")["reserved"], 0)
        self.control = ControlPlane(Ledger(self.control.ledger.path))
        self.tasks = SemanticTasks(self.control)
        self.assertNotIn("nim_chat", self.control.adapters)
        recovered = self.act(view, "infer", "crash")
        self.assertEqual(recovered["reservation"]["state"], "SETTLED")
        self.assertEqual(self.control.ledger.account("agent")["reserved"], 0)
        self.assertTrue(recovered["resource_result"]["schema_valid"])
