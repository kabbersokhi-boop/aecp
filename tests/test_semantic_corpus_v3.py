"""Corpus structure checks do not tune a worker against held-out answers."""

import json
import unittest

from aecp.semantic_corpus_v3 import corpus, manifest
from aecp.semantic_workload import manifest as historical_manifest


class CorpusV3Tests(unittest.TestCase):
    def test_disjoint_reproducible_and_historical_unchanged(self):
        self.assertEqual(manifest("development"), manifest("development"))
        self.assertEqual(manifest("heldout")["cases"], 36)
        self.assertFalse({case.observation["task_id"] for case in corpus("development")} &
                         {case.observation["task_id"] for case in corpus("heldout")})
        self.assertEqual(historical_manifest("heldout")["full_corpus_hash"],
                         "1ba8a9d152970ded5cf42fc5a8b883166f83ea6f7eb5638ef04e515c9f4fcdbc")

    def test_development_composition_and_hidden_boundary(self):
        cases = corpus("development")
        combinations = {(case.truth["composition"]["topology"], case.truth["composition"]["access"])
                        for case in cases}
        self.assertEqual(len(combinations), 12)
        for case in cases:
            encoded = json.dumps(case.observation)
            for field in ("composition", "semantic_kind", "required_sources", "seed", "reviewer_evidence"):
                self.assertNotIn(field, encoded)
            self.assertEqual(len(case.observation["payments"]), 4)
            self.assertEqual(len({payment["id"] for payment in case.observation["payments"]}), 4)
            if case.truth["required_sources"]:
                self.assertNotIn(case.sources["remittance"][0]["text"], encoded)
