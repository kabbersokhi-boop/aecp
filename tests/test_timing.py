"""Optional bounded timing does not change ledger projections."""

import tempfile
import unittest
from pathlib import Path

from aecp.ledger import Ledger
from aecp.timing import TransactionTimings


class TimingTests(unittest.TestCase):
    def test_opt_in_records_acquisition_and_retains_bounded_samples(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            collector = TransactionTimings(maximum_samples=2)
            ledger.transaction_timings = collector
            ledger.create_account("agent", 10, unit="SIM_COST_MICRO")
            ledger.reserve("agent", "request", 5, task_id="task", operation_id="operation", request_hash="hash")
            ledger.mark_dispatched("request")
            ledger.settle("request", 3)
            self.assertTrue(ledger.audit()["consistent"])
            snapshot = collector.snapshot()
            self.assertGreater(snapshot["total_transactions"], 2)
            self.assertEqual(len(snapshot["retained_samples"]), 2)
            self.assertTrue(all(acquisition >= 0 and transaction >= 0
                                for acquisition, transaction, _failed in snapshot["retained_samples"]))
