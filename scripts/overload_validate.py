"""Open-loop scheduled arrivals against bounded local admission; no provider/network beyond loopback."""

import argparse
import asyncio
import json
import platform
import tempfile
import threading
import time
from pathlib import Path

from aecp.control import SimulatedAdapter
from aecp.engine import Engine, code_revision
from aecp.performance import summarize
from aecp.server import Application, credentials
from aecp.timing import TransactionTimings


class DelayedAdapter(SimulatedAdapter):
    def execute(self, resource, parameters):
        time.sleep(0.05)
        return super().execute(resource, parameters)


async def phase(application, token, rate, seconds, identity, *, read=False):
    start = time.perf_counter()
    results = []
    pending = set()
    peak_pending = 0
    generator_drops = 0
    before = application.admission_snapshot()

    async def request(index, scheduled):
        launched = time.perf_counter()
        status = 0
        writer = None
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", application.server_port), 5)
            body = json.dumps({"request_id": f"{identity}-{index}", "task_id": "load-task", "resource": "cheap",
                               "parameters": {"invoice_cents": 100, "payments": [100]}}).encode()
            route = "GET /api/v1/system" if read else "POST /api/v1/resource-requests"
            body = b"" if read else body
            header = (f"{route} HTTP/1.1\r\nHost: 127.0.0.1:{application.server_port}\r\n"
                      f"Authorization: Bearer {token}\r\nContent-Type: application/json\r\n"
                      f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n").encode()
            writer.write(header + body)
            await writer.drain()
            response = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 10)
            status = int(response.split(b" ", 2)[1])
            length = next(int(line.split(b":", 1)[1]) for line in response.split(b"\r\n")
                          if line.lower().startswith(b"content-length:"))
            await asyncio.wait_for(reader.readexactly(length), 10)
        except (OSError, TimeoutError, asyncio.IncompleteReadError):
            status = 0
        finally:
            if writer:
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError:
                    pass
        ended = time.perf_counter()
        results.append({"status": status, "latency_ms": (ended - scheduled) * 1000,
                        "execution_ms": (ended - launched) * 1000, "launch_lag_ms": (launched - scheduled) * 1000})

    for index in range(rate * seconds):
        scheduled = start + index / rate
        await asyncio.sleep(max(0, scheduled - time.perf_counter()))
        if len(pending) >= 512:
            generator_drops += 1
            continue
        task = asyncio.create_task(request(index, scheduled))
        pending.add(task)
        task.add_done_callback(pending.discard)
        peak_pending = max(peak_pending, len(pending))
    if pending:
        await asyncio.gather(*pending)
    elapsed = time.perf_counter() - start
    after = application.admission_snapshot()
    successful = [row["latency_ms"] for row in results if row["status"] == 200]
    return {"offered_rate": rate, "arrival_seconds": seconds, "offered": rate * seconds,
            "completed": len(successful), "rejected": sum(row["status"] in {429, 503} for row in results),
            "agent_cap_rejections": sum(row["status"] == 429 for row in results),
            "global_cap_rejections": sum(row["status"] == 503 for row in results),
            "transport_errors": sum(row["status"] == 0 for row in results), "generator_drops": generator_drops,
            "other_http_errors": sum(row["status"] not in {0, 200, 429, 503} for row in results),
            "admitted": after["admitted"] - before["admitted"], "drained_elapsed_seconds": elapsed,
            "completed_per_arrival_second": len(successful) / seconds,
            "peak_generator_pending": peak_pending, "admission": after,
            "successful_latency": summarize(successful, elapsed, []), "requests": results}


def run(output, seconds):
    if not 3 <= seconds <= 30:
        raise ValueError("each phase must last 3-30 seconds")
    with tempfile.TemporaryDirectory(prefix="aecp-overload-") as directory:
        root = Path(directory)
        engine = Engine(root / "state.sqlite3")
        engine.ledger.create_account("load", 100000, unit="SIM_COST_MICRO")
        engine.control.register_task("load", "load-task", "reconcile")
        engine.control.adapter = DelayedAdapter()
        timing = TransactionTimings()
        engine.ledger.transaction_timings = timing
        principals = credentials(root / "capabilities.json")
        principals["passive"]["agent_id"] = "load"
        application = Application(("127.0.0.1", 0), engine, principals, max_connections=4)
        route_timing = TransactionTimings()
        application.route_timings = route_timing
        thread = threading.Thread(target=application.serve_forever, daemon=True)
        thread.start()
        try:
            phases = []
            for index, rate in enumerate((5, 20, 80, 5)):
                result = asyncio.run(phase(application, principals["passive"]["token"], rate, seconds, index))
                result["audit"] = engine.ledger.audit()
                result["authority"] = engine.ledger.account("load")
                phases.append(result)
            evidence = {"version": "open-loop-admission.v2.1", "code_revision": code_revision(),
                        "host": platform.platform(), "phases": phases, "transaction_timing": timing.snapshot(),
                        "mutation_lock_wait_and_route_ms": route_timing.snapshot(),
                        "provider_delay_ms": 50, "provider_calls": 0,
                        "scope": "development host, four admitted connections, zero application waiting queue; "
                                 "kernel TCP backlog and mutation-lock wait remain; not a production SLO"}
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(evidence, indent=2) + "\n")
            return [{key: row[key] for key in ("offered_rate", "completed", "rejected", "transport_errors",
                                              "generator_drops", "audit")} for row in phases]
        finally:
            application.shutdown()
            application.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=15)
    parser.add_argument("--output", type=Path, default=Path("var/evidence-v21/overload.json"))
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.output, arguments.seconds)))
