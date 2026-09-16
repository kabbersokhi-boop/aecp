"""Execute documented challenge outputs using only the public consumer SDK."""

import importlib.util
import tempfile
import threading
import unittest
from pathlib import Path

from aecp.client import Client, ControlPlaneError
from aecp.engine import Engine
from aecp.server import Application, credentials

specification = importlib.util.spec_from_file_location(
    "challenge_provisioner", Path(__file__).parents[1] / "scripts/provision_challenge.py")
provisioner = importlib.util.module_from_spec(specification)
specification.loader.exec_module(provisioner)


class ExternalChallengeTests(unittest.TestCase):
    def test_documented_success_duplicate_denial_and_reopened_uncertainty(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database, capabilities, token = root / "state.sqlite3", root / "caps.json", root / "agent.token"
            provisioner.provision_challenge(database, capabilities, token)
            self.assertEqual(token.stat().st_mode & 0o777, 0o600)
            for _restart in range(2):
                server = Application(("127.0.0.1", 0), Engine(database), credentials(capabilities))
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    consumer = Client(f"http://127.0.0.1:{server.server_port}", token.read_text())
                    uncertain = consumer.call("/api/v1/requests/challenge-uncertain-attempt")
                    self.assertEqual(uncertain["reservation"]["state"], "UNRESOLVED")
                    self.assertEqual(uncertain["reservation"]["upper_bound"], 4)
                    result = consumer.execute("first", "challenge-invoice", "cheap",
                                              {"invoice_cents": 12500, "payments": [5000, 7500]})
                    self.assertEqual(result["reservation"]["state"], "SETTLED")
                    self.assertEqual(result["result"]["resolution"], "matched")
                    self.assertEqual(consumer.budget()["budget"]["spent"], 4)
                    with self.assertRaises(ControlPlaneError) as denied:
                        consumer.execute("second", "challenge-invoice", "cheap",
                                         {"invoice_cents": 12500, "payments": [5000, 7500]})
                    self.assertEqual(denied.exception.status, 409)
                    self.assertEqual(denied.exception.code, "BUDGET_EXHAUSTED_OR_INACTIVE")
                    self.assertIn("insufficient", denied.exception.detail)
                    self.assertIn(denied.exception.code, str(denied.exception))
                    with self.assertRaises(ControlPlaneError) as unknown:
                        consumer.execute("unknown", "not-registered", "cheap",
                                         {"invoice_cents": 12500, "payments": []})
                    self.assertEqual(unknown.exception.status, 403)
                    self.assertEqual(unknown.exception.code, "UNKNOWN_TASK")
                    self.assertIsNone(unknown.exception.detail)
                    self.assertTrue(server.engine.ledger.audit()["consistent"])
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=5)
