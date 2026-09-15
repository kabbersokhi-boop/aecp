"""Paired-seed sensitivity study of information cost and strategic reporting, without providers."""

import argparse
import gzip
import json
import statistics
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from aecp.determinism import stable_digest
from aecp.engine import code_revision
from aecp.reporting_study import POLICIES, VERSION, ReportingConfig, run, tariffs
from aecp.study import StudyConfig, study_corpus


def study(output: Path, seeds: int):
    if not 1 <= seeds <= 50 or output.exists():
        raise ValueError("use a fresh artifact path and 1-50 seeds")
    trials = []
    summaries = []
    for budget in (90, 180, 300):
        for fee in (0, 2, 6):
            for reliability in (60, 90):
                config = ReportingConfig(StudyConfig(budget=budget, signal_quality=90,
                                         provider_reliability=reliability), report_cost=fee)
                rows = []
                for seed in range(seeds):
                    corpus_hash = stable_digest([asdict(case) for case in study_corpus(seed, config.economy)])
                    for policy in POLICIES:
                        row = {"seed": seed, "config": asdict(config), "corpus_hash": corpus_hash,
                               "tariff_hash": stable_digest(tariffs(seed)), **run(seed, config, policy)}
                        trials.append(row)
                        rows.append(row)
                averages = {}
                for policy in POLICIES:
                    values = [row for row in rows if row["policy"] == policy]
                    averages[policy] = {"mean_verified_value": statistics.mean(row["verified_value"] for row in values),
                                        "sd_verified_value": statistics.stdev(row["verified_value"] for row in values)
                                        if seeds > 1 else 0,
                                        "mean_cost": statistics.mean(row["cost"] for row in values),
                                        "mean_reporting_cost": statistics.mean(row["reporting_cost"] for row in values),
                                        "mean_oracle": statistics.mean(
                                            row["oracle"]["verified_value"] for row in values)}
                paired = {}
                for left, right in (("shared-truthful", "paced-public"), ("shared-strategic", "shared-truthful"),
                                    ("shared-noisy", "shared-truthful"), ("market-private", "private-no-market"),
                                    ("market-private", "private-request-rotation"),
                                    ("shared-selective", "shared-truthful"), ("shared-selective", "paced-public")):
                    differences = [next(row["verified_value"] for row in rows if row["seed"] == seed
                                        and row["policy"] == left)
                                   - next(row["verified_value"] for row in rows if row["seed"] == seed
                                          and row["policy"] == right) for seed in range(seeds)]
                    paired[left + " minus " + right] = {"mean": statistics.mean(differences),
                        "sd": statistics.stdev(differences) if seeds > 1 else 0,
                        "positive": sum(value > 0 for value in differences),
                        "negative": sum(value < 0 for value in differences), "ties": differences.count(0)}
                maximum = max(row["mean_verified_value"] for row in averages.values())
                summaries.append({"config": asdict(config), "policies": averages, "paired": paired,
                                  "winners": [policy for policy, row in averages.items()
                                              if row["mean_verified_value"] == maximum]})
    result = {"version": VERSION, "code_revision": code_revision(),
              "dirty_worktree": bool(subprocess.check_output(["git", "status", "--porcelain"])),
              "timestamp": datetime.now(UTC).isoformat(), "seed_count": seeds, "trials": len(trials),
              "cells": summaries, "provider_calls": 0,
              "limitations": ["synthetic utility, not money",
                              "shared reports assumed truthful except explicit treatment",
                              "strategic overstatement is not equilibrium behavior",
                              "market contrast includes resource selection, ranking, credits and bidding tax",
                              "reporting noise is known to noisy central and its posterior is adjusted",
                              "future central pacing uses public mean arrivals, not actual future outcomes"]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    with gzip.GzipFile(str(output.with_suffix(".trials.json.gz")), "wb", mtime=0) as stream:
        stream.write(json.dumps(trials, separators=(",", ":")).encode())
    return {"trials": len(trials), "cells": len(summaries),
            "cell_wins_including_ties": {policy: sum(policy in cell["winners"] for cell in summaries)
                                         for policy in POLICIES}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("var/evidence-v3/reporting-study.json"))
    parser.add_argument("--seeds", type=int, default=20)
    arguments = parser.parse_args()
    print(json.dumps(study(arguments.output, arguments.seeds)))
