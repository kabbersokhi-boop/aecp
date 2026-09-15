"""Synthetic invoice reconciliation: observable documents and evaluator-only facts."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from aecp.determinism import semantic_u64, stable_digest

VERSION = "finops.v1"


@dataclass(frozen=True)
class Observation:
    task_id: str
    counterparty: str
    invoice_cents: int
    visible_payments: tuple[int, ...]
    document_status: str
    arrival: int
    deadline: int
    value: int
    mandatory: bool


@dataclass(frozen=True)
class Case:
    observation: Observation
    bank_payments: tuple[int, ...]
    resolution: str


def resolve(invoice: int, payments: tuple[int, ...] | list[int]) -> str:
    total = sum(payments)
    if total == invoice:
        return "matched"
    if len(payments) > 1 and len(set(payments)) < len(payments) and total > invoice:
        return "duplicate"
    return "underpaid" if total < invoice else "overpaid"


def corpus(seed: int, count: int = 36, *, burst: bool = False) -> list[Case]:
    cases = []
    for index in range(count):
        task_id = f"case-{index:03d}"
        invoice = 1000 + semantic_u64(seed, VERSION, task_id, "invoice") % 90000
        cause = semantic_u64(seed, VERSION, task_id, "cause") % 4
        payments = ((invoice,), (invoice, invoice), (invoice - 500,), (invoice + 500,))[cause]
        missing = semantic_u64(seed, VERSION, task_id, "document") % 3 == 0
        visible = (invoice,) if missing else payments
        arrival = index // (9 if burst else 3)
        observation = Observation(
            task_id, f"vendor-{index % 9:02d}", invoice, visible, "partial" if missing else "complete",
            arrival, arrival + 2 + semantic_u64(seed, VERSION, task_id, "deadline") % 4,
            20 + semantic_u64(seed, VERSION, task_id, "value") % 180,
            index % 11 == 0,
        )
        cases.append(Case(observation, payments, resolve(invoice, payments)))
    return cases


def corpus_identity(cases: list[Case]) -> str:
    return stable_digest([asdict(case) for case in cases])


def evidence(case: Case, resource: str, *, outage: bool = False) -> dict:
    """Resource returns evidence, not the evaluator's answer. Outage serves stale local records."""
    payments = case.observation.visible_payments
    if resource in {"premium", "consultation"} and not outage:
        payments = case.bank_payments
    return {"invoice_cents": case.observation.invoice_cents, "payments": list(payments),
            "source": "bank_statement" if resource != "cheap" and not outage else "local_ledger",
            "degraded": outage}
