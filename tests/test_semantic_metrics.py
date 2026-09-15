"""Protocol fixtures cannot masquerade as measured live provider consumption."""

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

scripts = Path(__file__).parents[1] / "scripts"
specification = importlib.util.spec_from_file_location("semantic_validate", scripts / "semantic_validate.py")
study = importlib.util.module_from_spec(specification)
with patch.object(sys, "path", [str(scripts), *sys.path]):
    specification.loader.exec_module(study)


class SemanticMetricsTests(unittest.TestCase):
    def test_fixture_and_live_usage_have_distinct_labels(self):
        cases = [{"observation": {"value": 100}, "outcome": None, "actions": [{"result": {
            "action": "infer", "resource_result": {"schema_valid": False,
                "provider_usage": {"prompt_tokens": 100, "completion_tokens": 40, "total_tokens": 140}}}}]}]
        offline = study.metrics(cases, live=False)
        self.assertEqual(offline["provider_receipts"], 0)
        self.assertEqual(offline["total_tokens"], 0)
        self.assertEqual(offline["fixture_usage"]["total_tokens"], 140)
        self.assertEqual(offline["fixture_receipts"], 1)
        live = study.metrics(cases, live=True)
        self.assertEqual(live["provider_receipts"], 1)
        self.assertEqual(live["total_tokens"], 140)
        self.assertIsNone(live["fixture_usage"])
        self.assertEqual(live["schema_valid"], 0)
        self.assertEqual(live["verified_tasks"], 0)
