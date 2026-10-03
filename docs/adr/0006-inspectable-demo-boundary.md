# ADR 0006: inspectable requests without new execution authority

Status: implemented on `portfolio/aecp-demo-story`, based on public revision
`4d5120529659d9e182fbddb1a565e3f7fe6730fd`.

The portfolio demonstration needs a visible request origin and a readable failure
boundary. These are presentation improvements, not new economic primitives.

The independent `/agent.html` console uses the existing agent-scoped HTTP API.
Its capability stays in page memory, not browser storage. Task policy, funding,
approval and settlement remain server-owned. Reviewer requests are submitted once
per attempt per connection; browser reload is not a durable approval-status lookup.

`GET /api/v1/me/trace/{request_id}` is an agent-only read. One SQLite transaction
checks the request owner and selects events by both account and attempt. Denial
events can exist without a request row. Foreign and absent identities are hidden
behind the same not-found result. The original mutation response and subsequent
trace are displayed separately; inspection failures cannot relabel a definitive
execution response as transport ambiguity.

The failure viewer imports a bounded local `failure-conformance.v1` JSON export.
It does not expose arbitrary server paths, run benchmarks through an HTTP route,
or grant reconciliation authority. A SHA-256 identifies file bytes; it does not
attest generation time or truth. Scenario audits are report-supplied facts. Each
scenario is an independent fixture, not another stage of one live request. The
provider journal is ex-post evaluation evidence, not information available to an
agent when deciding to spend.

No paid inference, new backend dependency, accounting migration, n8n/GHL workflow,
or provider exactly-once guarantee is introduced. Existing NIM integration stays
opt-in; fresh hosted calls require explicit owner authorization and bounded use.
