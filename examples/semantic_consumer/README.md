# Independent semantic consumer (development checkpoint)

This standard-library application imports no AECP implementation modules. It receives only a gateway URL and one agent capability. The server retains task evidence, evaluator state, provider credentials and settlement authority.

The operator first registers the scoped development cases with `POST /api/v1/admin/semantic-cases`, JSON `{"agent_id":"gateway/passive","split":"development"}`. Only the operator can register cases. Give the consumer a file containing **only its own token**, not the server capability configuration.

```bash
python3 examples/semantic_consumer/main.py \
  --url http://127.0.0.1:8765 --token-file /path/to/own-agent-token \
  --policy deterministic-only --output /tmp/consumer-result.json
```

The public contract is `GET /api/v1/semantic/tasks`, `GET /api/v1/semantic/tasks/{task_id}` and `POST /api/v1/semantic/actions`. Action fields are `request_id`, `task_id`, `action`, `reason`, plus `payment_ids` for checks/finalization or `source` for evidence retrieval. Actions: `check`, `fetch`, `infer`, `consult`, `finalize`, `abstain`, `escalate`. Every action incurs modeled planning cost; tools and inference additionally reserve quoted operating exposure. Escalation records a need for mandatory oversight; it does not manufacture approval or award resolved-task value.

`always-llm` and `selective` require a server-configured NIM adapter. No provider credential is accepted by this consumer. Rules recognize explicit references/allocation statements; arithmetic remains deterministic. The worker can buy an attachment, act on a model proposal, consult a scarce modeled reviewer, abstain or escalate. It stops on denial or unresolved execution rather than silently retrying a potentially billable operation. The limit is eight steps and at most two inference calls per task. Mandatory-review and missing-evidence cases stop without inference in every policy; “always” applies to cases eligible for autonomous resolution.

`--unix-socket` supports a fixed-destination relay for the forthcoming namespace demonstration. Same-user execution is **not** filesystem isolation. The subprocess regression proves the public contract, not hostile-code sandboxing or outside human adoption.

Held-out evaluation has not started. Development results are not held-out quality evidence.
