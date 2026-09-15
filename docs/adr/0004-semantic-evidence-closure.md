# ADR 0004: focused V2.1 closure (in progress)

V2 baseline: `8131eba`, clean worktree, private PR #2 open, all remote checks green.
Reverified locally: 116 deterministic tests in 15.765 seconds, state machine in
4.755 seconds, Ruff pass. Historical V2 artifacts remain immutable.

## Decisions

1. Semantic work will link permitted narrative evidence to payment records; Python
   will still do arithmetic. Development and held-out corpora will have separate
   identities, with a committed held-out manifest before final prompt/policy tuning.
   Invalidating an evaluation requires a documented implementation/evaluator defect,
   not an unfavorable answer. No live tuning on held-out failures.
2. Structured output will accept a bounded, closed JSON-schema subset, quote its byte
   allocation, bind its identity to authorization, and independently validate output.
   Known usage survives schema or provider-model anomalies. A single funded hosted
   probe will establish observed compatibility before any held-out execution.
3. Keep the original economic study evidence. Add paced public/shared central and a
   private-information no-auction control with matched fallback behavior. Distinguish
   never executed from executed incorrectly. Do not interpret information gains as
   evidence that auction prices caused them.
4. Implement bounded admission before expensive work, then measure sustained offered
   arrivals independently of completions. Instrument transaction acquisition rather
   than attributing every latency tail to SQLite by assumption.
5. Use Linux namespaces rather than a second distributed service. Bubblewrap executes
   successfully on this host. An isolated consumer will have no host home/database,
   provider environment, host process namespace or external network. A fixed-target
   Unix socket relay will expose only the existing governed HTTP service. The consumer
   remains a separate project using public HTTP contracts. Human validation remains
   an explicitly external dependency.

The closure is not complete at this checkpoint. The full user-requested workload,
economic controls, isolation, overload experiments and evidence amendments remain
required before PR #2 can be declared merge-ready. No self-merge is authorized.
