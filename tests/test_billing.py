"""No live billing: integer/rational future adapter contract and honest invoice status."""

import unittest

from aecp.billing import BillableDimension, BillingContract


class BillingContractTests(unittest.TestCase):
    def contract(self, **changes):
        values = {"pricing_source_version": "offline-fixture.rate-card.v1", "model_sku": "fixture-model",
                  "quoted_at": "2026-09-09T00:00:00Z", "cost_kind": "commercial_quote", "currency": "USD",
                  "accounting_unit": "USD_MICRO", "dimensions": (
                      BillableDimension("input", "tokens", 100, 3, 2),
                      BillableDimension("output", "tokens", 20, 2),
                      BillableDimension("tool", "executions", 1, 50))}
        return BillingContract(**{**values, **changes})

    def test_fixed_point_dimensions_bound_and_breach_remain_unclipped(self):
        contract = self.contract()
        self.assertEqual(contract.upper_bound(), 240)
        receipt = contract.reconcile({"input": 100, "output": 30, "tool": 1})
        self.assertEqual(receipt["calculated_cost"], 260)
        self.assertEqual(receipt["breached_dimensions"], ["output"])
        self.assertIsNone(receipt["actual_cash_spend"])

    def test_unknown_usage_or_unsupported_billable_dimension_fails_closed(self):
        with self.assertRaises(ValueError):
            self.contract(unsupported_dimensions=("provider-side-search",)).upper_bound()
        with self.assertRaises(ValueError):
            self.contract().reconcile({"input": 1, "output": 1})

    def test_actual_invoice_is_not_fabricated_from_quote(self):
        usage = {"input": 100, "output": 20, "tool": 1}
        with self.assertRaises(ValueError):
            self.contract().reconcile(usage, invoice_status="confirmed")
        receipt = self.contract().reconcile(usage, invoice_status="confirmed", invoice_amount=210)
        self.assertEqual(receipt["calculated_cost"], 240)
        self.assertEqual(receipt["actual_cash_spend"], 210)

    def test_no_float_currency_or_false_invoice(self):
        with self.assertRaises(ValueError):
            BillableDimension("tokens", "tokens", 100, 0.3)
        with self.assertRaises(ValueError):
            self.contract(cost_kind="modeled")
        contract = self.contract(cost_kind="modeled", currency=None, accounting_unit="MODELED_RESOURCE_UNIT")
        receipt = contract.reconcile({"input": 1, "output": 1, "tool": 0}, invoice_status="free_access_declared")
        self.assertEqual(receipt["actual_cash_spend"], 0)
        self.assertEqual(receipt["calculated_cost"], 4)
        self.assertFalse(receipt["provider_invoice_verified_by_this_function"])
