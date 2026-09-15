"""Offline quote/receipt vocabulary; commercial billing enforcement requires a trusted adapter."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class BillableDimension:
    name: str
    unit: str
    maximum_units: int
    price_numerator: int
    price_denominator: int = 1

    def __post_init__(self):
        if not self.name or not self.unit:
            raise ValueError("billable dimension needs a name and unit")
        if any(type(value) is not int or value < 0 for value in
               (self.maximum_units, self.price_numerator, self.price_denominator)) or not self.price_denominator:
            raise ValueError("prices and bounded units must be nonnegative integers with positive denominator")

    def charge(self, units: int) -> int:
        if type(units) is not int or units < 0:
            raise ValueError("usage must be a nonnegative integer")
        return (units * self.price_numerator + self.price_denominator - 1) // self.price_denominator


@dataclass(frozen=True)
class BillingContract:
    pricing_source_version: str
    model_sku: str
    quoted_at: str
    cost_kind: str
    accounting_unit: str
    currency: str | None
    dimensions: tuple[BillableDimension, ...]
    unsupported_dimensions: tuple[str, ...] = ()

    def __post_init__(self):
        if not all((self.pricing_source_version, self.model_sku, self.quoted_at, self.accounting_unit)):
            raise ValueError("quote provenance must identify source, SKU, timestamp and accounting unit")
        if self.cost_kind not in {"modeled", "allocated", "commercial_quote"}:
            raise ValueError("unknown cost kind")
        if self.cost_kind == "commercial_quote":
            if not isinstance(self.currency, str) or len(self.currency) != 3 or not self.currency.isupper():
                raise ValueError("commercial quotes require an explicit three-letter currency")
        elif self.currency is not None:
            raise ValueError("modeled/allocated units must not masquerade as monetary currency")
        if not self.dimensions or len({dimension.name for dimension in self.dimensions}) != len(self.dimensions):
            raise ValueError("quote dimensions must be nonempty and unique")

    def upper_bound(self) -> int:
        if self.unsupported_dimensions:
            raise ValueError("unsupported billable dimensions prevent a complete liability bound")
        return sum(dimension.charge(dimension.maximum_units) for dimension in self.dimensions)

    def describe(self) -> dict:
        return {"version": "provider-billing-contract.v1", **asdict(self),
                "rounding": "ceil per billable dimension, in integer accounting units",
                "guarantee": "conditional quote only; trusted adapter must bound every chargeable dimension"}

    def reconcile(self, usage: dict[str, int], *, invoice_status: str = "unavailable",
                  invoice_amount: int | None = None) -> dict:
        if invoice_status not in {"unavailable", "pending", "confirmed", "free_access_declared"}:
            raise ValueError("unknown invoice status")
        if set(usage) != {dimension.name for dimension in self.dimensions}:
            raise ValueError("missing or unknown usage dimensions cannot establish settlement truth")
        if invoice_status == "confirmed":
            if self.cost_kind != "commercial_quote" or type(invoice_amount) is not int or invoice_amount < 0:
                raise ValueError("confirmed cash requires an explicit trusted invoice amount, not rate-card arithmetic")
        elif invoice_amount is not None:
            raise ValueError("invoice amount requires confirmed status")
        amount = sum(dimension.charge(usage[dimension.name]) for dimension in self.dimensions)
        breaches = [dimension.name for dimension in self.dimensions
                    if usage[dimension.name] > dimension.maximum_units]
        cash = 0 if invoice_status == "free_access_declared" else invoice_amount
        return {"cost_kind": self.cost_kind, "accounting_unit": self.accounting_unit,
                "currency": self.currency, "usage": dict(usage), "calculated_cost": amount,
                "breached_dimensions": breaches, "invoice_status": invoice_status,
                "actual_cash_spend": cash, "provider_invoice_verified_by_this_function": False}
