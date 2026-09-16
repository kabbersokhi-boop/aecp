# Agent integration contract

Status: native local gateway and Python SDK implemented. The authority contract below applies; exact routes follow.

## Working integration

Run `make demo`, `make serve`, then `make integration` in a second terminal. The harness launches both examples as independent processes with individual tokens and no database access. It separately uses operator authority for auction opening/clearing.

Examples read `AECP_AGENT_TOKEN` and optional `AECP_URL`. Native bidding uses `AECP_AUCTION_ID`; retain its `AECP_REQUEST_ID`, clear through the operator, then rerun without the auction variable to execute.

Implemented routes:

* Public: `GET /health`, `/`, `/app.js`, `/style.css`.
* Agent reads: `GET /api/v1/me/budget`, `/api/v1/requests/{id}`, `/api/v1/market/allocations`.
* Agent proposals: `POST /api/v1/resource-requests`, `/api/v1/market/bids`, `/api/v1/approval-requests`, `/api/v1/requests/cancel`.
* Viewer/operator: `GET /api/v1/system`, `/api/v1/runs`, `/api/v1/runs/{id}`.
* Reviewer: `GET /api/v1/reviewer/queue`; `POST /api/v1/reviewer/decisions`.
* Operator: `POST /api/v1/admin/tasks`, `/api/v1/admin/runs`, `/api/v1/admin/step`, `/api/v1/admin/complete`, `/api/v1/admin/auctions`, `/api/v1/admin/clear`.

An operator registers `{agent_id, task_id, required_operation}` first. Demo identities have `external-invoice-1`, `external-invoice-2`, `protected-payment`. Native requests use `{request_id, task_id, resource, parameters, operation?}`; parameters are exactly `{invoice_cents: integer, payments: integer[]}`. The request ID is the idempotency key. The optional V2 chat surface is described below; arbitrary outbound URLs remain forbidden.

Bids add `{bid_id, auction_id, price}` to a premium request. Each new native bidding operation costs 2 modeled operating units, independently of credit escrow; idempotent repeats do not recharge it. Operator auctions accept `{auction_id, capacity}` and expire after 300 seconds. Pending direct requests expire after 300 seconds; bid reservations inherit auction expiry. Dispatch uncertainty never expires into a refund. Approval requests add `approval_id` to the immutable action; reviewers inspect the full action and submit `{approval_id, approve: boolean}`. Approvals bind request and quote and expire after 300 seconds. Unknown tasks, operation downgrades and conflicting duplicate requests fail closed.

Adapters return a typed `Receipt` containing payload, actual integer units, accounting unit and source. Persisting the result and receipt is atomic; recovery settles that receipt without calling the provider again. Actual usage below the quote releases unused authority; a bound breach records the full charge and freezes the affected ancestry. An invalid or missing receipt leaves dispatched liability unresolved. A changed quote before dispatch requires fresh authorization.

Responses distinguish unauthenticated (401), permission/policy denial (403), accounting/lifecycle conflict (409) and malformed input (400). The SDK raises `ControlPlaneError` with the status and payload. A capacity denial can leave a funded request pending; cancel it explicitly if abandoning it. Agents cannot settle or reconcile. No live adapter is configured by default.

`ControlPlaneError` also exposes `code`, optional `detail`, and optional
`retry_same_idempotency_key` attributes so consumers do not need to parse the raw
payload for ordinary denial handling. A transport ambiguity is not a typed denial:
inspect the original request ID before deciding whether a separately funded retry is
appropriate.

## V2: independent OpenAI-compatible consumer

Only `POST /v1/chat/completions` is supported: non-streaming `model`, `messages`,
`max_tokens` (1–256), and temperature 0 or 0.1. No tools, Responses API, arbitrary
parameters or provider URLs. `Authorization: Bearer <agent-capability>` authenticates
the agent; `X-AECP-Task` identifies a registered reconcile task; `Idempotency-Key`
identifies one immutable attempt. Protected operations are not supported by this
chat route and cannot be downgraded. Native action-bound approval remains available.

Operator setup, in a trusted shell with the temporary provider key already present:

```bash
export AECP_ENABLE_LIVE_NIM=1
PYTHONPATH=src python3 -m aecp nim-discover --output var/nim-selected.json
export AECP_NIM_MODEL="$(python3 -c 'import json; print(json.load(open("var/nim-selected.json"))["selected_model"])')"
make serve
```

Do not proceed if discovery has no selected model. It performs at most three tiny
requests per candidate and makes no automatic transport retries. Hosted base defaults
to `https://integrate.api.nvidia.com/v1`; `AECP_NIM_BASE_URL` may only identify that
approved HTTPS origin/path. Model catalog presence alone is not proof of usability.

In a separate **operator** process, provision an individual capability through the
documented SDK, without handing the consumer the operator file:

```python
import json
from pathlib import Path
from aecp.client import Client

principals = json.loads(Path("var/local-capabilities.json").read_text())
operator = Client("http://127.0.0.1:8765", principals["operator"]["token"])
identity = operator.call("/api/v1/admin/agents", {"name": "consumer-one", "budget": 800})
operator.call("/api/v1/admin/live-cases", {"agent_id": identity["agent_id"], "seed": 7, "count": 8})
```

Transfer only `identity["token"]` by a secure local mechanism to the consumer's
`AECP_AGENT_TOKEN`; set `AECP_URL` and the selected `AECP_NIM_MODEL`. Do not print
capabilities into shared logs. Child budgets share the gateway's existing 2,000-unit
root, rather than creating funding. Names must be new; duplicates fail closed.

```bash
python3 -m venv /tmp/aecp-consumer
/tmp/aecp-consumer/bin/pip install openai
env -u NVIDIA_API_KEY -u AECP_ENABLE_LIVE_NIM /tmp/aecp-consumer/bin/python examples/openai_consumer.py
```

The consumer imports only the OpenAI SDK and standard library. It fetches its permitted
observations from `/api/v1/me/tasks`, uses `base_url=AECP_URL + "/v1"`, and disables
SDK retries (`max_retries=0`). `AECP_CONSUMER_POLICY=hybrid` selects native cheap
execution for complete documents. A one-unit identity demonstrates HTTP 409 without
provider dispatch. An unknown task gives HTTP 403. Repeating an idempotency key must
not issue a new provider request; an intentional retry requires a new key and hold.

Operator/viewer `GET /api/v1/provider-executions` and the Provider evidence dashboard
show quote assumptions, actual usage, modeled cost, zero declared cash, settlement
and independent schema/hidden-bank evaluation. Malformed answers do not earn utility,
but valid usage still settles. See [the demo](DEMO.md) for the automated clean-process
consumer and real crash checkpoints. This is independent integration, not adoption.

## Integration promise

A passive agent sends normal resource requests through a gateway and receives a result or a structured denial. A budget-aware agent additionally observes its permitted balance and participates in resource allocation. Neither receives database credentials, provider keys, or authority to edit balances.

Keep the control plane usable without the dashboard and the simulator. Provide a tiny standalone client example in a separate process to prove the boundary is real.

## Authority surfaces

| Principal | Permitted operations |
| --- | --- |
| Operator/admin | Provision identities, assign pre-funded scopes, configure a run, pause execution |
| Agent | Inspect own scope; request permitted resources; bid with own escrow; request optional consultation |
| Reviewer | Approve or reject an immutable action in an authorized scope |
| Adapter/worker | Claim authorized execution, report validated usage, reconcile ambiguous attempts |
| Dashboard viewer | Read permitted projections and evidence; no implicit operator authority |

A request-body `agent_id` is a selector, not authentication. Bind a presented credential to its principal server-side, validate ownership of referenced IDs, and apply authorization on every route. Agent-readable telemetry must not reveal evaluator-only seeds, hidden answers, other principals' private evidence, or provider credentials. Operator-visible audit detail is not automatically safe to expose to agents. Development tokens must be generated/configured outside source control and redacted from logs. Local-only demo mode must be clearly labeled and never exposed publicly by default.

## Suggested first API

The exact names can change when justified; authority separation cannot.

```text
GET  /health
GET  /api/v1/me/budget
POST /api/v1/resource-requests
GET  /api/v1/requests/{request_id}
POST /api/v1/market/bids
GET  /api/v1/market/allocations
POST /api/v1/approval-requests
POST /api/v1/reviewer/decisions       reviewer only
POST /api/v1/admin/runs              operator only
GET  /api/v1/runs/{run_id}/events     scoped read or server-sent events
GET  /api/v1/runs/{run_id}/metrics    scoped read
```

Funding, policy changes, settlement, and no-charge reconciliation are not agent APIs. Do not expose unauthenticated `/budgets/fund` or agent-controlled `/transactions/settle` endpoints.

A resource request contains task identity, requested resource, bounded request parameters, and an idempotency key. The server derives a quote, checks mandatory authorization, obtains capacity, reserves the applicable cost cap, persists dispatch, executes the adapter, and settles/reconciles. The quote and canonical request fingerprint must bind to the actual operation. The agent's maximum acceptable price is not itself a valid provider cost bound.

Return structured denials such as `BUDGET_EXHAUSTED`, `CAPACITY_UNAVAILABLE`, `APPROVAL_REQUIRED`, `POLICY_DENIED`, `QUOTE_UNBOUNDED`, and `ACCOUNT_FROZEN`. SDKs should expose typed outcomes rather than infinite automatic retries. A cost view includes unit, source/mode, quote version, reserved/settled amounts, and unresolved exposure.

## Compatibility scope

An OpenAI-compatible route is optional after native integration works. If implemented, document the exact supported endpoints, parameters, streaming behavior, tools, error semantics, and provider translations. Test a real client against it. Do not claim universal drop-in support or invent provider model identifiers.

A future commercial adapter must keep keys in the gateway, declare all billable components, bound attempts and output, and document price provenance/reconciliation. A local adapter must distinguish marginal cash spend from allocated hardware cost. Implemented modes, fixtures, and unavailable modes must not be visually conflated.

## Deployment limit

Application mediation is enforceable only within its trust boundary. An agent retaining raw provider credentials or unrestricted paid-resource access can bypass the gateway. First-build request-level security tests do not establish host isolation. Keep local service binding and origin controls explicit; do not present a localhost token demo as hardened public multitenancy.
