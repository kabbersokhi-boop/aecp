# Independent integration challenge

**Target: 15–30 minutes. No outside engineer has completed it yet.** Automated
clean-room integration is not external adoption. Review is subject to the
[noncommercial license](../LICENSE); commercial integration needs separate permission.

## Operator preparation—not consumer privileges

Install Python 3.11+, then use fresh paths from the repository:

```bash
python3 -m pip install .
python3 scripts/provision_challenge.py --db var/challenge.sqlite3 \
  --tokens var/challenge-capabilities.json --agent-token-file var/challenge-agent.token
aecp serve --db var/challenge.sqlite3 --tokens var/challenge-capabilities.json --port 8765
```

Provisioning creates eight modeled units and a four-unit fake dispatched uncertainty
before server startup. No provider is called. Give the consumer only the endpoint,
its individual token through a private channel, and the task below. Never distribute
the capability collection, database path, provider key or operator/reviewer token.
The reference server is loopback-only, not an Internet multitenant deployment.

## Choice A: native HTTP or Python SDK (offline)

Write your own consumer with these inputs:
- Endpoint: `http://127.0.0.1:8765`.
- Your individual capability, privately stored as `agent.token`.
- Task: `challenge-invoice`; invoice 12,500 cents; payments `[5000, 7500]`.
- Permitted resource: `cheap`; operation: `reconcile`.
- Existing uncertainty: `challenge-uncertain-attempt`.

Produce:
1. A successful governed reconciliation with its reservation/settlement.
2. A duplicate using the same request ID that does not spend again.
3. A second distinct request denied for exhausted authority.
4. The existing uncertain attempt's upper bound before and after the operator
   restarts the server. It must remain unresolved, not refunded.
5. One understandable denial for an unknown task or self-approval attempt.

Optional SDK starting point, after installing the supplied wheel in your environment:

```python
from pathlib import Path
from aecp.client import Client

client = Client("http://127.0.0.1:8765", Path("agent.token").read_text().strip())
result = client.execute("my-first-attempt", "challenge-invoice", "cheap",
                        {"invoice_cents": 12500, "payments": [5000, 7500]})
print(result["reservation"]["state"], result["result"]["resolution"])
trace = client.call("/api/v1/requests/challenge-uncertain-attempt")
print(trace["reservation"]["state"], trace["reservation"]["upper_bound"])
```

Native HTTP uses `POST /api/v1/resource-requests` with request_id, task_id, resource,
parameters and operation; authenticate with your Bearer capability and JSON content
type. Inspect `GET /api/v1/me/budget` and `GET /api/v1/requests/{request_id}`.
Errors are JSON: budget 409, forbidden authority 403, authentication 401, per-agent
concurrency 429, global overload 503. Do not create a fresh request ID automatically
after an ambiguous transport error.

## Choice B: OpenAI-compatible client (operator opt-in)

This alternative requires a separately provisioned NIM-enabled server and sufficient
modeled authority; the eight-unit offline fixture cannot afford inference. The
operator supplies a registered task, probed model and agent capability. The provider
key stays server-side. No tools, streaming or arbitrary provider URLs are supported.

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8765/v1",
                api_key=agent_token, max_retries=0)
result = client.chat.completions.create(
    model=operator_supplied_model,
    messages=[{"role": "user", "content": permitted_task_evidence}],
    max_tokens=96, temperature=0,
    extra_headers={"X-AECP-Task": registered_task,
                   "Idempotency-Key": "my-funded-attempt"},
)
```

Here api_key means your AECP capability, not the NVIDIA key. A base-URL change alone
cannot identify task authority; the two headers supply that context. Inspect the
same native provenance endpoints. See [integration](INTEGRATION.md) for details.

## Automated clean-room verification

```bash
uv build
python3 scripts/clean_install_validate.py \
  --wheel dist/agent_economic_control_plane-0.2.0-py3-none-any.whl
```

The harness creates a fresh environment, installs only the wheel and declared
dependencies, copies the public consumer to a separate project, and runs it in
Bubblewrap without source-tree PYTHONPATH, database mounts, provider environment or
external networking. Linux/Bubblewrap/user namespaces are required for this security
proof, not ordinary SDK use. It is fake-provider recovery, not fresh NIM evidence.

## Invitation the owner may send

> Would you be willing to spend 15–30 minutes integrating a local, offline AECP
> endpoint into a small agent or client you already wrote? You will receive only a
> loopback URL, your scoped AECP capability, one registered task, and the supported
> API contract—no provider, database, operator, reviewer, or other-agent credentials.
> Please attempt one useful request, one denial, provenance inspection, and recovery
> inspection, then return the blank feedback fields below. This is source-available
> under PolyForm Noncommercial 1.0.0; no public endorsement is requested.

Do not send this invitation without separate authorization and an identified human
participant.

## Feedback—leave unanswered until a human participant tries it

- Existing application/client used:
- Exact setup steps taken:
- Setup time:
- Time to first governed request:
- Confusing instruction:
- Unexpected behavior:
- Denial code and interpretation:
- Recovery/unresolved-liability interpretation:
- Provenance fields inspected:
- Defect or security concern found:
- Could this fit the existing application? Why or why not?

Include sanitized request IDs/error codes, never capabilities or private records.
An outside engineer's actual report remains the non-automatable validation step.
