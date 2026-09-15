"""Transactional reference reservation kernel for trusted, local callers.

This module is not an authenticated gateway, market journal, or provider adapter.
All amounts are integer units. Initial units explicitly distinguish modeled
cost from internal market credits; there is no real-money billing integration.

Safety assumes trusted callers, exclusive use of this interface, a correctly
functioning local SQLite database, and correct upper bounds. Actual charges
above a bound are recorded in full and freeze the account: they are not clipped
or hidden to preserve the appearance of an invariant.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from aecp.determinism import canonical_json

MAX_AMOUNT = 2**63 - 1
UNITS = frozenset({"SIM_COST_MICRO", "MARKET_CREDIT"})
OUTSTANDING = ("RESERVED", "DISPATCHED", "UNRESOLVED")


class LedgerError(Exception):
    """Base exception for reference-kernel operations."""


class BudgetRejected(LedgerError):
    """A frozen account or insufficient funding prevented a new commitment."""


class IdempotencyConflict(LedgerError):
    """A previously used identifier was supplied with different semantics."""


class InvalidTransition(LedgerError):
    """The requested transition is not valid for the current durable state."""


def _amount(value: int, *, positive: bool = False) -> int:
    if type(value) is not int or not (1 if positive else 0) <= value <= MAX_AMOUNT:
        raise ValueError("amount must be an integer in the supported nonnegative range")
    return value


def _identifier(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ValueError("identifier must be non-empty text of at most 256 characters")
    return value


class Ledger:
    """File-backed reference kernel; each method uses an independent connection.

    SQLite serializes writers with BEGIN IMMEDIATE. A failed database operation
    never produces authorization. Do not place the database on a network share.
    """

    def __init__(self, path: str | Path):
        self.transaction_timings = None
        self.path = str(path)
        if self.path == ":memory:":
            raise ValueError("a file-backed database is required for recovery and concurrency")
        connection = self._connect()
        try:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    unit TEXT NOT NULL CHECK(unit IN ('SIM_COST_MICRO', 'MARKET_CREDIT')),
                    funded INTEGER NOT NULL CHECK(funded >= 0),
                    spent INTEGER NOT NULL DEFAULT 0 CHECK(spent >= 0),
                    reserved INTEGER NOT NULL DEFAULT 0 CHECK(reserved >= 0),
                    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'FROZEN'))
                );
                CREATE TABLE IF NOT EXISTS holds (
                    id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL REFERENCES accounts(id),
                    task_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    upper_bound INTEGER NOT NULL CHECK(upper_bound > 0),
                    state TEXT NOT NULL CHECK(state IN
                        ('RESERVED', 'DISPATCHED', 'UNRESOLVED', 'SETTLED', 'RELEASED')),
                    actual INTEGER CHECK(actual >= 0)
                );
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    hold_id TEXT,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS holds_account ON holds(account_id);
            """)
            connection.execute("BEGIN IMMEDIATE")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > 3:
                raise LedgerError("unsupported ledger schema version")
            if version == 0:
                connection.execute("ALTER TABLE accounts ADD COLUMN parent_id TEXT REFERENCES accounts(id)")
                connection.execute("ALTER TABLE accounts ADD COLUMN lifecycle TEXT NOT NULL DEFAULT 'ACTIVE'")
                connection.execute("ALTER TABLE holds ADD COLUMN expires_at INTEGER")
                connection.execute("PRAGMA user_version = 1")
            if version < 2:
                connection.execute("ALTER TABLE holds ADD COLUMN resource TEXT")
                connection.execute("PRAGMA user_version = 2")
            if version < 3:
                connection.execute("ALTER TABLE accounts ADD COLUMN spent_high TEXT NOT NULL DEFAULT '0'")
                connection.execute("PRAGMA user_version = 3")
            connection.commit()
        finally:
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        collector = self.transaction_timings
        started = time.perf_counter() if collector is not None else 0
        acquired = None
        failed = False
        try:
            connection.execute("BEGIN IMMEDIATE")
            if collector is not None:
                acquired = time.perf_counter()
            yield connection
            connection.commit()
        except BaseException:
            failed = True
            connection.rollback()
            raise
        finally:
            connection.close()
            if collector is not None:
                ended = time.perf_counter()
                if acquired is None:
                    acquired = ended
                collector.record((acquired - started) * 1000, (ended - acquired) * 1000, failed)

    @staticmethod
    def _event(connection: sqlite3.Connection, kind: str, account_id: str,
               hold_id: str | None = None, **payload: Any) -> None:
        connection.execute(
            "INSERT INTO events(kind, account_id, hold_id, payload) VALUES (?, ?, ?, ?)",
            (kind, account_id, hold_id, canonical_json(payload)),
        )

    @staticmethod
    def _account(connection: sqlite3.Connection, account_id: str) -> dict[str, Any]:
        row = connection.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown account: {account_id}")
        result = dict(row)
        result["spent"] += int(result["spent_high"]) * (MAX_AMOUNT + 1)
        return result

    @staticmethod
    def _hold(connection: sqlite3.Connection, hold_id: str) -> sqlite3.Row:
        row = connection.execute("SELECT * FROM holds WHERE id = ?", (hold_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown reservation: {hold_id}")
        return row

    @staticmethod
    def _ancestors(connection: sqlite3.Connection, account_id: str) -> list[dict[str, Any]]:
        result = []
        while account_id is not None:
            account = Ledger._account(connection, account_id)
            result.append(account)
            account_id = account["parent_id"]
        return result

    def create_account(self, account_id: str, funded: int, *, unit: str,
                       parent_id: str | None = None) -> dict[str, Any]:
        """Trusted initial funding only. Repeating the same request never re-funds."""
        _identifier(account_id)
        _amount(funded)
        if unit not in UNITS:
            raise ValueError(f"unit must be one of {sorted(UNITS)}")
        with self._transaction() as connection:
            old = connection.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
            if old is not None:
                if (old["funded"], old["unit"], old["parent_id"]) != (funded, unit, parent_id):
                    raise IdempotencyConflict("account already exists with different funding or unit")
                return dict(self._account(connection, account_id))
            if parent_id is not None:
                parent = self._account(connection, parent_id)
                if parent["unit"] != unit or funded > parent["funded"]:
                    raise BudgetRejected("delegation must fit its parent and retain its unit")
                if any(scope["status"] != "ACTIVE" or scope["lifecycle"] != "ACTIVE"
                       for scope in self._ancestors(connection, parent_id)):
                    raise BudgetRejected("parent is not active")
            connection.execute(
                "INSERT INTO accounts(id, unit, funded, parent_id) VALUES (?, ?, ?, ?)",
                (account_id, unit, funded, parent_id)
            )
            self._event(connection, "scope_delegated" if parent_id else "account_funded", account_id,
                        funded=funded, unit=unit, parent_id=parent_id)
            return dict(self._account(connection, account_id))

    def reserve(self, account_id: str, hold_id: str, upper_bound: int, *, task_id: str,
                operation_id: str, request_hash: str, expires_at: int | None = None,
                resource: str | None = None) -> dict[str, Any]:
        """Reserve once per attempt. The caller must bind request_hash to the action.

        A retry with possible additional billing requires a NEW hold identifier.
        Reusing an identifier returns its existing state, not permission to
        execute again. Dispatch must separately claim a RESERVED hold.
        """
        for value in (account_id, hold_id, task_id, operation_id, request_hash):
            _identifier(value)
        _amount(upper_bound, positive=True)
        if resource is not None:
            _identifier(resource)
        if expires_at is not None:
            _amount(expires_at)
        rejection: str | None = None
        with self._transaction() as connection:
            old = connection.execute("SELECT * FROM holds WHERE id = ?", (hold_id,)).fetchone()
            if old is not None:
                fields = ("account_id", "upper_bound", "task_id", "operation_id", "request_hash",
                          "expires_at", "resource")
                expected = (account_id, upper_bound, task_id, operation_id, request_hash, expires_at, resource)
                if tuple(old[field] for field in fields) != expected:
                    raise IdempotencyConflict("reservation identifier has different request parameters")
                return dict(old)
            scopes = self._ancestors(connection, account_id)
            for account in scopes:
                if account["status"] != "ACTIVE" or account["lifecycle"] != "ACTIVE":
                    rejection = "account is frozen or inactive"
                elif account["spent"] + account["reserved"] + upper_bound > account["funded"]:
                    rejection = "insufficient uncommitted funding"
            if rejection:
                self._event(connection, "reservation_denied", account_id, hold_id,
                            reason=rejection, upper_bound=upper_bound, task_id=task_id)
            else:
                connection.execute(
                    "INSERT INTO holds VALUES (?, ?, ?, ?, ?, ?, 'RESERVED', NULL, ?, ?)",
                    (hold_id, account_id, task_id, operation_id, request_hash, upper_bound, expires_at, resource),
                )
                connection.executemany(
                    "UPDATE accounts SET reserved = reserved + ? WHERE id = ?",
                    [(upper_bound, scope["id"]) for scope in scopes],
                )
                self._event(connection, "reserved", account_id, hold_id, upper_bound=upper_bound,
                            task_id=task_id, operation_id=operation_id, request_hash=request_hash)
        if rejection:
            raise BudgetRejected(rejection)
        return self.reservation(hold_id)

    def mark_dispatched(self, hold_id: str, *, now: int = 0) -> dict[str, Any]:
        """Claim dispatch once. A duplicate claim raises rather than reauthorizing.

        Persisting this state precedes external execution. A crash between these
        steps is uncertain and requires reconciliation, NOT automatic replay.
        """
        with self._transaction() as connection:
            return self._dispatch(connection, hold_id, now)

    def _dispatch(self, connection: sqlite3.Connection, hold_id: str, now: int) -> dict[str, Any]:
        hold = self._hold(connection, hold_id)
        if hold["state"] != "RESERVED":
            raise InvalidTransition(f"cannot dispatch from {hold['state']}")
        _amount(now)
        if hold["expires_at"] is not None and now >= hold["expires_at"]:
            raise InvalidTransition("reservation expired before dispatch")
        if any(account["status"] != "ACTIVE" or account["lifecycle"] != "ACTIVE"
               for account in self._ancestors(connection, hold["account_id"])):
            raise BudgetRejected("account is frozen; new execution is forbidden")
        connection.execute("UPDATE holds SET state = 'DISPATCHED' WHERE id = ?", (hold_id,))
        self._event(connection, "dispatched", hold["account_id"], hold_id)
        return dict(self._hold(connection, hold_id))

    def mark_unresolved(self, hold_id: str) -> dict[str, Any]:
        """Record uncertainty while retaining the entire possible liability."""
        with self._transaction() as connection:
            hold = self._hold(connection, hold_id)
            if hold["state"] == "UNRESOLVED":
                return dict(hold)
            if hold["state"] != "DISPATCHED":
                raise InvalidTransition(f"cannot mark unresolved from {hold['state']}")
            connection.execute("UPDATE holds SET state = 'UNRESOLVED' WHERE id = ?", (hold_id,))
            self._event(connection, "unresolved", hold["account_id"], hold_id)
            return dict(self._hold(connection, hold_id))

    def settle(self, hold_id: str, actual: int) -> dict[str, Any]:
        """Trusted usage settlement. Never erase an actual bound violation."""
        _amount(actual)
        with self._transaction() as connection:
            hold = self._hold(connection, hold_id)
            if hold["state"] == "SETTLED":
                if hold["actual"] != actual:
                    raise IdempotencyConflict("reservation already settled for a different amount")
                return dict(hold)
            if hold["state"] not in ("DISPATCHED", "UNRESOLVED"):
                raise InvalidTransition(f"cannot settle from {hold['state']}")
            breached = actual > hold["upper_bound"]
            for account in self._ancestors(connection, hold["account_id"]):
                new_spent = account["spent"] + actual
                spent_high, spent_low = divmod(new_spent, MAX_AMOUNT + 1)
                status = "FROZEN" if breached else account["status"]
                connection.execute(
                    "UPDATE accounts SET spent = ?, spent_high = ?, reserved = reserved - ?, status = ? WHERE id = ?",
                    (spent_low, str(spent_high), hold["upper_bound"], status, account["id"]),
                )
            connection.execute(
                "UPDATE holds SET state = 'SETTLED', actual = ? WHERE id = ?", (actual, hold_id)
            )
            self._event(connection, "settled", hold["account_id"], hold_id, actual=actual,
                        released=max(0, hold["upper_bound"] - actual))
            if breached:
                self._event(connection, "liability_bound_breached", hold["account_id"], hold_id,
                            upper_bound=hold["upper_bound"], actual=actual)
            return dict(self._hold(connection, hold_id))

    def release(self, hold_id: str) -> dict[str, Any]:
        """Cancel only before dispatch. A timeout is not evidence of no charge."""
        return self._release(hold_id, evidence=None)

    def reconcile_no_charge(self, hold_id: str, *, evidence: str) -> dict[str, Any]:
        """Trusted reconciliation; a non-empty reference is not proof of truth.

        The future adapter must validate external evidence. Agents may never
        invoke this method as a way to refund themselves.
        """
        _identifier(evidence)
        return self._release(hold_id, evidence=evidence)

    def _release(self, hold_id: str, *, evidence: str | None) -> dict[str, Any]:
        with self._transaction() as connection:
            hold = self._hold(connection, hold_id)
            if hold["state"] == "RELEASED":
                return dict(hold)
            allowed = ("RESERVED",) if evidence is None else ("DISPATCHED", "UNRESOLVED")
            if hold["state"] not in allowed:
                raise InvalidTransition(f"cannot release from {hold['state']} without valid reconciliation")
            connection.execute("UPDATE holds SET state = 'RELEASED' WHERE id = ?", (hold_id,))
            connection.executemany("UPDATE accounts SET reserved = reserved - ? WHERE id = ?",
                                   [(hold["upper_bound"], account["id"])
                                    for account in self._ancestors(connection, hold["account_id"])])
            kind = "released" if evidence is None else "reconciled_no_charge"
            self._event(connection, kind, hold["account_id"], hold_id, evidence=evidence)
            return dict(self._hold(connection, hold_id))

    def account(self, account_id: str) -> dict[str, Any]:
        connection = self._connect()
        try:
            result = dict(self._account(connection, account_id))
            result["headroom"] = result["funded"] - result["spent"] - result["reserved"]
            result["effective_headroom"] = min(scope["funded"] - scope["spent"] - scope["reserved"]
                                               for scope in self._ancestors(connection, account_id))
            return result
        finally:
            connection.close()

    def reservation(self, hold_id: str) -> dict[str, Any]:
        connection = self._connect()
        try:
            return dict(self._hold(connection, hold_id))
        finally:
            connection.close()

    def events(self) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            return [dict(row) for row in connection.execute("SELECT * FROM events ORDER BY seq")]
        finally:
            connection.close()

    def audit(self) -> dict[str, Any]:
        """Check projections against holds and report funding breaches separately.

        This does not validate database authenticity or a full double-entry book.
        """
        connection = self._connect()
        try:
            connection.execute("BEGIN")
            consistency_errors: list[str] = []
            funding_breaches: list[str] = []
            for account in connection.execute("SELECT * FROM accounts ORDER BY id"):
                holds = connection.execute(
                    """WITH RECURSIVE descendants(id) AS (
                        SELECT ? UNION ALL SELECT accounts.id FROM accounts
                        JOIN descendants ON accounts.parent_id = descendants.id
                    ) SELECT holds.* FROM holds JOIN descendants ON holds.account_id = descendants.id""",
                    (account["id"],)
                ).fetchall()
                spent = sum(h["actual"] for h in holds if h["state"] == "SETTLED")
                reserved = sum(h["upper_bound"] for h in holds if h["state"] in OUTSTANDING)
                projected_spent = account["spent"] + int(account["spent_high"]) * (MAX_AMOUNT + 1)
                if spent != projected_spent or reserved != account["reserved"]:
                    consistency_errors.append(account["id"])
                if spent + reserved > account["funded"]:
                    funding_breaches.append(account["id"])
            bound_breaches = connection.execute(
                "SELECT count(*) FROM events WHERE kind = 'liability_bound_breached'"
            ).fetchone()[0]
            return {"consistent": not consistency_errors, "within_funding": not funding_breaches,
                    "consistency_errors": consistency_errors, "funding_breaches": funding_breaches,
                    "bound_breach_count": bound_breaches}
        finally:
            connection.close()

    def set_lifecycle(self, account_id: str, lifecycle: str) -> None:
        """Operator control; winding down permits reconciliation but no new dispatch."""
        if lifecycle not in {"ACTIVE", "SUSPENDED", "WINDING_DOWN"}:
            raise ValueError("invalid lifecycle")
        with self._transaction() as connection:
            self._account(connection, account_id)
            connection.execute("UPDATE accounts SET lifecycle = ? WHERE id = ?", (lifecycle, account_id))
            self._event(connection, "lifecycle_changed", account_id, lifecycle=lifecycle)

    def expire(self, now: int, *, scope: str | None = None) -> int:
        """Release expired pre-dispatch work only; never release uncertain liabilities."""
        _amount(now)
        with self._transaction() as connection:
            holds = connection.execute(
                """WITH RECURSIVE descendants(id) AS (
                    SELECT id FROM accounts WHERE id = ? OR ? IS NULL
                    UNION SELECT accounts.id FROM accounts JOIN descendants ON accounts.parent_id = descendants.id
                ) SELECT holds.* FROM holds JOIN descendants ON holds.account_id = descendants.id
                WHERE state = 'RESERVED' AND expires_at <= ?""", (scope, scope, now)
            ).fetchall()
            for hold in holds:
                connection.execute("UPDATE holds SET state = 'RELEASED' WHERE id = ?", (hold["id"],))
                for scope in self._ancestors(connection, hold["account_id"]):
                    connection.execute("UPDATE accounts SET reserved = reserved - ? WHERE id = ?",
                                       (hold["upper_bound"], scope["id"]))
                self._event(connection, "expired", hold["account_id"], hold["id"], now=now)
            return len(holds)
