"""Bounded information-structure experiment; evaluator-only exact offline allocation oracle."""

from __future__ import annotations

import itertools
import json
import statistics
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from aecp.determinism import semantic_u64, stable_digest
from aecp.engine import code_revision
from aecp.workload import resolve

VERSION = "private-finops-rounds.v2"
STUDY_VERSION = "information-mechanism-controls.v2.1"
ALLOCATORS = ("central-public", "central-shared", "central-paced-public", "central-paced-shared",
              "decentralized-private-no-market", "market-public", "market-private", "priority", "equal", "evcost")
RESOURCES = ("defer", "cheap", "premium", "consultation")
RESOURCE_COST = {"defer": 0, "cheap": 4, "premium": 14, "consultation": 24}


@dataclass(frozen=True)
class PublicCase:
    task_id: str
    agent: int
    round: int
    value: int
    mandatory: bool
    invoice_cents: int
    visible_payments: tuple[int, ...]


@dataclass(frozen=True)
class PrivateView:
    public: PublicCase
    unposted_signal: bool


@dataclass(frozen=True)
class Truth:
    public: PublicCase
    private: PrivateView
    bank_payments: tuple[int, ...]
    premium_available: bool

    def correct(self, resource: str) -> bool:
        if resource == "defer":
            return False
        payments = self.bank_payments if resource == "consultation" or (
            resource == "premium" and self.premium_available) else self.public.visible_payments
        return resolve(self.public.invoice_cents, payments) == resolve(self.public.invoice_cents, self.bank_payments)


@dataclass(frozen=True)
class StudyConfig:
    budget: int = 180
    rounds: int = 6
    signal_quality: int = 75
    premium_capacity: int = 1
    consultation_capacity: int = 1
    mandatory_capacity: int = 2
    bid_cost: int = 2
    provider_reliability: int = 90
    strategy: str = "unshaded"
    endowments: tuple[int, int, int] = (120, 120, 120)

    def validate(self):
        if not (1 <= self.rounds <= 20 and 1 <= self.budget <= 1000 and 50 <= self.signal_quality <= 95
                and 0 <= self.provider_reliability <= 100 and 0 <= self.bid_cost <= 10
                and all(0 <= capacity <= 3 for capacity in (
                    self.premium_capacity, self.consultation_capacity, self.mandatory_capacity))
                and self.strategy in {"unshaded", "shade", "overstate", "hoard"}
                and len(self.endowments) == 3 and all(type(value) is int and value >= 0 for value in self.endowments)):
            raise ValueError("study exceeds bounded documented configuration")


def study_corpus(seed: int, config: StudyConfig) -> list[Truth]:
    config.validate()
    result = []
    for index in range(config.rounds * 3):
        identity = f"case-{index:03d}"
        def draw(name, identity=identity):
            return semantic_u64(seed, VERSION, identity, name)
        invoice = 1000 + draw("invoice") % 90000
        visible = (invoice - (500 if draw("visible") % 2 else 0),)
        unposted = bool(draw("unposted") % 2)
        bank = (*visible, invoice) if unposted else visible
        signal = unposted if draw("signal-noise") % 100 < config.signal_quality else not unposted
        public = PublicCase(identity, index % 3, index // 3, 20 + draw("value") % 180,
                            index // 3 % 2 == 0 or index % 3 == 0, invoice, visible)
        result.append(Truth(public, PrivateView(public, signal), bank,
                            draw("delivery") % 100 < config.provider_reliability))
    return result


def expected(public: PublicCase, resource: str, config: StudyConfig, private: PrivateView | None = None) -> int:
    missing = (config.signal_quality if private.unposted_signal else 100 - config.signal_quality) if private else 50
    probability = {"defer": 0, "cheap": 100 - missing, "consultation": 100,
                   "premium": 100 - missing * (100 - config.provider_reliability) // 100}[resource]
    return public.value * probability


def execution_cost(public: PublicCase, resource: str) -> int:
    return RESOURCE_COST[resource] + (2 + 3 * int(public.mandatory) if resource != "defer" else 0)


def review_eligible(public: list[PublicCase], config: StudyConfig) -> set[str]:
    mandatory = sorted((case for case in public if case.mandatory),
                       key=lambda case: ((case.agent - case.round) % 3, case.task_id))
    return {case.task_id for case in mandatory[:config.mandatory_capacity]} | {
        case.task_id for case in public if not case.mandatory}


def feasible(public: list[PublicCase], choices: tuple[str, ...], config: StudyConfig) -> bool:
    return (choices.count("premium") <= config.premium_capacity
            and all(choice == "defer" or case.task_id in review_eligible(public, config)
                    for case, choice in zip(public, choices, strict=True))
            and choices.count("consultation") <= config.consultation_capacity
            and sum(case.mandatory and choice != "defer" for case, choice in zip(public, choices, strict=True))
            <= config.mandatory_capacity)


def bundles(public: list[PublicCase], config: StudyConfig):
    for choices in itertools.product(RESOURCES, repeat=len(public)):
        if feasible(public, choices, config):
            yield choices, sum(execution_cost(case, choice) for case, choice in zip(public, choices, strict=True))


def oracle(cases: list[Truth], config: StudyConfig) -> dict:
    """Exact relaxed omniscient bound for synchronized rounds, not a deployable allocator.

    Three units of candidate planning per round are charged whenever any task executes.
    No bidding tax is required because the oracle can allocate centrally. All physical
    capacities and paid verification/review costs remain constrained.
    """
    config.validate()
    states = {0: (0, [])}
    for round_index in range(config.rounds):
        batch = cases[round_index * 3:round_index * 3 + 3]
        options = []
        for choices, cost in bundles([case.public for case in batch], config):
            cost += 3 if any(choice != "defer" for choice in choices) else 0
            value = sum(case.public.value * case.correct(choice) for case, choice in zip(batch, choices, strict=True))
            options.append((choices, cost, value))
        updated = {}
        for spent, (value, schedule) in states.items():
            for choices, cost, gain in options:
                total = spent + cost
                if total <= config.budget and (total not in updated or updated[total][0] < value + gain):
                    updated[total] = (value + gain, [*schedule, list(choices)])
        states = updated
    cost, (value, schedule) = max(states.items(), key=lambda item: (item[1][0], -item[0]))
    return {"value": value, "cost": cost, "schedule": schedule,
            "definition": "exact relaxed offline round-bundle DP; no bidding tax or planning for empty rounds"}


def choose_public(public: list[PublicCase], config: StudyConfig, headroom: int,
                  reports: list[PrivateView] | None = None) -> tuple[str, ...]:
    """Typed public-only central interface unless a declared shared-information ablation supplies reports."""
    candidates = []
    for choices, cost in bundles(public, config):
        if cost <= headroom:
            value = sum(expected(case, choice, config, reports[index] if reports else None)
                        for index, (case, choice) in enumerate(zip(public, choices, strict=True)))
            candidates.append((value, -cost, choices))
    return max(candidates)[2] if candidates else ("defer",) * len(public)


@lru_cache(maxsize=512)
def future_budget_values(config: StudyConfig, next_round: int) -> tuple[int, ...]:
    """Expected future value by available budget using declared priors, never future cases.

    Known synchronous arrivals and mandatory-review schedule are public. Unknown
    future task values use the generator's rounded mean (110); future signals and
    provider realizations are not observed. Empty rounds still pay planning tax.
    """
    values = [0] * (config.budget + 1)
    for round_index in reversed(range(next_round, config.rounds)):
        public = [PublicCase(f"forecast-{agent}", agent, round_index, 110,
                             round_index % 2 == 0 or agent == 0, 100, (100,)) for agent in range(3)]
        options = [(cost + 3, sum(expected(case, choice, config)
                                 for case, choice in zip(public, choices, strict=True)))
                   for choices, cost in bundles(public, config)]
        values = [max((gain + values[budget - cost] for cost, gain in options if cost <= budget), default=0)
                  for budget in range(config.budget + 1)]
    return tuple(values)


def choose_paced(public: list[PublicCase], config: StudyConfig, headroom: int,
                 reports: list[PrivateView] | None = None) -> tuple[str, ...]:
    continuation = future_budget_values(config, public[0].round + 1)
    candidates = []
    for choices, cost in bundles(public, config):
        if cost <= headroom:
            current = sum(expected(case, choice, config, reports[index] if reports else None)
                          for index, (case, choice) in enumerate(zip(public, choices, strict=True)))
            candidates.append((current + continuation[headroom - cost], -cost, choices))
    return max(candidates)[2] if candidates else ("defer",) * len(public)


def run_policy(cases: list[Truth], config: StudyConfig, allocator: str) -> dict:
    if allocator not in ALLOCATORS:
        raise ValueError("unknown study allocator")
    remaining = config.budget
    credits = list(config.endowments)
    revenue = 0
    utility = 0
    coordination = 0
    access = [0, 0, 0]
    review_access = [0, 0, 0]
    traces = []
    for round_index in range(config.rounds):
        batch = cases[round_index * 3:round_index * 3 + 3]
        public = [case.public for case in batch]
        authorized_review = review_eligible(public, config)
        planning = min(remaining, len(public))
        remaining -= planning
        coordination += planning
        if planning < len(public):
            break
        if allocator.startswith("central"):
            private = [case.private for case in batch] if allocator.endswith("shared") else None
            chooser = choose_paced if "paced" in allocator else choose_public
            choices = chooser(public, config, remaining, private)
        else:
            private_information = allocator in {"market-private", "decentralized-private-no-market"}
            resource_requests = allocator.startswith("market") or allocator == "decentralized-private-no-market"
            choices = ["defer"] * 3
            bids = []
            for index, case in enumerate(batch):
                private = case.private if private_information else None
                gain = max(0, (expected(case.public, "premium", config, private)
                               - expected(case.public, "cheap", config, private)) // 100)
                bid = gain
                if index == 0 and allocator.startswith("market"):
                    if config.strategy == "shade":
                        bid //= 2
                    elif config.strategy == "overstate":
                        bid *= 3
                    elif config.strategy == "hoard":
                        bid = 0 if round_index < config.rounds // 2 else bid
                bids.append(min(bid, credits[index]) if allocator.startswith("market") else gain)
            if resource_requests:
                eligible = []
                reserved = 0
                fee = config.bid_cost if allocator.startswith("market") else 0
                for index in range(3):
                    bound = execution_cost(public[index], "premium")
                    if (public[index].task_id in authorized_review and bids[index] > 0
                            and remaining >= fee + reserved + bound):
                        remaining -= fee
                        coordination += fee
                        eligible.append(index)
                        reserved += bound
                order = sorted(eligible, key=lambda index: (
                    -bids[index] if allocator.startswith("market") else (index - round_index) % 3,
                    public[index].task_id))
                slots = config.premium_capacity
                reviews = config.mandatory_capacity
                for index in order:
                    cost = execution_cost(public[index], "premium")
                    if slots and remaining >= cost and (not public[index].mandatory or reviews):
                        choices[index] = "premium"
                        remaining -= cost
                        slots -= 1
                        reviews -= int(public[index].mandatory)
                        if allocator.startswith("market"):
                            credits[index] -= bids[index]
                            revenue += bids[index]
                available_order = sorted(range(3), key=lambda index: (-public[index].value, index))
            else:
                available_order = sorted(range(3), key=lambda index: (
                    (index - round_index) % 3 if allocator == "equal" else
                    -public[index].value * (100 if allocator == "evcost" else 1)
                    / (execution_cost(public[index], "cheap") if allocator == "evcost" else 1), index))
                reviews = config.mandatory_capacity
            for index in available_order:
                if choices[index] != "defer" or public[index].task_id not in authorized_review:
                    continue
                allowed = [resource for resource in ("cheap", "consultation", "premium")
                           if remaining >= execution_cost(public[index], resource)
                           and (resource != "premium" or (not resource_requests
                                and choices.count("premium") < config.premium_capacity))
                           and (resource != "consultation"
                                or choices.count("consultation") < config.consultation_capacity)]
                if allowed and (not public[index].mandatory or reviews):
                    private = batch[index].private if private_information else None
                    resource = max(allowed, key=lambda resource: (
                        expected(public[index], resource, config, private) / execution_cost(public[index], resource),
                        -execution_cost(public[index], resource)))
                    choices[index] = resource
                    remaining -= execution_cost(public[index], resource)
                    reviews -= int(public[index].mandatory)
            remaining += sum(execution_cost(case, choice) for case, choice in zip(public, choices, strict=True))
        cost = sum(execution_cost(case, choice) for case, choice in zip(public, choices, strict=True))
        assert cost <= remaining and feasible(public, tuple(choices), config)
        remaining -= cost
        for case, choice in zip(batch, choices, strict=True):
            correct = case.correct(choice)
            utility += case.public.value if correct else 0
            access[case.public.agent] += int(choice != "defer")
            review_access[case.public.agent] += int(choice != "defer" and case.public.mandatory)
            traces.append({"task": case.public.task_id, "choice": choice, "verified": correct,
                           "status": "deferred" if choice == "defer" else "verified" if correct else "incorrect",
                           "value": case.public.value if correct else 0})
    assert sum(credits) + revenue == sum(config.endowments) and remaining >= 0
    denominator = 3 * sum(value * value for value in access)
    return {"allocator": allocator, "verified_value": utility, "total_value": sum(case.public.value for case in cases),
            "modeled_cost": config.budget - remaining, "coordination_cost": coordination,
            "verified_tasks": sum(trace["verified"] for trace in traces), "access": access,
            "review_access": review_access, "unserved": len(cases) - sum(access),
            "served_incorrect": sum(trace["status"] == "incorrect" for trace in traces),
            "deferred": len(cases) - sum(access), "denied": 0, "unresolved": 0,
            "jain_access": sum(access) ** 2 / denominator if denominator else 0,
            "credits_remaining": credits, "market_revenue": revenue, "trace": traces}


def allocation_study(output: Path, *, seeds: int = 30) -> dict:
    if not 1 <= seeds <= 100:
        raise ValueError("bounded study supports 1-100 paired seeds")
    rows = []
    for budget, quality, bid_cost in itertools.product((90, 180, 300), (50, 75, 90), (0, 2, 6)):
        config = StudyConfig(budget=budget, signal_quality=quality, bid_cost=bid_cost)
        for seed in range(seeds):
            cases = study_corpus(seed, config)
            bound = oracle(cases, config)
            for allocator in ALLOCATORS:
                result = run_policy(cases, config, allocator)
                assert result["verified_value"] <= bound["value"]
                rows.append({"seed": seed, "config": asdict(config), "public_corpus_hash": stable_digest([
                    asdict(case.public) for case in cases]),
                    "evaluator_corpus_hash": stable_digest([(asdict(case.public), case.bank_payments,
                                                             case.premium_available) for case in cases]),
                    "signal_corpus_hash": stable_digest([asdict(case.private) for case in cases]),
                    "oracle": bound["value"],
                    **{key: value for key, value in result.items() if key != "trace"}})
    strategic = []
    for strategy in ("unshaded", "shade", "overstate", "hoard"):
        config = StudyConfig(strategy=strategy, signal_quality=90)
        for seed in range(seeds):
            result = run_policy(study_corpus(seed, config), config, "market-private")
            strategic.append({"seed": seed, "strategy": strategy, **result})
    groups = []
    for budget, quality, bid_cost in itertools.product((90, 180, 300), (50, 75, 90), (0, 2, 6)):
        selected = [row for row in rows if (row["config"]["budget"], row["config"]["signal_quality"],
                    row["config"]["bid_cost"]) == (budget, quality, bid_cost)]
        summaries = {}
        for allocator in ALLOCATORS:
            trials = [row for row in selected if row["allocator"] == allocator]
            values = [row["verified_value"] for row in trials]
            summaries[allocator] = {"value_mean": statistics.mean(values),
                                    "value_sd": statistics.stdev(values) if seeds > 1 else None,
                                    "cost_mean": statistics.mean(row["modeled_cost"] for row in trials),
                                    "oracle_ratio_mean": statistics.mean(row["verified_value"] / row["oracle"]
                                                                          for row in trials)}
        groups.append({"budget": budget, "signal_quality": quality, "bid_cost": bid_cost, "summaries": summaries})
    artifact = {"version": STUDY_VERSION, "environment_version": VERSION,
                "created_at": datetime.now(UTC).isoformat(), "code_revision": code_revision(),
                "seeds": seeds, "rows": rows, "groups": groups, "strategic": strategic,
                "execution_mode": "pure bounded research model, not replay of V1 execution ledger",
                "interpretation": "Private-market vs public-central mixes information and mechanism. "
                    "Shared central controls information sharing; paced central uses public arrival priors. "
                    "Private-no-market uses the same local signals, funded premium requests and fallback rule "
                    "but rotates scarce allocation without prices or bid tax. The market contrast includes "
                    "allocation ordering, credit constraints and tax, not price alone.",
                "metric_definitions": {"unserved": "never attempted, including omitted post-exhaustion cases",
                    "served_incorrect": "attempted but independently incorrect", "denied": "zero: no execution API",
                    "unresolved": "zero: research model has known resource results, not external ambiguity"}}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2) + "\n")
    return artifact
