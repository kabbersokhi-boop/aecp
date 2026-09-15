"""Loopback native HTTP gateway. Bearer capabilities never come from request-body identity."""

from __future__ import annotations

import json
import os
import re
import secrets
import threading
import time
from contextlib import nullcontext
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from aecp.control import Denied
from aecp.engine import Engine
from aecp.ledger import BudgetRejected, IdempotencyConflict, InvalidTransition, _amount, _identifier
from aecp.live import LiveTasks, chat_completion
from aecp.semantic import SemanticTasks


def credentials(path: Path) -> dict:
    """Persist random local demo capabilities outside source control, owner-readable only."""
    if path.exists():
        if path.stat().st_mode & 0o077:
            raise ValueError("credential file must have mode 0600")
        principals = json.loads(path.read_text())
        validate_credentials(principals)
        return principals
    path.parent.mkdir(parents=True, exist_ok=True)
    principals = {name: {"token": secrets.token_urlsafe(32), "role": role, "agent_id": agent}
                  for name, role, agent in (
                      ("operator", "operator", None), ("viewer", "viewer", None),
                      ("reviewer", "reviewer", None), ("passive", "agent", "gateway/passive"),
                      ("native", "agent", "gateway/native"))}
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        json.dump(principals, output, indent=2)
    return principals


def validate_credentials(principals: dict) -> None:
    if not isinstance(principals, dict) or not principals:
        raise ValueError("invalid capability configuration")
    tokens = set()
    for name, principal in principals.items():
        if not isinstance(name, str) or not name or not isinstance(principal, dict):
            raise ValueError("invalid principal")
        if set(principal) != {"token", "role", "agent_id"}:
            raise ValueError("invalid principal fields")
        token = principal["token"]
        if not isinstance(token, str) or len(token) < 32 or token in tokens:
            raise ValueError("capabilities must be unique nonempty random strings")
        tokens.add(token)
        if principal["role"] not in {"agent", "reviewer", "operator", "viewer"}:
            raise ValueError("invalid role")
        if (principal["role"] == "agent") != (isinstance(principal["agent_id"], str) and bool(principal["agent_id"])):
            raise ValueError("invalid scoped identity")


def provision(engine: Engine) -> None:
    ledger = engine.ledger
    ledger.create_account("gateway", 2000, unit="SIM_COST_MICRO")
    engine.market.endow("gateway/treasury", 1000)
    for name in ("passive", "native"):
        ledger.create_account(f"gateway/{name}", 1000, unit="SIM_COST_MICRO", parent_id="gateway")
        engine.market.transfer(f"gateway/endow/{name}", "gateway/treasury", f"gateway/{name}", 300)
        engine.control.register_task(f"gateway/{name}", "protected-payment", "release_payment")
        engine.control.register_task(f"gateway/{name}", "external-invoice-1", "reconcile")
        engine.control.register_task(f"gateway/{name}", "external-invoice-2", "reconcile")


class Application(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], engine: Engine, principals: dict, token_file: Path | None = None,
                 *, max_connections: int = 32, max_agent_requests: int = 4):
        if address[0] not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("reference gateway is loopback-only")
        self.engine = engine
        validate_credentials(principals)
        self.principals = principals
        self.token_file = token_file
        self.live_tasks = LiveTasks(engine.control)
        self.semantic_tasks = SemanticTasks(engine.control)
        self.mutation_lock = threading.RLock()
        self.principals_lock = threading.Lock()
        self.route_timings = None
        if type(max_connections) is not int or not 1 <= max_connections <= 128:
            raise ValueError("reference gateway supports 1-128 simultaneous admitted connections")
        if type(max_agent_requests) is not int or not 1 <= max_agent_requests <= 128:
            raise ValueError("agent request cap must be 1-128")
        self.admission_lock = threading.Lock()
        self.admission = {"limit": max_connections, "active": 0, "peak": 0, "admitted": 0,
                          "rejected": 0, "completed": 0, "application_queue_capacity": 0}
        self.agent_limit = min(max_agent_requests, max_connections)
        self.agent_admission = {}
        super().__init__(address, Handler)

    def process_request(self, request, address):
        with self.admission_lock:
            admitted = self.admission["active"] < self.admission["limit"]
            self.admission["admitted" if admitted else "rejected"] += 1
            if admitted:
                self.admission["active"] += 1
                self.admission["peak"] = max(self.admission["peak"], self.admission["active"])
        if not admitted:
            payload = b'{"error":"GATEWAY_SATURATED","retry_requires_same_idempotency_key":true}'
            try:
                request.settimeout(0.1)
                request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nContent-Type: application/json\r\n"
                                b"Connection: close\r\nRetry-After: 1\r\nContent-Length: "
                                + str(len(payload)).encode() + b"\r\n\r\n" + payload)
            except OSError:
                pass
            finally:
                self.shutdown_request(request)
            return
        request.settimeout(5)
        try:
            super().process_request(request, address)
        except BaseException:
            with self.admission_lock:
                self.admission["active"] -= 1
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            with self.admission_lock:
                self.admission["active"] -= 1
                self.admission["completed"] += 1

    def admission_snapshot(self):
        with self.admission_lock:
            return {**self.admission, "per_agent_limit": self.agent_limit,
                    "agents": {agent: dict(counters) for agent, counters in self.agent_admission.items()}}

    def admit_agent(self, agent: str) -> bool:
        with self.admission_lock:
            counters = self.agent_admission.setdefault(agent, {"active": 0, "peak": 0, "admitted": 0,
                                                               "rejected": 0, "completed": 0})
            if counters["active"] >= self.agent_limit:
                counters["rejected"] += 1
                return False
            counters["active"] += 1
            counters["admitted"] += 1
            counters["peak"] = max(counters["peak"], counters["active"])
            return True

    def finish_agent(self, agent: str) -> None:
        with self.admission_lock:
            self.agent_admission[agent]["active"] -= 1
            self.agent_admission[agent]["completed"] += 1


class Handler(BaseHTTPRequestHandler):
    server: Application
    server_version = "AECP/0.2"

    def log_message(self, format: str, *args) -> None:
        return

    def _send(self, status: int, value, *, content_type: str = "application/json") -> None:
        def exact_json(item):
            if type(item) is int and abs(item) > 2**53 - 1:
                return str(item)
            if isinstance(item, dict):
                return {key: exact_json(entry) for key, entry in item.items()}
            if isinstance(item, list):
                return [exact_json(entry) for entry in item]
            return item
        payload = (json.dumps(exact_json(value), allow_nan=False).encode()
                   if content_type == "application/json" else value)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; "
                         "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(payload)

    def _principal(self, roles: set[str]) -> dict:
        header = self.headers.get("Authorization", "")
        token = header.removeprefix("Bearer ") if header.startswith("Bearer ") else ""
        if not token:
            raise Denied("UNAUTHENTICATED")
        with self.server.principals_lock:
            principals = tuple(self.server.principals.items())
        for name, principal in principals:
            if secrets.compare_digest(token, principal["token"]):
                if principal["role"] not in roles:
                    raise Denied("FORBIDDEN")
                return {**principal, "name": name}
        raise Denied("UNAUTHENTICATED")

    def _origin(self) -> None:
        port = self.server.server_address[1]
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if self.headers.get("Host") not in hosts:
            raise Denied("HOST_FORBIDDEN")
        origin = self.headers.get("Origin")
        if origin is not None and origin not in {f"http://{host}" for host in hosts}:
            raise Denied("ORIGIN_FORBIDDEN")

    @staticmethod
    def _fields(body: dict, required: set[str], optional: set[str] = frozenset()) -> None:
        if not required <= body.keys() or body.keys() - required - optional:
            raise Denied("INVALID_FIELDS")

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def _handle(self, method: str) -> None:
        admitted_agent = None
        try:
            self._origin()
            path = unquote(urlsplit(self.path).path)
            if path.startswith(("/api/", "/v1/")):
                principal = self._principal({"agent", "operator", "reviewer", "viewer"})
                if principal["role"] == "agent":
                    if not self.server.admit_agent(principal["agent_id"]):
                        self._send(429, {"error": "AGENT_CONCURRENCY_LIMIT", "retry_same_idempotency_key": True})
                        return
                    admitted_agent = principal["agent_id"]
            body = {}
            if method == "POST":
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 65536 or self.headers.get("Transfer-Encoding"):
                    raise Denied("INVALID_BODY_SIZE")
                if self.headers.get_content_type() != "application/json":
                    raise Denied("JSON_REQUIRED")
                self.connection.settimeout(5)
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise Denied("INVALID_BODY")
            concurrent = (method == "GET" or path in {"/v1/chat/completions", "/api/v1/semantic/actions"}
                          or path == "/api/v1/resource-requests" and body.get("resource") == "cheap")
            collector = self.server.route_timings
            started = time.perf_counter() if collector is not None else 0
            with nullcontext() if concurrent else self.server.mutation_lock:
                acquired = time.perf_counter() if collector is not None else 0
                failed = True
                try:
                    result = self._route(method, path, body)
                    failed = False
                finally:
                    if collector is not None:
                        collector.record((acquired - started) * 1000,
                                         (time.perf_counter() - acquired) * 1000, failed)
            if result is not None:
                self._send(200, result)
        except Denied as error:
            self._send(401 if error.code == "UNAUTHENTICATED" else 403, {"error": error.code})
        except BudgetRejected as error:
            self._send(409, {"error": "BUDGET_EXHAUSTED_OR_INACTIVE", "detail": str(error)})
        except (IdempotencyConflict, InvalidTransition) as error:
            self._send(409, {"error": type(error).__name__, "detail": str(error)})
        except (ValueError, TypeError, KeyError) as error:
            self._send(400, {"error": "INVALID_REQUEST", "type": type(error).__name__})
        except Exception:
            self._send(500, {"error": "INTERNAL_ERROR_EXECUTION_NOT_AUTHORIZED"})
        finally:
            if admitted_agent is not None:
                self.server.finish_agent(admitted_agent)

    def _route(self, method: str, path: str, body: dict):
        engine = self.server.engine
        now = int(time.time())
        if method == "GET" and path == "/api/v1/admission":
            self._principal({"operator", "viewer"})
            return self.server.admission_snapshot()
        if method == "GET" and path == "/api/v1/semantic/tasks":
            principal = self._principal({"agent"})
            return self.server.semantic_tasks.observations(principal["agent_id"])
        if method == "GET" and path.startswith("/api/v1/semantic/tasks/"):
            principal = self._principal({"agent"})
            return self.server.semantic_tasks.provenance(
                principal["agent_id"], path.removeprefix("/api/v1/semantic/tasks/"))
        if method == "POST" and path == "/api/v1/semantic/actions":
            principal = self._principal({"agent"})
            return self.server.semantic_tasks.action(principal["agent_id"], body)
        if method == "GET" and path == "/api/v1/semantic-evidence":
            self._principal({"operator", "viewer"})
            return self.server.semantic_tasks.snapshot()
        if method == "POST" and path == "/api/v1/admin/semantic-cases":
            self._principal({"operator"})
            self._fields(body, {"agent_id", "split"}, {"workload"})
            return self.server.semantic_tasks.register(body["agent_id"], body["split"],
                                                       workload=body.get("workload", "v2.1"))
        if method == "POST" and path == "/v1/chat/completions":
            principal = self._principal({"agent"})
            return chat_completion(engine.control, principal["agent_id"], self.headers.get("X-AECP-Task", ""),
                                   self.headers.get("Idempotency-Key", ""), body, now=now)
        if method == "GET" and path == "/api/v1/me/tasks":
            principal = self._principal({"agent"})
            return self.server.live_tasks.observations(principal["agent_id"])
        if method == "GET" and path == "/api/v1/provider-executions":
            self._principal({"operator", "viewer"})
            return self.server.live_tasks.snapshot()
        if method == "POST" and path == "/api/v1/admin/live-cases":
            self._principal({"operator"})
            self._fields(body, {"agent_id", "seed"}, {"count"})
            return self.server.live_tasks.register(body["agent_id"], seed=body["seed"], count=body.get("count", 6))
        if method == "POST" and path == "/api/v1/admin/agents":
            self._principal({"operator"})
            self._fields(body, {"name", "budget"})
            name = body["name"]
            if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", name):
                raise Denied("INVALID_AGENT_NAME")
            if name in self.server.principals:
                raise Denied("IDENTITY_ALREADY_EXISTS")
            agent = f"gateway/{name}"
            engine.ledger.create_account(agent, body["budget"], unit="SIM_COST_MICRO", parent_id="gateway")
            principal = {"token": secrets.token_urlsafe(32), "role": "agent", "agent_id": agent}
            with self.server.principals_lock:
                self.server.principals[name] = principal
            if self.server.token_file:
                temporary = self.server.token_file.with_suffix(".tmp")
                descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(descriptor, "w") as stream:
                    json.dump(self.server.principals, stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.server.token_file)
            return principal
        engine.market.expire(now, scope="gateway")
        if method == "GET" and path == "/health":
            return {"status": "ok", "mode": "live-provider-enabled" if "nim_chat" in engine.control.adapters
                    else "simulated", "actual_cash_spend": 0}
        if method == "GET" and path in {"/", "/app.js", "/style.css", "/favicon.svg"}:
            name = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css",
                    "/favicon.svg": "favicon.svg"}[path]
            content_type = {"/": "text/html; charset=utf-8", "/app.js": "text/javascript",
                            "/style.css": "text/css", "/favicon.svg": "image/svg+xml"}[path]
            self._send(200, (Path(__file__).parent / "static" / name).read_bytes(), content_type=content_type)
            return None
        if method == "GET" and path == "/api/v1/me/budget":
            principal = self._principal({"agent"})
            budget = engine.ledger.account(principal["agent_id"])
            wallet = next((wallet for wallet in engine.market.snapshot()["wallets"]
                           if wallet["id"] == principal["agent_id"]), {"balance": 0})
            return {"budget": budget, "market_credit": wallet["balance"], "unit": "SIM_COST_MICRO"}
        if method == "GET" and path.startswith("/api/v1/requests/"):
            principal = self._principal({"agent"})
            return engine.control.request(path.removeprefix("/api/v1/requests/"), principal["agent_id"])
        if method == "GET" and path == "/api/v1/market/allocations":
            principal = self._principal({"agent"})
            return [bid for bid in engine.market.snapshot()["bids"] if bid["agent_id"] == principal["agent_id"]]
        if method == "GET" and path == "/api/v1/runs":
            self._principal({"operator", "viewer"})
            with engine.ledger._transaction() as connection:
                identities = [row[0] for row in connection.execute("SELECT id FROM runs ORDER BY created_at DESC")]
            return [{"id": identity, "config": engine.run(identity)["config"],
                     "metrics": engine.snapshot(identity)["metrics"]} for identity in identities]
        if method == "GET" and path == "/api/v1/system":
            self._principal({"operator", "viewer"})
            with engine.ledger._transaction() as connection:
                roots = [engine.ledger._account(connection, row[0]) for row in connection.execute(
                    "SELECT id FROM accounts WHERE parent_id IS NULL AND unit = 'SIM_COST_MICRO' ORDER BY id")]
                exposure = sum(row[0] for row in connection.execute(
                    "SELECT upper_bound FROM holds JOIN accounts ON holds.account_id = accounts.id "
                    "WHERE holds.state IN ('DISPATCHED', 'UNRESOLVED') "
                    "AND accounts.unit = 'SIM_COST_MICRO'"))
                states = {row[0]: row[1] for row in connection.execute(
                    "SELECT lifecycle, count(*) FROM accounts WHERE parent_id IS NOT NULL GROUP BY lifecycle")}
            return {"roots": roots, "funded": sum(root["funded"] for root in roots),
                    "spent": sum(root["spent"] for root in roots), "reserved": sum(root["reserved"] for root in roots),
                    "unresolved": exposure, "scope_states": states, "actual_cash_spend": 0}
        if method == "GET" and path.startswith("/api/v1/runs/"):
            self._principal({"operator", "viewer"})
            return engine.snapshot(path.removeprefix("/api/v1/runs/"))
        if method == "POST" and path in {"/api/v1/resource-requests", "/api/v1/market/bids",
                                          "/api/v1/approval-requests"}:
            principal = self._principal({"agent"})
            required = {"request_id", "task_id", "resource", "parameters"}
            if path.endswith("/bids"):
                required |= {"bid_id", "auction_id", "price"}
            if path.endswith("/approval-requests"):
                required |= {"approval_id"}
            self._fields(body, required, {"operation"})
            if body["resource"] not in {"cheap", "premium", "consultation"}:
                raise Denied("RESOURCE_NOT_ALLOWED")
            if path.endswith("/bids"):
                if body["resource"] != "premium":
                    raise Denied("RESOURCE_NOT_ALLOWED")
                _amount(body["price"], positive=True)
                _identifier(body["bid_id"])
                _identifier(body["auction_id"])
            agent = principal["agent_id"]
            operation = body.get("operation", "reconcile")
            engine.control.validate_task(agent, body["task_id"], operation, body["resource"])
            if path.endswith("/approval-requests"):
                fingerprint = engine.control.fingerprint(agent, body["task_id"], body["resource"], operation,
                                                         body["parameters"], body["request_id"])
                return engine.control.approval_request(body["approval_id"], agent, fingerprint, now + 300, action=body)
            with engine.ledger._transaction() as connection:
                existing = connection.execute(
                    "SELECT holds.expires_at FROM requests JOIN holds ON requests.id = holds.id WHERE requests.id = ?",
                    (body["request_id"],)).fetchone()
                expires_at = existing[0] if existing else now + 300
                if path.endswith("/bids"):
                    auction = connection.execute("SELECT expires_at FROM auctions WHERE id = ?",
                                                 (body["auction_id"],)).fetchone()
                    if not auction:
                        raise Denied("AUCTION_NOT_FOUND")
                    if not existing:
                        expires_at = auction[0]
            engine.control.prepare(body["request_id"], agent, body["task_id"], body["resource"], body["parameters"],
                                   operation=operation, now=now, expires_at=expires_at)
            if path.endswith("/bids"):
                try:
                    fee_id = f"{body['request_id']}/bid-fee"
                    engine.control.prepare(fee_id, agent, body["task_id"], "bidding", {}, now=now,
                                           expires_at=expires_at)
                    engine.control.execute(fee_id, agent, now=now, trusted_capacity=True)
                    return engine.market.bid(body["bid_id"], body["auction_id"], agent, body["price"],
                                             body["request_id"], now)
                except (BudgetRejected, InvalidTransition, IdempotencyConflict):
                    if not existing and engine.ledger.reservation(body["request_id"])["state"] == "RESERVED":
                        engine.ledger.release(body["request_id"])
                    raise
            result = engine.control.execute(body["request_id"], agent, now=now)
            if result["reservation"]["state"] == "SETTLED":
                self.server.live_tasks.evaluate(result)
                for bid in engine.market.snapshot()["bids"]:
                    if bid["hold_id"] == body["request_id"] and bid["state"] == "ALLOCATED":
                        engine.market.finish(bid["id"], delivered=True, now=now)
            return result
        if method == "POST" and path == "/api/v1/reviewer/decisions":
            principal = self._principal({"reviewer"})
            self._fields(body, {"approval_id", "approve"})
            if type(body["approve"]) is not bool:
                raise Denied("INVALID_DECISION")
            engine.control.review(body["approval_id"], principal["name"], approve=body["approve"], now=now)
            return {"recorded": True, "role": principal["role"]}
        if method == "POST" and path == "/api/v1/requests/cancel":
            principal = self._principal({"agent"})
            self._fields(body, {"request_id"})
            engine.control.request(body["request_id"], principal["agent_id"])
            engine.ledger.release(body["request_id"])
            for bid in engine.market.snapshot()["bids"]:
                if bid["hold_id"] == body["request_id"]:
                    if bid["state"] == "ESCROWED":
                        engine.market.cancel(bid["id"], principal["agent_id"])
                    elif bid["state"] == "ALLOCATED":
                        engine.market.finish(bid["id"], delivered=False, now=now)
            return {"cancelled": True}
        if method == "GET" and path == "/api/v1/reviewer/queue":
            self._principal({"reviewer", "operator", "viewer"})
            with engine.ledger._transaction() as connection:
                return [dict(row) for row in connection.execute(
                    "SELECT approvals.*, approval_actions.action FROM approvals LEFT JOIN approval_actions "
                    "ON approvals.id = approval_actions.approval_id WHERE state = 'PENDING'")]
        if method == "POST" and path == "/api/v1/admin/runs":
            self._principal({"operator"})
            self._fields(body, {"run_id"}, {"seed", "budget", "scenario", "scheduler", "style", "count"})
            return engine.create(**body)
        if method == "POST" and path == "/api/v1/admin/tasks":
            self._principal({"operator"})
            self._fields(body, {"agent_id", "task_id", "required_operation"})
            engine.ledger.account(body["agent_id"])
            engine.control.register_task(**body)
            return {"registered": True}
        if method == "POST" and path in {"/api/v1/admin/step", "/api/v1/admin/complete"}:
            self._principal({"operator"})
            self._fields(body, {"run_id"})
            return engine.step(body["run_id"]) if path.endswith("/step") else engine.complete(body["run_id"])
        if method == "POST" and path == "/api/v1/admin/auctions":
            self._principal({"operator"})
            self._fields(body, {"auction_id", "capacity"})
            engine.market.open(body["auction_id"], body["capacity"], now + 300)
            return {"created": True}
        if method == "POST" and path == "/api/v1/admin/clear":
            self._principal({"operator"})
            self._fields(body, {"auction_id"})
            return engine.market.clear(body["auction_id"], now)
        raise Denied("ROUTE_NOT_ALLOWED")


def serve(database: Path, token_file: Path, port: int) -> None:
    engine = Engine(database)
    provision(engine)
    if os.environ.get("AECP_ENABLE_LIVE_NIM") == "1":
        from aecp.nim import DEFAULT_BASE, NimAdapter, NimTransport
        model = os.environ.get("AECP_NIM_MODEL")
        if not model:
            raise ValueError("configure the discovered AECP_NIM_MODEL before enabling live execution")
        engine.control.adapters["nim_chat"] = NimAdapter(model, NimTransport(
            base_url=os.environ.get("AECP_NIM_BASE_URL", DEFAULT_BASE)))
    server = Application(("127.0.0.1", port), engine, credentials(token_file), token_file)
    print(f"Financial debugger: http://127.0.0.1:{server.server_port}", flush=True)
    print(f"Local capabilities: {token_file} (operator/viewer/reviewer/passive/native)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
