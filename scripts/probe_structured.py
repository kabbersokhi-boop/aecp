"""One opt-in, funded structured-output compatibility request; never silent retries."""

import argparse
import json
from pathlib import Path

from aecp.control import ControlPlane
from aecp.engine import code_revision
from aecp.ledger import Ledger
from aecp.nim import NimAdapter, NimTransport


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, default=Path("var/evidence-v21/structured-probe.json"))
    args = parser.parse_args()
    database = args.output.with_suffix(".sqlite3")
    if args.output.exists() or database.exists():
        parser.error("probe evidence exists; refusing to silently repeat a live request")
    transport = NimTransport(journal=Path("var/nim-v21-requests.jsonl"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    control = ControlPlane(Ledger(database))
    control.ledger.create_account("probe", 1000, unit="SIM_COST_MICRO")
    control.register_task("probe", "development-schema-probe", "reconcile")
    control.adapters["nim_chat"] = NimAdapter(args.model, transport)
    response_format = {"type": "json_schema", "json_schema": {"name": "resolution_probe_v21", "strict": True,
        "schema": {"type": "object", "properties": {"resolution": {"type": "string", "enum": ["matched"]}},
                   "required": ["resolution"], "additionalProperties": False}}}
    parameters = {"model": args.model, "max_tokens": 48, "temperature": 0, "response_format": response_format,
                  "messages": [{"role": "user", "content":
                      'Invoice 100, paid 100. Return JSON resolution matched and also an extra sum field of 100.'}]}
    control.prepare("structured-probe", "probe", "development-schema-probe", "nim_chat", parameters, expires_at=100)
    result = control.execute("structured-probe", "probe")
    artifact = {"code_revision": code_revision(), "model": args.model, "response_format": response_format,
                "request": result, "schema_supported_observed": bool(result["result"] and
                    result["result"].get("schema_valid")), "chat_attempts": 1, "catalog_attempts": 0,
                "actual_cash_spend": 0, "cash_basis": "operator-declared free prototype; no invoice",
                "interpretation": "one compatibility observation, not proof of semantic correctness"}
    args.output.write_text(json.dumps(artifact, indent=2) + "\n")
    print(json.dumps({key: artifact[key] for key in ("model", "schema_supported_observed", "chat_attempts")}))


if __name__ == "__main__":
    main()
