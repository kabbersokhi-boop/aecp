"""Paired-seed experiments and reproducible safety stress evidence."""

from __future__ import annotations

import json
import statistics
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from aecp.engine import SCHEDULERS, Engine, code_revision
from aecp.ledger import BudgetRejected, InvalidTransition, Ledger
from aecp.market import Market


def benchmark(output: Path, seeds: list[int], budgets: list[int], scenario: str = "burst") -> dict:
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for budget in budgets:
        for seed in seeds:
            for scheduler in SCHEDULERS:
                with tempfile.TemporaryDirectory(prefix="aecp-trial-") as directory:
                    engine = Engine(Path(directory) / "state.sqlite3")
                    engine.create("trial", seed=seed, budget=budget, scenario=scenario, scheduler=scheduler)
                    result = engine.complete("trial")
                    rows.append({"seed": seed, "budget": budget, "scheduler": scheduler,
                                 "scenario": scenario, "digest": result["digest"],
                                 "corpus_hash": result["run"]["config"]["corpus_hash"],
                                 "metrics": result["metrics"], "audit": result["audit"],
                                 "credit_conservation": result["market"]["consistent"] and
                                 result["market"]["total"] == result["market"]["issued"]})
    aggregates = []
    for budget in budgets:
        for scheduler in SCHEDULERS:
            selected = [row for row in rows if row["budget"] == budget and row["scheduler"] == scheduler]
            values = [row["metrics"]["verified_value"] for row in selected]
            costs = [row["metrics"]["modeled_cost"] for row in selected]
            paired = [row["metrics"]["verified_value"] - next(
                central["metrics"]["verified_value"] for central in rows if central["budget"] == budget
                and central["seed"] == row["seed"] and central["scheduler"] == "central") for row in selected]
            summaries = {}
            for metric in selected[0]["metrics"]:
                samples = [row["metrics"][metric] for row in selected
                           if type(row["metrics"][metric]) in {int, float}]
                if samples:
                    summaries[metric] = {"mean": statistics.mean(samples),
                                         "sd": statistics.stdev(samples) if len(samples) > 1 else None,
                                         "n": len(samples)}
            aggregates.append({"budget": budget, "scheduler": scheduler, "n": len(values),
                               "verified_value_mean": statistics.mean(values),
                               "verified_value_sd": statistics.stdev(values) if len(values) > 1 else None,
                               "modeled_cost_mean": statistics.mean(costs),
                               "paired_value_delta_vs_central_mean": statistics.mean(paired),
                               "paired_delta_sd": statistics.stdev(paired) if len(paired) > 1 else None,
                               "metric_summaries": summaries})
    artifact = {"method": "paired-seed deterministic reruns; sample SD, no significance claim",
                "created_at": datetime.now(UTC).isoformat(), "code_revision": code_revision(),
                "scenario": scenario, "seeds": seeds, "budgets": budgets,
                "policy": "adaptive", "rows": rows, "aggregates": aggregates,
                "actual_cash_spend": 0, "cost_unit": "SIM_COST_MICRO"}
    (output / "benchmark.json").write_text(json.dumps(artifact, sort_keys=True, indent=2) + "\n")
    return artifact


def stress(path: Path) -> dict:
    ledger = Ledger(path)
    ledger.create_account("stress", 100, unit="SIM_COST_MICRO")
    for index in range(8):
        ledger.create_account(f"child-{index}", 100, unit="SIM_COST_MICRO", parent_id="stress")

    def attempt(index: int) -> bool:
        try:
            ledger.reserve(f"child-{index % 8}", f"attempt-{index}", 7, task_id="concurrency",
                           operation_id="request", request_hash=f"hash-{index}")
            return True
        except BudgetRejected:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(40)))
    concurrency = {"requests": 40, "admitted": sum(results), "denied": 40 - sum(results),
                   "reserved": ledger.account("stress")["reserved"], "funded": 100,
                   "prevented_unfunded_exposure": (40 - sum(results)) * 7}
    with ledger._transaction() as connection:
        holds = [row[0] for row in connection.execute("SELECT id FROM holds ORDER BY id")]
    ledger.mark_dispatched(holds[0])
    recovered = Ledger(path)
    recovered.mark_unresolved(holds[0])
    for identity in holds[1:]:
        recovered.release(identity)
    liability = recovered.account("stress")["reserved"]
    no_timeout_refund = False
    try:
        recovered.release(holds[0])
    except InvalidTransition:
        no_timeout_refund = True
    for index in range(10):
        identity = f"retry-{index}"
        try:
            recovered.reserve("child-0", identity, 10, task_id="retries", operation_id="retry",
                              request_hash=identity)
            recovered.mark_dispatched(identity)
            recovered.mark_unresolved(identity)
        except BudgetRejected:
            break
    malicious_denied = 0
    for amount in (-1, True, 1.5, 2**63, 1000000):
        try:
            recovered.reserve("child-1", f"malicious-{amount}", amount, task_id="invalid",
                              operation_id="bad", request_hash="bad")
        except (ValueError, BudgetRejected):
            malicious_denied += 1
    recovered.set_lifecycle("stress", "SUSPENDED")
    spawn_denied = False
    try:
        recovered.create_account("spawn-after-suspension", 100, unit="SIM_COST_MICRO", parent_id="stress")
    except BudgetRejected:
        spawn_denied = True
    market = Market(recovered)
    recovered.create_account("hoarder", 50, unit="SIM_COST_MICRO")
    market.endow("credit-treasury", 100)
    market.transfer("endow-hoarder", "credit-treasury", "hoarder", 100)
    recovered.reserve("hoarder", "hoard", 14, task_id="hoard", operation_id="premium", request_hash="h",
                      expires_at=2, resource="premium")
    market.open("hoarding", 1, 2)
    market.bid("hoard-bid", "hoarding", "hoarder", 100, "hoard", 0)
    market.clear("hoarding", 0)
    market.expire(2)
    return {"concurrent_descendants": concurrency, "restart_preserved_liability": liability,
            "timeout_refund_prevented": no_timeout_refund,
            "retry_pressure_exposure": recovered.account("stress")["reserved"],
            "malicious_requests_denied": malicious_denied, "suspended_spawn_denied": spawn_denied,
            "hoarding_expired": recovered.reservation("hoard")["state"] == "RELEASED",
            "market_conserved": market.snapshot()["consistent"], "audit": recovered.audit()}
