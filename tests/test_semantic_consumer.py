"""Development-only policy checks, without provider execution or held-out tuning."""

import importlib.util
import json
import unittest
from pathlib import Path

from aecp.semantic_workload import corpus

specification = importlib.util.spec_from_file_location(
    "semantic_consumer_policy", Path(__file__).parents[1] / "examples/semantic_consumer/policy.py")
policy = importlib.util.module_from_spec(specification)
specification.loader.exec_module(policy)


class ConsumerPolicyTests(unittest.TestCase):
    def view(self, kind):
        case = next(case for case in corpus("development") if case.truth["semantic_kind"] == kind)
        return {**case.observation, "consultations_remaining": 2, "remaining_authority": 8000,
                "fetched_sources": []}, case

    def test_rules_resolve_all_available_development_allocation_templates(self):
        for kind in ("direct", "po_split", "replacement"):
            with self.subTest(kind=kind):
                view, case = self.view(kind)
                self.assertEqual(policy.deterministic_links(view), case.truth["payment_ids"])
                self.assertEqual(policy.choose(view, "selective", [{"action": "check"}])["action"], "finalize")

    def test_fetch_specific_source_before_spending_on_reasoning(self):
        view, _ = self.view("fetch")
        self.assertEqual(policy.choose(view, "selective", [{"action": "check"}])["source"], "remittance")

    def test_always_model_pays_even_when_rules_suffice(self):
        view, _ = self.view("direct")
        self.assertEqual(policy.choose(view, "always-llm", [{"action": "check"}])["action"], "infer")

    def test_mandatory_authority_and_missing_evidence_not_model_decisions(self):
        for kind, expected in (("conflict", "escalate"), ("missing", "abstain")):
            view, _ = self.view(kind)
            for mode in ("selective", "always-llm", "deterministic-only"):
                self.assertEqual(policy.choose(view, mode, [{"action": "check"}])["action"], expected)

    def test_schema_failure_does_not_become_a_resolution(self):
        view, _ = self.view("direct")
        action = policy.choose(view, "always-llm", [{"action": "infer", "resource_result": {"schema_valid": False}}])
        self.assertEqual(action["action"], "abstain")

    def test_model_can_choose_specific_additional_evidence(self):
        view, _ = self.view("fetch")
        proposal = {"action": "fetch", "payment_ids": [], "source": "remittance", "confidence": "low",
                    "reason": "Need the allocation attachment."}
        receipt = {"schema_valid": True, "completion": {"choices": [{"message": {"content": json.dumps(proposal)}}]}}
        action = policy.choose(view, "always-llm", [{"action": "infer", "resource_result": receipt}])
        self.assertEqual(action["action"], "fetch")
        self.assertEqual(action["source"], "remittance")
