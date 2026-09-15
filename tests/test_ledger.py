from __future__ import annotations

import random
import sqlite3
import tempfile
import unittest
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

from aecp.ledger import BudgetRejected, IdempotencyConflict, InvalidTransition, Ledger


def reserve_in_process(path: str, index: int) -> bool:
    ledger = Ledger(path)
    try:
        ledger.reserve("agent", f"process-{index}", 7, task_id="task", operation_id=f"op-{index}",
                       request_hash=f"request-{index}")
        return True
    except BudgetRejected:
        return False


class LedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "ledger.sqlite3"
        self.ledger = Ledger(self.path)
        self.ledger.create_account("agent", 100, unit="SIM_COST_MICRO")

    def reserve(self, hold_id: str = "attempt", amount: int = 40) -> dict:
        return self.ledger.reserve("agent", hold_id, amount, task_id="task", operation_id="operation",
                                   request_hash="request-digest")

    def assert_healthy(self) -> None:
        audit = self.ledger.audit()
        self.assertTrue(audit["consistent"], audit)
        self.assertTrue(audit["within_funding"], audit)
        self.assertEqual(audit["bound_breach_count"], 0)

    def test_funding_is_integer_and_unit_explicit(self) -> None:
        self.assertEqual(self.ledger.account("agent")["unit"], "SIM_COST_MICRO")
        self.assertEqual(self.ledger.account("agent")["headroom"], 100)
        with self.assertRaises(ValueError):
            self.ledger.create_account("real", 100, unit="USD")

    def test_account_creation_is_idempotent_not_a_top_up(self) -> None:
        self.reserve()
        self.ledger.create_account("agent", 100, unit="SIM_COST_MICRO")
        self.assertEqual(self.ledger.account("agent")["headroom"], 60)
        self.assertEqual(sum(e["kind"] == "account_funded" for e in self.ledger.events()), 1)

    def test_conflicting_account_creation(self) -> None:
        with self.assertRaises(IdempotencyConflict):
            self.ledger.create_account("agent", 101, unit="SIM_COST_MICRO")

    def test_reservation_counts_before_dispatch(self) -> None:
        self.reserve()
        self.assertEqual(self.ledger.account("agent")["reserved"], 40)
        self.assertEqual(self.ledger.account("agent")["spent"], 0)
        self.assert_healthy()

    def test_duplicate_reservation_does_not_reserve_twice(self) -> None:
        first = self.reserve()
        self.assertEqual(self.reserve(), first)
        self.assertEqual(self.ledger.account("agent")["reserved"], 40)

    def test_request_hash_is_bound_to_idempotency(self) -> None:
        self.reserve()
        with self.assertRaises(IdempotencyConflict):
            self.ledger.reserve("agent", "attempt", 40, task_id="task", operation_id="operation",
                                request_hash="different-request")

    def test_upper_bound_is_bound_to_idempotency(self) -> None:
        self.reserve()
        with self.assertRaises(IdempotencyConflict):
            self.reserve(amount=41)

    def test_excess_is_rejected_and_audited(self) -> None:
        self.reserve(amount=100)
        with self.assertRaises(BudgetRejected):
            self.reserve("extra", 1)
        self.assertEqual(self.ledger.events()[-1]["kind"], "reservation_denied")
        self.assert_healthy()

    def test_negative_float_bool_and_out_of_range_rejected(self) -> None:
        for value in (-1, 1.1, True, "12", 2**63):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.reserve(amount=value)
        with self.assertRaises(ValueError):
            self.reserve(amount=0)
        self.assert_healthy()

    def test_missing_account_does_not_create_money(self) -> None:
        with self.assertRaises(KeyError):
            self.ledger.reserve("new", "attempt", 1, task_id="task", operation_id="operation",
                                request_hash="hash")
        self.assert_healthy()

    def test_invalid_identifiers_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.reserve(hold_id="  ")

    def test_dispatch_claim_cannot_be_repeated(self) -> None:
        self.reserve()
        self.ledger.mark_dispatched("attempt")
        with self.assertRaises(InvalidTransition):
            self.ledger.mark_dispatched("attempt")

    def test_settlement_requires_dispatch(self) -> None:
        self.reserve()
        with self.assertRaises(InvalidTransition):
            self.ledger.settle("attempt", 20)
        self.assert_healthy()

    def test_normal_settlement_releases_only_unused_cap(self) -> None:
        self.reserve()
        self.ledger.mark_dispatched("attempt")
        self.ledger.settle("attempt", 25)
        self.assertEqual(self.ledger.account("agent")["spent"], 25)
        self.assertEqual(self.ledger.account("agent")["reserved"], 0)
        self.assertEqual(self.ledger.account("agent")["headroom"], 75)
        self.assert_healthy()

    def test_zero_charge_is_a_valid_settlement(self) -> None:
        self.reserve()
        self.ledger.mark_dispatched("attempt")
        self.ledger.settle("attempt", 0)
        self.assertEqual(self.ledger.account("agent")["headroom"], 100)

    def test_settlement_idempotency_and_conflict(self) -> None:
        self.reserve()
        self.ledger.mark_dispatched("attempt")
        self.ledger.settle("attempt", 25)
        self.ledger.settle("attempt", 25)
        with self.assertRaises(IdempotencyConflict):
            self.ledger.settle("attempt", 26)
        self.assertEqual(sum(e["kind"] == "settled" for e in self.ledger.events()), 1)
        self.assert_healthy()

    def test_unresolved_keeps_full_reservation(self) -> None:
        self.reserve()
        self.ledger.mark_dispatched("attempt")
        self.ledger.mark_unresolved("attempt")
        self.ledger.mark_unresolved("attempt")
        self.assertEqual(self.ledger.account("agent")["reserved"], 40)
        with self.assertRaises(InvalidTransition):
            self.ledger.release("attempt")
        self.assert_healthy()

    def test_restart_does_not_erase_uncertain_liability(self) -> None:
        self.reserve()
        self.ledger.mark_dispatched("attempt")
        self.ledger.mark_unresolved("attempt")
        recovered = Ledger(self.path)
        self.assertEqual(recovered.reservation("attempt")["state"], "UNRESOLVED")
        self.assertEqual(recovered.account("agent")["reserved"], 40)
        recovered.settle("attempt", 30)
        self.assertEqual(recovered.account("agent")["headroom"], 70)
        self.assert_healthy()

    def test_predispatch_cancellation_is_idempotent(self) -> None:
        self.reserve()
        self.ledger.release("attempt")
        self.ledger.release("attempt")
        self.assertEqual(self.ledger.account("agent")["headroom"], 100)
        with self.assertRaises(InvalidTransition):
            self.ledger.mark_dispatched("attempt")

    def test_no_timeout_refund_for_dispatched(self) -> None:
        self.reserve()
        self.ledger.mark_dispatched("attempt")
        with self.assertRaises(InvalidTransition):
            self.ledger.release("attempt")

    def test_trusted_no_charge_reconciliation_requires_evidence(self) -> None:
        self.reserve()
        self.ledger.mark_dispatched("attempt")
        with self.assertRaises(ValueError):
            self.ledger.reconcile_no_charge("attempt", evidence="")
        self.ledger.reconcile_no_charge("attempt", evidence="fixture:provider-confirmation-1")
        self.assertEqual(self.ledger.account("agent")["headroom"], 100)
        self.assertEqual(self.ledger.events()[-1]["kind"], "reconciled_no_charge")
        with self.assertRaises(InvalidTransition):
            self.ledger.settle("attempt", 10)

    def test_retries_have_independent_liabilities(self) -> None:
        self.reserve("attempt-1", 40)
        self.ledger.mark_dispatched("attempt-1")
        self.ledger.mark_unresolved("attempt-1")
        self.reserve("attempt-2", 40)
        self.ledger.mark_dispatched("attempt-2")
        self.ledger.settle("attempt-2", 30)
        self.assertEqual(self.ledger.account("agent")["headroom"], 30)
        self.ledger.settle("attempt-1", 35)
        self.assertEqual(self.ledger.account("agent")["spent"], 65)
        self.assert_healthy()

    def test_bound_violation_is_not_hidden(self) -> None:
        self.reserve(amount=40)
        self.ledger.mark_dispatched("attempt")
        self.ledger.settle("attempt", 120)
        account = self.ledger.account("agent")
        self.assertEqual(account["spent"], 120)
        self.assertEqual(account["headroom"], -20)
        self.assertEqual(account["status"], "FROZEN")
        audit = self.ledger.audit()
        self.assertTrue(audit["consistent"])
        self.assertFalse(audit["within_funding"])
        self.assertEqual(audit["bound_breach_count"], 1)
        with self.assertRaises(BudgetRejected):
            self.reserve("new", 1)

    def test_frozen_account_cannot_dispatch_old_reservations(self) -> None:
        self.reserve("first", 20)
        self.reserve("second", 20)
        self.ledger.mark_dispatched("first")
        self.ledger.settle("first", 21)
        with self.assertRaises(BudgetRejected):
            self.ledger.mark_dispatched("second")
        self.ledger.release("second")
        self.assertTrue(self.ledger.audit()["consistent"])

    def test_model_cost_and_market_credits_are_separate_units(self) -> None:
        self.ledger.create_account("market", 500, unit="MARKET_CREDIT")
        self.ledger.reserve("market", "market-attempt", 200, task_id="task", operation_id="market-op",
                            request_hash="market-bid")
        self.assertEqual(self.ledger.account("agent")["headroom"], 100)
        self.assertEqual(self.ledger.account("market")["headroom"], 300)

    def test_threaded_reservation_has_one_spendable_balance(self) -> None:
        def attempt(index: int) -> bool:
            try:
                self.reserve(f"thread-{index}", 7)
                return True
            except BudgetRejected:
                return False
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(attempt, range(40)))
        self.assertEqual(sum(results), 14)
        self.assertEqual(self.ledger.account("agent")["reserved"], 98)
        self.assert_healthy()

    def test_processes_share_transactional_admission(self) -> None:
        with ProcessPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(reserve_in_process, [str(self.path)] * 24, range(24)))
        self.assertEqual(sum(results), 14)
        self.assertEqual(self.ledger.account("agent")["reserved"], 98)
        self.assert_healthy()

    def test_duplicate_dispatch_race_has_one_winner(self) -> None:
        self.reserve()
        def dispatch(_: int) -> bool:
            try:
                self.ledger.mark_dispatched("attempt")
                return True
            except InvalidTransition:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(dispatch, range(16)))
        self.assertEqual(sum(results), 1)

    def test_randomized_lifecycle_sequences_preserve_invariants(self) -> None:
        rng = random.Random(481)
        for index in range(200):
            hold_id = f"sequence-{index}"
            cap = rng.randint(1, 12)
            try:
                self.reserve(hold_id, cap)
            except BudgetRejected:
                self.assert_healthy()
                continue
            if rng.randrange(3) == 0:
                self.ledger.release(hold_id)
            else:
                self.ledger.mark_dispatched(hold_id)
                if rng.randrange(2):
                    self.ledger.mark_unresolved(hold_id)
                self.ledger.settle(hold_id, rng.randint(0, cap))
            self.assert_healthy()

    def test_projection_corruption_is_detected(self) -> None:
        self.reserve()
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("UPDATE accounts SET reserved = 0 WHERE id = 'agent'")
            connection.commit()
        self.assertFalse(self.ledger.audit()["consistent"])

    def test_memory_database_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            Ledger(":memory:")

    def test_failed_transition_leaves_no_partial_changes(self) -> None:
        self.reserve()
        before = self.ledger.events()
        with self.assertRaises(InvalidTransition):
            self.ledger.mark_unresolved("attempt")
        self.assertEqual(self.ledger.events(), before)
        self.assertEqual(self.ledger.reservation("attempt")["state"], "RESERVED")
        self.assert_healthy()


if __name__ == "__main__":
    unittest.main()
