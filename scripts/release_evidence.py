"""Rebuild bounded release scenario, policy, stress and provenance evidence offline."""

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from aecp.engine import SCENARIOS, Engine, code_revision
from aecp.experiments import stress


def main() -> None:
    output = Path("docs/reports")
    output.mkdir(parents=True, exist_ok=True)
    metadata = {"source_revision": code_revision(), "created_at": datetime.now(UTC).isoformat(),
                "seed": 7, "budget": 450, "mode": "deterministic_reproduction"}

    def write(name: str, results: object) -> None:
        (output / name).write_text(json.dumps({**metadata, "results": results}, indent=2, sort_keys=True) + "\n")

    scenarios = []
    policies = []
    with tempfile.TemporaryDirectory(prefix="aecp-release-") as directory:
        for scenario in SCENARIOS:
            engine = Engine(Path(directory) / f"{scenario}.sqlite3")
            engine.create(scenario, seed=7, budget=450, scenario=scenario)
            snapshot = engine.complete(scenario)
            assert snapshot["audit"]["consistent"] and snapshot["audit"]["within_funding"]
            assert snapshot["market"]["consistent"]
            scenarios.append({"scenario": scenario, "run": snapshot["run"], "metrics": snapshot["metrics"],
                              "digest": snapshot["digest"], "audit": snapshot["audit"]})
            if scenario == "outage":
                trace = next(trace for trace in snapshot["traces"] if trace["status"] == "UNRESOLVED")
                write("SAMPLE_TRACE.json", {"task": trace, "snapshot": snapshot})
        for style in ("conservative", "value", "adaptive"):
            engine = Engine(Path(directory) / f"policy-{style}.sqlite3")
            engine.create(style, seed=7, budget=450, style=style)
            snapshot = engine.complete(style)
            policies.append({"style": style, "metrics": snapshot["metrics"], "digest": snapshot["digest"],
                             "beliefs": snapshot["run"]["checkpoint"]["beliefs"]})
        write("STRESS.json", stress(Path(directory) / "stress.sqlite3"))
    write("SCENARIOS.json", scenarios)
    write("POLICIES.json", policies)
    print(json.dumps({"scenarios": len(scenarios), "policies": len(policies), "source": code_revision()}))


if __name__ == "__main__":
    main()
