# Experiment and mechanism contract

## Grounded workload

`finops.v1` generates 36 invoices by default, with matched, duplicate, underpaid or overpaid bank payment records. Partial local ledgers can omit the decisive evidence. Policies see invoice/visible payments, counterparty, evidence availability, utility, arrival, deadline and mandatory-action flag. They never receive bank ground truth, the seed, evaluator labels or future faults.

Cheap execution processes the local ledger. Premium and optional consultation can retrieve bank evidence. The separate evaluator scores a structured resolution. Paid verification reports correctness after execution; it does not repair the answer. Premium outcomes can remain ambiguous during outages; consultation can return degraded local evidence. All potential evidence is keyed to semantic task coordinates.

## Modeled operating cost

| Activity | SIM_COST_MICRO |
| --- | ---: |
| Planning, including per-candidate orchestration | 1 |
| Bid submission | 2 |
| Cheap execution | 4 |
| Premium execution | 14 |
| Optional consultation | 24 |
| Verification | 2 |
| Simulated mandatory review | 3 |

Every activity passes through the spending kernel. Verification is reserved before execution. Failed bids still pay incurred planning/bidding expenses. Uncertainty retains the full cap, and retries add independent liabilities. Internal auction payments are not counted again as operating costs.

Capacity per tick: two premium slots, one optional consultation slot, two protected mandatory reviews. Review exhaustion blocks mandatory operations. The auction sells **premium only**, never mandatory permission. Consultation is capacity-limited outside this auction. Logical clocks are isolated per run; gateway wall-clock sweeps cannot expire simulation liabilities.

## Policies and baselines

Conservative agents process complete evidence cheaply and abandon incomplete cases. Value-seeking agents choose premium evidence when valuable and affordable. Adaptive agents maximize estimated utility minus resource cost using Beta-Bernoulli quality posteriors by resource/document class and separate delivery-availability posteriors. Absent responses inform availability, not hidden correctness.

Declared synthetic priors: complete/premium evidence Beta(9,1), partial cheap evidence Beta(1,3), delivery Beta(9,1). Tests show that both verified feedback and unavailable-provider feedback change subsequent decisions. These are interpretable assumptions, not calibrated real-model accuracies.

All benchmark allocators use the same adaptive population, seeded tasks, partial observations, costs and capacities:

* Equal rotates first access among agents each tick.
* Priority orders deadlines, then task value.
* Evcost orders estimated value per planned resource cost.
* Central solves a multiple-choice knapsack over currently visible task/resource alternatives, funded headroom and scarce capacities. It can override proposals using the same observable beliefs. It is a receding-horizon allocator, not a privileged offline oracle.
* Market clears funded private bids. Losers may wait and pay for planning again. Only the market pays bidding cost.

`--style mixed` is a distinct population experiment. Planning's modeled unit includes scheduling, but exact knapsack CPU runtime is not dynamically priced; this is a benchmark limitation.

## One specified auction

One integer bid requests one premium slot and requires an active owned premium operating hold. The entire bid is escrowed in MARKET_CREDIT. One hold cannot back multiple bids. At clearing, descending price wins up to capacity; lexicographic bid ID resolves ties. Agent-selectable IDs can manipulate exact ties: the rule is deterministic, not strategy-proof.

Winners retain escrow until delivered execution settles, then pay **their own bids**. There is no uniform clearing price. Losers, pre-clearing cancellations, expired unclaimed capacity and confirmed pre-dispatch failure refund credits and release unused operating holds. Expiry bounds dispatch time, not the right to erase an incurred or uncertain charge. Unresolved execution retains operating exposure and winner escrow. Trusted no-charge reconciliation is required before an uncertain failed-delivery refund. Generic transfers cannot drain escrow wallets.

Each run issues 3,000 credits to a named treasury and transfers 700 to each of three agents. The remaining 900 stay in treasury. No task rewards are paid in v1. The journal supports finite balanced transfers without creating operating authority; auditing reconstructs every wallet from issuance and movements.

## Reporting and reproduction

Artifacts retain config, seed, corpus hash, environment/policy/entropy versions, code revision, canonical economic digest, outcomes, cost categories, funding audit and credit conservation. Detailed per-run artifacts include all requests, holds, approvals, decisions and events. Append-oriented task-outcome events preserve prior decisions even when the current trace projection changes.

Utility's denominator includes every generated task. Metrics include coverage, failures, abandonment, unresolved exposure, deadline non-service, conditional completion latency, terminal-decision latency, quality/oversight/coordination costs, premium utilization, and separate Jain indices for task access, premium access and verified outcomes. Ratios/statistics may use floating point; accounting does not.

For completed runs `deadline_misses` counts every case not correctly verified by deadline, including unresolved/abandoned work. It is null until completion. Fast refusal cannot masquerade as fast successful completion.

The benchmark retains all per-seed rows plus grouped means/sample SD and paired differences versus central. These small synthetic samples support description, not significance or real-market generalization. Markets can lose without changing the workload or denominator.

Deterministic reproduction recomputes a new run; recorded replay reads captured output; restart resumes the same experiment without automatically replaying ambiguous effects. V2 adds opt-in fresh NIM execution; it is not deterministic reproduction.

## V2 evidence study

`python -m aecp allocation-study --seeds 30` runs a separately versioned, bounded
pure allocation model: 27 budget/signal/bidding-cost cells, seven allocator labels,
paired seeds, and four bid perturbations. It does not replay the V1 execution ledger.
Public cases exclude private signals and evaluator truth. Central-shared and
market-public are information ablations; comparing only private-market with
public-central confounds mechanism and information. Mandatory review eligibility is
publicly rotated before bids. No participant buys a policy exemption.

The exact offline DP knows future delivery and hidden bank records. It is a relaxed
upper bound: it avoids bidding and empty-round planning costs. Ratios to this bound
are headroom estimates, not regret against a deployable equal-information policy.
The unshaded bid is incremental premium-versus-cheap expected value, not an
incentive-compatible truthful strategy. No equilibrium or collusion result is claimed.

Machine-readable evidence, sensitivity tables, unsuccessful live outputs, corpus
hashes and threats to validity are documented in [EVIDENCE_STUDY_002](reports/EVIDENCE_STUDY_002.md).
