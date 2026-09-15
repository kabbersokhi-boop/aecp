"""Information boundaries, independent oracle feasibility, and resource parity."""

import itertools
import unittest
from dataclasses import asdict, replace

from aecp.study import (
    ALLOCATORS,
    RESOURCES,
    StudyConfig,
    choose_paced,
    choose_public,
    execution_cost,
    feasible,
    oracle,
    run_policy,
    study_corpus,
)


class StudyTests(unittest.TestCase):
    def test_public_interface_has_no_private_signal_or_evaluator_fields(self):
        config = StudyConfig()
        cases = study_corpus(7, config)
        public = [case.public for case in cases[:3]]
        encoded = str([asdict(case) for case in public])
        for forbidden in ("unposted_signal", "bank_payments", "premium_available", "seed"):
            self.assertNotIn(forbidden, encoded)
        before = choose_public(public, config, 100)
        changed = [replace(case, private=replace(case.private, unposted_signal=not case.private.unposted_signal))
                   for case in cases[:3]]
        self.assertEqual(before, choose_public([case.public for case in changed], config, 100))

    def test_private_signal_is_imperfect_and_quality_changes_information_not_workload(self):
        low = study_corpus(7, StudyConfig(signal_quality=50))
        high = study_corpus(7, StudyConfig(signal_quality=90))
        self.assertEqual([case.public for case in low], [case.public for case in high])
        self.assertEqual([case.bank_payments for case in low], [case.bank_payments for case in high])
        matched = []
        for seed in range(30):
            for case in study_corpus(seed, StudyConfig(signal_quality=75)):
                matched.append(case.private.unposted_signal == (len(case.bank_payments) > 1))
        accuracy = sum(matched) / len(matched)
        self.assertGreater(accuracy, 0.65)
        self.assertLess(accuracy, 0.85)

    def test_oracle_matches_independent_exhaustive_two_round_search(self):
        config = StudyConfig(rounds=2, budget=60)
        cases = study_corpus(9, config)
        best = 0
        for choices in itertools.product(RESOURCES, repeat=6):
            if not all(feasible([case.public for case in cases[start:start + 3]], choices[start:start + 3], config)
                       for start in (0, 3)):
                continue
            cost = sum(execution_cost(case.public, choice) for case, choice in zip(cases, choices, strict=True))
            cost += sum(3 for start in (0, 3) if any(choice != "defer" for choice in choices[start:start + 3]))
            if cost <= config.budget:
                best = max(best, sum(case.public.value * case.correct(choice)
                                     for case, choice in zip(cases, choices, strict=True)))
        self.assertEqual(oracle(cases, config)["value"], best)

    def test_oracle_dominates_and_all_allocators_obey_mandatory_capacity(self):
        for capacity in (0, 1, 2):
            config = StudyConfig(mandatory_capacity=capacity, rounds=4)
            cases = study_corpus(7, config)
            bound = oracle(cases, config)
            for allocator in ALLOCATORS:
                with self.subTest(capacity=capacity, allocator=allocator):
                    result = run_policy(cases, config, allocator)
                    self.assertLessEqual(result["verified_value"], bound["value"])
                    self.assertLessEqual(result["modeled_cost"], config.budget)
                    self.assertLessEqual(sum(result["review_access"]), 2 * capacity + 2 * min(1, capacity))
                    self.assertEqual(sum(result["credits_remaining"]) + result["market_revenue"],
                                     sum(config.endowments))

    def test_no_information_ablation_equalizes_central_views(self):
        config = StudyConfig(signal_quality=50)
        cases = study_corpus(5, config)
        public = run_policy(cases, config, "central-public")
        shared = run_policy(cases, config, "central-shared")
        self.assertEqual(public["trace"], shared["trace"])

    def test_paced_policy_saves_authority_for_expected_future_demand(self):
        config = StudyConfig(rounds=2, budget=45)
        public = [replace(case.public, value=20) for case in study_corpus(7, config)[:3]]
        myopic = choose_public(public, config, 42)
        paced = choose_paced(public, config, 42)
        def cost(choices):
            return sum(execution_cost(case, choice) for case, choice in zip(public, choices, strict=True))
        self.assertLess(cost(paced), cost(myopic))

    def test_paced_public_first_decision_does_not_read_future_or_private_state(self):
        config = StudyConfig(rounds=3, budget=70)
        cases = study_corpus(9, config)
        changed = [replace(case, private=replace(case.private, unposted_signal=not case.private.unposted_signal),
                           bank_payments=(), premium_available=not case.premium_available,
                           public=replace(case.public, value=10000) if index >= 3 else case.public)
                   for index, case in enumerate(cases)]
        before = run_policy(cases, config, "central-paced-public")
        after = run_policy(changed, config, "central-paced-public")
        self.assertEqual([trace["choice"] for trace in before["trace"][:3]],
                         [trace["choice"] for trace in after["trace"][:3]])

    def test_private_no_market_never_spends_credits_or_bidding_tax(self):
        config = StudyConfig(bid_cost=10, strategy="overstate")
        cases = study_corpus(8, config)
        result = run_policy(cases, config, "decentralized-private-no-market")
        untaxed = run_policy(cases, replace(config, bid_cost=0, strategy="unshaded"),
                            "decentralized-private-no-market")
        self.assertEqual(result, untaxed)
        self.assertEqual(result["market_revenue"], 0)
        self.assertEqual(result["credits_remaining"], list(config.endowments))

    def test_attempted_wrong_is_not_unserved(self):
        config = StudyConfig(budget=300, provider_reliability=0)
        for allocator in ALLOCATORS:
            result = run_policy(study_corpus(8, config), config, allocator)
            self.assertEqual(result["unserved"], result["deferred"])
            self.assertEqual(result["deferred"] + result["served_incorrect"] + result["verified_tasks"], 18)

    def test_strategies_do_not_create_credits(self):
        for strategy in ("unshaded", "shade", "overstate", "hoard"):
            config = StudyConfig(strategy=strategy, endowments=(20, 100, 300))
            result = run_policy(study_corpus(2, config), config, "market-private")
            self.assertEqual(sum(result["credits_remaining"]) + result["market_revenue"], 420)
            self.assertTrue(all(value >= 0 for value in result["credits_remaining"]))

    def test_bids_cannot_buy_mandatory_review_eligibility(self):
        from aecp.study import review_eligible
        for strategy in ("unshaded", "shade", "overstate", "hoard"):
            config = StudyConfig(strategy=strategy, mandatory_capacity=1)
            cases = study_corpus(2, config)
            allowed = set().union(*(review_eligible([case.public for case in cases[start:start + 3]], config)
                                    for start in range(0, len(cases), 3)))
            for allocator in ALLOCATORS:
                result = run_policy(cases, config, allocator)
                self.assertTrue(all(trace["choice"] == "defer" or trace["task"] in allowed
                                    for trace in result["trace"]))
