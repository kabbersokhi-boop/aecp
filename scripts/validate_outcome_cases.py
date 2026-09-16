"""Validate future outcome-study cases without evaluating any worker or calling a provider."""

import argparse
import json
from pathlib import Path


def validate(path: Path, *, require_independent: bool = False) -> dict:
    data = json.loads(path.read_text())
    if data.get("version") != "aecp.outcome-cases.v1":
        raise ValueError("unsupported case format")
    contributor = data.get("contributor")
    if not isinstance(contributor, dict) or not contributor.get("permission_to_use"):
        raise ValueError("contributor permission is required")
    if not contributor.get("provenance_statement"):
        raise ValueError("contributor provenance statement is required")
    independently_authored = contributor.get("independently_authored") is True
    if require_independent and not independently_authored:
        raise ValueError("final study requires independently authored cases")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("at least one case is required")
    identities = set()
    for case in cases:
        required = {"case_id", "observation", "acceptable_outcomes", "provenance", "confidential_material"}
        if not isinstance(case, dict) or set(case) != required:
            raise ValueError("case fields do not match the v1 contract")
        if case["case_id"] in identities:
            raise ValueError("duplicate case identity")
        identities.add(case["case_id"])
        if not isinstance(case["observation"], dict) or not case["observation"]:
            raise ValueError("case observation must be a non-empty object")
        outcomes = case["acceptable_outcomes"]
        if not isinstance(outcomes, list) or not outcomes:
            raise ValueError("acceptable outcomes must be predeclared")
        for outcome in outcomes:
            if set(outcome) != {"classification", "action", "reason"}:
                raise ValueError("acceptable outcome fields do not match the v1 contract")
            if outcome["classification"] not in {"correct_resolution", "appropriate_abstention",
                                                   "appropriate_escalation"}:
                raise ValueError("invalid acceptable outcome classification")
        if not isinstance(case["provenance"], str) or not case["provenance"].strip():
            raise ValueError("case provenance is required")
        confidential = case["confidential_material"]
        if confidential not in {"none", "authorized"}:
            raise ValueError("confidential material requires explicit authorization")
    return {"cases": len(cases), "independently_authored": independently_authored,
            "permission_to_use": True, "provider_calls": 0,
            "eligible_for_final_study": independently_authored and data.get("fixture") is False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--require-independent", action="store_true")
    arguments = parser.parse_args()
    print(json.dumps(validate(arguments.path, require_independent=arguments.require_independent), sort_keys=True))
