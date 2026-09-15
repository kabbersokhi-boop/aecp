"""Transparent rules and bounded semantic purchasing; no evaluator or AECP implementation imports."""

from __future__ import annotations

import json
import re

VERSION = "semantic-consumer.v2.1.frozen-1"


def deterministic_links(view: dict) -> list[str] | None:
    available = {payment["id"] for payment in view["payments"]}
    direct = [payment["id"] for payment in view["payments"] if payment["reference"] == view["invoice_id"]]
    if direct:
        return sorted(direct)
    text = " ".join(document["text"] for document in view["documents"]
                    if document["source"] in {"vendor", "treasury"})
    patterns = [r"Allocate payments (TX-\d+) and (TX-\d+) to invoice " + re.escape(view["invoice_id"]),
                r"Treasury sent (TX-\d+) as the first instalment and (TX-\d+) as the balance for "
                + re.escape(view["invoice_id"]),
                r"Its replacement is (TX-\d+)\. The other tranche, (TX-\d+), cleared normally"]
    matches = {tuple(sorted(match.groups())) for pattern in patterns for match in re.finditer(pattern, text)}
    if len(matches) == 1:
        identities = list(next(iter(matches)))
        if set(identities) <= available:
            return identities
    return None


def choose(view: dict, mode: str, history: list[dict]) -> dict:
    def decision(action, reason, **parameters):
        return {"action": action, "reason": reason, **parameters}

    if not history:
        return decision("check", "Run deterministic reference and arithmetic checks before purchasing interpretation.",
                        payment_ids=deterministic_links(view) or [])
    if view["mandatory_review"]:
        return decision("escalate", "Conflicting allocation requires mandatory authorization, not consultation.")
    if not view["reviewer_can_help"]:
        return decision("abstain", "Allocation evidence is unavailable; amount matching cannot establish identity.")
    last = history[-1]
    payload = last.get("resource_result") or {}
    if last.get("action") == "consult" and payload.get("consultation", {}).get("payment_ids"):
        return decision("finalize", "Use purchased consultation allocation with deterministic arithmetic.",
                        payment_ids=payload["consultation"]["payment_ids"])
    if last.get("action") == "infer":
        if not payload.get("schema_valid"):
            return decision("abstain", "Provider output failed independent schema validation; usage still counts.")
        proposal = json.loads(payload["completion"]["choices"][0]["message"]["content"])
        if proposal["action"] == "finalize" and proposal["confidence"] != "high":
            return decision("consult" if view["consultations_remaining"] else "abstain",
                            "Model allocation remains uncertain; do not finalize confidently.")
        result = decision(proposal["action"], proposal["reason"])
        if proposal["action"] == "finalize":
            result["payment_ids"] = proposal["payment_ids"]
        if proposal["action"] == "fetch":
            if proposal["source"] in view["fetched_sources"]:
                return decision("abstain", "Repeated evidence request would consume resources without new evidence.")
            result["source"] = proposal["source"]
        return result
    links = deterministic_links(view)
    calls = sum(item.get("action") == "infer" for item in history)
    sources = {source["id"] for source in view["available_sources"]} - set(view["fetched_sources"])
    if mode != "always-llm" and links is not None:
        return decision("finalize", "Explicit deterministic allocation suffices; inference adds no expected gain.",
                        payment_ids=links)
    if mode != "always-llm" and "remittance" in sources:
        return decision("fetch", "Purchase the missing allocation attachment before reasoning.", source="remittance")
    if mode != "deterministic-only" and calls < 2:
        worthwhile = view["value"] // 2 > 600 and view["remaining_authority"] >= 1000
        if mode == "always-llm" or worthwhile:
            return decision("infer", "Semantic ambiguity remains; purchase bounded interpretation of evidence.")
    if links is not None:
        return decision("finalize", "Deterministic allocation remains available.", payment_ids=links)
    if view["consultations_remaining"] and view["remaining_authority"] >= 604:
        return decision("consult", "No reliable allocation; purchase scarce consultation rather than invent links.")
    return decision("abstain", "No justified affordable resolution remains.")
