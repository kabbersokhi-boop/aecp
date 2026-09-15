# ADR 0002: local deterministic release

Status: implemented for 0.1.0.

## Decisions

1. Keep local SQLite WAL, FULL synchronous writes and BEGIN IMMEDIATE financial mutations. Immutable parent links aggregate single-copy holds. Migrate legacy flat accounts as roots and add resource-bound holds. Reject unknown future ledger versions.
2. Keep runtime dependencies at zero. Serve plain browser assets from a loopback standard-library HTTP server; ship them in the wheel. Playwright is optional verification tooling. This is a local debugger, not an internet-facing service.
3. Agents receive individual capabilities and trusted registered task IDs. Bind principal, operation, parameters, resource, request identity, policy and configured quote. Validate approval and claim dispatch atomically. Funding, settlement and reconciliation are trusted interfaces only.
4. Use a finite credit journal and one first-price premium auction. Refund unused operating authority with credit escrow. Generic transfers cannot touch escrow. Optional consultation and mandatory review have separate capacity.
5. Persist tick plans before effects and stable attempt IDs. A POSIX advisory lock serializes simulation operators and is released on process death; snapshots take a shared lock. Each run has an isolated logical clock.
6. Keep append-oriented outcome events alongside current projections. Store successful adapter results before settlement. A dispatched request without stored output becomes unresolved rather than running again.
7. Compare against a tick-local multiple-choice knapsack allocator. Include planning, bidding, verification, oversight and resource costs. Never conflate actual cash, modeled costs, internal credits or synthetic utility.

## Deliberate limits

No TypeScript bundler, hosted services, distributed workers or broad compatibility layer are needed for the demonstrated path. Commercial/local model execution is deferred; a typed resource interface and allocated local-compute model establish a future boundary without pretending to have run an LLM.

The workload uses synthetic structured payment evidence, not arbitrary documents or a prompt-injection evaluation. There is no actual payment execution, lending, reward optimization, offline oracle or single-agent benchmark.

Linux/macOS are supported because simulation locking uses POSIX flock. SQLite is not distributed consensus. Same-process code/storage access is trusted. Individual amounts fit signed 64-bit integers; cumulative spend uses a low integer limb plus exact decimal high limb to record breaches beyond that range without float coercion. HTTP serializes integers beyond JavaScript's exact range as decimal strings.

Synthetic results do not price solver CPU time precisely or prove strategic auction properties. Agent-selectable IDs can bias ties. Public identity rotation/revocation, TLS, isolation and rate limiting remain outside this local reference.
