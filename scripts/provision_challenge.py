"""Operator-only offline provisioning; consumer receives one token, never trusted state paths."""

import argparse
import json
import os
import secrets
from pathlib import Path

from aecp.engine import Engine
from aecp.server import credentials, provision


def provision_challenge(database: Path, capabilities: Path, agent_token: Path):
    if database.exists() or capabilities.exists() or agent_token.exists():
        raise ValueError("use fresh challenge paths; this command must run before starting the server")
    database.parent.mkdir(parents=True, exist_ok=True)
    engine = Engine(database)
    provision(engine)
    principals = credentials(capabilities)
    agent = "gateway/challenge"
    engine.ledger.create_account(agent, 8, unit="SIM_COST_MICRO", parent_id="gateway")
    for task in ("challenge-invoice", "challenge-uncertain"):
        engine.control.register_task(agent, task, "reconcile")
    engine.control.prepare("challenge-uncertain-attempt", agent, "challenge-uncertain", "cheap",
                           {"invoice_cents": 100, "payments": [100]}, expires_at=2**53)
    engine.control.execute("challenge-uncertain-attempt", agent, ambiguous=True)
    principal = {"token": secrets.token_urlsafe(32), "role": "agent", "agent_id": agent}
    principals["challenge"] = principal
    with capabilities.open("w") as stream:
        json.dump(principals, stream)
        stream.flush()
        os.fsync(stream.fileno())
    agent_token.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(agent_token, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(principal["token"])
    return {"agent": agent, "funded": 8, "unresolved": 4, "available": 4,
            "task": "challenge-invoice", "uncertain_request": "challenge-uncertain-attempt",
            "provider_calls": 0, "outside_human_validation": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--tokens", type=Path, required=True)
    parser.add_argument("--agent-token-file", type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(provision_challenge(arguments.db, arguments.tokens, arguments.agent_token_file)))
