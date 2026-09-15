"""Post-evaluation diagnostics only: never changes policies, prompts or frozen cases."""

import argparse
import json
from pathlib import Path

from aecp.semantic_workload import corpus


def analyze(path: Path):
    study = json.loads(path.read_text())
    truth = {case.observation["task_id"]: case.truth for case in corpus(study["corpus"]["split"])}
    diagnostics = {}
    for policy, consumer in study["consumers"].items():
        counts = {"model_proposals": 0, "unavailable_source_proposals": 0, "repeated_source_proposals": 0,
                  "appropriate_fetches_delivered": 0, "unnecessary_fetches_delivered": 0,
                  "nonempty_extractions": 0, "correct_extractions": 0, "model_finalizations": 0,
                  "provider_finish_length": 0}
        for case in consumer["cases"]:
            permitted = {source["id"] for source in case["provenance"]["observation"]["available_sources"]}
            fetched = set()
            for action in case["history"]:
                payload = action.get("resource_result") or {}
                if action.get("action") == "fetch" and "documents" in payload:
                    appropriate = payload["source"] in truth[case["task_id"]]["required_sources"]
                    counts["appropriate_fetches_delivered" if appropriate else "unnecessary_fetches_delivered"] += 1
                    fetched.add(payload["source"])
                if action.get("action") != "infer" or not payload.get("schema_valid"):
                    continue
                choice = payload["completion"]["choices"][0]
                proposal = json.loads(choice["message"]["content"])
                counts["model_proposals"] += 1
                counts["provider_finish_length"] += choice["finish_reason"] == "length"
                counts["model_finalizations"] += proposal["action"] == "finalize"
                if proposal["payment_ids"]:
                    counts["nonempty_extractions"] += 1
                    counts["correct_extractions"] += (
                        sorted(proposal["payment_ids"]) == truth[case["task_id"]]["payment_ids"])
                if proposal["action"] == "fetch":
                    counts["unavailable_source_proposals"] += proposal["source"] not in permitted
                    counts["repeated_source_proposals"] += proposal["source"] in fetched
        diagnostics[policy] = counts
    result = {"version": study["version"], "corpus": study["corpus"], "model": study["model"],
              "code_revision": study["code_revision"], "provider_calls": study["provider_calls"],
              "summaries": study["summaries"], "diagnostics": diagnostics, "audit": study["audit"],
              "purpose": "post-frozen-run descriptive analysis; no tuning or re-execution"}
    path.with_suffix(".summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return diagnostics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    print(json.dumps(analyze(parser.parse_args().path)))
