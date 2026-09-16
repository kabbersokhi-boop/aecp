"""Run the offline failure contract and bounded cost-of-safety study."""

import argparse
import json
from pathlib import Path

from aecp.failure_conformance import run_conformance, run_cost_of_safety

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("benchmark", "cost-study"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    arguments = parser.parse_args()
    if arguments.command == "benchmark":
        result = run_conformance(arguments.output)
        summary = {"scenarios": len(result["scenarios"]), "controls": list(result["controls"]),
                   "provider_calls": result["provider_calls"]}
    else:
        result = run_cost_of_safety(arguments.output, seeds=tuple(arguments.seeds))
        summary = {"trials": result["trials"], "aggregates": result["aggregates"],
                   "provider_calls": result["provider_calls"]}
    print(json.dumps(summary, sort_keys=True))
