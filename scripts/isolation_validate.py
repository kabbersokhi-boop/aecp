"""Execute a public-interface consumer in a new filesystem, PID and network namespace."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import selectors
import socket
import socketserver
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import aecp
from aecp.engine import Engine, code_revision
from aecp.server import Application, credentials, provision


class FixedRelay(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True

    def __init__(self, path, destination):
        self.destination = destination
        self.capacity = threading.BoundedSemaphore(8)
        super().__init__(path, RelayHandler)

    def process_request(self, request, address):
        if not self.capacity.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.capacity.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.capacity.release()


class RelayHandler(socketserver.BaseRequestHandler):
    def handle(self):
        with socket.create_connection(self.server.destination, timeout=90) as upstream:
            self.request.settimeout(90)
            with selectors.DefaultSelector() as selector:
                selector.register(self.request, selectors.EVENT_READ, upstream)
                selector.register(upstream, selectors.EVENT_READ, self.request)
                while events := selector.select(timeout=90):
                    for key, _mask in events:
                        data = key.fileobj.recv(65536)
                        if not data:
                            return
                        key.data.sendall(data)


def validate(output: Path, consumer_directory: Path | None = None) -> dict:
    with tempfile.TemporaryDirectory(prefix="aecp-isolation-") as directory:
        root = Path(directory)
        database = root / "trusted.sqlite3"
        capabilities = root / "capabilities.json"
        engine = Engine(database)
        provision(engine)
        principals = credentials(capabilities)
        agent = "sandbox/worker"
        engine.ledger.create_account(agent, 200, unit="SIM_COST_MICRO", parent_id="gateway")
        principals["passive"]["agent_id"] = agent
        capabilities.write_text(json.dumps(principals))
        engine.control.register_task(agent, "isolation-unknown", "reconcile")
        engine.control.prepare("isolation-uncertain", agent, "isolation-unknown", "cheap",
                               {"invoice_cents": 100, "payments": [100]}, expires_at=2**53)
        engine.control.execute("isolation-uncertain", agent, ambiguous=True)
        engine = Engine(database)
        application = Application(("127.0.0.1", 0), engine, principals)
        application.semantic_tasks.register(agent, "development")
        gateway_thread = threading.Thread(target=application.serve_forever, daemon=True)
        gateway_thread.start()
        relay = FixedRelay(str(root / "relay.sock"), ("127.0.0.1", application.server_port))
        relay_thread = threading.Thread(target=relay.serve_forever, daemon=True)
        relay_thread.start()
        token = root / "agent-token"
        token.write_text(principals["passive"]["token"])
        token.chmod(0o600)
        configuration = root / "configuration.json"
        configuration.write_text(json.dumps({"url": f"http://127.0.0.1:{application.server_port}",
            "forbidden_paths": {"database_unreadable": str(database), "capabilities_unreadable": str(capabilities)}}))
        consumer = (consumer_directory or Path(__file__).resolve().parents[1] / "examples/semantic_consumer").resolve()
        if not (consumer / "isolation_probe.py").is_file():
            raise ValueError("consumer directory must contain the public integration example")
        command = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session", "--ro-bind", "/usr", "/usr",
                   "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib",
                   "--symlink", "usr/lib", "/lib64", "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                   "--ro-bind", str(consumer), "/app", "--ro-bind", str(token), "/agent-token",
                   "--ro-bind", str(configuration), "/configuration.json",
                   "--ro-bind", str(root / "relay.sock"), "/gateway.sock", "--clearenv", "--chdir", "/app",
                   "/usr/bin/python3", "-B", "/app/isolation_probe.py", "/configuration.json"]
        try:
            started = time.perf_counter()
            process = subprocess.run(command, env={"PATH": os.defpath}, capture_output=True, text=True, timeout=120)
            if process.returncode:
                raise RuntimeError(f"isolation consumer failed: exit {process.returncode}; {process.stderr[:1000]}")
            evidence = json.loads(process.stdout)
            evidence["operator_evaluation"] = application.semantic_tasks.snapshot()
            evidence["audit"] = engine.ledger.audit()
            evidence["boundary"] = "bubblewrap mount/PID/user/network namespaces; fixed destination Unix relay"
            evidence["external_human_validation"] = False
            evidence["consumer_wall_seconds"] = round(time.perf_counter() - started, 3)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(evidence, indent=2) + "\n")
            cases = evidence["operator_evaluation"]["cases"]
            summary = {"checks": evidence["isolation_checks"], "cases": len(cases),
                       "verified": sum(case["outcome"]["verified"] for case in cases),
                       "audit": evidence["audit"], "consumer_wall_seconds": evidence["consumer_wall_seconds"],
                       "artifact_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                       "package_location": str(Path(aecp.__file__).parent),
                       "source_commit": code_revision(),
                       "provider_calls": 0, "external_human_validation": False,
                       "scope": "development corpus; reopened fake ambiguous dispatch; not a live failure replication"}
            output.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            return summary
        finally:
            relay.shutdown()
            relay.server_close()
            application.shutdown()
            application.server_close()
            relay_thread.join(timeout=5)
            gateway_thread.join(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("var/evidence-v21/isolation.json"))
    parser.add_argument("--consumer-dir", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(validate(arguments.output, arguments.consumer_dir)))
