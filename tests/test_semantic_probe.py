"""Model selection is development-only, bounded and financially governed."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

specification = importlib.util.spec_from_file_location(
    "semantic_probe_v3", Path(__file__).parents[1] / "scripts/semantic_probe_v3.py")
probe = importlib.util.module_from_spec(specification)
specification.loader.exec_module(probe)


class FixtureTransport:
    def __init__(self, *, base_url, journal):
        self.base_url, self.journal = base_url, journal

    def request(self, path, body=None):
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        usage = {"prompt_tokens": 100, "completion_tokens": 40, "total_tokens": 140} if body else {}
        with self.journal.open("a") as stream:
            stream.write(json.dumps({"phase": "returned", "endpoint": path, "usage": usage}) + "\n")
        if not body:
            return {"data": [{"id": probe.PREFERENCES[0]}]}
        return {"model": body["model"], "usage": usage,
                "choices": [{"message": {"content": json.dumps({"assessment": "uncertain", "payment_ids": [],
                    "document_ids": [], "confidence": "low", "summary": "Fixture only."})}, "finish_reason": "stop"}]}


class ProbeTests(unittest.TestCase):
    def test_bounded_governed_development_calls_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(probe, "NimTransport", FixtureTransport):
            output = Path(directory) / "probe.json"
            result = probe.probe(output)
            self.assertEqual(result["chat_calls"], 3)
            self.assertEqual(result["catalog_calls"], 1)
            self.assertEqual(result["usage"]["total_tokens"], 420)
            record = json.loads(output.read_text())
            for attempt in record["probes"][0]["attempts"]:
                self.assertIn("DEVELOPMENT", attempt["task_id"])
                self.assertEqual(attempt["execution"]["reservation"]["state"], "SETTLED")
                self.assertTrue(attempt["schema_valid"])
                self.assertFalse(attempt["linking_correct"])
            with self.assertRaises(ValueError):
                probe.probe(output)
