"""Run a scoped worker without database, operator capabilities or provider credentials."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from client import Client, GatewayError
from policy import VERSION, choose
from policy_v3 import POLICIES, RECOVERABLE
from policy_v3 import VERSION as VERSION_V3
from policy_v3 import choose as choose_v3


def run(client: Client, mode: str) -> dict:
    tasks = client.request("GET", "/api/v1/semantic/tasks")
    version_three = bool(tasks and tasks[0].get("workload_version", "").startswith("semantic-finops.v3"))
    results = []
    for initial in tasks:
        task = initial["task_id"]
        history = []
        for step in range(initial["deadline_steps"]):
            provenance = client.request("GET", "/api/v1/semantic/tasks/" + task)
            view = provenance["observation"]
            if view["status"] != "OPEN":
                break
            proposal = choose_v3(view, mode, history) if version_three else choose(view, mode, history)
            try:
                result = client.request("POST", "/api/v1/semantic/actions", {
                    "request_id": f"{task}-{step}", "task_id": task, **proposal})
            except GatewayError as error:
                history.append({"action": proposal["action"], "denied": error.payload, "status": error.status})
                if version_three and error.payload.get("error") in RECOVERABLE:
                    continue
                break
            history.append(result)
            if result.get("unresolved") or proposal["action"] in {"finalize", "abstain", "escalate"}:
                break
        results.append({"task_id": task, "history": history,
                        "provenance": client.request("GET", "/api/v1/semantic/tasks/" + task)})
    return {"policy": mode, "policy_version": VERSION_V3 if version_three else VERSION, "cases": results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--unix-socket")
    parser.add_argument("--policy", choices=sorted(set(POLICIES) | {"deterministic-only", "selective"}), required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    client = Client(arguments.url, arguments.token_file.read_text().strip(), arguments.unix_socket)
    result = run(client, arguments.policy)
    arguments.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"policy": arguments.policy, "tasks": len(result["cases"])}))


if __name__ == "__main__":
    main()
