"""Corpus identity and observation/evaluator separation, without model-dependent grading."""

import json
import unittest

from aecp.semantic_workload import corpus, manifest


class SemanticWorkloadTests(unittest.TestCase):
    def test_split_identity_reproducible_and_disjoint(self):
        self.assertEqual(manifest("development"), manifest("development"))
        self.assertNotEqual(manifest("development")["full_corpus_hash"], manifest("heldout")["full_corpus_hash"])
        self.assertFalse({case.observation["task_id"] for case in corpus("development")} &
                         {case.observation["task_id"] for case in corpus("heldout")})

    def test_observations_exclude_evaluator_and_purchasable_documents(self):
        for case in corpus("development"):
            encoded = json.dumps(case.observation)
            for field in ("semantic_kind", "required_sources", "full_corpus_hash", "seed", "reviewer_evidence"):
                self.assertNotIn(field, encoded)
            if case.truth["required_sources"]:
                self.assertNotIn(case.sources["remittance"][0]["text"], encoded)

    def test_wrong_links_can_have_same_sum_so_arithmetic_is_not_enough(self):
        case = next(case for case in corpus("development") if case.truth["semantic_kind"] == "replacement")
        amounts = {payment["id"]: payment["amount_cents"] for payment in case.observation["payments"]}
        target = case.truth["payment_ids"]
        alternative = next(identity for identity in amounts if identity not in target)
        replaced = next(identity for identity in target if amounts[identity] == amounts[alternative])
        naive = [alternative if identity == replaced else identity for identity in target]
        self.assertNotEqual(set(target), set(naive))
        self.assertEqual(sum(amounts[identity] for identity in target), sum(amounts[identity] for identity in naive))
