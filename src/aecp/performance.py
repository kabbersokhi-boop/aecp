"""Closed-loop local contention measurements; never claims production or provider throughput."""

from __future__ import annotations

import json
import math
import platform
import secrets
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from aecp.client import Client
from aecp.engine import Engine, code_revision
from aecp.ledger import Ledger
from aecp.server import Application, credentials, provision


def summarize(samples: list[float], elapsed: float, errors: list[str]) -> dict:
    ordered = sorted(samples)

    def quantile(fraction):
        return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)] if ordered else None

    return {"operations": len(samples), "wall_seconds": elapsed, "operations_per_second": len(samples) / elapsed,
            "p50_ms": quantile(0.50), "p95_ms": quantile(0.95), "p99_ms": quantile(0.99),
            "errors": errors, "latency_samples_ms": samples}


def performance(output: Path, *, operations: int = 300, concurrency: tuple[int, ...] = (1, 4, 16)) -> dict:
    if not 20 <= operations <= 400 or not concurrency or any(not 1 <= workers <= 32 for workers in concurrency):
        raise ValueError("bounded load study requires 20-400 operations and 1-32 workers")
    results = []
    with tempfile.TemporaryDirectory(prefix="aecp-load-") as directory:
        for mode in ("reservation", "governed-http", "http-read-under-write"):
            for workers in concurrency:
                path = Path(directory) / f"{mode}-{workers}.sqlite3"
                server = None
                thread = None
                client = None
                if mode == "reservation":
                    ledger = Ledger(path)
                    ledger.create_account("load", operations, unit="SIM_COST_MICRO")
                else:
                    engine = Engine(path)
                    provision(engine)
                    ledger = engine.ledger
                    principals = credentials(Path(directory) / f"{mode}-{workers}.capabilities.json")
                    ledger.create_account("gateway/load", operations * 4, unit="SIM_COST_MICRO", parent_id="gateway")
                    engine.control.register_task("gateway/load", "external-invoice-1", "reconcile")
                    principals["load"] = {"token": secrets.token_urlsafe(32), "role": "agent",
                                          "agent_id": "gateway/load"}
                    server = Application(("127.0.0.1", 0), engine, principals)
                    thread = threading.Thread(target=server.serve_forever, daemon=True)
                    thread.start()
                    client = Client(f"http://127.0.0.1:{server.server_port}", principals["load"]["token"])
                errors = []
                reads = []
                writes = []

                def operation(index, mode=mode, ledger=ledger, client=client, errors=errors,
                              reads=reads, writes=writes):
                    started = time.perf_counter()
                    kind = "write"
                    try:
                        if mode == "reservation":
                            ledger.reserve("load", f"request-{index}", 1, task_id="load", operation_id="reserve",
                                           request_hash=f"request-{index}")
                        elif mode == "http-read-under-write" and index % 2 == 0:
                            kind = "read"
                            client.budget()
                        else:
                            client.execute(f"request-{index}", "external-invoice-1", "cheap",
                                           {"invoice_cents": 100, "payments": [100]})
                    except Exception as error:
                        errors.append(type(error).__name__)
                    elapsed = (time.perf_counter() - started) * 1000
                    (reads if kind == "read" else writes).append(elapsed)
                    return elapsed

                started = time.perf_counter()
                try:
                    with ThreadPoolExecutor(max_workers=workers) as pool:
                        samples = list(pool.map(operation, range(operations)))
                    elapsed = time.perf_counter() - started
                finally:
                    if server:
                        server.shutdown()
                        server.server_close()
                        thread.join(timeout=5)
                result = {"mode": mode, "concurrency": workers, **summarize(samples, elapsed, errors),
                          "read_latency_ms": reads, "write_latency_ms": writes, "audit": ledger.audit()}
                assert result["audit"]["consistent"] and result["audit"]["within_funding"]
                results.append(result)
    artifact = {"created_at": datetime.now(UTC).isoformat(), "code_revision": code_revision(),
                "python": platform.python_version(), "platform": platform.platform(), "processor": platform.machine(),
                "sqlite_durability": "WAL + synchronous FULL; local temporary filesystem",
                "method": "bounded closed-loop ThreadPoolExecutor; timing starts inside each worker; "
                          "no coordinated-omission correction, no warmup; local deterministic provider only",
                "provider_network_calls": 0, "results": results}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2) + "\n")
    return artifact
