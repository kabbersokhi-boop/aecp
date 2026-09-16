"""Real HTTP boundary tests; agents never possess operator credentials or the database."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from aecp.client import Client, ControlPlaneError
from aecp.control import Denied
from aecp.engine import Engine
from aecp.server import Application, credentials, provision, validate_credentials


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.engine = Engine(root / "state.db")
        provision(self.engine)
        for agent in ("gateway/passive", "gateway/native"):
            self.engine.control.register_task(agent, "case", "reconcile")
        self.principals = credentials(root / "capabilities.json")
        self.server = Application(("127.0.0.1", 0), self.engine, self.principals, token_file=root / "capabilities.json")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.clients = {name: Client(self.url, principal["token"]) for name, principal in self.principals.items()}
        self.body = {"request_id": "request", "task_id": "case", "resource": "cheap",
                     "parameters": {"invoice_cents": 100, "payments": [100]}}

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def denied(self, client, path, body=None):
        with self.assertRaises(ControlPlaneError) as raised:
            client.call(path, body)
        self.assertIn(raised.exception.status, (401, 403, 409))
        return raised.exception

    def test_authenticated_passive_execution_idempotency_and_owner_isolation(self):
        first = self.clients["passive"].call("/api/v1/resource-requests", self.body)
        second = self.clients["passive"].call("/api/v1/resource-requests", self.body)
        self.assertEqual(first, second)
        self.assertEqual(first["result"]["resolution"], "matched")
        self.assertEqual(first["reservation"]["actual"], 4)
        self.denied(self.clients["native"], "/api/v1/requests/request")
        self.assertEqual(self.clients["passive"].budget()["budget"]["spent"], 4)

    def test_connection_overload_rejects_before_reservation_then_recovers(self):
        with self.server.admission_lock:
            self.server.admission["limit"] = 2
        sockets = [socket.create_connection(("127.0.0.1", self.server.server_port), timeout=5) for _ in range(2)]
        try:
            deadline = time.monotonic() + 3
            while self.server.admission_snapshot()["active"] != 2 and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(self.server.admission_snapshot()["active"], 2)
            with self.assertRaises(ControlPlaneError) as raised:
                self.clients["passive"].call("/api/v1/resource-requests", self.body)
            self.assertEqual(raised.exception.status, 503)
            self.assertEqual(raised.exception.code, "GATEWAY_SATURATED")
            self.assertTrue(raised.exception.retry_same_idempotency_key)
            self.assertEqual(self.engine.ledger.account("gateway/passive")["spent"], 0)
            self.assertEqual(self.engine.ledger.account("gateway/passive")["reserved"], 0)
        finally:
            for connection in sockets:
                connection.close()
        deadline = time.monotonic() + 3
        while self.server.admission_snapshot()["active"] and time.monotonic() < deadline:
            time.sleep(0.01)
        result = self.clients["passive"].call("/api/v1/resource-requests", self.body)
        self.assertEqual(result["reservation"]["state"], "SETTLED")
        self.assertLessEqual(self.server.admission_snapshot()["peak"], 2)
        self.assertGreaterEqual(self.server.admission_snapshot()["rejected"], 1)

    def test_separate_semantic_consumer_uses_only_public_scoped_contract(self):
        self.clients["operator"].call("/api/v1/admin/semantic-cases",
                                      {"agent_id": "gateway/passive", "split": "development"})
        root = Path(self.directory.name)
        token = root / "agent-token"
        token.write_text(self.principals["passive"]["token"])
        token.chmod(0o600)
        output = root / "consumer-result.json"
        source = Path(__file__).parents[1] / "examples/semantic_consumer/main.py"
        process = subprocess.run(
            [sys.executable, str(source), "--url", self.url, "--token-file", str(token),
             "--policy", "deterministic-only", "--output", str(output)],
            cwd=root, env={"PATH": os.defpath}, capture_output=True, text=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(len(json.loads(output.read_text())["cases"]), 12)
        evidence = self.clients["operator"].call("/api/v1/semantic-evidence")
        self.assertEqual(sum(case["outcome"]["verified"] for case in evidence["cases"]), 8)
        self.assertTrue(all(case["observation"]["status"] != "OPEN" for case in evidence["cases"]))
        self.assertEqual(self.clients["native"].call("/api/v1/semantic/tasks"), [])
        task = evidence["cases"][0]["task"]
        self.denied(self.clients["native"], "/api/v1/semantic/tasks/" + task)
        self.denied(self.clients["passive"], "/api/v1/semantic-evidence")
        self.denied(self.clients["passive"], "/api/v1/admin/semantic-cases",
                    {"agent_id": "gateway/native", "split": "development"})

    def test_openai_http_surface_enforces_task_and_preserves_receipt(self):
        from test_nim import FakeTransport

        from aecp.nim import NimAdapter
        transport = FakeTransport()
        self.engine.control.adapters["nim_chat"] = NimAdapter("configured-model", transport)
        body = {"model": "configured-model", "messages": [{"role": "user", "content": "invoice 100 paid 100"}],
                "max_tokens": 48, "temperature": 0}
        headers = {"Authorization": "Bearer " + self.principals["passive"]["token"],
                   "Content-Type": "application/json", "X-AECP-Task": "case", "Idempotency-Key": "chat"}
        for _attempt in range(2):
            request = Request(self.url + "/v1/chat/completions", data=json.dumps(body).encode(), headers=headers)
            with urlopen(request, timeout=10) as response:
                completion = json.load(response)
            self.assertEqual(completion["usage"]["total_tokens"], 17)
            self.assertEqual(completion["aecp"]["state"], "SETTLED")
        headers["X-AECP-Task"] = "unknown"
        request = Request(self.url + "/v1/chat/completions", data=json.dumps(body).encode(), headers=headers)
        with self.assertRaises(HTTPError) as error:
            urlopen(request, timeout=10)
        self.assertEqual(error.exception.code, 403)
        self.assertEqual(transport.calls, 1)
        self.assertEqual(len(self.clients["operator"].call("/api/v1/provider-executions")["requests"]), 1)

    def test_agent_cannot_fund_settle_approve_admin_or_read_evaluator_state(self):
        client = self.clients["passive"]
        for path, body in (
            ("/api/v1/admin/runs", {"run_id": "evil"}),
            ("/api/v1/reviewer/decisions", {"approval_id": "x", "approve": True}),
            ("/budgets/fund", {"amount": 1000000}),
            ("/transactions/settle", {"request_id": "request", "actual": 0}),
            ("/api/v1/runs", None),
        ):
            with self.subTest(path=path):
                self.denied(client, path, body)
        self.denied(client, "/api/v1/resource-requests", {**self.body, "agent_id": "gateway/native"})
        self.denied(client, "/api/v1/resource-requests", {**self.body, "resource": "planning"})
        self.denied(client, "/api/v1/resource-requests", {**self.body, "task_id": "unregistered-alias"})

    def test_missing_empty_and_wrong_credentials_are_rejected(self):
        self.denied(Client(self.url, ""), "/api/v1/me/budget")
        self.denied(Client(self.url, "wrong"), "/api/v1/me/budget")
        self.denied(self.clients["viewer"], "/api/v1/admin/runs", {"run_id": "bad"})
        invalid = {"operator": {"token": "", "role": "operator", "agent_id": None}}
        with self.assertRaises(ValueError):
            validate_credentials(invalid)

    def test_operator_created_identity_persists_without_minting_root_authority(self):
        before = self.engine.ledger.account("gateway")["funded"]
        identity = self.clients["operator"].call("/api/v1/admin/agents", {"name": "outside", "budget": 800})
        stored = credentials(Path(self.directory.name) / "capabilities.json")
        self.assertTrue(any(item["token"] == identity["token"] and item["agent_id"] == identity["agent_id"]
                            for item in stored.values()))
        self.assertEqual(self.engine.ledger.account("gateway")["funded"], before)

    def test_mandatory_task_class_cannot_be_downgraded(self):
        body = {**self.body, "task_id": "protected-payment"}
        failure = self.denied(self.clients["passive"], "/api/v1/resource-requests", body)
        self.assertEqual(failure.payload["error"], "OPERATION_POLICY_MISMATCH")
        protected = {**body, "operation": "release_payment"}
        self.denied(self.clients["passive"], "/api/v1/resource-requests", protected)
        approval = self.clients["passive"].call("/api/v1/approval-requests",
                                               {**protected, "approval_id": "approval"})
        self.assertEqual(approval["state"], "PENDING")
        queue = self.clients["reviewer"].call("/api/v1/reviewer/queue")
        self.assertEqual(json.loads(queue[0]["action"])["parameters"], body["parameters"])
        self.clients["reviewer"].call("/api/v1/reviewer/decisions", {"approval_id": "approval", "approve": True})
        result = self.clients["passive"].call("/api/v1/resource-requests", protected)
        self.assertEqual(result["reservation"]["state"], "SETTLED")
        self.denied(self.clients["passive"], "/api/v1/resource-requests", {**protected, "request_id": "retry"})

    def test_economic_native_bid_clear_execute_and_resource_binding(self):
        operator = self.clients["operator"]
        native = self.clients["native"]
        operator.call("/api/v1/admin/auctions", {"auction_id": "slots", "capacity": 1})
        bid = {**self.body, "resource": "premium", "bid_id": "bid", "auction_id": "slots", "price": 20}
        admitted = native.call("/api/v1/market/bids", bid)
        self.assertEqual(admitted["state"], "ESCROWED")
        operator.call("/api/v1/admin/clear", {"auction_id": "slots"})
        result = native.call("/api/v1/resource-requests", {**self.body, "resource": "premium"})
        self.assertEqual(result["reservation"]["state"], "SETTLED")
        self.assertEqual(native.call("/api/v1/market/allocations")[0]["state"], "DELIVERED")
        self.assertEqual(native.budget()["market_credit"], 280)
        before = native.budget()["budget"]["reserved"]
        self.denied(native, "/api/v1/market/bids", {**bid, "request_id": "wrong", "resource": "consultation"})
        self.assertEqual(native.budget()["budget"]["reserved"], before)
        with self.engine.ledger._transaction() as connection:
            self.assertIsNone(connection.execute("SELECT id FROM holds WHERE id = 'wrong'").fetchone())

    def test_conflicting_bid_does_not_cancel_existing_authority(self):
        operator = self.clients["operator"]
        native = self.clients["native"]
        operator.call("/api/v1/admin/auctions", {"auction_id": "slots", "capacity": 1})
        bid = {**self.body, "resource": "premium", "bid_id": "bid", "auction_id": "slots", "price": 20}
        native.call("/api/v1/market/bids", bid)
        self.denied(native, "/api/v1/market/bids", {**bid, "price": 21})
        self.assertEqual(native.call("/api/v1/requests/request")["reservation"]["state"], "RESERVED")
        self.assertEqual(native.budget()["budget"]["spent"], 2)

    def test_pending_gateway_requests_expire_and_can_be_cancelled(self):
        native = self.clients["native"]
        self.denied(native, "/api/v1/resource-requests", {**self.body, "resource": "premium"})
        self.assertEqual(native.budget()["budget"]["reserved"], 14)
        request = native.call("/api/v1/requests/request")
        self.assertIsInstance(request["reservation"]["expires_at"], int)
        native.call("/api/v1/requests/cancel", {"request_id": "request"})
        self.assertEqual(native.budget()["budget"]["reserved"], 0)

    def test_interrupted_bid_fee_reservation_expires_after_recovery(self):
        self.clients["operator"].call("/api/v1/admin/auctions", {"auction_id": "slots", "capacity": 1})
        bid = {**self.body, "resource": "premium", "bid_id": "bid", "auction_id": "slots", "price": 20}
        with patch.object(self.engine.control, "execute", side_effect=Denied("INTERRUPTED_BEFORE_DISPATCH")):
            self.denied(self.clients["native"], "/api/v1/market/bids", bid)
        self.assertEqual(self.engine.ledger.account("gateway/native")["reserved"], 16)
        primary = self.engine.ledger.reservation("request")
        fee = self.engine.ledger.reservation("request/bid-fee")
        self.assertEqual(fee["expires_at"], primary["expires_at"])
        recovered = Engine(Path(self.directory.name) / "state.db")
        recovered.market.expire(primary["expires_at"] + 1, scope="gateway")
        self.assertEqual(recovered.ledger.reservation("request")["state"], "RELEASED")
        self.assertEqual(recovered.ledger.reservation("request/bid-fee")["state"], "RELEASED")
        self.assertEqual(recovered.ledger.account("gateway/native")["reserved"], 0)

    def test_cross_origin_and_oversized_payload_fail_closed(self):
        request = Request(self.url + "/api/v1/me/budget", headers={
            "Authorization": f"Bearer {self.principals['passive']['token']}", "Origin": "https://evil.example"})
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=5)
        self.assertEqual(raised.exception.code, 403)
        raised.exception.close()
        self.denied(self.clients["passive"], "/api/v1/resource-requests", {**self.body, "padding": "x" * 70000})

    def test_dashboard_serves_real_backend_trace(self):
        operator = self.clients["operator"]
        operator.call("/api/v1/admin/runs", {"run_id": "demo", "count": 3})
        operator.call("/api/v1/admin/complete", {"run_id": "demo"})
        snapshot = self.clients["viewer"].call("/api/v1/runs/demo")
        self.assertEqual(len(snapshot["traces"]), 3)
        self.assertTrue(snapshot["holds"])
        self.assertTrue(snapshot["audit"]["consistent"])
        with urlopen(self.url + "/", timeout=5) as response:
            self.assertIn(b"Transaction inspector", response.read())
            self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])


if __name__ == "__main__":
    unittest.main()
