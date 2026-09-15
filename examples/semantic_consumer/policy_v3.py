"""Public-state economic controller; interpretation never owns tool availability or money."""

from __future__ import annotations

import json
import re
import unicodedata

VERSION = "semantic-controller.v3.dev-1"
POLICIES = ("rules-only", "rules-reviewer", "always-llm", "selective-llm", "selective-reviewer")
RECOVERABLE = {"EVIDENCE_SOURCE_NOT_AVAILABLE", "CONSULTATION_CAPACITY_EXHAUSTED"}
MODEL_SUCCESS_PRIOR_PERCENT = 60
REVIEW_SUCCESS_PRIOR_PERCENT = 98


def deterministic_links(view: dict) -> list[str] | None:
    def normalize(value):
        return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKC", value).casefold())

    invoice = view["invoice_id"]
    direct = {payment["id"] for payment in view["payments"]
              if normalize(payment["reference"]) == normalize(invoice)}
    available = {payment["id"] for payment in view["payments"]}
    candidates = set()
    for document in view["documents"]:
        if document["source"] not in {"vendor", "treasury"}:
            continue
        text = " ".join(document["text"].split())
        pattern = (r"For\s+" + re.escape(invoice) + r",\s*allocate\s+(PAY-\d+)"
                   r"(?:\s+and\s+(PAY-\d+))?\.")
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            selected = frozenset(identity.upper() for identity in match.groups() if identity)
            if selected <= available:
                candidates.add(selected)
    if direct:
        candidates.add(frozenset(direct))
    if len(candidates) == 1:
        return sorted(next(iter(candidates)))
    return None


def interpretation(result: dict, view: dict) -> list[str] | None:
    payload = result.get("resource_result") or {}
    if payload.get("schema_valid") is not True:
        return None
    try:
        answer = json.loads(payload["completion"]["choices"][0]["message"]["content"])
        identities = answer["payment_ids"]
        documents = answer["document_ids"]
        if (answer["assessment"] != "supported" or answer["confidence"] != "high" or not identities or not documents
                or len(identities) != len(set(identities)) or len(documents) != len(set(documents))
                or not set(identities) <= {payment["id"] for payment in view["payments"]}
                or not set(documents) <= {document["id"] for document in view["documents"]}):
            return None
        return sorted(identities)
    except (ValueError, KeyError, TypeError, IndexError):
        return None


def choose(view: dict, mode: str, history: list[dict]) -> dict:
    if mode not in POLICIES:
        raise ValueError("unknown V3 policy")

    def decision(action, reason, **parameters):
        return {"action": action, "reason": reason, **parameters}

    valid = dict(view["valid_actions"])
    for item in history:
        if item.get("denied"):
            if item["denied"].get("error") not in RECOVERABLE:
                return decision("abstain", "Terminal authority or financial denial; do not search for a bypass.")
            valid.pop(item["action"], None)
    if view["mandatory_review"]:
        return decision("escalate", "Mandatory approval cannot be replaced by inference or optional consultation.")
    if not history:
        return decision("check", "Run deterministic reference matching and arithmetic first.",
                        payment_ids=deterministic_links(view) or [])
    if not view["reviewer_can_help"]:
        return decision("abstain", "No recoverable allocation evidence; matching amounts cannot prove identity.")
    last = history[-1]
    if last.get("action") == "consult":
        proposal = (last.get("resource_result") or {}).get("consultation", {})
        if proposal.get("payment_ids"):
            return decision("finalize", "Use the purchased reviewer allocation; arithmetic remains deterministic.",
                            payment_ids=proposal["payment_ids"])
    if last.get("action") == "infer":
        links = interpretation(last, view)
        if links:
            return decision("finalize", "High-confidence interpretation cites visible evidence; verify independently.",
                            payment_ids=links)
    budget = view["remaining_authority"]
    bounds = view["resource_bounds"]
    finish = bounds["finalize"]
    sources = valid.get("fetch", {}).get("sources", [])
    if "remittance" in sources and budget >= bounds["fetch"] + finish:
        return decision("fetch", "Buy the offered allocation attachment before paying for interpretation.",
                        source="remittance")
    links = deterministic_links(view)
    calls = sum(item.get("action") == "infer" for item in history)
    if links and (mode != "always-llm" or calls):
        return decision("finalize", "Unambiguous deterministic allocation; no further intelligence purchase.",
                        payment_ids=links)
    reviewer = (mode in {"rules-reviewer", "selective-reviewer"} and "consult" in valid
                and budget >= bounds["consult"] + finish)
    inference = (mode in {"always-llm", "selective-llm", "selective-reviewer"} and "infer" in valid
                 and calls == 0 and budget >= bounds.get("infer", budget + 1) + finish)
    expected_cost = max(1, bounds.get("infer", 0) - 256)
    benefit = view["value"] * MODEL_SUCCESS_PRIOR_PERCENT
    if inference and (mode == "always-llm" or benefit > expected_cost * 100):
        if (not reviewer or MODEL_SUCCESS_PRIOR_PERCENT * bounds["consult"]
                >= REVIEW_SUCCESS_PRIOR_PERCENT * expected_cost):
            return decision("infer", "Interpretation has positive prior expected value; quote is affordable. "
                            "60% success and 128 output tokens are declared assumptions, not calibrated facts.")
    if reviewer and view["value"] * REVIEW_SUCCESS_PRIOR_PERCENT > bounds["consult"] * 100:
        return decision("consult", "Scarce modeled reviewer has the better assumed value-per-cost alternative.")
    return decision("abstain", "No remaining purchase justifies its expected cost within authority and action limits.")
