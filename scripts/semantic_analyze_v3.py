"""Post-run independent grading; never imported by the worker or used for tuning."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from aecp.semantic_corpus_v3 import corpus, manifest


def analyze(source: Path, journal: Path, output: Path) -> dict:
    data = json.loads(source.read_text())
    if not data["live"] or data["corpus"] != manifest("heldout"):
        raise ValueError("requires the frozen live V3 held-out artifact")
    truth = {case.observation["task_id"]: case.truth for case in corpus("heldout")}
    policies = {}
    for policy, summary in data["summaries"].items():
        confidence = defaultdict(lambda: {"responses": 0, "linking_correct": 0})
        attempts = unsupported = 0
        for case in data["operator_evidence"]["cases"]:
            if case["agent"] != "semantic-study/" + policy:
                continue
            for action in case["actions"]:
                if action["proposal"]["action"] != "infer":
                    continue
                attempts += 1
                payload = (action.get("result") or {}).get("resource_result") or {}
                if not payload.get("schema_valid"):
                    continue
                answer = json.loads(payload["completion"]["choices"][0]["message"]["content"])
                group = confidence[answer["confidence"]]
                group["responses"] += 1
                correct = sorted(answer["payment_ids"]) == truth[case["task"]]["payment_ids"]
                group["linking_correct"] += correct
                unsupported += answer["assessment"] == "supported" and not correct
        spent, outstanding = summary["authority"]["spent"], summary["authority"]["reserved"]
        value = summary["verified_value"]
        policies[policy] = {**summary, "inference_attempts": attempts, "confidence_linkage": dict(confidence),
                            "schema_valid_unsupported_allocations": unsupported,
                            "settled_plus_outstanding": spent + outstanding,
                            "exposure_per_verified_value": (spent + outstanding) / value if value else None}
    rows = [json.loads(line) for line in journal.read_text().splitlines()]
    returned = [row for row in rows if row["phase"] == "returned"]
    result = {"version": "semantic-postrun.v3.1", "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "journal_sha256": hashlib.sha256(journal.read_bytes()).hexdigest(), "corpus": data["corpus"],
              "frozen_protocol": data["frozen_protocol"], "policies": policies,
              "provider_attempts": sum(row["phase"] == "dispatch" for row in rows),
              "provider_outcomes": dict(Counter(row["category"] for row in returned)),
              "known_usage": {name: sum(row.get("usage", {}).get(name, 0) for row in returned)
                              for name in ("prompt_tokens", "completion_tokens", "total_tokens")},
              "audit": data["audit"], "actual_cash_spend": 0,
              "limitations": ["one sequential live replication; provider conditions may differ by policy",
                              "timeout usage is unknown, not zero; retained liabilities included in exposure ratios",
                              "confidence groups are descriptive, not calibrated probabilities",
                              "synthetic reviewer and utility; no actual human or commercial invoice"]}
    with output.open("x") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    return {"provider_attempts": result["provider_attempts"], "provider_outcomes": result["provider_outcomes"],
            "known_usage": result["known_usage"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(analyze(arguments.source, arguments.journal, arguments.output)))
