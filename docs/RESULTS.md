# Results at a glance

AECP tests economic authority separately from agent quality. Correct accounting
does not imply useful work. A valid model schema does not imply a correct answer.

## Frozen V2.1: the model did not earn its cost

The 12-case held-out narrative study compared three independently running,
namespace-isolated consumers through governed NIM execution:

| Policy | Verified /12 | Modeled cost | Live calls |
| --- | --- | --- | --- |
| Rules plus modeled reviewer | 6 | 1292 | 0 |
| Always LLM | 0 | 3261 | 10 |
| Selective | 4 | 1766 | 5 |

All 15 hosted responses were schema-valid. The model nevertheless made poor
evidence/action choices. Selective successes came from deterministic logic; no
incremental model value was demonstrated. These outcomes remain unchanged.
See [the frozen study](reports/EVIDENCE_STUDY_002.md).

## V3: a new worker, not a retuned old test

A new 36-case held-out corpus was committed before worker tuning. The model now
interprets visible payment/document relationships; deterministic code enumerates
valid actions, performs arithmetic, budgets purchases and bounds replanning.
Five policies distinguish rules, inference and simulated reviewer use.

The final policy/source contract was committed at `ebd42a9` before one live run
using `nvidia/nemotron-3.5-lightning-30b-a3b`. Each policy received the same 36 cases,
12000 modeled units and, where permitted, six simulated reviewer slots.

| Policy | Verified /36 | Settled modeled cost | Outstanding upper bounds | NIM attempts | Reviews |
| --- | --- | --- | --- | --- | --- |
| Rules only | 6 | 216 | 0 | 0 | 0 |
| Rules + reviewer | 12 | 3840 | 0 | 0 | 6 |
| Always LLM | 9 | 6439 | 3491 | 18 | 0 |
| Selective LLM | 11 | 5071 | 1405 | 12 | 0 |
| Selective + reviewer | 15 | 6471 | 708 | 6 | 6 |

**Useful semantic work was demonstrated, not universal economic superiority.**
Selective inference adds five verified cases and 10805 synthetic value beyond rules
alone, at 4855 additional settled units plus 1405 outstanding. With the same six
reviewer slots, selective+reviewer adds three cases and 5841 value beyond rules+reviewer.
Rules remain cheapest per verified value; simulated review remains more economical
than inference-only. Selective inference improves quality and cost relative to always
inference in this run. These are tradeoffs, not measured cash savings.

The study made 36 chat attempts: 28 responses and eight timeouts. Known usage is
18434 input / 4262 output tokens; timeout usage is unknown. All 5604 unresolved
modeled units remain reserved. There were no incorrect confident finalizations, but
five/two/one cases remained unfinished in always/selective/selective+reviewer because
of uncertain execution. Those cases stay in the denominator. Twenty-five responses
were schema-valid; schema validity alone did not establish a successful resolution.

Nine missing-evidence cases and nine mandatory-review cases per policy were correctly
abstained/escalated, not counted as verified resolutions. Reviewer answers are modeled,
not supplied by humans. One sequential live replication cannot separate provider-time
variation from policy effects or establish statistical significance. Full artifacts,
frozen identities and limitations are in [report 003](reports/BUILD_REPORT_003.md).

## Information is valuable, but not free

V3's reviewed deterministic study runs 20 paired seeds across 18 cells and 11
policies: **3960 policy trials**, not 3960 independent environments. Public resource
tariffs differ by agent/resource. Centralized planners can buy selected private
reports, receive known noisy reports, or face a fixed overstatement intervention.
A matched rotating-request control shares the market's resource-request/fallback
policy without ranking, payments or bidding fees.

Representative cell means: budget180, 90% signal quality, 90% provider reliability.
Values are synthetic verified utility, not dollars.

| Report cost per agent | Paced public | Forced honest sharing | Selective report buying | Rotating requests | Private market |
| --- | --- | --- | --- | --- | --- |
| 0 | 1169.20 | 1329.85 | 1329.85 | 923.45 | 970.95 |
| 2 | 1169.20 | 1144.00 | 1193.75 | 923.45 | 970.95 |
| 6 | 1169.20 | 857.05 | 1169.00 | 923.45 | 970.95 |

Selective-report central wins or ties 12 of 18 cell means; the private market wins
none. The market can improve on rotating premium requests without beating stronger
central allocation. This is an **auction-package** contrast, not proof that prices
alone caused the gain. Expensive forced reporting is not the strongest central
baseline: the selective buyer can decline information using an ex-ante value model.

The oracle is an exact relaxed offline DP with identical tariffs/capacities but
omniscient outcomes and no reporting/bidding fees. It is not deployable. Reporting
overstatement is a fixed intervention, not a game-theoretic equilibrium. The study
is a pure economic model, not a claim of API execution/settlement for every trial.

## Measured gateway improvement

Same host, same 50 ms fake provider, four admitted connections, independently
scheduled arrivals over 15 seconds at each load. At 80 offered requests/second:

| Measurement | Before | After |
| --- | --- | --- |
| Completions /1200 | 203 | 588 |
| Explicit overload rejections | 997 | 612 |
| Completion rate per arrival second | 13.53 | 39.20 |
| Successful p50 / p95 / p99 ms | 297.22 / 307.39 / 309.30 | 93.76 / 120.62 / 149.03 |

Every drained phase has a consistent within-funding audit. There are zero transport
errors or generator drops; recovery completes 75/75 arrivals. Requests rejected
before authorization create no reservation. This is a local reference measurement,
not a production SLO or a distributed benchmark.

With an authenticated cap of two requests per agent, three steady agents completed
225/225 combined requests while a noisy agent offered 1200. All 75 dashboard reads
succeeded. Raw pre-authentication socket flooding remains outside the fairness claim.

## Reproduce without a key

```bash
make check
make property
make demo
make isolation
PYTHONPATH=src python3 scripts/semantic_validate.py --workload v3 --output var/v3-development.json
PYTHONPATH=src python3 scripts/reporting_study.py --seeds 20 --output var/v3-reporting.json
PYTHONPATH=src python3 scripts/overload_validate.py --seconds 15 --output var/v3-overload.json
PYTHONPATH=src python3 scripts/fairness_validate.py --seconds 15 --output var/v3-fairness.json
```

Use fresh artifact paths. Archived [V3 machine-readable evidence](reports/evidence-v3/OFFLINE_MANIFEST.json)
is recorded evidence, not fresh replication. Provider tokens in live records are
observations; operating cost is modeled; prototype cash is declared zero, not an
invoice. No external-human adoption, commercial billing bound or production use is claimed.
