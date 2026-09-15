"""Independent execution, same-ID races and authenticated fairness under blocked provider work."""

import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

import test_gateway

from aecp.client import ControlPlaneError
from aecp.control import SimulatedAdapter


class ConcurrentGatewayTests(unittest.TestCase):
    setUp = test_gateway.GatewayTests.setUp
    close_server = test_gateway.GatewayTests.close_server

    def test_independent_calls_overlap_without_serializing_reads(self):
        barrier = threading.Barrier(3)
        release = threading.Event()

        class BlockingAdapter(SimulatedAdapter):
            def execute(self, resource, parameters):
                barrier.wait(timeout=5)
                if not release.wait(5):
                    raise RuntimeError("test release timed out")
                return super().execute(resource, parameters)

        self.engine.control.adapter = BlockingAdapter()
        with ThreadPoolExecutor(max_workers=3) as workers:
            attempts = [workers.submit(self.clients["passive"].call, "/api/v1/resource-requests",
                                       {**self.body, "request_id": "parallel-" + str(index)}) for index in range(2)]
            try:
                barrier.wait(timeout=5)
                snapshot = workers.submit(self.clients["operator"].call, "/api/v1/system").result(timeout=2)
                self.assertEqual(snapshot["reserved"], 8)
            finally:
                release.set()
            for attempt in attempts:
                self.assertEqual(attempt.result()["reservation"]["state"], "SETTLED")
        self.assertTrue(self.engine.ledger.audit()["consistent"])

    def test_noisy_authenticated_agent_does_not_hold_all_execution_slots(self):
        entered = threading.Event()
        release = threading.Event()
        self.server.agent_limit = 1

        class BlockingAdapter(SimulatedAdapter):
            def execute(self, resource, parameters):
                if parameters["invoice_cents"] == 100:
                    entered.set()
                    if not release.wait(5):
                        raise RuntimeError("test release timed out")
                return super().execute(resource, parameters)

        self.engine.control.adapter = BlockingAdapter()
        with ThreadPoolExecutor(max_workers=2) as workers:
            pending = workers.submit(self.clients["passive"].call, "/api/v1/resource-requests", self.body)
            try:
                self.assertTrue(entered.wait(3))
                with self.assertRaises(ControlPlaneError) as denied:
                    self.clients["passive"].call("/api/v1/resource-requests", {**self.body, "request_id": "noisy"})
                self.assertEqual(denied.exception.status, 429)
                result = self.clients["native"].call("/api/v1/resource-requests", {
                    **self.body, "request_id": "legitimate",
                    "parameters": {"invoice_cents": 200, "payments": [200]}})
                self.assertEqual(result["reservation"]["state"], "SETTLED")
                self.assertEqual(self.engine.ledger.account("gateway/passive")["reserved"], 4)
            finally:
                release.set()
            pending.result(timeout=3)
        stats = self.server.admission_snapshot()["agents"]["gateway/passive"]
        self.assertEqual(stats["peak"], 1)
        self.assertEqual(stats["active"], 0)
        self.assertEqual(stats["rejected"], 1)

    def test_same_id_concurrency_never_dispatches_twice(self):
        calls = []
        lock = threading.Lock()
        entered = threading.Event()
        release = threading.Event()

        class CountingAdapter(SimulatedAdapter):
            def execute(self, resource, parameters):
                with lock:
                    calls.append(resource)
                entered.set()
                if not release.wait(5):
                    raise RuntimeError("test release timed out")
                return super().execute(resource, parameters)

        self.engine.control.adapter = CountingAdapter()

        def request():
            try:
                return self.clients["passive"].call("/api/v1/resource-requests", self.body)
            except ControlPlaneError as error:
                self.assertIn(error.status, {409, 429})
                return None

        with ThreadPoolExecutor(max_workers=4) as workers:
            original = workers.submit(request)
            try:
                self.assertTrue(entered.wait(3))
                duplicates = list(workers.map(lambda _: request(), range(3)))
                self.assertTrue(all(result is None or result["reservation"]["state"] in {"DISPATCHED", "UNRESOLVED"}
                                    for result in duplicates))
                self.assertEqual(self.engine.ledger.account("gateway/passive")["reserved"], 4)
                self.assertEqual(self.engine.ledger.account("gateway/passive")["spent"], 0)
            finally:
                release.set()
            original.result(timeout=3)
        final = self.clients["passive"].call("/api/v1/resource-requests", self.body)
        self.assertEqual(final["reservation"]["state"], "SETTLED")
        self.assertEqual(calls, ["cheap"])
        self.assertEqual(self.engine.ledger.account("gateway/passive")["spent"], 4)
        with self.engine.ledger._transaction() as connection:
            receipts = connection.execute("SELECT count(*) FROM receipts WHERE request_id = 'request'").fetchone()[0]
            self.assertEqual(receipts, 1)
        self.assertTrue(self.engine.ledger.audit()["consistent"])
