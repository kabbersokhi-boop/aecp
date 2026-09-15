# ADR 0003: Evidence without a second control plane

Status: accepted for V2 review.

V1 remains the deterministic reference. V2 adds a per-resource adapter lookup, not a
second accounting kernel. Unknown task policy is rejected inside `ControlPlane`,
including callers that never use HTTP. The existing SQLite dispatch claim and
trusted receipt recovery also govern NIM. Missing usage or lost receipts retain
liability; malformed output with valid usage still costs resources.

The hosted NIM adapter is explicit opt-in. It admits only a configured, empirically
probed model at the approved NVIDIA HTTPS origin. Redirects and ambient HTTP proxies
are disabled. Each adapter invocation makes exactly one HTTP attempt. Provider
credentials remain in the server environment. No tools, streaming, arbitrary URLs,
agent-reported usage, or provider-side automatic retries are supported.

`SIM_COST_MICRO` is retained for schema compatibility but live receipts explicitly
say `live_provider_modeled_cost`. This is a request-byte/output-token allocation,
not cash pricing. Free prototype cash spend is declared zero, not inferred from an
invoice. A change to commercial billing requires a different, defensible adapter
contract, not changing a label in the UI.

The bounded private-information study is a separate pure experiment, not a claim
that its allocations were executed through the V1 ledger. Public, private-signal,
and evaluator data types and corpus hashes are separated. Mandatory review access
is assigned by a public rotating rule before any allocation; no bid buys eligibility.
The offline dynamic program is an exact optimizer of a *relaxed* full-information
problem: no bidding tax and no planning cost for entirely empty rounds. This is an
upper bound, not a deployable or equal-information baseline. Unshaded bids are
value-based heuristics, not incentive-compatible truth telling or equilibrium play.

The reference HTTP server and five-second dashboard polling are retained. Provider
requests do not hold the global simulation mutation lock. SQLite transactions,
not the browser or model, remain authoritative. Closed-loop local load tests measure
the implementation's limits; they do not establish a production service SLO.
