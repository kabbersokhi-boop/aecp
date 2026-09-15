"""Bounded isolated semantic worker study. Development fake or single frozen held-out live evaluation."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import tempfile
import threading
from pathlib import Path

from isolation_validate import FixedRelay
from semantic_protocol import claim, validate

from aecp import interpretation, semantic_corpus_v3
from aecp.engine import Engine, code_revision
from aecp.nim import DEFAULT_BASE, NimAdapter, NimTransport, ProviderFailure
from aecp.semantic import PROMPT_VERSION, RESPONSE_FORMAT
from aecp.semantic_workload import manifest
from aecp.server import Application, credentials
from aecp.structured import schema_identity

POLICIES = ("deterministic-only", "always-llm", "selective")
POLICIES_V3 = ("rules-only", "rules-reviewer", "always-llm", "selective-llm", "selective-reviewer")


class BoundedTransport:
    def __init__(self, transport, limit=32):
        self.transport = transport
        self.base_url = transport.base_url
        self.limit = limit
        self.calls = 0

    def request(self, path, body):
        if self.calls >= self.limit:
            raise ProviderFailure("local_study_request_limit")
        self.calls += 1
        return self.transport.request(path, body)


class DevelopmentTransport:
    """Protocol fixture uses permitted text only; never eligible for quality evidence."""
    base_url = DEFAULT_BASE

    def request(self, path, body):
        view = json.loads(body["messages"][-1]["content"])
        direct = [payment["id"] for payment in view["payments"] if payment["reference"] == view["invoice_id"]]
        proposal = {"action": "finalize" if direct else "abstain", "payment_ids": direct, "source": "none",
                    "confidence": "high" if direct else "low", "reason": "Offline protocol fixture, not model quality."}
        if body.get("response_format", {}).get("json_schema", {}).get("name") == "allocation_interpretation_v3":
            proposal = {"assessment": "supported" if direct else "uncertain", "payment_ids": direct,
                        "document_ids": ["invoice"] if direct else [], "confidence": "high" if direct else "low",
                        "summary": "Offline protocol fixture, not model quality."}
        return {"id": "offline-fixture", "model": body["model"],
                "choices": [{"message": {"content": json.dumps(proposal)}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 40, "total_tokens": 140}}


def metrics(cases, *, live: bool):
    actions = [action for case in cases for action in case["actions"]]
    results = [action["result"] for action in actions if action["result"]]
    provider = [result["resource_result"] for result in results
                if result.get("action") == "infer" and result.get("resource_result")]
    outcomes = [case["outcome"] for case in cases if case["outcome"]]
    value = sum(outcome["verified_value"] for outcome in outcomes)
    verified = sum(outcome["verified"] for outcome in outcomes)
    unnecessary = 0
    for case in cases:
        records = [action["result"] for action in case["actions"] if action["result"]]
        initially_linked = next((result.get("resource_result", {}).get("payment_ids", []) for result in records
                                 if result.get("action") == "check"), [])
        if initially_linked:
            unnecessary += sum(result.get("action") == "infer" for result in records)
    usage = {name: sum(payload["provider_usage"][field] for payload in provider)
             for name, field in (("input_tokens", "prompt_tokens"), ("output_tokens", "completion_tokens"),
                                 ("total_tokens", "total_tokens"))}
    return {"tasks": len(cases), "verified_tasks": verified, "verified_value": value,
            "total_task_value": sum(case["observation"]["value"] for case in cases),
            "finalized": sum(outcome["disposition"] == "finalize" for outcome in outcomes),
            "appropriate_abstentions": sum(outcome["appropriate_abstention"] for outcome in outcomes),
            "appropriate_escalations": sum(outcome["appropriate_escalation"] for outcome in outcomes),
            "incorrect_confident_actions": sum(outcome["inappropriate_confident_action"] for outcome in outcomes),
            "evidence_requests": sum(result.get("action") == "fetch" for result in results),
            "consultations": sum(result.get("action") == "consult" for result in results),
            "schema_valid": sum(payload.get("schema_valid") is True for payload in provider),
            "provider_receipts": len(provider) if live else 0,
            "fixture_receipts": 0 if live else len(provider),
            "usage_basis": "provider_reported" if live else "offline_fixture_not_provider_usage",
            "fixture_usage": None if live else usage,
            "inference_despite_deterministic_links": unnecessary,
            **{name: amount if live else 0 for name, amount in usage.items()},
            "unfinished": len(cases) - len(outcomes), "denied_actions": sum("denied" in result for result in results),
            "actual_cash_spend": 0, "cash_basis": "declared free prototype access; not provider invoice evidence"
            if live else "offline fixture; no external execution"}


def run_study(output: Path, model: str, live: bool, *, workload: str = "v2.1", protocol: Path | None = None):
    if workload not in {"v2.1", "v3"}:
        raise ValueError("unknown workload")
    policies = POLICIES_V3 if workload == "v3" else POLICIES
    authority = 12000 if workload == "v3" else 4000
    corpus_manifest = semantic_corpus_v3.manifest if workload == "v3" else manifest
    split = "heldout" if live else "development"
    database = output.with_suffix(".sqlite3")
    if output.exists() or database.exists():
        raise ValueError("refusing to overwrite or silently repeat an existing study")
    frozen = None
    if live and workload == "v3":
        if protocol is None:
            raise ValueError("V3 held-out execution requires a committed --protocol")
        frozen = validate(Path(__file__).resolve().parents[1], protocol, model,
                          os.environ.get("AECP_NIM_BASE_URL", DEFAULT_BASE))
    provider = (NimTransport(base_url=os.environ.get("AECP_NIM_BASE_URL", DEFAULT_BASE),
                             journal=output.with_suffix(".provider-journal.jsonl"))
                if live else DevelopmentTransport())
    if frozen is not None:
        claim(protocol, frozen, output)
    transport = BoundedTransport(provider, limit=60 if workload == "v3" else 32)
    output.parent.mkdir(parents=True, exist_ok=True)
    engine = Engine(database)
    engine.ledger.create_account("semantic-study", authority * len(policies), unit="SIM_COST_MICRO")
    with tempfile.TemporaryDirectory(prefix="aecp-semantic-run-") as directory:
        root = Path(directory)
        principals = credentials(root / "capabilities.json")
        for policy in policies:
            agent = "semantic-study/" + policy
            engine.ledger.create_account(agent, authority, unit="SIM_COST_MICRO", parent_id="semantic-study")
            principals[policy] = {"token": secrets.token_urlsafe(32), "role": "agent", "agent_id": agent}
        engine.control.adapters["nim_chat"] = NimAdapter(model, transport)
        application = Application(("127.0.0.1", 0), engine, principals)
        for policy in policies:
            application.semantic_tasks.register("semantic-study/" + policy, split, workload=workload)
        thread = threading.Thread(target=application.serve_forever, daemon=True)
        thread.start()
        relay = FixedRelay(str(root / "relay.sock"), ("127.0.0.1", application.server_port))
        relay_thread = threading.Thread(target=relay.serve_forever, daemon=True)
        relay_thread.start()
        consumers = {}
        try:
            for policy in policies:
                token = root / "agent-token"
                token.write_text(principals[policy]["token"])
                token.chmod(0o600)
                configuration = root / "configuration.json"
                configuration.write_text(json.dumps({"url": f"http://127.0.0.1:{application.server_port}",
                                                      "policy": policy}))
                consumer = Path(__file__).resolve().parents[1] / "examples/semantic_consumer"
                command = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session", "--ro-bind", "/usr", "/usr",
                           "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib",
                           "--symlink", "usr/lib", "/lib64", "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                           "--ro-bind", str(consumer), "/app", "--ro-bind", str(token), "/agent-token",
                           "--ro-bind", str(configuration), "/configuration.json",
                           "--ro-bind", str(root / "relay.sock"), "/gateway.sock", "--clearenv", "--chdir", "/app",
                           "/usr/bin/python3", "-B", "/app/entry.py", "/configuration.json"]
                process = subprocess.run(command, env={"PATH": os.defpath}, capture_output=True,
                                         text=True, timeout=1200)
                if process.returncode:
                    raise RuntimeError(f"consumer failure: {process.returncode}; {process.stderr[:500]}")
                consumers[policy] = json.loads(process.stdout)
            snapshot = application.semantic_tasks.snapshot()
            summaries = {}
            for policy in policies:
                agent = "semantic-study/" + policy
                cases = [case for case in snapshot["cases"] if case["agent"] == agent]
                summaries[policy] = {**metrics(cases, live=live), "authority": engine.ledger.account(agent)}
                spent = summaries[policy]["authority"]["spent"]
                verified = summaries[policy]["verified_tasks"]
                value = summaries[policy]["verified_value"]
                summaries[policy].update(cost_per_verified_task=spent / verified if verified else None,
                                         cost_per_verified_value=spent / value if value else None)
            result = {"version": "semantic-quality." + workload, "corpus": corpus_manifest(split), "model": model,
                      "live": live, "prompt_version": interpretation.VERSION if workload == "v3" else PROMPT_VERSION,
                      "schema_id": "state-conditioned; exact identities in quotes" if workload == "v3"
                      else schema_identity(RESPONSE_FORMAT),
                      "code_revision": code_revision(), "provider_calls": transport.calls if live else 0,
                      "fixture_calls": 0 if live else transport.calls, "summaries": summaries,
                      "frozen_protocol": frozen,
                      "consumers": consumers, "operator_evidence": snapshot, "audit": engine.ledger.audit()}
            output.write_text(json.dumps(result, indent=2) + "\n")
            return {"provider_calls": result["provider_calls"], "summaries": summaries}
        finally:
            relay.shutdown()
            relay.server_close()
            application.shutdown()
            application.server_close()
            thread.join(timeout=5)
            relay_thread.join(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="nvidia/nemotron-3.5-lightning-30b-a3b")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--workload", choices=["v2.1", "v3"], default="v2.1")
    parser.add_argument("--protocol", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(run_study(arguments.output, arguments.model, arguments.live, workload=arguments.workload,
                               protocol=arguments.protocol)))
