"""Open-loop authenticated noisy-neighbour test, with dashboard reads and post-overload recovery."""

import argparse
import asyncio
import json
import secrets
import tempfile
import threading
from pathlib import Path

from overload_validate import DelayedAdapter, phase

from aecp.engine import Engine, code_revision
from aecp.server import Application, credentials
from aecp.timing import TransactionTimings


def run(output: Path, seconds: int) -> dict:
    if not 3 <= seconds <= 30 or output.exists():
        raise ValueError("use a fresh artifact path and a bounded 3-30 second interval")
    with tempfile.TemporaryDirectory(prefix="aecp-fairness-") as directory:
        root = Path(directory)
        engine = Engine(root / "state.sqlite3")
        engine.ledger.create_account("load", 100000, unit="SIM_COST_MICRO")
        engine.control.adapter = DelayedAdapter()
        principals = credentials(root / "capabilities.json")
        rates = {"noisy": 80, "steady-a": 5, "steady-b": 5, "steady-c": 5}
        for name in rates:
            agent = "load/" + name
            engine.ledger.create_account(agent, 25000, unit="SIM_COST_MICRO", parent_id="load")
            engine.control.register_task(agent, "load-task", "reconcile")
            principals[name] = {"role": "agent", "agent_id": agent, "token": secrets.token_urlsafe(32)}
        application = Application(("127.0.0.1", 0), engine, principals, max_connections=16, max_agent_requests=2)
        engine.ledger.transaction_timings = TransactionTimings()
        application.route_timings = TransactionTimings()
        thread = threading.Thread(target=application.serve_forever, daemon=True)
        thread.start()

        async def arrivals():
            return await asyncio.gather(
                *(phase(application, principals[name]["token"], rate, seconds, name)
                  for name, rate in rates.items()),
                phase(application, principals["operator"]["token"], 5, seconds, "dashboard", read=True))

        try:
            results = asyncio.run(arrivals())
            recovery = asyncio.run(phase(application, principals["noisy"]["token"], 5, 3, "recovery"))
            result = {"version": "authenticated-fairness.v3", "code_revision": code_revision(),
                      "agents": dict(zip(rates, results[:-1], strict=True)), "dashboard": results[-1],
                      "recovery": recovery, "admission": application.admission_snapshot(),
                      "audit": engine.ledger.audit(), "authority": engine.ledger.account("load"),
                      "sqlite_timing": engine.ledger.transaction_timings.snapshot(),
                      "route_timing": application.route_timings.snapshot(), "provider_delay_ms": 50,
                      "provider_calls": 0,
                      "scope": "authenticated request fairness; not protection against raw socket flooding"}
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2) + "\n")
            return {"agents": {name: {key: row[key] for key in ("offered", "completed", "rejected",
                                      "agent_cap_rejections", "transport_errors")}
                               for name, row in result["agents"].items()},
                    "dashboard_completed": result["dashboard"]["completed"], "audit": result["audit"],
                    "remaining_exposure": result["authority"]["reserved"]}
        finally:
            application.shutdown()
            application.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("var/evidence-v3/fairness.json"))
    parser.add_argument("--seconds", type=int, default=15)
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.output, arguments.seconds)))
