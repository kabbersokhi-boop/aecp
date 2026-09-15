"""Interpretable policies consuming permitted observations only."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from aecp.workload import Observation

VERSION = "policies.v1"
COSTS = {"cheap": 4, "premium": 14, "consultation": 24, "planning": 1, "bidding": 2, "verification": 2,
         "mandatory_review": 3}


@dataclass
class Decision:
    resource: str
    bid: int
    expected_value: int
    explanation: dict


@dataclass
class Policy:
    style: str
    beliefs: dict[str, list[int]] = field(default_factory=dict)

    def probability(self, resource: str, document_status: str) -> int:
        prior = [9, 1] if resource != "cheap" or document_status == "complete" else [1, 3]
        success, failure = self.beliefs.get(f"{resource}:{document_status}", prior)
        delivered, unavailable = self.beliefs.get(f"delivery:{resource}", [9, 1])
        return 10000 * success * delivered // ((success + failure) * (delivered + unavailable))

    def choose(self, observation: Observation, headroom: int, tick: int) -> Decision:
        candidates = [resource for resource in ("cheap", "premium", "consultation")
                      if COSTS[resource] + COSTS["verification"] + COSTS["planning"] <= headroom]
        if tick >= observation.deadline or not candidates:
            return Decision("defer", 0, 0, {"reason": "deadline or insufficient authority"})
        if self.style == "conservative":
            resource = "cheap" if observation.document_status == "complete" else "defer"
        elif self.style == "value":
            resource = "premium" if observation.document_status == "partial" else "cheap"
            if resource not in candidates or observation.value < COSTS.get(resource, 0) * 2:
                resource = "defer"
        elif self.style == "adaptive":
            resource = max(candidates, key=lambda option: (
                observation.value * self.probability(option, observation.document_status) // 10000
                - COSTS[option], -COSTS[option]
            ))
        else:
            raise ValueError("unknown policy")
        probability = self.probability(resource, observation.document_status) if resource != "defer" else 0
        expected = observation.value * probability // 10000
        bid = max(1, expected - COSTS.get(resource, 0)) if resource != "defer" else 0
        return Decision(resource, bid, expected, {
            "style": self.style, "observation": asdict(observation), "headroom": headroom,
            "tick": tick, "probability_bps": probability, "beliefs": dict(self.beliefs),
            "rule": "expected utility minus modeled resource cost" if self.style == "adaptive" else self.style,
        })

    def observe(self, resource: str, document_status: str, verified: bool) -> None:
        if self.style != "adaptive":
            return
        key = f"{resource}:{document_status}"
        prior = [9, 1] if resource != "cheap" or document_status == "complete" else [1, 3]
        posterior = self.beliefs.setdefault(key, prior.copy())
        posterior[0 if verified else 1] += 1

    def observe_delivery(self, resource: str, delivered: bool) -> None:
        """A missing response is evidence about availability, not hidden task correctness."""
        if self.style == "adaptive":
            posterior = self.beliefs.setdefault(f"delivery:{resource}", [9, 1])
            posterior[0 if delivered else 1] += 1
