"""Independent OpenAI-SDK consumer: only an AECP agent capability, no provider credentials or database."""

import json
import os
import sys
from urllib.request import Request, urlopen

from openai import APIStatusError, OpenAI

base = os.environ.get("AECP_URL", "http://127.0.0.1:8765")
token = os.environ["AECP_AGENT_TOKEN"]
client = OpenAI(base_url=base + "/v1", api_key=token, max_retries=0, timeout=60)
request = Request(base + "/api/v1/me/tasks", headers={"Authorization": "Bearer " + token})
with urlopen(request, timeout=10) as response:
    tasks = json.load(response)
results = []
for task in [task for task in tasks if not task["mandatory"]][:int(os.environ.get("AECP_CASE_LIMIT", "3"))]:
    identity = os.environ.get("AECP_ATTEMPT_PREFIX", "consumer") + "-" + task["task_id"]
    if os.environ.get("AECP_CONSUMER_POLICY") == "hybrid" and task["document_status"] == "complete":
        body = {"request_id": identity, "task_id": task["task_id"], "resource": "cheap", "parameters": {
            "invoice_cents": task["invoice_cents"], "payments": task["visible_payments"]}}
        request = Request(base + "/api/v1/resource-requests", data=json.dumps(body).encode(),
                          headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        with urlopen(request, timeout=10) as response:
            result = json.load(response)
        results.append({"task": task["task_id"], "decision": "cheap complete evidence", "usage": None,
                        "answer": result["result"]["resolution"],
                        "actual_modeled_cost": result["receipt"]["actual_units"]})
        continue
    try:
        completion = client.chat.completions.create(
            model=os.environ["AECP_NIM_MODEL"], max_tokens=96, temperature=0,
            messages=[{"role": "system", "content":
                "Reconcile permitted invoice evidence. Return only JSON with one field resolution: "
                "matched, duplicate, underpaid or overpaid. Sum all visible_payments. If the sum equals invoice_cents, "
                "return matched. If the sum exceeds invoice_cents and any payment amount repeats, return duplicate. "
                "Otherwise return underpaid if the sum is smaller or overpaid if larger. "
                "No markdown. Do not invent missing evidence."},
                {"role": "user", "content": json.dumps(task)}],
            extra_headers={"X-AECP-Task": task["task_id"], "Idempotency-Key":
                           identity})
        results.append({"task": task["task_id"], "answer": completion.choices[0].message.content,
                        "usage": completion.usage.model_dump(), "aecp": completion.model_extra.get("aecp")})
    except APIStatusError as error:
        results.append({"task": task["task_id"], "denied_status": error.status_code})
json.dump({"consumer": "independent OpenAI SDK process", "prompt_version": "explicit-resolution-semantics.v2",
           "policy": os.environ.get("AECP_CONSUMER_POLICY", "llm"), "results": results,
           "provider_credential_present": bool(os.environ.get("NVIDIA_API_KEY"))}, sys.stdout, indent=2)
print()
