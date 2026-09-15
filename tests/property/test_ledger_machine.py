"""Generated lifecycle sequences against an independent in-memory projection model."""

import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from aecp.ledger import Ledger, LedgerError


class SpendingMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "state.sqlite3"
        self.ledger = Ledger(self.path)
        self.ledger.create_account("root", 200, unit="SIM_COST_MICRO")
        self.ledger.create_account("independent", 200, unit="SIM_COST_MICRO")
        self.parents = {"root": None, "independent": None}
        self.caps = {"root": 200, "independent": 200}
        self.holds = {}
        self.clock = 0
        self.serial = 0
        self.breached_scopes = set()
        self.breached_holds = set()

    def identity(self):
        self.serial += 1
        return f"operation-{self.serial}"

    def ancestors(self, account):
        result = []
        while account is not None:
            result.append(account)
            account = self.parents[account]
        return result

    @rule(parent=st.integers(0, 20), cap=st.integers(1, 250))
    def delegate(self, parent, cap):
        if len(self.parents) >= 12:
            return
        parent = list(self.parents)[parent % len(self.parents)]
        identity = self.identity()
        try:
            self.ledger.create_account(identity, cap, unit="SIM_COST_MICRO", parent_id=parent)
        except LedgerError:
            return
        self.parents[identity] = parent
        self.caps[identity] = cap

    def reserve(self, account, amount, identity):
        try:
            self.ledger.reserve(account, identity, amount, task_id="case", operation_id="attempt",
                                request_hash=identity, expires_at=self.clock + 3)
            return True
        except LedgerError:
            return False

    @rule(account=st.integers(0, 20), amount=st.integers(1, 80))
    def reserve_or_retry(self, account, amount):
        account = list(self.parents)[account % len(self.parents)]
        identity = self.identity()
        if self.reserve(account, amount, identity):
            self.holds[identity] = {"account": account, "bound": amount, "state": "RESERVED",
                                    "actual": None, "expiry": self.clock + 3}

    @rule(amount=st.integers(1, 100))
    def concurrent_pressure(self, amount):
        identities = [self.identity() for _ in range(3)]
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(lambda identity: self.reserve("root", amount, identity), identities))
        for identity, accepted in zip(identities, results, strict=True):
            if accepted:
                self.holds[identity] = {"account": "root", "bound": amount, "state": "RESERVED",
                                        "actual": None, "expiry": self.clock + 3}

    @rule(index=st.integers(0, 100), action=st.sampled_from(
        ["dispatch", "unresolved", "settle", "breach", "cancel", "no_charge"]), fraction=st.integers(0, 100))
    def transition(self, index, action, fraction):
        if not self.holds:
            return
        identity = list(self.holds)[index % len(self.holds)]
        hold = self.holds[identity]
        before = dict(hold)
        try:
            if action == "dispatch":
                self.ledger.mark_dispatched(identity, now=self.clock)
                hold["state"] = "DISPATCHED"
            elif action == "unresolved":
                self.ledger.mark_unresolved(identity)
                hold["state"] = "UNRESOLVED"
            elif action in {"settle", "breach"}:
                actual = hold["bound"] + 1 if action == "breach" else hold["bound"] * fraction // 100
                if hold["state"] == "SETTLED":
                    actual = hold["actual"]
                self.ledger.settle(identity, actual)
                hold.update(state="SETTLED", actual=actual)
                if actual > hold["bound"]:
                    self.breached_scopes.update(self.ancestors(hold["account"]))
                    self.breached_holds.add(identity)
            elif action == "cancel":
                self.ledger.release(identity)
                hold["state"] = "RELEASED"
                assert before["state"] in {"RESERVED", "RELEASED"}
            else:
                self.ledger.reconcile_no_charge(identity, evidence="trusted fixture provider no-charge attestation")
                hold["state"] = "RELEASED"
        except LedgerError:
            assert hold == before

    @rule()
    def expire_and_reopen(self):
        self.clock += 1
        self.ledger.expire(self.clock)
        for hold in self.holds.values():
            if hold["state"] == "RESERVED" and hold["expiry"] <= self.clock:
                hold["state"] = "RELEASED"
        self.ledger = Ledger(self.path)

    @rule(index=st.integers(0, 20), lifecycle=st.sampled_from(["ACTIVE", "SUSPENDED", "WINDING_DOWN"]))
    def lifecycle(self, index, lifecycle):
        account = list(self.parents)[index % len(self.parents)]
        self.ledger.set_lifecycle(account, lifecycle)

    @invariant()
    def projections_and_authority(self):
        for account in self.parents:
            expected_spent = sum(hold["actual"] for hold in self.holds.values()
                                 if account in self.ancestors(hold["account"]) and hold["state"] == "SETTLED")
            expected_reserved = sum(hold["bound"] for hold in self.holds.values()
                                    if account in self.ancestors(hold["account"])
                                    and hold["state"] in {"RESERVED", "DISPATCHED", "UNRESOLVED"})
            actual = self.ledger.account(account)
            assert actual["funded"] == self.caps[account]
            assert actual["spent"] == expected_spent
            assert actual["reserved"] == expected_reserved
            if account not in self.breached_scopes:
                assert expected_spent + expected_reserved <= self.caps[account]
            else:
                assert actual["status"] == "FROZEN"
            if self.breached_scopes.intersection(self.ancestors(account)):
                assert not self.reserve(account, 1, f"forbidden-after-breach-{account}")
        assert self.ledger.account("root")["funded"] == 200
        assert self.ledger.account("independent")["funded"] == 200
        audit = self.ledger.audit()
        assert audit["consistent"]
        assert audit["bound_breach_count"] == len(self.breached_holds)
        for identity, hold in self.holds.items():
            assert self.ledger.reservation(identity)["state"] == hold["state"]
            if identity in self.breached_holds:
                assert self.ledger.reservation(identity)["actual"] == hold["actual"] > hold["bound"]

    def teardown(self):
        self.directory.cleanup()


TestSpendingMachine = SpendingMachine.TestCase
TestSpendingMachine.settings = settings(max_examples=35, stateful_step_count=60, deadline=None, derandomize=True)
