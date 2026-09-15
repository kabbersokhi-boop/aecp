"""Opt-in, bounded in-memory transaction diagnostics; not accounting authority."""

import threading
from collections import deque


class TransactionTimings:
    def __init__(self, maximum_samples=100000):
        self.lock = threading.Lock()
        self.samples = deque(maxlen=maximum_samples)
        self.total = 0

    def record(self, acquisition_ms, transaction_ms, failed):
        with self.lock:
            self.samples.append((acquisition_ms, transaction_ms, failed))
            self.total += 1

    def snapshot(self):
        with self.lock:
            return {"total_transactions": self.total, "retained_samples": list(self.samples),
                    "sample_capacity": self.samples.maxlen}
