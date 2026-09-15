# Architecture and assurance boundary

Status: architectural contract implemented in the local 0.1.0 reference; see ADR 0002 and the build report for evidence and limits.

## Components

The spending kernel, economy, workload, and evaluation harness are separate modules in one application. A gateway adapts agent requests to these modules. A dashboard reads the same persisted records and cannot invent authority. Provider SDKs and framework integrations belong at the edge.

The kernel now implements aggregate parent scopes and a reservation lifecycle. A separate market journal conserves funded internal credits. HTTP authorization, simulation and dashboard projections share persisted state without giving agents accounting authority.

## Two economies, distinct units

External-resource accounting records the unit and liability contract supplied by the trusted adapter. Both the deterministic adapter and current live NIM adapter use modeled operating cost in `SIM_COST_MICRO`, not invoices or a hard dollar bound. NIM records observed provider tokens separately from declared zero prototype cash. The offline billing vocabulary does not establish a commercial billing guarantee. Local inference cost modeling is an allocation model, not a claim that hardware is free.

Internal markets use `MARKET_CREDIT`. Initial endowments and task rewards must come from a named, funded treasury. Transfers and escrow are balanced: each debit has an equal credit in the same unit. Credits do not replenish modeled/real operating budgets. Issuance changes are explicit experimental interventions, not a hidden reward source.

A market payment is not an external API cost. Avoid double-counting it as an additional resource consumption metric. Track task value in declared synthetic utility units unless a justified monetary mapping exists.

## Budget scopes

The target hierarchy is run/tenant -> workflow -> agent, with task caps where useful. A parent cap aggregates descendant spend and commitments. Do not add parent rollups to child charges when reporting total economic expenditure: these are views of the same charge, not additional charges.

Check and reserve every applicable cap in a single storage transaction. Parent limits cannot be evaded with multiple accounts, workers, delegated identities, parallel auctions, or retries. Creating a child requires authorized parent scope and does not fund it. Simultaneous market escrow and resource authorization need explicit rollback/compensation semantics; no allocation may authorize unfunded execution.

## Reservation and execution state

```text
RESERVED -> DISPATCHED -> SETTLED
    |             |
    v             v
RELEASED       UNRESOLVED -> SETTLED
                  |
                  v
         RELEASED only with trusted no-charge evidence
```

`DISPATCHED` is persisted before attempting the external effect. A crash in that gap is deliberately conservative: an uncertain request does not become free. A retry that may incur another bill needs its own attempt and reservation. Bind idempotency to principal, operation, resource, immutable request parameters, quote version, and attempt identity.

`mark_dispatched` is a single-winner claim, not an idempotent permission to repeat the provider call. This does not promise exactly-once external execution or billing. A provider-specific adapter must declare reconciliation and retry semantics.

Reservations can expire before dispatch. Dispatch-in-progress liabilities cannot be released just because a local lease or HTTP timeout expired. Fail closed on unavailable authoritative state. Document the resulting availability trade-off.

## Truthful bound breaches

For valid bounds, trusted mediation, correct storage, and no out-of-band liabilities:

`settled spend + outstanding upper-bound liabilities <= funded budget`

An estimate or percentile is not a hard bound. A strict live mode must reject a resource that cannot supply a defensible cap on all billable components. If a trusted adapter discovers actual cost above a declared cap, record the full charge, freeze the affected scopes, retain unresolved exposure, and emit a bound-breach incident. Do not overwrite the prior quote or claim the guarantee survived.

The reference library records such a breach and freezes the account. It can report negative headroom while the accounting remains internally consistent. This is an intentional distinction between accounting integrity and solvency.

## Authorization and oversight

An admin provisions identities, budgets, and policy. An agent can request resources, inspect permitted balances, and submit bids; it cannot mint funds, edit policy, settle itself, or approve its own action. A reviewer can approve a particular immutable action within a defined scope and expiry. A trusted adapter reconciles usage. The browser is not one of these authorities merely because it has a button.

Mandatory authorization cannot be purchased, traded, or downgraded when review capacity is exhausted. Optional consultation can be a scarce allocatable resource, but it does not grant authorization. A demo reviewer simulator must be labeled simulated.

## Persistence and reproducibility

Use transactional economic records and durable events. Observability may be derived from these records; sampled traces cannot serve as the only financial record. For the first deployment, local SQLite is sufficient if writer serialization, migrations, restart tests, and documented limits are present. Do not claim distributed consistency.

Separate logical simulation time and semantic randomness from wall-clock telemetry. A recorded execution, a deterministic rerun, and a changed-policy counterfactual are separate artifacts. Checkpoint economy state, policy state, outstanding liabilities, logical event queue, and entropy version. Replaying only balances is not enough.

## Explicit exclusions

No public multitenancy, payment execution, customer data, arbitrary user code, adversarial same-process isolation, market credit creation without funding, provider-guarantee claims without an adapter, or general claims about real financial markets. Hashing a local event file is not tamper-proof logging against the host administrator.
## V2 extension: one execution boundary

The authoritative task check lives in `ControlPlane`, including unknown-task denial.
Per-resource adapter lookup preserves the simulated default and adds opt-in NIM.
`live.py` owns the trusted observation registry and independent exact evaluator;
`nim.py` owns approved-origin transport, versioned modeled quotes and reported usage.
The narrow chat endpoint authenticates agent metadata and never forwards provider keys.
Persisted receipts settle on restart without provider access; lost receipts remain
unresolved. Provider snapshots read request/hold/event/outcome state in one transaction.
`study.py` is a separate pure research model, not a parallel production execution path.
See [ADR 0003](adr/0003-evidence-not-infrastructure.md) for scope and assumptions.
