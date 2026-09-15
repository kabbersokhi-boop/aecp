# Explaining AECP without overstating it

## Thirty seconds

AECP puts a deterministic budget and authorization boundary between autonomous
agents and expensive resources. Agents can request inference, evidence or reviewer
capacity, but cannot create spending authority, self-approve or erase a possibly
billable request after a timeout. A synthetic financial-operations environment
measures whether those purchases produce independently verified work.

## Two-minute architecture

An agent receives one scoped HTTP capability. The server validates its registered
task, operation and immutable resource quote, then atomically reserves capacity
through every applicable budget ancestor. A durable single-winner dispatch claim
precedes execution. A trusted receipt settles actual modeled resource use; missing
receipts leave unresolved exposure. Every potentially billable retry needs separate
authority. SQLite persists this state and the dashboard reads its provenance.

Market credits are a separate conserved internal ledger, not provider money. NIM
tokens are observed usage; its prototype cash cost is declared zero. The modeled
cost number is useful for controlled experiments, not evidence of dollars saved.

V3's worker interprets narrative payment relationships while deterministic code
controls available actions, arithmetic, authority, evidence retrieval and bounded
replanning. Its frozen live comparison verifies 6/12/9/11/15 out of 36 cases for
rules/rules+reviewer/always-model/selective-model/selective+reviewer. Selective
inference adds coverage but does not beat rules on cost per verified value. Eight
timeouts retain 5604 modeled units. This is one synthetic live replication, not
production savings or evidence that models always outperform deterministic code.

## Five-minute demonstration

Run `make demo`, then `make serve`, and follow [the demo](DEMO.md). Inspect a settled
charge and an unresolved one. Explain why expiry cannot release the second. Run
`make isolation` to demonstrate a separate consumer using only public interfaces.
Show the frozen V2.1 negative result, then V3's selective coverage gains alongside
its higher cost per verified value than rules. The final live, development and load
artifacts are described in [report 003](reports/BUILD_REPORT_003.md).

## Strong engineering evidence

- Transactional hierarchy, independent retry liabilities, one-winner dispatch and
  recovery that distinguishes a durable receipt from an unknown remote outcome.
- API-key-free property tests plus real historical NIM execution and process death.
- Executed Linux namespace isolation: no host database, provider key or direct
  external networking in the demonstrated consumer.
- Same-host open-loop measurement identifying gateway serialization rather than
  guessing that SQLite was the bottleneck; bounded authenticated admission.

## Research findings and limitations

V2.1's hosted model produced valid schemas but no incremental verified value.
Its selective worker verified 4/12 versus 6/12 for rules plus modeled consultation.
Paced shared central allocation won 43 cell means and tied two; private market won
none. Those negative results remain frozen and visible.

V3 explores information-sharing cost, heterogeneity and strategic reports. Do not
describe the first-price auction as incentive-compatible, its behavior as an
equilibrium, or the omniscient oracle as deployable. All utility remains synthetic.

There is no production deployment, commercial invoice validation or independent
outside-human integration. The corpus is authored. The host/kernel and trusted
server remain assumptions. A reference workload is not a production SLO.

## Interview questions worth preparing for

**Why not Python alone?** Use Python for arithmetic and explicit references. The
research question is whether language interpretation adds verified value on
ambiguous evidence. V2.1 did not demonstrate it; V3's frozen selective policy adds
five verified cases beyond rules-only, but at higher modeled cost. Do not replace
deterministic arithmetic or claim general finance competence from this small study.

**What if the model hallucinates?** Its interpretation is untrusted. It cannot
authorize a resource or settle a receipt. Independent evaluation can still mark
an authorized answer wrong; budget enforcement does not prove usefulness.

**What if the provider succeeds before a crash?** A persisted receipt permits
settlement without redispatch. With no trusted receipt, retain unresolved exposure.
Do not infer no charge from a timeout.

**Why include a market if central wins?** It is a falsifiable allocation hypothesis,
not a required product architecture. The control plane works with either allocator.

**Can an agent steal the key?** The demonstrated namespace consumer cannot read the
server environment or filesystem and cannot reach the external network. Arbitrary
same-user processes outside that namespace do not inherit this guarantee.

## Resume bullet candidates

Use only accomplishments you can personally explain and reproduce:

- Built a SQLite-backed economic execution control plane with hierarchical integer
  budgets, atomic reservations, durable dispatch and failure-safe liability recovery.
- Evaluated five governed worker policies on a frozen 36-case semantic workload:
  selective inference verified 11 cases versus six for rules, retaining uncertain
  liabilities and reporting higher cost rather than claiming cash savings.
- Measured a local gateway bottleneck and increased saturated completion throughput
  from 13.5 to 39.2 requests/s on the same 50 ms fake-provider workload while retaining
  consistent accounting and bounded overload rejection.
- Tested isolated consumers and authenticated admission fairness: three steady
  agents completed 225/225 requests during an 80-request/s noisy-agent experiment.
- Implemented reproducible synthetic allocator comparisons with strong centralized
  baselines, private-information controls and an offline oracle, preserving negative
  market and historical model findings across 3960 paired policy trials.

These are portfolio claims, not customer adoption, production throughput or guaranteed
financial savings. The owner selected noncommercial source-available licensing;
repository visibility remains private until separately authorized.
