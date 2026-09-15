# Evidence study 002 — information, overhead and failed model outputs

Date: 2026-09-09. Synthetic research reference, not a financial-service evaluation.
Primary executed source: `2b740d8`; subsequent validation/documentation fixes are
identified in [BUILD_REPORT_002](BUILD_REPORT_002.md). Artifacts are under
[`evidence-v2`](evidence-v2/summary.json), gzip-compressed with uncompressed SHA-256
hashes in the manifest. `gzip -dc <artifact.json.gz>` reads them without AECP.

## Questions and hypotheses

1. Can the same trusted execution boundary govern a separate real-model consumer,
   including a process death after external execution?
2. Does private information improve decentralized allocation enough to offset bidding
   overhead? Does that survive comparison with a shared-information central control?
3. How much headroom separates online policies from an offline full-information bound?
4. Where does local SQLite/gateway concurrency increase tail latency?

Expected directions were specified by the V2 brief, not statistical preregistration.
This is descriptive sensitivity analysis, not a significance claim. No unfavorable
trial was dropped because its result contradicted the project thesis.

## Three distinct experiments

**V1 replication:** 75 ledger-backed executions, seeds 1–5, budgets 180/300/450,
burst workload, five allocators. The central planning state now explicitly includes
mandatory-review capacity. All 15 grouped mean utilities exactly match the archived
V1 benchmark. This fix closes a planning inconsistency but does not change those
sampled results. Central beats market at all three budgets; evcost beats central at
180/300, and priority beats central at 450. Central is not universally best.

**V2 information study:** 30 seeds × 27 cells × seven allocator labels = **5,670**
pure-model trials, plus **120** bid-perturbation trials. Each corpus has 18 tasks in
six synchronized rounds and three agents. Cells cross budget 90/180/300, signal
quality 50/75/90%, and bid cost 0/2/6. Premium capacity is one, consultation one,
mandatory capacity two and premium reliability 90%. Those capacities/reliability
are held fixed: this run is not a sweep of every suggested dimension.

**Live integration:** three catalog GETs and **32 chat POST attempts** over discovery,
an initial pilot, a corrected-prompt final workload and four real crash calls total.
This is tiny integration evidence, not a model leaderboard. The final suite has six
LLM-first tasks and six paired hybrid tasks (four deterministic, two NIM), a budget
denial and two crash calls. No automatic HTTP/SDK retries occurred.

## Information and physical constraints

Public cases contain invoice, visible payments, value, round, agent and mandatory
status. A hidden extra bank payment changes the correct resolution in half the
generative cases. Each agent sees a noisy local signal of that unposted payment.
The known symmetric prior and signal quality define interpretable Bayesian expected
success. Premium reveals bank evidence if available; consultation does so reliably.
Cheap resolution uses visible payments. Truth and future delivery are evaluator-only.

Public, evaluator and signal corpus hashes are recorded separately. Changing signal
quality preserves public documents and hidden bank/delivery facts. Central-public
accepts public records only. Central-shared additionally receives the same private
reports as market-private. Market-public supplies the mechanism's no-information
control. This is logical isolation in trusted Python, not a hostile-code sandbox.

Mandatory review eligibility is assigned **before bidding** by public rotating agent
order, applied to every allocator and the oracle. Bids cannot buy a review exemption.
Execution costs are cheap 4, premium 14, consultation 24, verification 2, plus mandatory
review 3 where required. Three planning units are charged each entered round; markets
also pay each admitted bid's configured cost. Funding and conserved internal credits
are separate constraints. Auction eligibility provisionally covers aggregate operating
liabilities; no credit balance is treated as operating funding.

Central solves the current round's multiple-choice knapsack, not future-budget pacing.
Market clears first-price premium bids, then chooses affordable fallback resources.
Public priority, rotating equal and evcost are included, but their results coincide
throughout this sampled grid. They are not three independent empirical findings:
the small batches and cheap-resource preference collapse their behavior. V1's richer
arrival/deadline workload distinguishes them. This limitation is disclosed, not
“fixed” by arbitrary tie changes solely to manufacture different curves.

## Offline oracle

Exact dynamic programming enumerates each round's feasible resource bundles, carries
budget states across all rounds, and knows hidden truth/future delivery. The supported
problem is bounded to 20 rounds and 1,000 modeled budget units. An independent brute
force enumeration verifies a two-round instance in `test_study.py`.

It is a **relaxed upper bound**, not equal-cost deployable performance: no bidding tax,
and no candidate planning cost in all-deferred rounds. All physical review/premium/
consultation constraints and execution/verification charges still apply. Full-grid
results assert no online policy exceeds it. Utility ratios mean per-seed fractions
of this relaxed bound, not regret against a realizable online service.

At signal quality 90%, bid cost 2:

| Budget | Oracle mean | Public central | Shared central | Private market | Market/oracle mean ratio |
|---|---:|---:|---:|---:|---:|
| 90 | 992.9 | 472.3 | 507.2 | 511.4 | 0.508 |
| 180 | 1493.4 | 947.2 | 980.8 | 1013.3 | 0.674 |
| 300 | 1657.0 | 1510.7 | 1542.0 | 1518.3 | 0.918 |

At budget 180, sample SDs are respectively 176.7 (public central), 157.0 (shared
central), and 237.0 (private market). Modest mean differences amid this dispersion
must not be sold as general superiority.

## Sensitivity: when each policy wins

Mean verified utility, 30 paired seeds per cell, 90% signal quality:

| Budget | Bid cost | Public central | Shared central | Public market | Private market | Simple heuristic |
|---|---:|---:|---:|---:|---:|---:|
| 90 | 0 | 472.3 | 507.2 | 539.5 | 565.7 | 535.2 |
| 90 | 2 | 472.3 | 507.2 | 470.1 | 511.4 | 535.2 |
| 90 | 6 | 472.3 | 507.2 | 418.2 | 430.1 | 535.2 |
| 180 | 0 | 947.2 | 980.8 | 1079.6 | 1097.9 | 788.1 |
| 180 | 2 | 947.2 | 980.8 | 929.8 | 1013.3 | 788.1 |
| 180 | 6 | 947.2 | 980.8 | 835.3 | 865.1 | 788.1 |
| 300 | 0 | 1510.7 | 1542.0 | 1168.0 | 1529.7 | 788.1 |
| 300 | 2 | 1510.7 | 1542.0 | 1168.0 | 1518.3 | 788.1 |
| 300 | 6 | 1510.7 | 1542.0 | 1167.3 | 1434.5 | 788.1 |

At 50% signal quality, shared/public central and private/public market coincide as
they should. At budget 300 and bid cost 2, private information raises market mean
utility from 1168.0 to 1518.3; shared central still reaches 1542.0. Information is
valuable, but this does not prove auctions beat direct information sharing.

Market sometimes beats central even without private information, especially with
zero bidding tax at tight budgets. This is partly differing online spending/resource
preferences versus a myopic current-round optimizer, **not** evidence that private
information caused those gains. A future paced central baseline would sharpen this
comparison. A simple heuristic wins the tight-budget, bid-cost-2 cell. High bidding
tax can destroy market gains. All generated task value stays in the denominator.

## Bid perturbations, not equilibrium claims

Only agent zero changes bid behavior; others use unshaded incremental premium-versus-
cheap expected value. Credits start equal at 120 each. There is no terminal utility
for credits or agent-specific reward function, so “truthful,” rational equilibrium,
collusion and incentive compatibility would be misleading labels.

| Perturbation | Verified value mean | Operating cost | Credit revenue | Jain task access |
|---|---:|---:|---:|---:|
| Unshaded | 1013.3 | 178.9 | 263.1 | 0.969 |
| Half bid | 1035.9 | 178.9 | 226.2 | 0.967 |
| Triple bid | 997.3 | 179.0 | 269.9 | 0.970 |
| Hoard first half | 1011.0 | 179.0 | 194.5 | 0.965 |

Budget 180, signal 90%, bid cost 2, 30 seeds each. Overstatement lowers social value
here; shading raises it slightly. These are controlled perturbations, not a proof
about strategic stability or individual welfare. Credit conservation is asserted.

## Live model selection and failed workload

The catalog returned 81 model IDs. Initial tiny lightning and gpt-oss probes failed
the structured-answer test; the preferred llama ID was absent. Three catalog-listed
fallback models returned 404. Disabling lightning thinking through the documented
`chat_template_kwargs` produced **three of three** valid tiny JSON/usage responses.
Selected: **`nvidia/nemotron-3.5-lightning-30b-a3b`** at the approved hosted endpoint.
That establishes compatibility under this configuration, not general reliability.

Sources: [NVIDIA model card](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/build),
[NVIDIA deployment guidance](https://docs.nvidia.com/nemo-platform/latest/documentation/models-and-inference/deploy-models),
[NIM API reference](https://docs.api.nvidia.com/nim/reference/llm-apis), and
[OpenAI chat contract](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).

The initial 12-case pilot scored 2/12 versus visible deterministic logic's 8/12. Its
label semantics were underspecified. The final prompt explicitly defined reconciliation
semantics, but the model added a `sum` field to every answer. The evaluator requires
exactly `{resolution: <enum>}` and rejects extra fields instead of silently cleaning
them to improve the score. Prompt versioning and original outputs are retained.

| Final paired policy | Correct / cases | Verified value / total | Modeled settled cost |
|---|---:|---:|---:|
| LLM first | 0/6 | 0/602 | 512 |
| Hybrid: complete evidence cheap | 4/6 | 487/602 | 182 |
| Visible deterministic comparison | 4/6 | 487/602 | 24 execution-only units |

The deterministic comparison resolves all six permitted observations; the hybrid's
four correct results are its cheap actions. The model cannot recover inaccessible
bank evidence from a prompt. These results provide **no model-quality gain** and show
that valid JSON alone is not schema compliance. Server-side schema-constrained output
and richer permitted documents are worthwhile follow-up, not a reason to loosen the
evaluator or spend quota until a favorable sample appears.

Consumer: separate Python 3.12.13 environment, OpenAI SDK 3.9.0, no AECP imports,
SQLite access or provider credential. It used one agent capability and the narrow
chat endpoint. One-unit authority was denied before dispatch. The control plane uses
Python 3.14.6. This is independent consumer integration, **not external adoption**.

Across the entire run, provider-reported usage totals **3,487 input + 442 output =
3,929 tokens**. There were 32 chat attempts, three catalog requests, three 404 model-
unavailable responses and no automatic retries. Successful transport categories
include structurally invalid model answers; they are not quality successes.

Final ten chat calls reported 1,540 input + 180 output = 1,720 tokens. The dashboard
shows 1,670 because the deliberately lost ledger receipt's 50 tokens remain only in
the diagnostic transport journal. It does not invent request-linked settlement truth.
Final provider round-trip latency: minimum 425.6 ms, median 718.2 ms, maximum 17,059.2 ms.

Cash is **zero, operator-declared free prototype access**, not a provider invoice.
Modeled cost is `ceil(canonical_message_bytes/16) + 2 * output_tokens`. The bound
substitutes authorized output allowance. Input token counts are observations, not a
guaranteed tokenizer estimate. The hard contract is conditional modeled exposure,
not dollars or NVIDIA free-tier quota. Local evaluator CPU is labeled unmetered;
this is not a complete commercial total-cost model.

## Real failures and prompt injection

Both pilot and final suites killed actual workers around real NIM execution:
receipt-persisted exit 73 settles after restart with no adapter; response-lost exit 74
remains UNRESOLVED after expiry. Final unresolved liability is 106 modeled units.
No recovery provider call or double settlement was made. The proof intentionally does
not claim certainty about a response whose ledger receipt was lost.

Timeout, 429, 5xx, missing usage, malformed output, over-bound usage, changed models,
redirects, unknown tasks and prompt-injected actions are tested offline. The injection
test deliberately supplies a complying fake model response; the trusted boundary
still denies protected execution. It is not a live-model refusal experiment.

## Local performance

Nine closed-loop cells, 300 operations each (2,700 total), Python 3.14.6, Linux x86_64,
local temporary SQLite WAL + synchronous FULL. Zero observed operation errors; all
funding/projection audits passed. No warmup, isolated-host guarantee, arrival model or
coordinated-omission correction. Work was measured on a development host alongside
other build activity. This is a characterization, not a production capacity forecast.

| Operation | Workers | Ops/s | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| Reservation | 1 | 2010.6 | 0.77 | 1.23 |
| Reservation | 4 | 2450.4 | 4.05 | 18.82 |
| Reservation | 16 | 2189.0 | 34.09 | 104.87 |
| Governed cheap HTTP | 1 | 120.7 | 11.84 | 14.22 |
| Governed cheap HTTP | 4 | 112.5 | 50.61 | 57.15 |
| Governed cheap HTTP | 16 | 116.9 | 195.74 | 230.47 |
| Mixed agent reads/writes | 1 | 215.7 | 8.52 | 9.53 |
| Mixed agent reads/writes | 4 | 222.0 | 22.79 | 24.96 |
| Mixed agent reads/writes | 16 | 207.2 | 97.06 | 102.55 |

Raw samples, p50, split read/write timings and audits are retained. Provider inference
is absent from these measurements. Live round trips above are separate, not subtracted
to fabricate exact per-live-request AECP overhead. No SQLite busy errors occurred;
writer contention is inferred from tail growth, not instrumented lock-wait attribution.
Native HTTP writes remain serialized, while live inference is outside that mutation
lock. Higher sustained workloads/multihost operation would justify another backend;
these measurements alone do not justify adding distributed infrastructure now.

## Threats to validity and interpretation

Synthetic utility, small public records, synchronized rounds, fixed response behavior,
known signal priors and a relaxed oracle limit generalization. Multiple cells are
correlated by paired seeds; 5,670 rows are not 5,670 independent worlds. No statistical
significance, real financial savings, commercial invoice bound, independent adoption,
production multitenancy or LLM quality improvement is established. Initial discovery
and pilot artifacts identify the main commit with a dirty V2 worktree; they are
historical pilot evidence, not exact source-pinned reproduction. Final study/live/load
artifacts identify committed `2b740d8`.

The defensible result is a governed execution experiment that preserves liabilities
and unfavorable outcomes, separates information advantages from mechanism claims,
and shows measured local limitations. It is stronger evidence, not a claim that the
remaining research questions have been solved.

## V2.1 amendment: pacing and mechanism controls

Historical V2 artifacts and tables above are retained. The amended study is
`information-mechanism-controls.v2.1`; the environment remains
`private-finops-rounds.v2`. Seeds, task values, bank truth and provider draws are
unchanged. This is a policy/control revision, not a market-favoring new generator.

### Causal design

`central-paced-public` and `central-paced-shared` optimize the current feasible
bundle plus a dynamic-programming approximation of remaining-horizon value. They
know the declared arrival/review schedule and use the rounded public value prior
110 for future tasks. They do not read future arrivals' realized values, bank
truth, future private signals or provider outcomes. Shared means current-round
signals are supplied directly. The future-demand model is approximate, not an
oracle; a regression confirms low-value current work can be deferred to preserve
budget. Candidate planning, paid verification and mandatory review costs remain
the same across central policies. Planning is a modeled per-candidate charge, not
a measurement of dynamic-programming CPU expense.

`decentralized-private-no-market` has the market-private local signal and fallback
rule. Agents request funded premium capacity, but a rotating allocator grants slots
without prices, credit requirements or bid tax. This isolates decentralized private
decision-making from the auction *package*. The remaining market contrast includes
ranking, payment/endowment constraints and bidding overhead; it does not identify
a pure price effect. Mandatory-review eligibility and physical capacities are
identical across every deployable policy and the oracle.

`unserved` now means never attempted/deferred, not wrong. `served_incorrect`,
`verified_tasks`, and `deferred` partition the corpus. Denied/unresolved are explicitly
zero in this pure known-outcome research model, not evidence that the execution
kernel never denies work or retains ambiguous exposure. Post-exhaustion cases count
as deferred and remain in the total-value denominator.

### Executed results

Primary grid: 30 paired seeds × 27 budget/information/tax cells × 10 policies =
8,100 policy trials, plus 120 strategic runs. Extension: 20 paired seeds × 18
provider-reliability/mandatory-review/premium-capacity cells × 10 policies = 3,600
trials. Seeds and cells are reused; these are not 11,700 independent worlds.

Mean verified synthetic value at 90% signal quality and **zero bid tax**:

| Budget | Myopic public | Paced public | Paced shared | Private no market | Private market | Relaxed oracle |
|---|---:|---:|---:|---:|---:|---:|
| 90 | 472.3 | 606.0 | 810.1 | 486.1 | 565.7 | 992.9 |
| 180 | 947.2 | 1151.2 | 1316.0 | 1003.1 | 1097.9 | 1493.4 |
| 300 | 1510.7 | 1517.4 | 1568.1 | 1524.4 | 1529.7 | 1657.0 |

At budget 180, increasing bid tax to six lowers private-market value to 865.1;
paced-shared central remains 1316.0 and private-no-market remains 1003.1. At budget
300 with zero tax, the market's increment over rotating private allocation is only
5.3. A private-information advantage over myopic public central was not convincing
evidence of an intrinsically superior market mechanism.

Private market exceeds paced shared central in **zero of 27 primary cell means**
and **zero of 18 extension cell means**. Its mean increment over rotating private
allocation must not be confused with strict central wins: paced shared central
wins all 27 primary cells and 16 extension cells, with **two extension ties**.
The private market's increment over rotating private
allocation ranges from −194.3 to +94.8 in primary cells and −109.5 to +21.25 in
extension cells. Ranking can help relative to rotation, but scarcity, credit
constraints and coordination tax can erase that benefit. This does not prove all
central mechanisms dominate all markets: the shared central policy assumes direct
honest information sharing, and this first-price market is not incentive compatible.

The oracle remains the exact *relaxed* offline round-bundle upper bound: actual
future outcomes, equal physical capacities and paid execution/review, no bidding
tax, no planning charge for empty rounds. Paced shared central at budget 180 reaches
88.1% of its mean value (ratio of means, not mean per-run efficiency).

Negative baseline finding retained: priority/equal/evcost still coincide in this
small fixed-cost environment. Those labels are not three independent successes or
evidence of experimental breadth. The stronger contrasts are information sharing,
pacing, rotating private allocation and auction tax. More heterogeneous workloads
are needed before generalizing scheduling heuristics.

Commands: `python3 -m aecp allocation-study --seeds 30 --output var/evidence-v21/study.json`
with `PYTHONPATH=src`, then `PYTHONPATH=src python3 scripts/analyze_closure_study.py`.
Generated causal summaries include per-cell paired difference dispersion and
win/tie/loss counts, not manufactured significance. Artifacts are under
`var/evidence-v21/`; archived copies accompany the closure evidence. These studies
make no hosted provider calls and establish no commercial savings.

## V2.1 frozen live semantic study — negative result retained

The protocol was committed at `6738ec7` before held-out execution. The 12-case
corpus was frozen at `510fe50`, hash
`1ba8a9d152970ded5cf42fc5a8b883166f83ea6f7eb5638ef04e515c9f4fcdbc`.
Three namespace-isolated consumers received equal 4,000-unit authority and two
600-unit modeled consultations. They used public HTTP interfaces only. The model
received invoice/vendor/treasury narratives and purchasable evidence descriptions,
not evaluator labels. Python performed arithmetic and independent allocation checks.
The strict `semantic_action_v21` schema, prompt and policy were not retuned after
held-out execution. Original V2 0/6 schema and hybrid 4/6 evidence remains unchanged.

| Frozen policy | Verified cases / 12 | Verified value | Modeled spend | NIM calls | Tokens | Consultations |
|---|---:|---:|---:|---:|---:|---:|
| Deterministic-only | 6 | 12040 | 1292 | 0 | 0 | 2 |
| Always-LLM | 0 | 0 | 3261 | 10 | 7167 | 0 |
| Selective | 4 | 8357 | 1766 | 5 | 3860 | 0 |

“Deterministic-only” means no LLM: it includes two purchased *modeled* reviewer
consultations, not two actual human reviews. Four cases were resolved by ordinary
rules in the selective run. Thus the selective model calls did not add verified
task value and were not economically justified here. The no-LLM baseline costs
215.3 modeled units per verified case versus selective's 441.5. All policies retain
the full 26,362-value denominator, including abstained/escalated/unfinished cases.

All 15 live responses passed strict server-side schema validation, but none proposed
finalization. Always-LLM proposed six unavailable-source fetches and two redundant
fetches; selective proposed two unavailable and two redundant fetches, and purchased
one unnecessary vendor-profile document. One always-LLM response extracted the
correct payment IDs but still proposed a nonexistent evidence retrieval. This is
schema compliance without competent action selection. Four always-LLM calls were
made despite existing deterministic links. No response ended for output length.

Every policy appropriately escalated two mandatory-review cases and abstained on
two unrecoverably missing-evidence cases. Always-LLM left six tasks unfinished after
denial; selective left two. Neither earned value for mere abstention/escalation.
No confidently wrong finalization was submitted. All unavailable-source proposals
were denied by deterministic infrastructure; no extra authority or approval was
granted. The model's apparent obedience or disobedience to malicious document text
is not the security control.

Fifteen fresh held-out calls reported 10,051 input + 976 output = 11,027 tokens,
all transport-success responses. Including the earlier strict-schema probe, this
closure pass used 16 chats, zero catalog calls, 10,095 input + 990 output = 11,085
tokens. Actual cash is declared zero for free prototype access, not inferred from
a commercial invoice. All study holds settled; audit is consistent and within
funding. No additional live crash run was necessary; existing receipt-loss and
durable-receipt recovery regressions remain the relevant failure tests.

Command: `AECP_ENABLE_LIVE_NIM=1 PYTHONPATH=src python3 scripts/semantic_validate.py --live
--model nvidia/nemotron-3.5-lightning-30b-a3b --output var/evidence-v21/semantic-heldout.json`
(one shell line). Analysis: `PYTHONPATH=src python3 scripts/analyze_semantic.py
var/evidence-v21/semantic-heldout.json`. Complete actions/quotes/receipts and independent
outcomes remain persisted and archived, not replaced with favourable examples.

**Interpretation:** the richer workload demonstrates governed autonomous decisions,
but not useful model-added autonomy for this tested model/policy. Stronger structured
output fixed syntactic compliance, not semantic action quality. The result does not
support a claim that the LLM earns its resource consumption. A future redesigned
policy must be evaluated on a newly frozen corpus, not this now-inspected holdout.
Small authored templates, a heuristic selective value model, synthetic reviewers,
one model, one replication and fixed policy order limit all quality conclusions.

## V2.1 open-loop overload

The final 60-second test used independent scheduled arrivals, not completion-paced
clients: 15 seconds each at 5, 20, 80 and 5 requests/second. Four connections were
admitted at once; excess arrivals received 503 before authorization/reservation.
Each completed call used the deterministic adapter with an explicit 50 ms delay.
There was no live inference. The source-pinned final run followed completion of
tests; a separate concurrent-test pilot is not used for these latency claims.

| Offered/s | Offered | Completed | Rejected 503 | Success p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|---:|---:|
| 5 | 75 | 75 | 0 | 71.68 | 74.95 | 77.84 |
| 20 | 300 | 234 | 66 | 235.24 | 262.22 | 269.67 |
| 80 | 1200 | 232 | 968 | 259.13 | 272.82 | 279.94 |
| 5 recovery | 75 | 75 | 0 | 65.82 | 91.83 | 105.85 |

Saturation was about 15–16 completions/second under this delayed, serialized path.
It is not a claim about SQLite's maximum throughput. Mutation-lock wait p99 was
204.17 ms; route duration p99 74.62 ms includes the 50 ms fake-provider delay.
SQLite `BEGIN IMMEDIATE` acquisition p99 was 0.106 ms; transaction-plus-close p99
1.197 ms. All four phase audits were consistent and within funding. No retained
reservations, transport errors or generator drops remained after draining.

Latency starts at scheduled arrival, with launch lag retained, avoiding the obvious
closed-loop coordinated-omission error. Generator outstanding work is capped at 512
and any drops are explicit. The gateway has no application waiting queue, but its
bounded admitted handlers wait on the mutation lock and the kernel has a TCP
backlog. Connection admission is not per-tenant fairness or a hostile-network DoS
guarantee. This is a local reference implementation/development host experiment,
not a production SLO or distributed benchmark. Dashboard traffic was not included.
