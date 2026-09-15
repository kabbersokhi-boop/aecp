# Security boundary

This is an early research/engineering project, not a certified financial system or a public multitenant service.

The kernel assumes trusted Python callers and a protected local SQLite database. HTTP authenticates separate agent/operator/reviewer/viewer capabilities and admits only scoped registered operations. Direct storage access, malicious same-process code, host compromise and out-of-band paid API access are outside its boundary. Hashes aid reproduction, not tamper-proof logging.

No provider credentials, customer data or payment capability are distributed. An optional NIM adapter executes real hosted inference with server-side opt-in. Its resource expenses are modeled, provider tokens are observed, and prototype cash spend is declared zero rather than invoice-verified. Credentials remain in the gateway, never in frontend bundles, agent observations, logs, traces, fixtures or committed environment files.

A strict spending claim depends on a valid liability bound and complete mediation. A guessed price, estimated token count, or local request timeout does not establish that condition. Unexpected actual charges must be retained and surfaced, not suppressed.

HTTP binds only to loopback, checks Host/Origin, bounds JSON bodies, applies CSP and redacts internal exceptions. It validates unique capability configuration. Task policy comes from the operator; unknown IDs fail closed. Reviewer identity cannot come from an agent field. There is no execution tool or external URL proxy.

Approval binds the request and configured quote. Capacity checks and dispatch claims share one transaction. Provider exceptions retain liabilities. Capabilities are generated into an ignored mode-0600 file and distributed individually. TLS, public identity rotation/revocation, rate limits and multi-host coordination are not implemented.

Individual amounts are signed 64-bit integers. Cumulative spend uses `spent + spent_high * 2^63`, where `spent_high` is an exact decimal integer string. This preserves even multiple maximal invoices without SQLite promoting arithmetic to floating point. Public projections decode the full total and audits recompute it from holds. HTTP integers beyond JavaScript's exact range are decimal strings. These safeguards are tested; they do not substitute for a defensible provider liability bound.

Report vulnerabilities privately to the repository owner through an available private channel. Do not include credentials or sensitive records in an issue. Public security-reporting and release policies will be established before public operation.
# V2 hosted-provider boundary

Unknown tasks fail closed inside `ControlPlane.prepare`, not just the HTTP adapter.
NIM is disabled unless `AECP_ENABLE_LIVE_NIM=1` and a server-side key are present.
The hosted HTTPS origin is allowlisted; redirects and ambient proxy configuration
cannot redirect its credential. The OpenAI-compatible surface does not accept tools,
streaming, arbitrary provider endpoints, settlement truth or model-selected identity.

The live adapter binds model, input-byte size, output allowance and versioned resource
cost to authorization. Missing usage retains uncertainty; valid usage on malformed
output still settles. This is a modeled resource bound, **not a hard dollar bound**.
Free prototype cash is operator-declared zero, not invoice reconciliation. Transition
to a billed endpoint requires a new reviewed cost/billing contract.

Provider output is untrusted text. The exact-output evaluator rejects extra fields
and non-scalar labels; model compliance with malicious instructions cannot grant
approval or budget. No reasoning fields are retained. Provider error bodies and
authorization headers are never copied into provenance. `scripts/secret_audit.py`
checks generated state and tracked git blobs without printing the runtime secret.

## V2.1 demonstrated consumer boundary

`scripts/isolation_validate.py` and the semantic study runner launch consumers in
Bubblewrap user/mount/PID/network namespaces. They receive a read-only consumer
directory, runtime libraries, public task configuration, their own scoped token
and a Unix socket connected by a bounded relay to one fixed loopback gateway.
Host home directories, SQLite, other capabilities and provider environment are
not mounted or inherited. Direct external networking is unavailable. Executed
probes cover credential/database reads, unauthorized settlement/operator/reviewer
routes, identity changes, budget denial and public inspection of uncertain exposure.
This protects the demonstrated namespace process, not arbitrary same-user processes
launched outside it. Host/kernel compromise and production hostile multitenancy
remain outside the reference guarantee.

Gateway admission bounds active connection threads before financial authorization.
Excess connections receive 503; no application waiting queue grows without limit.
Admitted handlers can wait on the mutation lock, and the kernel has a TCP backlog.
Five-second socket read timeouts bound slow header/body readers. This is bounded
local backpressure, not per-agent fairness or a general Internet DoS defence.

V3 adds an authenticated per-agent concurrent-request cap (four by default) before
body processing and financial authorization. Excess authenticated work returns 429
without a reservation. Independent cheap execution and read routes no longer wait
for the global market/operator mutation lock. SQLite still arbitrates dispatch and
settlement; semantic workflows retain task-local locks and durable pending-action
checks. The earlier V2.1 paragraph describes its historical admission behavior.
Raw connections are capped before authentication, so an unauthenticated socket
flood can still deny service: identity-based fairness cannot precede identity.

Structured NIM requests bind a restricted closed schema into the immutable quote
and request fingerprint. Independent post-response validation does not transform
schema compliance into semantic correctness. Known provider usage survives bad
output or unexpected model labels. The semantic tool adapter checks agent/task
context at the trusted primitive, and optional consultation never grants mandatory
approval. Workflow completion/evaluation writes are atomic; a stale concurrent
duplicate cannot downgrade a completed result. Frozen live quality evidence remains
negative despite these enforcement guarantees.
