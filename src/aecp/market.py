"""Funded first-price unit auctions. Credits never become operating authority."""

from __future__ import annotations

from typing import Any

from aecp.ledger import BudgetRejected, IdempotencyConflict, InvalidTransition, Ledger, _amount, _identifier


class Market:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger
        with ledger._transaction() as connection:
            for statement in (
                "CREATE TABLE IF NOT EXISTS wallets(id TEXT PRIMARY KEY, balance INTEGER NOT NULL CHECK(balance >= 0))",
                """CREATE TABLE IF NOT EXISTS credit_moves(
                    id TEXT PRIMARY KEY, source TEXT, destination TEXT NOT NULL, amount INTEGER NOT NULL,
                    reason TEXT NOT NULL)""",
                """CREATE TABLE IF NOT EXISTS auctions(
                    id TEXT PRIMARY KEY, capacity INTEGER NOT NULL, expires_at INTEGER NOT NULL,
                    state TEXT NOT NULL DEFAULT 'OPEN')""",
                """CREATE TABLE IF NOT EXISTS bids(
                    id TEXT PRIMARY KEY, auction_id TEXT NOT NULL REFERENCES auctions(id),
                    agent_id TEXT NOT NULL, price INTEGER NOT NULL, hold_id TEXT NOT NULL UNIQUE,
                    state TEXT NOT NULL DEFAULT 'ESCROWED')""",
            ):
                connection.execute(statement)

    @staticmethod
    def _move(connection, identity: str, source: str | None, destination: str, amount: int, reason: str) -> None:
        old = connection.execute("SELECT * FROM credit_moves WHERE id = ?", (identity,)).fetchone()
        if old:
            if (old["source"], old["destination"], old["amount"], old["reason"]) != (
                source, destination, amount, reason
            ):
                raise IdempotencyConflict("credit movement changed")
            return
        connection.execute("INSERT OR IGNORE INTO wallets VALUES (?, 0)", (destination,))
        if source is not None:
            changed = connection.execute(
                "UPDATE wallets SET balance = balance - ? WHERE id = ? AND balance >= ?",
                (amount, source, amount),
            ).rowcount
            if not changed:
                raise BudgetRejected("insufficient MARKET_CREDIT")
        destination_balance = connection.execute(
            "SELECT balance FROM wallets WHERE id = ?", (destination,)
        ).fetchone()[0]
        _amount(destination_balance + amount)
        connection.execute("UPDATE wallets SET balance = balance + ? WHERE id = ?", (amount, destination))
        connection.execute("INSERT INTO credit_moves VALUES (?, ?, ?, ?, ?)",
                           (identity, source, destination, amount, reason))

    def endow(self, treasury: str, amount: int) -> None:
        """Operator-only named initial issuance, idempotent and independently auditable."""
        _identifier(treasury)
        _amount(amount)
        with self.ledger._transaction() as connection:
            self._move(connection, f"issue:{treasury}", None, treasury, amount, "initial issuance")

    def transfer(self, identity: str, source: str, destination: str, amount: int) -> None:
        _amount(amount, positive=True)
        if source.startswith("escrow:") or destination.startswith("escrow:"):
            raise BudgetRejected("escrow can move only through the auction lifecycle")
        with self.ledger._transaction() as connection:
            self._move(connection, identity, source, destination, amount, "transfer")

    def open(self, auction_id: str, capacity: int, expires_at: int) -> None:
        _identifier(auction_id)
        _amount(capacity)
        _amount(expires_at, positive=True)
        with self.ledger._transaction() as connection:
            old = connection.execute("SELECT * FROM auctions WHERE id = ?", (auction_id,)).fetchone()
            if old:
                if (old["capacity"], old["expires_at"]) != (capacity, expires_at):
                    raise IdempotencyConflict("auction changed")
                return
            connection.execute("INSERT INTO auctions(id, capacity, expires_at) VALUES (?, ?, ?)",
                               (auction_id, capacity, expires_at))

    def bid(self, bid_id: str, auction_id: str, agent_id: str, price: int, hold_id: str, now: int) -> dict:
        """Admission atomically checks existing operating reservation and locks all bid credits."""
        _identifier(bid_id)
        _amount(price, positive=True)
        _amount(now)
        with self.ledger._transaction() as connection:
            old = connection.execute("SELECT * FROM bids WHERE id = ?", (bid_id,)).fetchone()
            if old:
                if (old["auction_id"], old["agent_id"], old["price"], old["hold_id"]) != (
                    auction_id, agent_id, price, hold_id
                ):
                    raise IdempotencyConflict("bid changed")
                return dict(old)
            auction = connection.execute("SELECT * FROM auctions WHERE id = ?", (auction_id,)).fetchone()
            if not auction or auction["state"] != "OPEN" or now >= auction["expires_at"]:
                raise InvalidTransition("auction unavailable")
            hold = self.ledger._hold(connection, hold_id)
            if hold["account_id"] != agent_id or hold["state"] != "RESERVED" or hold["resource"] != "premium":
                raise BudgetRejected("bid requires owned, reserved operating authority")
            if any(scope["status"] != "ACTIVE" or scope["lifecycle"] != "ACTIVE"
                   for scope in self.ledger._ancestors(connection, agent_id)):
                raise BudgetRejected("inactive bidder")
            if hold["expires_at"] is not None and hold["expires_at"] < auction["expires_at"]:
                raise BudgetRejected("operating authority expires before allocation")
            self._move(connection, f"escrow:{bid_id}", agent_id, f"escrow:{bid_id}", price, "bid escrow")
            connection.execute("INSERT INTO bids(id, auction_id, agent_id, price, hold_id) VALUES (?, ?, ?, ?, ?)",
                               (bid_id, auction_id, agent_id, price, hold_id))
            self.ledger._event(connection, "bid_admitted", agent_id, hold_id,
                               bid_id=bid_id, price=price, unit="MARKET_CREDIT", auction_id=auction_id)
            return dict(connection.execute("SELECT * FROM bids WHERE id = ?", (bid_id,)).fetchone())

    def clear(self, auction_id: str, now: int) -> list[dict]:
        _amount(now)
        with self.ledger._transaction() as connection:
            auction = connection.execute("SELECT * FROM auctions WHERE id = ?", (auction_id,)).fetchone()
            if not auction:
                raise KeyError(auction_id)
            if auction["state"] == "OPEN":
                bids = connection.execute(
                    "SELECT * FROM bids WHERE auction_id = ? AND state = 'ESCROWED' ORDER BY price DESC, id ASC",
                    (auction_id,),
                ).fetchall()
                awarded = 0
                for bid in bids:
                    hold = self.ledger._hold(connection, bid["hold_id"])
                    eligible = hold["state"] == "RESERVED" and all(
                        scope["status"] == "ACTIVE" and scope["lifecycle"] == "ACTIVE"
                        for scope in self.ledger._ancestors(connection, bid["agent_id"])
                    )
                    if eligible and now < auction["expires_at"] and awarded < auction["capacity"]:
                        state = "ALLOCATED"
                        awarded += 1
                        connection.execute("UPDATE bids SET state = ? WHERE id = ?", (state, bid["id"]))
                    else:
                        self._refund(connection, bid, "LOST")
                    self.ledger._event(connection, "auction_cleared", bid["agent_id"], bid["hold_id"],
                                       bid_id=bid["id"], allocated=eligible and awarded > 0 and
                                       connection.execute("SELECT state FROM bids WHERE id = ?",
                                                          (bid["id"],)).fetchone()[0] == "ALLOCATED")
                connection.execute("UPDATE auctions SET state = 'CLEARED' WHERE id = ?", (auction_id,))
            return [dict(row) for row in connection.execute(
                "SELECT * FROM bids WHERE auction_id = ? ORDER BY id", (auction_id,)
            )]

    def _refund(self, connection, bid, state: str) -> None:
        self._move(connection, f"refund:{bid['id']}", f"escrow:{bid['id']}", bid["agent_id"],
                   bid["price"], state)
        connection.execute("UPDATE bids SET state = ? WHERE id = ?", (state, bid["id"]))
        hold = self.ledger._hold(connection, bid["hold_id"])
        if hold["state"] == "RESERVED":
            connection.execute("UPDATE holds SET state = 'RELEASED' WHERE id = ?", (hold["id"],))
            for scope in self.ledger._ancestors(connection, hold["account_id"]):
                connection.execute("UPDATE accounts SET reserved = reserved - ? WHERE id = ?",
                                   (hold["upper_bound"], scope["id"]))
            self.ledger._event(connection, "released", hold["account_id"], hold["id"], reason=state)

    def finish(self, bid_id: str, *, delivered: bool, now: int) -> None:
        """Trusted delivery reconciliation; unresolved delivery cannot be refunded by an agent."""
        _amount(now)
        with self.ledger._transaction() as connection:
            bid = connection.execute("SELECT * FROM bids WHERE id = ?", (bid_id,)).fetchone()
            if not bid:
                raise KeyError(bid_id)
            expected = "DELIVERED" if delivered else "REFUNDED"
            if bid["state"] == expected:
                return
            if bid["state"] != "ALLOCATED":
                raise InvalidTransition("allocation is not pending delivery")
            hold = self.ledger._hold(connection, bid["hold_id"])
            if delivered:
                if hold["state"] != "SETTLED":
                    raise InvalidTransition("delivery requires settled execution")
                self._move(connection, f"payment:{bid_id}", f"escrow:{bid_id}", "market:operator",
                           bid["price"], "first-price payment")
                connection.execute("UPDATE bids SET state = 'DELIVERED' WHERE id = ?", (bid_id,))
            else:
                if hold["state"] not in {"RESERVED", "RELEASED"}:
                    raise InvalidTransition("ambiguous delivery retains escrow")
                self._refund(connection, bid, "REFUNDED")
            self.ledger._event(connection, "allocation_finished", bid["agent_id"], bid["hold_id"],
                               bid_id=bid_id, delivered=delivered, now=now)

    def cancel(self, bid_id: str, agent_id: str) -> None:
        with self.ledger._transaction() as connection:
            bid = connection.execute("SELECT * FROM bids WHERE id = ?", (bid_id,)).fetchone()
            if not bid or bid["agent_id"] != agent_id:
                raise BudgetRejected("not owned")
            if bid["state"] == "CANCELLED":
                return
            if bid["state"] != "ESCROWED":
                raise InvalidTransition("only uncleared bids can be cancelled")
            self._refund(connection, bid, "CANCELLED")

    def expire(self, now: int, *, scope: str | None = None) -> None:
        with self.ledger._transaction() as connection:
            bids = connection.execute(
                """WITH RECURSIVE descendants(id) AS (
                    SELECT id FROM accounts WHERE id = ? OR ? IS NULL
                    UNION SELECT accounts.id FROM accounts JOIN descendants ON accounts.parent_id = descendants.id
                ) SELECT bids.* FROM bids JOIN auctions ON bids.auction_id = auctions.id
                   JOIN descendants ON bids.agent_id = descendants.id
                   WHERE auctions.expires_at <= ? AND bids.state IN ('ESCROWED', 'ALLOCATED')""", (scope, scope, now)
            ).fetchall()
            for bid in bids:
                hold = self.ledger._hold(connection, bid["hold_id"])
                if hold["state"] in {"RESERVED", "RELEASED"}:
                    self._refund(connection, bid, "EXPIRED")
        self.ledger.expire(now, scope=scope)

    def snapshot(self) -> dict[str, Any]:
        with self.ledger._transaction() as connection:
            wallets = [dict(row) for row in connection.execute("SELECT * FROM wallets ORDER BY id")]
            moves = [dict(row) for row in connection.execute("SELECT * FROM credit_moves ORDER BY id")]
            expected = {wallet["id"]: 0 for wallet in wallets}
            for movement in moves:
                expected[movement["destination"]] += movement["amount"]
                if movement["source"] is not None:
                    expected[movement["source"]] -= movement["amount"]
            return {
                "unit": "MARKET_CREDIT", "wallets": wallets,
                "consistent": all(wallet["balance"] == expected[wallet["id"]] for wallet in wallets),
                "issued": sum(movement["amount"] for movement in moves if movement["source"] is None),
                "total": sum(wallet["balance"] for wallet in wallets), "journal": moves,
                "bids": [dict(row) for row in connection.execute("SELECT * FROM bids ORDER BY id")],
                "auctions": [dict(row) for row in connection.execute("SELECT * FROM auctions ORDER BY id")],
            }
