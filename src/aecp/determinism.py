"""Versioned, semantic randomness independent of Python hash and call order.

This is a reproducibility utility, not cryptographic authentication or an LLM.
Policies must not receive the environment's secret outcome seed or hidden state.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA = "aecp.semantic-random.v1"


def canonical_json(value: Any) -> str:
    """Encode JSON values predictably; reject NaN and infinity.

    Monetary values and deterministic decision thresholds should use integers.
    Callers should keep wall-clock time and operational telemetry out of digests.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def semantic_u64(seed: int, *coordinates: str | int) -> int:
    """Return a stable draw keyed by meaning, never by execution order.

    Use coordinates such as ("outcome", task_id, resource_id, attempt_number).
    Include a policy name only for policy-private randomness, not for shared
    exogenous outcomes in a paired comparison.
    """
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError("seed must be an unsigned 64-bit integer")
    if not coordinates or any(type(item) not in (str, int) for item in coordinates):
        raise ValueError("coordinates must be a non-empty sequence of strings and integers")
    payload = canonical_json([SCHEMA, seed, list(coordinates)]).encode("ascii")
    return int.from_bytes(hashlib.blake2b(payload, digest_size=8).digest(), "big")


def bernoulli_bps(probability_bps: int, seed: int, *coordinates: str | int) -> bool:
    """Sample a Bernoulli event using integer basis points and a semantic draw."""
    if type(probability_bps) is not int or not 0 <= probability_bps <= 10_000:
        raise ValueError("probability_bps must be an integer in [0, 10000]")
    draw = semantic_u64(seed, *coordinates)
    return draw * 10_000 < probability_bps * 2**64


def stable_digest(value: Any) -> str:
    """Hash canonical artifacts; not a signature or a tamper-proof audit claim."""
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()
