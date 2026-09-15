"""Offline experiments, native gateway and financial debugger command line."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from aecp.determinism import stable_digest
from aecp.ledger import BudgetRejected, Ledger


def demo_ledger() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="aecp-") as directory:
        path = Path(directory) / "ledger.sqlite3"
        ledger = Ledger(path)
        ledger.create_account("investigator", 1_000_000, unit="SIM_COST_MICRO")
        ledger.reserve("investigator", "attempt-1", 400_000, task_id="case-1",
                       operation_id="investigate-1", request_hash=stable_digest({"resource": "premium"}))
        ledger.mark_dispatched("attempt-1")
        ledger.mark_unresolved("attempt-1")
        before = ledger.account("investigator")
        recovered = Ledger(path)
        recovered.settle("attempt-1", 250_000)
        try:
            recovered.reserve("investigator", "attempt-2", 800_000, task_id="case-2",
                              operation_id="investigate-2", request_hash="illustrative-request")
        except BudgetRejected:
            denied = True
        else:
            denied = False
        return {"mode": "deterministic-foundation-demo", "real_provider_spend": 0,
                "costs_are_simulated": True, "unresolved_snapshot": before,
                "reconciled_snapshot": recovered.account("investigator"),
                "unfunded_request_denied": denied, "audit": recovered.audit(),
                "events": recovered.events()}


def main() -> None:
    from aecp.engine import SCENARIOS, SCHEDULERS, Engine
    from aecp.experiments import benchmark, stress
    from aecp.server import serve

    parser = argparse.ArgumentParser(description="Economic control plane · deterministic reference application")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("demo-ledger")
    simulation = commands.add_parser("demo")
    simulation.add_argument("--db", type=Path, default=Path("var/demo.sqlite3"))
    simulation.add_argument("--run-id", default="demo")
    simulation.add_argument("--seed", type=int, default=7)
    simulation.add_argument("--budget", type=int, default=450)
    simulation.add_argument("--scenario", choices=SCENARIOS, default="ordinary")
    simulation.add_argument("--scheduler", choices=SCHEDULERS, default="market")
    simulation.add_argument("--style", choices=["adaptive", "conservative", "value", "mixed"], default="adaptive")
    simulation.add_argument("--steps", type=int)
    simulation.add_argument("--artifact", type=Path)
    gateway = commands.add_parser("serve")
    gateway.add_argument("--db", type=Path, default=Path("var/demo.sqlite3"))
    gateway.add_argument("--tokens", type=Path, default=Path("var/local-capabilities.json"))
    gateway.add_argument("--port", type=int, default=8765)
    trials = commands.add_parser("benchmark")
    trials.add_argument("--output", type=Path, default=Path("var/benchmark"))
    trials.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    trials.add_argument("--budgets", type=int, nargs="+", default=[180, 300, 450])
    trials.add_argument("--scenario", choices=SCENARIOS, default="burst")
    failures = commands.add_parser("stress")
    failures.add_argument("--db", type=Path)
    study = commands.add_parser("allocation-study")
    study.add_argument("--output", type=Path, default=Path("var/evidence-v21/study.json"))
    study.add_argument("--seeds", type=int, default=30)
    load = commands.add_parser("performance")
    load.add_argument("--output", type=Path, default=Path("var/evidence-v2/performance.json"))
    load.add_argument("--operations", type=int, default=300)
    discovery = commands.add_parser("nim-discover")
    discovery.add_argument("--output", type=Path, default=Path("var/nim-selected.json"))
    args = parser.parse_args()
    if hasattr(args, "db") and args.db is not None:
        args.db.parent.mkdir(parents=True, exist_ok=True)
    if args.command == "allocation-study":
        from aecp.study import allocation_study
        artifact = allocation_study(args.output, seeds=args.seeds)
        result = {"artifact": str(args.output), "trials": len(artifact["rows"]), "groups": len(artifact["groups"])}
    elif args.command == "performance":
        from aecp.performance import performance
        artifact = performance(args.output, operations=args.operations)
        result = {"artifact": str(args.output), "modes": len(artifact["results"])}
    elif args.command == "nim-discover":
        from aecp.nim import discover
        artifact = discover(args.output)
        result = {"artifact": str(args.output), "selected_model": artifact["selected_model"]}
    elif args.command == "demo-ledger":
        result = demo_ledger()
    elif args.command == "demo":
        engine = Engine(args.db)
        try:
            previous = engine.run(args.run_id)
        except KeyError:
            previous = None
        engine.create(args.run_id, seed=args.seed, budget=args.budget, scenario=args.scenario,
                      scheduler=args.scheduler, style=args.style)
        if args.steps is None:
            snapshot = engine.complete(args.run_id)
        else:
            if args.steps < 0:
                parser.error("steps must be nonnegative")
            for _step in range(args.steps):
                engine.step(args.run_id)
            snapshot = engine.snapshot(args.run_id)
        if args.artifact:
            args.artifact.parent.mkdir(parents=True, exist_ok=True)
            args.artifact.write_text(json.dumps(snapshot, sort_keys=True, indent=2) + "\n")
        result = {"run_id": args.run_id, "digest": snapshot["digest"], "metrics": snapshot["metrics"],
                  "audit": snapshot["audit"], "checkpoint": snapshot["run"]["checkpoint"],
                  "execution": "recorded_replay" if previous and previous["checkpoint"]["finished"] else
                  "restart_resume" if previous else "deterministic_reproduction"}
    elif args.command == "serve":
        serve(args.db, args.tokens, args.port)
        return
    elif args.command == "benchmark":
        artifact = benchmark(args.output, args.seeds, args.budgets, args.scenario)
        result = {"aggregates": artifact["aggregates"], "artifact": str(args.output / "benchmark.json")}
    else:
        if args.db:
            result = stress(args.db)
        else:
            with tempfile.TemporaryDirectory(prefix="aecp-stress-") as directory:
                result = stress(Path(directory) / "stress.sqlite3")
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
