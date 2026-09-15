"""Trusted live-task registry and deterministic scoring, separate from model observations."""

from __future__ import annotations

import json
import time
from dataclasses import asdict

from aecp.control import ControlPlane, Denied
from aecp.determinism import canonical_json
from aecp.ledger import IdempotencyConflict, _identifier
from aecp.workload import corpus, resolve


class LiveTasks:
    def __init__(self, control: ControlPlane):
        self.control = control
        with control.ledger._transaction() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS live_tasks(
                agent_id TEXT NOT NULL, task_id TEXT NOT NULL, observation TEXT NOT NULL, truth TEXT NOT NULL,
                PRIMARY KEY(agent_id, task_id))""")
            connection.execute("""CREATE TABLE IF NOT EXISTS live_outcomes(
                request_id TEXT PRIMARY KEY, result TEXT NOT NULL)""")

    def register(self, agent: str, *, seed: int, count: int = 6) -> list[dict]:
        if type(seed) is not int or not 0 <= seed <= 1000000 or type(count) is not int or not 1 <= count <= 12:
            raise ValueError("bounded live corpus requires 1-12 tasks and a nonnegative seed")
        observations = []
        for case in corpus(seed, count=count):
            public = asdict(case.observation)
            task = "live-" + public["task_id"]
            public["task_id"] = task
            operation = "release_payment" if public["mandatory"] else "reconcile"
            self.control.register_task(agent, task, operation)
            truth = resolve(public["invoice_cents"], list(case.bank_payments))
            with self.control.ledger._transaction() as connection:
                old = connection.execute("SELECT observation, truth FROM live_tasks WHERE agent_id = ? AND task_id = ?",
                                         (agent, task)).fetchone()
                values = (canonical_json(public), truth)
                if old and tuple(old) != values:
                    raise IdempotencyConflict("live task corpus is immutable for an identity")
                connection.execute("INSERT OR IGNORE INTO live_tasks VALUES (?, ?, ?, ?)", (agent, task, *values))
            observations.append(public)
        return observations

    def observations(self, agent: str) -> list[dict]:
        with self.control.ledger._transaction() as connection:
            return [json.loads(row[0]) for row in connection.execute(
                "SELECT observation FROM live_tasks WHERE agent_id = ? ORDER BY task_id", (agent,))]

    def evaluate(self, request: dict) -> dict | None:
        with self.control.ledger._transaction() as connection:
            case = connection.execute("SELECT observation, truth FROM live_tasks WHERE agent_id = ? AND task_id = ?",
                                      (request["agent_id"], request["task_id"])).fetchone()
            old = connection.execute("SELECT result FROM live_outcomes WHERE request_id = ?",
                                     (request["id"],)).fetchone()
            if old:
                return json.loads(old[0])
            if not case or not request["result"]:
                return None
            observation = json.loads(case[0])
            completion = request["result"].get("completion")
            content = (completion["choices"][0]["message"]["content"] if completion else
                       json.dumps({"resolution": request["result"].get("resolution")}))
            try:
                answer = json.loads(content)
            except (ValueError, TypeError):
                answer = None
            valid = (isinstance(answer, dict) and set(answer) == {"resolution"}
                     and isinstance(answer["resolution"], str)
                     and answer["resolution"] in {"matched", "duplicate", "underpaid", "overpaid"})
            correct = bool(valid and answer["resolution"] == case[1])
            visible_baseline = resolve(observation["invoice_cents"], observation["visible_payments"])
            result = {"schema_valid": valid, "verified": correct,
                      "verified_value": observation["value"] if correct else 0,
                      "total_task_value": observation["value"], "evaluator": "hidden-bank-exact.v1",
                      "deterministic_same_observation_correct": visible_baseline == case[1],
                      "verification_mode": "offline evaluation; unmetered host CPU, not purchased execution",
                      "decision": f"consumer selected governed {request['resource']} for permitted evidence"}
            connection.execute("INSERT INTO live_outcomes VALUES (?, ?)", (request["id"], canonical_json(result)))
            self.control.ledger._event(connection, "live_task_evaluated", request["agent_id"], request["id"], **result)
            return result

    def snapshot(self) -> dict:
        with self.control.ledger._transaction() as connection:
            rows = connection.execute(
                "SELECT id, agent_id FROM requests WHERE resource = 'nim_chat' ORDER BY rowid").fetchall()
            requests = []
            for row in rows:
                request = self.control.request(row[0], row[1], connection=connection)
                outcome = connection.execute("SELECT result FROM live_outcomes WHERE request_id = ?",
                                             (row[0],)).fetchone()
                observation = connection.execute(
                    "SELECT observation FROM live_tasks WHERE agent_id = ? AND task_id = ?",
                    (request["agent_id"], request["task_id"])).fetchone()
                request["outcome"] = json.loads(outcome[0]) if outcome else None
                request["observation"] = json.loads(observation[0]) if observation else None
                request["events"] = [dict(event) for event in connection.execute(
                    "SELECT * FROM events WHERE hold_id = ? ORDER BY seq", (row[0],))]
                requests.append(request)
        return {"requests": requests, "snapshot_scope": "all nim_chat requests in one SQLite transaction",
                "cash_basis": "free prototype access, not a provider invoice", "actual_cash_spend": 0}


def chat_completion(control: ControlPlane, agent: str, task: str, request_id: str, body: dict,
                    *, now: int | None = None) -> dict:
    _identifier(task)
    _identifier(request_id)
    if (set(body) - {"model", "messages", "max_tokens", "temperature", "stream", "response_format"}
            or body.get("stream", False) is not False):
        raise Denied("UNSUPPORTED_CHAT_FEATURE")
    if "nim_chat" not in control.adapters:
        raise Denied("LIVE_ADAPTER_NOT_CONFIGURED")
    parameters = {"model": body.get("model"), "messages": body.get("messages"),
                  "max_tokens": body.get("max_tokens", 96), "temperature": body.get("temperature", 0)}
    if "response_format" in body:
        parameters["response_format"] = body["response_format"]
    now = int(time.time()) if now is None else now
    identity = f"{agent}/chat/{request_id}"
    with control.ledger._transaction() as connection:
        old = connection.execute("SELECT expires_at FROM holds WHERE id = ?", (identity,)).fetchone()
    control.prepare(identity, agent, task, "nim_chat", parameters, now=now, expires_at=old[0] if old else now + 300)
    result = control.execute(identity, agent, now=now)
    if result["reservation"]["state"] != "SETTLED" or not result["result"]:
        raise Denied("EXECUTION_UNRESOLVED_OR_UNAVAILABLE")
    LiveTasks(control).evaluate(result)
    if not result["result"].get("response_shape_valid", True):
        raise Denied("MALFORMED_PROVIDER_RESULT_USAGE_SETTLED")
    if result["result"].get("schema_valid") is False:
        raise Denied("PROVIDER_SCHEMA_VIOLATION_USAGE_SETTLED")
    return {**result["result"]["completion"], "aecp": {"request_id": identity, "state": "SETTLED",
            "modeled_cost": result["reservation"]["actual"], "unit": result["unit"], "actual_cash_spend": 0}}
