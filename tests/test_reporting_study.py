"""Information interfaces, fixed workload pairing and heterogeneous resource conservation."""

import unittest
from itertools import product

from aecp.reporting_study import POLICIES, ReportingConfig, central, offline_bound, report_subset, run, tariffs
from aecp.study import RESOURCES, StudyConfig, feasible, study_corpus


class ReportingStudyTests(unittest.TestCase):
    def test_every_policy_under_same_relaxed_bound_and_budget(self):
        configuration = ReportingConfig(StudyConfig(rounds=3, budget=90), report_cost=2)
        for seed in range(3):
            with self.subTest(seed=seed):
                rows = [run(seed, configuration, policy) for policy in POLICIES]
                self.assertEqual(len({row["oracle"]["verified_value"] for row in rows}), 1)
                for row in rows:
                    self.assertLessEqual(row["verified_value"], row["oracle"]["verified_value"])
                    self.assertLessEqual(row["cost"], configuration.economy.budget)
                    self.assertEqual(row["cost"], row["coordination_cost"]
                                     + sum(trace["resource_cost"] for trace in row["traces"]))
                    self.assertEqual(row["total_tasks"], row["verified_tasks"] + row["attempted_incorrect"]
                                     + row["never_attempted"])
                    self.assertEqual(sum(row["credits"]) + row["market_revenue"], 360)

    def test_public_central_receives_no_private_reports(self):
        configuration = ReportingConfig(StudyConfig(rounds=2, budget=100))
        cases = study_corpus(5, configuration.economy)
        public = [case.public for case in cases[:3]]
        choices = central(public, configuration.economy, tariffs(5), 70, [None] * 3)
        self.assertEqual(len(choices), 3)
        row = run(5, configuration, "paced-public")
        self.assertTrue(all(trace["report"] is None for trace in row["traces"]))
        self.assertEqual(row["reporting_cost"], 0)

    def test_shared_reporting_is_charged_and_strategic_change_is_local(self):
        configuration = ReportingConfig(StudyConfig(rounds=2, budget=200), report_cost=2)
        truthful = run(8, configuration, "shared-truthful")
        strategic = run(8, configuration, "shared-strategic")
        self.assertEqual(truthful["reporting_cost"], 12)
        self.assertEqual(strategic["reporting_cost"], 12)
        for original, changed in zip(truthful["traces"], strategic["traces"], strict=True):
            if changed["agent"] == 0:
                self.assertTrue(changed["report"])
            else:
                self.assertEqual(original["report"], changed["report"])

    def test_tariffs_vary_reproducibly_without_future_outcomes(self):
        self.assertEqual(tariffs(7), tariffs(7))
        self.assertGreater(len({row[1] for row in tariffs(7)}), 1)
        configuration = ReportingConfig(StudyConfig(rounds=3, budget=90))
        self.assertEqual(run(7, configuration, "market-private"), run(7, configuration, "market-private"))

    def test_selective_reporting_can_refuse_unaffordable_information(self):
        config = StudyConfig(rounds=2, budget=90)
        public = [case.public for case in study_corpus(7, config)[:3]]
        self.assertFalse(report_subset(public, config, tariffs(7), 10, 12))
        row = run(7, ReportingConfig(config, report_cost=10), "shared-selective")
        forced = run(7, ReportingConfig(config, report_cost=10), "shared-truthful")
        self.assertLess(row["reporting_cost"], forced["reporting_cost"])

    def test_matched_request_control_has_identical_fallback_when_no_premium_exists(self):
        configuration = ReportingConfig(StudyConfig(rounds=3, budget=90, premium_capacity=0))
        market = run(7, configuration, "market-private")
        rotating = run(7, configuration, "private-request-rotation")
        self.assertEqual(market["traces"], rotating["traces"])
        self.assertEqual(market["cost"], rotating["cost"])

    def test_subset_purchase_excludes_ineligible_agents(self):
        config = StudyConfig(rounds=1, budget=90, mandatory_capacity=1)
        public = [case.public for case in study_corpus(7, config)]
        selected = report_subset(public, config, tariffs(7), 80, 0)
        self.assertTrue(set(selected) <= {0})

    def test_oracle_matches_independent_exhaustive_two_round_schedule(self):
        config = StudyConfig(rounds=2, budget=90)
        cases = study_corpus(17, config)
        prices = tariffs(17)
        best = (0, 0)
        for schedule in product(RESOURCES, repeat=6):
            expense = 0
            value = 0
            valid = True
            for offset in (0, 3):
                batch = cases[offset:offset + 3]
                choices = schedule[offset:offset + 3]
                if not feasible([case.public for case in batch], choices, config):
                    valid = False
                    break
                expense += 3 if any(choice != "defer" for choice in choices) else 0
                for case, resource in zip(batch, choices, strict=True):
                    if resource != "defer":
                        expense += prices[case.public.agent][RESOURCES.index(resource)] + 2 + 3 * case.public.mandatory
                    value += case.public.value * case.correct(resource)
            if valid and expense <= config.budget:
                best = max(best, (value, -expense))
        oracle = offline_bound(cases, config, prices)
        self.assertEqual((oracle["verified_value"], -oracle["cost"]), best)
