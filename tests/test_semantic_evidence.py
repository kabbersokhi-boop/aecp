"""Recompute the published V3 analysis from immutable recorded results, never live calls."""

import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

root = Path(__file__).parents[1]
specification = importlib.util.spec_from_file_location("semantic_analyze_v3", root / "scripts/semantic_analyze_v3.py")
analysis = importlib.util.module_from_spec(specification)
specification.loader.exec_module(analysis)


class SemanticEvidenceTests(unittest.TestCase):
    def test_recorded_analysis_recomputes_without_provider(self):
        evidence = root / "docs/reports/evidence-v3"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            source, journal, output = target / "source.json", target / "journal.jsonl", target / "analysis.json"
            source.write_bytes(gzip.decompress((evidence / "final-semantic-live.json.gz").read_bytes()))
            journal.write_bytes(gzip.decompress(
                (evidence / "final-semantic-live.provider-journal.jsonl.gz").read_bytes()))
            analysis.analyze(source, journal, output)
            expected = json.loads(gzip.decompress((evidence / "final-semantic-analysis.json.gz").read_bytes()))
            self.assertEqual(json.loads(output.read_text()), expected)
            self.assertEqual(expected["provider_attempts"], 36)
            self.assertEqual(expected["provider_outcomes"]["timeout_or_connection"], 8)
            self.assertEqual({name: policy["verified_tasks"] for name, policy in expected["policies"].items()},
                             {"rules-only": 6, "rules-reviewer": 12, "always-llm": 9,
                              "selective-llm": 11, "selective-reviewer": 15})
            self.assertEqual(sum(policy["authority"]["reserved"] for policy in expected["policies"].values()), 5604)
