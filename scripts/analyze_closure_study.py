"""Generate paired causal contrasts and a bounded scarcity/reliability extension."""

from __future__ import annotations

import argparse
import gzip
import itertools
import json
import statistics
from dataclasses import asdict
from pathlib import Path

from aecp.engine import code_revision
from aecp.study import ALLOCATORS, STUDY_VERSION, StudyConfig, oracle, run_policy, study_corpus

CONTRASTS = {
    "private_information_in_market": ("market-private", "market-public"),
    "sharing_with_paced_central": ("central-paced-shared", "central-paced-public"),
    "public_budget_pacing": ("central-paced-public", "central-public"),
    "shared_budget_pacing": ("central-paced-shared", "central-shared"),
    "auction_package_vs_rotating_private": ("market-private", "decentralized-private-no-market"),
    "private_market_vs_paced_shared": ("market-private", "central-paced-shared"),
}


def summarize(rows):
    paired = {(row["seed"], row["allocator"]): row for row in rows}
    contrasts = {}
    for name, (left, right) in CONTRASTS.items():
        differences = [paired[seed, left]["verified_value"] - paired[seed, right]["verified_value"]
                       for seed in sorted({row["seed"] for row in rows})]
        contrasts[name] = {"mean_difference": statistics.mean(differences),
                           "paired_difference_sd": statistics.stdev(differences),
                           "wins": sum(value > 0 for value in differences),
                           "ties": sum(value == 0 for value in differences),
                           "losses": sum(value < 0 for value in differences)}
    return {"contrasts": contrasts, "allocators": {
        allocator: {"value_mean": statistics.mean(row["verified_value"] for row in rows
                                                  if row["allocator"] == allocator),
                    "cost_mean": statistics.mean(row["modeled_cost"] for row in rows
                                                 if row["allocator"] == allocator)} for allocator in ALLOCATORS},
        "oracle_mean": statistics.mean(row["oracle"] for row in rows)}


def analyze(source: Path, output: Path, seeds: int):
    if not 2 <= seeds <= 30:
        raise ValueError("extension is bounded to 2-30 paired seeds")
    original = json.loads(source.read_text())
    cells = []
    for group in original["groups"]:
        rows = [row for row in original["rows"] if all(row["config"][key] == group[key]
                for key in ("budget", "signal_quality", "bid_cost"))]
        cells.append({**{key: group[key] for key in ("budget", "signal_quality", "bid_cost")}, **summarize(rows)})
    extension = []
    extension_cells = []
    for reliability, review_capacity, premium_capacity in itertools.product((50, 90), (0, 1, 2), (0, 1, 2)):
        config = StudyConfig(provider_reliability=reliability, mandatory_capacity=review_capacity,
                             premium_capacity=premium_capacity, signal_quality=90)
        rows = []
        for seed in range(seeds):
            cases = study_corpus(seed, config)
            bound = oracle(cases, config)
            for allocator in ALLOCATORS:
                result = run_policy(cases, config, allocator)
                assert result["verified_value"] <= bound["value"]
                rows.append({"seed": seed, "config": asdict(config), "oracle": bound["value"],
                             **{key: value for key, value in result.items() if key != "trace"}})
        extension.extend(rows)
        extension_cells.append({"config": asdict(config), **summarize(rows)})
    report = {"version": STUDY_VERSION, "code_revision": code_revision(), "primary_trials": len(original["rows"]),
              "primary_cells": cells, "extension_seeds": seeds, "extension_trials": len(extension),
              "extension_cells": extension_cells,
              "interpretation": "Paired descriptive contrasts; cells reuse seeds and are not independent samples. "
              "Auction contrast includes ranking/payment/endowment constraints and tax; not a price-only treatment."}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    output.with_suffix(".rows.json.gz").write_bytes(gzip.compress(json.dumps(extension).encode(), mtime=0))
    return {"primary_trials": len(original["rows"]), "extension_trials": len(extension)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("var/evidence-v21/study.json"))
    parser.add_argument("--output", type=Path, default=Path("var/evidence-v21/causal-analysis.json"))
    parser.add_argument("--seeds", type=int, default=20)
    arguments = parser.parse_args()
    print(json.dumps(analyze(arguments.source, arguments.output, arguments.seeds)))
