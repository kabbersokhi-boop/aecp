"""Bounded development-only catalog/semantic compatibility selection through funded execution."""

import argparse
import json
import os
from pathlib import Path

from aecp.control import ControlPlane
from aecp.engine import code_revision
from aecp.interpretation import parameters
from aecp.ledger import Ledger
from aecp.nim import DEFAULT_BASE, PREFERENCES, NimAdapter, NimTransport
from aecp.semantic_corpus_v3 import corpus, manifest


def probe(output: Path) -> dict:
    database = output.with_suffix(".sqlite3")
    journal = output.with_suffix(".journal.jsonl")
    if any(path.exists() for path in (output, database, journal)):
        raise ValueError("refusing to repeat or overwrite a compatibility probe")
    transport = NimTransport(base_url=os.environ.get("AECP_NIM_BASE_URL", DEFAULT_BASE), journal=journal)
    catalog = transport.request("/models")
    models = sorted(item["id"] for item in catalog.get("data", [])
                    if isinstance(item, dict) and isinstance(item.get("id"), str))
    cases = []
    for topology in ("single", "split", "replacement"):
        cases.append(next(case for case in corpus("development")
                          if case.truth["semantic_kind"] == topology
                          and case.truth["composition"]["access"] == "visible"))
    control = ControlPlane(Ledger(database))
    control.ledger.create_account("development-probe", 12000, unit="SIM_COST_MICRO")
    records = []
    for model_index, model in enumerate(PREFERENCES):
        if model not in models:
            records.append({"model": model, "catalog_present": False, "attempts": []})
            continue
        control.adapters["nim_chat"] = NimAdapter(model, transport)
        attempts = []
        for index, case in enumerate(cases):
            task = case.observation["task_id"]
            control.register_task("development-probe", task, "reconcile")
            identity = f"probe-{model_index}-{index}"
            control.prepare(identity, "development-probe", task, "nim_chat", parameters(case.observation, model))
            result = control.execute(identity, "development-probe")
            payload = result.get("result") or {}
            answer = json.loads(payload["completion"]["choices"][0]["message"]["content"]) \
                if payload.get("schema_valid") else {}
            attempts.append({"task_id": task, "schema_valid": payload.get("schema_valid", False),
                             "linking_correct": sorted(answer.get("payment_ids", [])) == case.truth["payment_ids"],
                             "execution": result})
            if result["reservation"]["state"] != "SETTLED":
                break
        records.append({"model": model, "catalog_present": True, "attempts": attempts})
    eligible = [record for record in records if len(record["attempts"]) == 3
                and all(attempt["schema_valid"] for attempt in record["attempts"])]
    selected = max(eligible, key=lambda record: sum(attempt["linking_correct"] for attempt in record["attempts"]),
                   default=None)
    entries = [json.loads(line) for line in journal.read_text().splitlines()]
    returned = [entry for entry in entries if entry["phase"] == "returned"]
    result = {"version": "semantic-selection.v3.1", "source_commit": code_revision(),
              "development_corpus": manifest("development"), "catalog": models, "base_url": transport.base_url,
              "selected_model": selected["model"] if selected else None, "probes": records,
              "selection_rule": "three schema-valid replies; highest development linkage, preference-order ties",
              "catalog_calls": sum(entry["endpoint"] == "/models" for entry in returned),
              "chat_calls": sum(entry["endpoint"] == "/chat/completions" for entry in returned),
              "usage": {name: sum(entry.get("usage", {}).get(name, 0) for entry in returned)
                        for name in ("prompt_tokens", "completion_tokens", "total_tokens")},
              "actual_cash_spend": 0, "cash_basis": "operator-declared free prototype access; no invoice",
              "audit": control.ledger.audit()}
    output.write_text(json.dumps(result, indent=2) + "\n")
    return {key: result[key] for key in ("selected_model", "catalog_calls", "chat_calls", "usage", "audit")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    print(json.dumps(probe(arguments.output)))
