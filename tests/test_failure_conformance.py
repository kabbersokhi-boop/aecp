import json
import tempfile
import unittest
from pathlib import Path

from aecp.failure_conformance import run_conformance, run_cost_of_safety


class FailureConformanceTests(unittest.TestCase):
    def test_contract_exercises_independent_ground_truth_and_calibration_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "conformance.json"
            result = run_conformance(output)
            self.assertEqual(json.loads(output.read_text()), result)
            scenarios = result["scenarios"]
            self.assertGreaterEqual(len(scenarios), 11)
            self.assertEqual(scenarios["normal_settlement"]["state"], "SETTLED")
            self.assertEqual(scenarios["concurrent_parent_authority"]["outcomes"], ["DENIED", "RESERVED"])
            self.assertEqual(scenarios["duplicate_immutable_identity"]["metrics"]["provider_executions"], 1)
            self.assertTrue(scenarios["changed_parameters_conflict"]["rejected"])
            lost = scenarios["executed_response_lost"]
            self.assertEqual(lost["state"], "UNRESOLVED")
            self.assertEqual(lost["provider_journal"][0]["executed"], 1)
            self.assertEqual(lost["provider_journal"][0]["delivered"], 0)
            self.assertEqual(scenarios["worker_dies_after_provider_execution"]["worker_exit"], 73)
            self.assertEqual(scenarios["worker_dies_after_provider_execution"]["state"], "UNRESOLVED")
            self.assertEqual(scenarios["durable_receipt_before_worker_death"]["worker_exit"], 74)
            self.assertEqual(scenarios["durable_receipt_before_worker_death"]["state"], "SETTLED")
            self.assertTrue(scenarios["independently_funded_retry"]["third_denied"])
            self.assertTrue(scenarios["expiry_cannot_erase_uncertainty"]["cancellation_denied"])
            self.assertEqual(scenarios["expiry_cannot_erase_uncertainty"]["first_after_expiry"], "UNRESOLVED")
            self.assertEqual(scenarios["trusted_reconciliation"]["charged"], "SETTLED")
            self.assertEqual(scenarios["trusted_reconciliation"]["no_charge"], "RELEASED")
            breach = scenarios["provider_bound_breach"]
            self.assertEqual(breach["actual"], 7)
            self.assertEqual(breach["status"], "FROZEN")
            self.assertEqual(breach["audit"]["bound_breach_count"], 1)
            modes = scenarios["provider_idempotency_modes"]
            self.assertEqual(modes["idempotent_executions"], 1)
            self.assertEqual(modes["non_idempotent_executions"], 2)
            naive = result["controls"]["naive-check-then-execute"]
            self.assertGreater(naive["settled"], naive["budget"])
            reject = result["controls"]["reject-all"]
            self.assertEqual(reject["useful_work_completed"], 0)
            self.assertEqual(result["provider_calls"], 0)

    def test_cost_study_is_paired_safe_and_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "first.json"
            second_path = Path(directory) / "second.json"
            first = run_cost_of_safety(first_path, seeds=(1,))
            second = run_cost_of_safety(second_path, seeds=(1,))
            self.assertEqual(first, second)
            self.assertEqual(first["trials"], 12)
            self.assertTrue(all(not row["safety"]["unaccounted_or_prematurely_released_exposure"]
                                for row in first["rows"]))
            self.assertLessEqual(first["aggregates"]["reconcile-1"]["authority_time_held"],
                                 first["aggregates"]["retain"]["authority_time_held"])
            self.assertGreaterEqual(first["aggregates"]["reconcile-1"]["useful_work_completed"],
                                    first["aggregates"]["retain"]["useful_work_completed"])
            self.assertEqual(first["provider_calls"], 0)
