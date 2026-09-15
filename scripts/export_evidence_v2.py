"""Export only named, sanitized evidence; never databases or capability files."""

import gzip
import hashlib
import json
import sqlite3
import statistics
from collections import Counter
from pathlib import Path

root = Path("docs/reports/evidence-v2")
root.mkdir(parents=True, exist_ok=True)
sources = ["var/nim-discovery.json", "var/nim-discovery-fallback.json", "var/nim-selected.json",
           "var/evidence-v2/live.json", "var/evidence-v2/live-final.json", "var/evidence-v2/study-final.json",
           "var/evidence-v2/performance-final.json", "var/evidence-v2/browser.json", "var/benchmark-v2/benchmark.json"]
manifest = []
for source in sources:
    payload = Path(source).read_bytes()
    destination = root / (Path(source).stem + ".json.gz")
    destination.write_bytes(gzip.compress(payload, mtime=0))
    manifest.append({"source": source, "artifact": destination.name,
                     "uncompressed_sha256": hashlib.sha256(payload).hexdigest()})
journal = [json.loads(line) for line in Path("var/nim-requests.jsonl").read_text().splitlines()]
(root / "provider-journal.json").write_text(json.dumps(journal, indent=2) + "\n")
returned = [row for row in journal if row["phase"] == "returned"]
dispatched = [row for row in journal if row["phase"] == "dispatch"]
usage = {name: sum(row.get("usage", {}).get(name, 0) for row in returned)
         for name in ("prompt_tokens", "completion_tokens", "total_tokens")}
with sqlite3.connect("file:var/live-v2-final.sqlite3?mode=ro", uri=True) as connection:
    outcomes = [{"request_id": row[0], "agent": row[1], "outcome": json.loads(row[2])} for row in connection.execute(
        "SELECT requests.id, requests.agent_id, live_outcomes.result FROM live_outcomes "
        "JOIN requests ON requests.id = live_outcomes.request_id ORDER BY requests.rowid")]
    accounts = {row[0]: {"settled": row[1], "reserved": row[2]} for row in connection.execute(
        "SELECT id, spent, reserved FROM accounts WHERE id IN ('gateway/live-first', 'gateway/live-repeat')")}
(root / "live-evaluations.json").write_text(json.dumps(outcomes, indent=2) + "\n")
quality = {}
for agent in sorted({row["agent"] for row in outcomes}):
    values = [row["outcome"] for row in outcomes if row["agent"] == agent]
    quality[agent] = {"cases": len(values), "verified": sum(row["verified"] for row in values),
                      "verified_value": sum(row["verified_value"] for row in values),
                      "total_value": sum(row["total_task_value"] for row in values),
                      "visible_deterministic_correct": sum(row["deterministic_same_observation_correct"]
                                                          for row in values),
                      **accounts[agent]}
study = json.loads(Path(sources[5]).read_text())
strategies = {strategy: {metric: statistics.mean(row[metric] for row in study["strategic"]
              if row["strategy"] == strategy) for metric in (
                  "verified_value", "modeled_cost", "market_revenue", "jain_access")}
              for strategy in sorted({row["strategy"] for row in study["strategic"]})}
summary = {"source_manifest": manifest, "all_run_provider_requests": len(dispatched),
           "chat_requests": sum(row["endpoint"] == "/chat/completions" for row in dispatched),
           "catalog_requests": sum(row["endpoint"] == "/models" for row in dispatched),
           "returned_categories": dict(Counter(row["category"] for row in returned)),
           "provider_reported_usage": usage, "actual_cash_spend": 0,
           "cash_basis": "operator-declared NVIDIA free prototype, no invoice", "live_quality": quality,
           "deterministic_trials": len(study["rows"]), "bid_perturbation_trials": len(study["strategic"]),
           "strategies": strategies}
(root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
