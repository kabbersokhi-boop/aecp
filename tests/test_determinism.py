from __future__ import annotations

import os
import subprocess
import sys
import unittest

from aecp.__main__ import demo_ledger
from aecp.determinism import bernoulli_bps, canonical_json, semantic_u64, stable_digest


class DeterminismTests(unittest.TestCase):
    def test_coordinate_types_are_not_conflated(self) -> None:
        self.assertNotEqual(semantic_u64(1, "1"), semantic_u64(1, 1))

    def test_order_of_calls_does_not_change_semantic_draws(self) -> None:
        first = {name: semantic_u64(17, "outcome", name) for name in ("a", "b", "c")}
        second = {name: semantic_u64(17, "outcome", name) for name in ("c", "a", "b")}
        self.assertEqual(first, second)

    def test_hash_seed_does_not_change_results(self) -> None:
        program = "from aecp.determinism import semantic_u64; print(semantic_u64(42, 'task', 1))"
        values = [subprocess.check_output([sys.executable, "-c", program],
                  env={**os.environ, "PYTHONHASHSEED": seed}, text=True) for seed in ("1", "927")]
        self.assertEqual(values[0], values[1])

    def test_probability_endpoints(self) -> None:
        self.assertFalse(bernoulli_bps(0, 0, "task"))
        self.assertTrue(bernoulli_bps(10_000, 0, "task"))

    def test_invalid_probability_and_seed_are_rejected(self) -> None:
        for probability in (-1, 10001, True, 0.5):
            with self.assertRaises(ValueError):
                bernoulli_bps(probability, 1, "task")
        for seed in (-1, 2**64, True, "1"):
            with self.assertRaises(ValueError):
                semantic_u64(seed, "task")
        with self.assertRaises(ValueError):
            semantic_u64(1)

    def test_canonical_digest_ignores_mapping_insertion_order(self) -> None:
        self.assertEqual(stable_digest({"a": 1, "b": 2}), stable_digest({"b": 2, "a": 1}))
        self.assertNotEqual(stable_digest([1, 2]), stable_digest([2, 1]))

    def test_nonfinite_numbers_are_not_valid_artifacts(self) -> None:
        with self.assertRaises(ValueError):
            canonical_json({"value": float("nan")})

    def test_demo_is_repeatable_and_explicitly_simulated(self) -> None:
        first, second = demo_ledger(), demo_ledger()
        self.assertEqual(first, second)
        self.assertEqual(first["real_provider_spend"], 0)
        self.assertTrue(first["costs_are_simulated"])
        self.assertTrue(first["unfunded_request_denied"])


if __name__ == "__main__":
    unittest.main()
