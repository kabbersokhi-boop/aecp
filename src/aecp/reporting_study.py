"""Priced information aggregation with heterogeneous public tariffs; not equilibrium analysis."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, replace
from fractions import Fraction
from functools import lru_cache

from aecp.determinism import semantic_u64
from aecp.study import (
    RESOURCES,
    PrivateView,
    PublicCase,
    StudyConfig,
    expected,
    feasible,
    review_eligible,
    study_corpus,
)

VERSION = "priced-reporting.v3.2"
ENVIRONMENT_VERSION = "priced-reporting.v3.1"
POLICIES = ("paced-public", "shared-truthful", "shared-selective", "shared-noisy", "shared-strategic",
            "private-no-market", "private-request-rotation", "market-private", "priority", "equal", "evcost")


@dataclass(frozen=True)
class ReportingConfig:
    economy: StudyConfig = StudyConfig()
    report_cost: int = 0
    report_noise: int = 20

    def validate(self):
        self.economy.validate()
        if (type(self.report_cost) is not int or not 0 <= self.report_cost <= 10
                or type(self.report_noise) is not int or not 0 <= self.report_noise <= 50):
            raise ValueError("reporting experiment must be bounded")


def tariffs(seed: int) -> tuple[tuple[int, ...], ...]:
    return tuple((0, 2 + semantic_u64(seed, ENVIRONMENT_VERSION, agent, "cheap") % 7,
                  10 + semantic_u64(seed, ENVIRONMENT_VERSION, agent, "premium") % 13,
                  18 + semantic_u64(seed, ENVIRONMENT_VERSION, agent, "consultation") % 19) for agent in range(3))


def cost(public: PublicCase, resource: str, prices: tuple) -> int:
    return prices[public.agent][RESOURCES.index(resource)] + (
        2 + 3 * int(public.mandatory) if resource != "defer" else 0)


def bundles(public: list[PublicCase], config: StudyConfig, prices: tuple):
    for choices in itertools.product(RESOURCES, repeat=len(public)):
        if feasible(public, choices, config):
            yield choices, sum(cost(case, choice, prices) for case, choice in zip(public, choices, strict=True))


@lru_cache(maxsize=512)
def forecast(config: StudyConfig, prices: tuple, next_round: int) -> tuple[int, ...]:
    values = [0] * (config.budget + 1)
    for round_index in reversed(range(next_round, config.rounds)):
        public = [PublicCase(f"forecast-{agent}", agent, round_index, 110,
                             round_index % 2 == 0 or agent == 0, 100, (100,)) for agent in range(3)]
        options = [(expense + 3, sum(expected(case, choice, config)
                                    for case, choice in zip(public, choices, strict=True)))
                   for choices, expense in bundles(public, config, prices)]
        values = [max((gain + values[budget - expense] for expense, gain in options if expense <= budget), default=0)
                  for budget in range(config.budget + 1)]
    return tuple(values)


def central(public: list[PublicCase], config: StudyConfig, prices: tuple, remaining: int,
            reports: list[PrivateView | None]) -> tuple[str, ...]:
    continuation = forecast(config, prices, public[0].round + 1)
    candidates = []
    for choices, expense in bundles(public, config, prices):
        if expense <= remaining:
            current = sum(expected(case, choice, config, reports[index])
                          for index, (case, choice) in enumerate(zip(public, choices, strict=True)))
            candidates.append((current + continuation[remaining - expense], -expense, choices))
    return max(candidates)[2] if candidates else ("defer",) * len(public)


def report_subset(public: list[PublicCase], config: StudyConfig, prices: tuple,
                  remaining: int, unit_fee: int) -> tuple[int, ...]:
    """Choose a current-round report subset before seeing any reports, using public priors."""
    continuation = forecast(config, prices, public[0].round + 1)

    def objective(headroom, reports):
        choices = central(public, config, prices, headroom, reports)
        expense = sum(cost(case, choice, prices) for case, choice in zip(public, choices, strict=True))
        return (sum(expected(case, choice, config, reports[index])
                    for index, (case, choice) in enumerate(zip(public, choices, strict=True)))
                + continuation[headroom - expense])

    best = (Fraction(objective(remaining, [None] * len(public))), 0, ())
    for mask in itertools.product((False, True), repeat=len(public)):
        subset = tuple(index for index, selected in enumerate(mask) if selected)
        fee = unit_fee * len(subset)
        if fee > remaining:
            continue
        total = 0
        for signals in itertools.product((False, True), repeat=len(subset)):
            reports = [None] * len(public)
            for index, signal in zip(subset, signals, strict=True):
                reports[index] = PrivateView(public[index], signal)
            total += objective(remaining - fee, reports)
        candidate = (Fraction(total, 2**len(subset)), -len(subset), subset)
        if candidate > best:
            best = candidate
    return best[2]


def offline_bound(cases, config: StudyConfig, prices: tuple) -> dict:
    states = {0: 0}
    for round_index in range(config.rounds):
        batch = cases[round_index * 3:round_index * 3 + 3]
        options = [(expense + (3 if any(choice != "defer" for choice in choices) else 0),
                    sum(case.public.value * case.correct(choice) for case, choice in zip(batch, choices, strict=True)))
                   for choices, expense in bundles([case.public for case in batch], config, prices)]
        updated = {}
        for spent, value in states.items():
            for expense, gain in options:
                if spent + expense <= config.budget:
                    updated[spent + expense] = max(updated.get(spent + expense, 0), value + gain)
        states = updated
    expense, value = max(states.items(), key=lambda item: (item[1], -item[0]))
    return {"verified_value": value, "cost": expense,
            "definition": "omniscient exact relaxed DP; identical tariffs/capacities, no reporting/bidding fees, "
                          "no planning fee for empty rounds"}


def run(seed: int, configuration: ReportingConfig, policy: str) -> dict:
    configuration.validate()
    if policy not in POLICIES:
        raise ValueError("unknown reporting policy")
    config = configuration.economy
    cases = study_corpus(seed, config)
    prices = tariffs(seed)
    remaining = config.budget
    coordination = 0
    reporting = 0
    revenue = 0
    credits = list(config.endowments)
    traces = []
    for round_index in range(config.rounds):
        batch = cases[round_index * 3:round_index * 3 + 3]
        public = [case.public for case in batch]
        planning = min(3, remaining)
        remaining -= planning
        coordination += planning
        if planning < 3:
            break
        reports = [None] * 3
        assumptions = config
        if policy.startswith("shared"):
            selected = (report_subset(public, config, prices, remaining, configuration.report_cost)
                        if policy == "shared-selective" else tuple(range(3)))
            fee = len(selected) * configuration.report_cost
            if fee <= remaining and selected:
                remaining -= fee
                coordination += fee
                reporting += fee
                for index, case in enumerate(batch):
                    if index not in selected:
                        continue
                    signal = case.private.unposted_signal
                    if policy == "shared-noisy" and semantic_u64(
                            seed, ENVIRONMENT_VERSION, case.public.task_id, "noise") % 100 < (
                            configuration.report_noise):
                        signal = not signal
                    if policy == "shared-strategic" and case.public.agent == 0:
                        signal = True
                    reports[index] = PrivateView(case.public, signal)
                if policy == "shared-noisy":
                    effective = (config.signal_quality * (100 - configuration.report_noise)
                                 + (100 - config.signal_quality) * configuration.report_noise) // 100
                    assumptions = replace(config, signal_quality=max(50, effective))
        if policy == "paced-public" or policy.startswith("shared"):
            choices = central(public, assumptions, prices, remaining, reports)
        else:
            choices = ["defer"] * 3
            authorized = review_eligible(public, config)
            order = sorted(range(3), key=lambda index: (index - round_index) % 3)
            local = policy in {"private-no-market", "private-request-rotation", "market-private"}
            if policy == "priority":
                order.sort(key=lambda index: -public[index].value)
            elif policy == "evcost":
                order.sort(key=lambda index: -expected(public[index], "cheap", config)
                           / cost(public[index], "cheap", prices))
            bids = []
            request_allocation = policy in {"market-private", "private-request-rotation"}
            if request_allocation and config.premium_capacity:
                for index in order:
                    case = batch[index]
                    gain = max(0, (expected(case.public, "premium", config, case.private)
                                   - expected(case.public, "cheap", config, case.private)) // 100)
                    bid = min(gain, credits[index]) if policy == "market-private" else gain
                    bid_fee = config.bid_cost if policy == "market-private" else 0
                    if (bid > 0 and case.public.task_id in authorized
                            and cost(case.public, "premium", prices) + bid_fee <= remaining):
                        remaining -= bid_fee
                        coordination += bid_fee
                        bids.append((bid, index))
                ranked = (sorted(bids, key=lambda item: (-item[0], public[item[1]].task_id))
                          if policy == "market-private" else bids)
                for bid, index in ranked:
                    proposed = tuple("premium" if candidate == index else choices[candidate] for candidate in range(3))
                    expense = cost(public[index], "premium", prices)
                    if feasible(public, proposed, config) and expense <= remaining:
                        choices[index] = "premium"
                        remaining -= expense
                        if policy == "market-private":
                            credits[index] -= bid
                            revenue += bid
            for index in order:
                if choices[index] != "defer":
                    continue
                candidates = []
                for resource in RESOURCES[1:]:
                    if request_allocation and resource == "premium":
                        continue
                    proposed = tuple(resource if candidate == index else choices[candidate] for candidate in range(3))
                    expense = cost(public[index], resource, prices)
                    if expense <= remaining and feasible(public, proposed, config):
                        value = expected(public[index], resource, config, batch[index].private if local else None)
                        candidates.append((value / expense, value, -expense, resource))
                if candidates:
                    resource = max(candidates)[-1]
                    choices[index] = resource
                    remaining -= cost(public[index], resource, prices)
        if policy == "paced-public" or policy.startswith("shared"):
            remaining -= sum(cost(case, resource, prices) for case, resource in zip(public, choices, strict=True))
        assert remaining >= 0 and feasible(public, tuple(choices), config)
        for index, (case, resource) in enumerate(zip(batch, choices, strict=True)):
            traces.append({"task_id": case.public.task_id, "agent": case.public.agent, "round": round_index,
                           "resource": resource, "attempted": resource != "defer", "verified": case.correct(resource),
                           "verified_value": case.public.value * case.correct(resource),
                           "resource_cost": cost(case.public, resource, prices),
                           "report": reports[index].unposted_signal if reports[index] else None})
    verified = sum(row["verified"] for row in traces)
    attempted = sum(row["attempted"] for row in traces)
    assert sum(credits) + revenue == sum(config.endowments)
    return {"policy": policy, "verified_value": sum(row["verified_value"] for row in traces),
            "verified_tasks": verified, "attempted_incorrect": attempted - verified,
            "never_attempted": len(cases) - attempted, "total_tasks": len(cases),
            "total_value": sum(case.public.value for case in cases), "cost": config.budget - remaining,
            "coordination_cost": coordination, "reporting_cost": reporting,
            "credits": credits, "market_revenue": revenue, "traces": traces,
            "agent_verified_value": [sum(row["verified_value"] for row in traces if row["agent"] == agent)
                                     for agent in range(3)],
            "agent_premium_access": [sum(row["resource"] == "premium" for row in traces if row["agent"] == agent)
                                     for agent in range(3)],
            "oracle": offline_bound(cases, config, prices), "public_tariffs": prices}
