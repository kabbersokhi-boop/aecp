# Engineering instructions

## Mission and authority

Build an economic control plane for autonomous agents, with the deterministic economy as its reference application. Optimize for correct, useful, inspectable software, not feature counts or favorable benchmark results.

Work autonomously on ordinary implementation decisions. Read the code, this file, `docs/ARCHITECTURE.md`, and the active build brief. Maintain a compact plan, implement, run tests, inspect failures, improve, and continue through the milestone. Do not stop after a plan, scaffold, one passing test, or one feature. Do not request approval for routine library, layout, or refactoring choices. Record material deviations in an ADR.

Preserve unrelated user work. Never change repository visibility, buy services, use paid inference, publish deployments/packages, disclose secrets, disable sandbox protections, or force-push without explicit owner authorization. Repo creation is authorized only for the private target in `docs/BOOTSTRAP.md`.

## Non-negotiable boundaries

- Deterministic default: no API key, external service, GPU, or outbound external network call at runtime. Loopback gateway traffic is allowed.
- Integer money and credit units. No floating-point balances, hidden conversion, or credit minting.
- Trusted execution owns funding, authorization, reservation, settlement, and mandatory approval. Agent proposals and valuations are untrusted inputs.
- Admission checks all applicable parent scopes atomically once hierarchy is implemented. Child identities cannot increase funded authority.
- Preserve uncertain liabilities across retries and restarts. Internal idempotency is not exactly-once provider billing.
- Record actual bound breaches honestly, freeze affected execution, and retain incident evidence. Never clip invoices or hide broken invariants.
- Mandatory approval is non-tradable. Reviewer identity and action-bound authorization are separate from optional consultation capacity.
- Simulated cost, allocated local cost, and actual billed cost must remain distinguishable in storage, APIs, reports, and UI.
- Policy code gets observations, not hidden answers or outcome seeds. Logical separation in a process is not a hostile-code sandbox.
- The UI is a projection. Do not make demo numbers independent of persisted backend state.

## Implementation discipline

Use a modular application with a small dependency surface. Start from Python and file-backed SQLite; justify any new service or database before adding it. Keep economic rules and safety accounting separate. Stable pure functions belong in the core; HTTP, storage, and rendering belong at boundaries. The current kernel is a reference implementation, not a fixed API that must be preserved at all costs.

Write negative and failure-path tests alongside features. Never weaken a meaningful test to make a broken implementation pass. Add model-based/property tests when they expose real state-space risk. Dependency lockfiles should reflect actual installs, never invented versions or integrity hashes. Verify current package/API documentation before relying on unfamiliar behavior.

Prefer a complete, tested path to a broad set of stubs. Do not introduce Kafka, Redis, Kubernetes, a workflow platform, plugin DSL, blockchain, lending, reinforcement learning, or arbitrary code execution merely for architectural appearance.

## Research and communication

A deterministic policy is not an LLM. A replay is not a fresh replication. A changed policy requires re-execution, not relabeling the old trace. Costs of bidding, planning, retries, verification, and review must be accounted for under documented models. Do not optimize fixtures or select seeds solely to make the market win.

Use professional, direct public-facing language. Distinguish implemented, tested, simulated, and planned. Do not call the system certified, bank-grade, tamper-proof, formally verified, or production-ready without evidence that supports that exact claim.

## Verification and handoff

Foundation commands:

```bash
PYTHONPATH=src python3 -m compileall -q src tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m aecp demo-ledger
```

Update commands when the application evolves. Keep offline checks usable. Run the full relevant test/build/demo suite, inspect the UI in a browser when available, and perform a final code review of accounting, authorization, and experiment fairness. Fix substantive findings in the same run.

Write `docs/reports/BUILD_REPORT_001.md` (or the next numbered report) following `docs/REVIEW_PROTOCOL.md`. Include exact commands, outcomes, source commit, limitations, and acceptance coverage. Never claim a check passed if it was not run. Commit coherent changes. Push a work branch and open a pull request when permissions permit, without merging it. If execution or token limits intervene, preserve a runnable checkpoint and a prioritized continuation record; do not claim completion.
