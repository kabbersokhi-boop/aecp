# Failure-conformance benchmark

This is an AECP project-defined contract, not certification or a claim about every
possible execution history. It asks: **what does a budget guarantee mean when
requests overlap, responses disappear, workers die, and reconciliation is delayed?**

## Run it offline

```bash
make failure-conformance
make cost-of-safety
```

Both targets use simulated `SIM_COST_MICRO` units, standard-library local processes,
Unix sockets, and SQLite. They make no hosted-provider calls. Generated evidence is
written under `var/`; reviewed release evidence is under
`docs/reports/failure-conformance-v1/`.

## Independent provider truth

`src/aecp/failure_conformance.py` starts a separate fake-provider process with its
own SQLite journal. The provider records receipt, actual execution, actual simulated
charge, result identity, response delivery/loss, and whether provider-side
idempotency was enabled. Its journal is not derived from AECP storage.

AECP receives only a delivered receipt. After a lost response it retains uncertainty
until the benchmark explicitly exposes a provider journal row as trusted
reconciliation evidence. Ex-post provider truth is available to the evaluator, not
to admission or execution policy. Correlation identity alone does not imply
provider idempotency: the contract runs both explicit idempotent and non-idempotent
provider modes.

The reusable `GatewayAdapter` protocol requires `attempt()` and `snapshot()`.
AECP, an intentionally unsafe check-then-execute control, and a reject-all control
share that surface. The naive control calibrates the harness; it does not represent
another product. Reject-all demonstrates why zero overspend without useful work is
not operational success.

## Scenarios

The suite covers normal settlement; concurrent children sharing insufficient parent
authority; immutable duplicate identity; changed-parameter conflict; execution with
a dropped response; worker death after provider execution; durable receipt followed
by worker death; independently funded retry; expiry/cancellation of uncertainty;
later charged/no-charge reconciliation; and a deliberate provider quote-bound
breach. The breach passes only when full actual cost is recorded, affected authority
freezes, the incident is visible, and accounting projections remain internally
consistent.

## Metrics

Safety metrics count independently journaled charges, gateway-settled cost,
outstanding upper-bound liability, prematurely released/unaccounted exposure,
duplicate executions, valid-bound funding violations, bound-breach visibility, and
reconciliation consistency. Parent and child projections are never summed as new
cost, and settled reservations are not counted again.

Availability metrics count offered useful work, completed useful work, legitimate
denials/deferrals, unresolved authority, reconciliation delay, recovery duration,
unaffected progress, and authority-time held in `SIM_COST_MICRO-ticks`. Authority-time
is modeled capacity occupancy, not commercial money.

Trust assumptions are trusted AECP storage/processes, complete mediation, and valid
bounds except in the deliberate breach case. Host compromise, malicious same-process
code, and out-of-band provider access remain unsupported.

## Cost-of-safety study

The bounded study pairs identical 12-task workloads and semantically keyed response
losses across five seeds, budgets 16/28, loss frequencies 25%/50%, and three explicit
strategies: retain uncertainty for the observation window, reconcile after one tick,
or reconcile after four ticks. No strategy refunds uncertainty on a timer; the two
reconciliation strategies require provider-owned evidence. The finite scale is
large enough to expose the stated capacity trade-off while keeping every row readily
inspectable. It is not a general reliability estimate.
