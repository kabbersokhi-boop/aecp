"""Explicitly opt-in bounded NIM evidence, independent consumer and real process-death recovery."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from unittest.mock import patch

from aecp.client import Client
from aecp.control import ControlPlane
from aecp.engine import Engine, code_revision
from aecp.ledger import Ledger
from aecp.live import LiveTasks
from aecp.nim import DEFAULT_BASE, NimAdapter, NimTransport
from aecp.server import Application, credentials, provision


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def adapter(model):
    return NimAdapter(model, NimTransport(base_url=os.environ.get("AECP_NIM_BASE_URL", DEFAULT_BASE)))


def crash_worker(database: Path, model: str, boundary: str) -> None:
    control = ControlPlane(Ledger(database))
    control.adapters["nim_chat"] = adapter(model)
    parameters = {"model": model, "messages": [{"role": "system", "content": "Return JSON only, no markdown."},
                  {"role": "user", "content": 'Invoice 100, payments [100]. Return {"resolution":"matched"}.'}],
                  "max_tokens": 48, "temperature": 0}
    control.prepare(boundary, "crash-agent", "crash-task", "nim_chat", parameters, now=0, expires_at=10)
    if boundary == "after-receipt":
        with patch.object(control.ledger, "settle", side_effect=lambda *args: os._exit(73)):
            control.execute(boundary, "crash-agent")
    else:
        original = control.adapters["nim_chat"].execute

        def lose_response(*args):
            original(*args)
            os._exit(74)

        with patch.object(control.adapters["nim_chat"], "execute", side_effect=lose_response):
            control.execute(boundary, "crash-agent")
    raise RuntimeError("crash boundary was not reached; inspect provider failure journal")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("var/live-v2.sqlite3"))
    parser.add_argument("--output", type=Path, default=Path("var/evidence-v2/live.json"))
    parser.add_argument("--consumer-python", default=sys.executable)
    parser.add_argument("--crash-worker", choices=("after-receipt", "before-receipt"))
    args = parser.parse_args()
    if os.environ.get("AECP_ENABLE_LIVE_NIM") != "1":
        parser.error("live validation requires AECP_ENABLE_LIVE_NIM=1; no requests made")
    model = os.environ.get("AECP_NIM_MODEL")
    if not model:
        parser.error("set AECP_NIM_MODEL to the discovered working model")
    if args.crash_worker:
        crash_worker(args.db, model, args.crash_worker)
        return
    if args.db.exists():
        parser.error("use a fresh --db path; live validation never silently repeats an existing experiment")
    args.db.parent.mkdir(parents=True, exist_ok=True)
    journal = Path("var/nim-requests.jsonl")
    journal_before = len(journal.read_text().splitlines()) if journal.exists() else 0
    engine = Engine(args.db)
    provision(engine)
    engine.create("offline-reference", seed=7, count=6)
    engine.complete("offline-reference")
    engine.control.adapters["nim_chat"] = adapter(model)
    principals = credentials(args.db.with_suffix(".capabilities.json"))
    server = Application(("127.0.0.1", 0), engine, principals, token_file=args.db.with_suffix(".capabilities.json"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    operator = Client(base, principals["operator"]["token"])
    consumer_results = []
    script = Path("examples/openai_consumer.py").resolve()
    try:
        for trial, name in enumerate(("live-first", "live-repeat", "denied-consumer")):
            identity = operator.call("/api/v1/admin/agents", {"name": name, "budget": 1 if trial == 2 else 850})
            operator.call("/api/v1/admin/live-cases", {"agent_id": identity["agent_id"], "seed": 7, "count": 8})
            environment = {key: os.environ[key] for key in ("PATH", "HOME", "LANG", "LD_LIBRARY_PATH")
                           if key in os.environ}
            environment.update(AECP_URL=base, AECP_AGENT_TOKEN=identity["token"], AECP_NIM_MODEL=model,
                               AECP_CASE_LIMIT="1" if trial == 2 else "6", AECP_ATTEMPT_PREFIX=name,
                               AECP_CONSUMER_POLICY="hybrid" if trial == 1 else "llm")
            completed = subprocess.run([args.consumer_python, str(script)], env=environment, cwd="/tmp",
                                       capture_output=True, text=True, timeout=360)
            if completed.returncode:
                raise RuntimeError("independent consumer failed; stderr suppressed to protect credentials")
            result = json.loads(completed.stdout)
            require(not result["provider_credential_present"], "consumer inherited provider credentials")
            if trial == 2:
                require(result["results"][0]["denied_status"] == 409, "budget denial not demonstrated")
            else:
                require(len(result["results"]) == 6 and all("usage" in item for item in result["results"]),
                        "consumer did not finish six governed cases")
            consumer_results.append(result)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    engine.ledger.create_account("crash-agent", 2000, unit="SIM_COST_MICRO")
    engine.control.register_task("crash-agent", "crash-task", "reconcile")
    recovery = []
    for boundary, exit_code in (("after-receipt", 73), ("before-receipt", 74)):
        completed = subprocess.run([sys.executable, __file__, "--db", str(args.db), "--crash-worker", boundary],
                                   env=os.environ, timeout=90, capture_output=True)
        require(completed.returncode == exit_code, "provider crash checkpoint not reached")
        recovered = ControlPlane(Ledger(args.db))
        before = recovered.request(boundary, "crash-agent")
        result = recovered.execute(boundary, "crash-agent")
        recovered.ledger.expire(100)
        require(result["reservation"]["state"] == ("SETTLED" if boundary == "after-receipt" else "UNRESOLVED"),
                "recovery failed to preserve/reconcile liability")
        recovery.append({"boundary": boundary, "process_exit": exit_code, "before": before, "after": result,
                         "after_expiry": recovered.ledger.reservation(boundary),
                         "recovery_adapter_configured": False})
    records = [json.loads(line) for line in journal.read_text().splitlines()[journal_before:]]
    dispatches = [record for record in records if record["phase"] == "dispatch"]
    workload_calls = sum(bool(item.get("usage")) for trial in consumer_results for item in trial["results"])
    require(len(dispatches) == workload_calls + len(recovery), "provider request journal count disagrees with evidence")
    artifact = {"code_revision": code_revision(), "selected_model": model, "consumer_trials": consumer_results,
                "snapshot": LiveTasks(engine.control).snapshot(), "recovery": recovery,
                "live_workload_calls": workload_calls, "real_crash_calls": len(recovery), "actual_cash_spend": 0,
                "provider_journal": records,
                "consumer_is_external_adoption": False, "consumer_dependency": "OpenAI Python SDK, no AECP import",
                "database": str(args.db), "cash_basis": "NVIDIA free prototype endpoint, no invoice"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n")
    print(json.dumps({"artifact": str(args.output), "model": model, "workload_calls": workload_calls,
                      "crash_calls": len(recovery),
                      "recovery": [item["after"]["reservation"]["state"] for item in recovery]}))


if __name__ == "__main__":
    main()
