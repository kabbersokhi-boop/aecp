# Build report 001 — deterministic economic control plane

Date: 2026-09-08. Maturity: working local research/reference release, not a production financial service.

## 1. Executive summary

The original 47-test spending-ledger foundation now supports a complete offline financial-operations economy, governed resource execution, funded first-price allocation, interpretable adaptive policies, meaningful scheduling alternatives, durable recovery and a live financial debugger. No paid inference or external provider execution occurred.

The release has **91 passing automated tests**, successful package and JavaScript checks, independent SDK subprocess demonstrations, real desktop/mobile Chromium validation, and **75 paired deterministic benchmark trials**. The market loses to centralized allocation at every tested budget on mean verified utility. This is an observed result, not a defect concealed by benchmark design.

Material improvements beyond the initial skeleton include exact cumulative accounting beyond SQLite's signed-integer range, scoped logical expiry, process-kill recovery inside unfinished ticks, independent delivery/quality beliefs, immutable adapter quotes and trusted usage receipts, a genuinely competing tick-local knapsack allocator, and browser-safe rendering of large integers. A final adversarial review found and fixed a rejected-bid reservation leak before handoff.

## 2. Git and review status

* Repository: **PRIVATE**, [kabbersokhi-boop/agent-economic-control-plane](https://github.com/kabbersokhi-boop/agent-economic-control-plane).
* Base/main foundation: `f6fb0ff`; implementation branch: `build/deterministic-economy-v1`.
* Main implementation: `031658e4d0b699091a145b12448a27349fd826c1`.
* Reviewed accounting/gateway checkpoint: `3f43161644e75e079996a33a72451cf59106c5a6`.
* Final fee-expiry recovery fix and evidence-regeneration script: `c1460aa85979eccc15a6ae9f6ac0d3764800903b` (91 tests). This only changes gateway fee expiry, not the simulator or benchmark outcomes.
* Review: [PR #1](https://github.com/kabbersokhi-boop/agent-economic-control-plane/pull/1), opened against main; not merged. Foundation and implementation branch were pushed without force.
* This report and captured artifacts are subsequent evidence changes; they do not change the implementation. Their containing commit is discoverable with `git log -1 -- docs/reports/BUILD_REPORT_001.md`, avoiding a self-referential report hash.
* [Remote implementation CI run](https://github.com/kabbersokhi-boop/agent-economic-control-plane/actions/runs/34203162647): five successful jobs, Python 3.11/3.12/3.13/3.14 and Chromium/browser integration, at `3f43161`. GitHub initially displayed the inherited workflow name “foundation”; job contents are the expanded control-plane checks, not merely the original tests.
* [Final implementation CI run](https://github.com/kabbersokhi-boop/agent-economic-control-plane/actions/runs/34203910301) also completed successfully at `c1460aa`, including the 91-test recovery fix. Confirmed with `gh run watch 34203910301 --exit-status --interval 15`. Report-only commits do not change those tested sources.

## 3. Architecture actually implemented

One Python application, file-backed SQLite, static same-origin browser assets and loopback HTTP. No runtime third-party Python dependencies, hosted database or frontend runtime CDN.

| Module | Actual responsibility |
| --- | --- |
| `src/aecp/ledger.py` | Transactional hierarchy, reservations, lifecycle, settlement, migrations, reconciliation audit |
| `src/aecp/control.py` | Trusted task registry, immutable requests/quotes, exact approval, dispatch, adapter receipts |
| `src/aecp/market.py` | Finite credit issuance, balanced transfers, escrow, capacity clearing and delivery payment |
| `src/aecp/workload.py` | Partial invoice observations, hidden bank evidence and independent correctness evaluator |
| `src/aecp/policies.py` | Three decision policies and explicit availability/quality beliefs |
| `src/aecp/engine.py` | Persisted experiments, scheduler alternatives, durable tick phases, metrics and snapshots |
| `src/aecp/experiments.py` | Paired trials, sample dispersion and quantitative stress evidence |
| `src/aecp/server.py`, `client.py` | Role-separated native gateway and small Python SDK |
| `src/aecp/static/` | Backend-backed financial debugger and provenance inspector |

Requests flow through identity → trusted task policy → immutable quote → budget reservation → exact approval/capacity → atomic dispatch → receipt or unresolved liability → settlement → task verification. Agents cannot report settlement truth. SQLite stores requests, holds, approvals, receipts, market state, run checkpoints, task projections and append-oriented events.

## 4. End-to-end capabilities

`make demo` creates ordinary and outage experiments. `make showcase` persists all five allocators for comparison. `make serve` opens the debugger at `http://127.0.0.1:8765`; use the locally generated operator capability from the ignored, mode-0600 file `var/local-capabilities.json`. Never give that entire file to an agent.

The browser can create an experiment, step it, finish it, inspect tasks and expenditures, inspect agent authority/beliefs, see credit allocation and approval state, and compare persisted results. Reopening a completed run is labeled recorded replay. Two independent example agent processes make governed HTTP requests without SQLite access.

## 5. Important decisions

See `docs/adr/0002-deterministic-release.md` for implementation rationale. SQLite is the transaction boundary; POSIX advisory locking serializes whole simulation phases while SQLite independently protects spending races. No distributed infrastructure was added.

There are three non-convertible quantities: modeled operating units, internal credits and verified task utility. Synthetic invoice cents are also not spendable authority. Local hardware cost is an optional integer allocation model, not a claim of free inference or an actual cash invoice.

Policies are transparent deterministic functions, not LLM role-play. One homogeneous premium auction is specified thoroughly rather than adding shallow mechanisms. The centralized baseline solves an exact *current-tick* allocation problem with comparable observations; it is deliberately not labeled a future-aware oracle.

## 6. Accounting invariants and trust assumptions

For every active scope, under valid adapter upper bounds:

```text
settled descendant spend + outstanding descendant upper bounds <= funded cap
```

Hierarchy rollups describe the same charges, so adding parent and child totals would double count. Admission atomically checks all ancestors. Creating a child provides a narrower cap, never additional root funding. Winding-down and suspended ancestors prevent new execution; settlement of existing exposure remains possible.

Money-like inputs reject floats, booleans, negatives and values beyond the per-operation bound. Cumulative actual breaches use exact high/low integer representation rather than allowing SQLite to coerce totals to floating point. Browser JSON uses decimal strings for integers beyond JavaScript's exact range.

Only pre-dispatch reservations may expire or cancel. Dispatched/unknown charges retain their full possible liability across restart. A retry creates another possible charge with independent authority. Duplicate settlement is idempotent only for matching actual usage. Result and receipt persistence is atomic; recovery settles a persisted receipt without reexecution. If a provider exceeds its bound, the system records the **full** breach and freezes affected ancestry; it cannot retroactively guarantee an invariant the provider violated.

Trust assumptions: complete mediation, trustworthy database/filesystem and adapter receipts, exclusive custody of real provider credentials if a future adapter is installed, and defensible quotes. The system does not prove expenditure usefulness, model correctness, arbitrary provider idempotency or hostile-host isolation.

## 7. Deterministic economy

Versioned `finops.v1` generates 36 coherent invoice cases per default run with counterparties, visible payment evidence, hidden full bank records, deadlines, values and four latent outcomes: matched, duplicate, underpaid and overpaid. Policies receive an `Observation`, not a `Case`, seed, hidden label or future shock schedule. Stable semantic seed/task coordinates prevent allocation order from changing hidden randomness.

Cheap processing resolves visible complete evidence; premium/optional consultation can acquire stronger records. Verification has an explicit charge and scores a proposed resolution independently. Outages can produce ambiguous dispatches rather than free failures. Scarce capacity, review collapse, deadlines and tight budgets change achievable utility.

Manifests retain seed, configuration, environment/policy identity, corpus hash, code revision, timestamps, interventions and checkpoints. Canonical economic digests omit wall-clock/run-identity differences and opaque identity-bound request hashes; they cover economic projections, not a cryptographically tamper-proof entire event log. Same-version deterministic reproduction, persisted replay and hypothetical future live replication are distinct.

## 8. Policies and evidence

* **Conservative:** uses cheap complete evidence; abandons uncertain work rather than consuming premium authority.
* **Value-seeking:** chooses stronger evidence for partial cases when utility and headroom justify it.
* **Adaptive:** selects estimated net utility and updates interpretable Beta-Bernoulli quality and delivery beliefs separately. An unavailable provider is not treated as an observed incorrect answer.

`test_observed_feedback_changes_adaptive_action` and `test_observed_provider_unavailability_changes_resource_choice` show evidence changing the subsequent resource decision. `POLICIES.json` retains final beliefs and results on the same seed-7 ordinary workload:

| Policy | Verified utility / 4329 | Modeled cost | Verified cases | Abandoned |
| --- | ---: | ---: | ---: | ---: |
| Conservative | 2941 | 204 | 26 | 10 |
| Value-seeking | 4307 | 366 | 35 | 1 |
| Adaptive | 4329 | 384 | 36 | 0 |

This single-seed comparison demonstrates different behavior, not general superiority or calibrated real-world probabilities.

## 9. Market mechanism

Premium capacity is sold in unit-quantity, sealed, first-price auctions. A bid identifies owner, auction, unique bid ID, owned premium operating reservation and nonnegative integer credit price. A hold backs at most one bid. All ancestry must remain eligible. Credit price is fully escrowed; operating exposure is independently reserved.

Clearing ranks price descending, then bid ID lexicographically. Winners pay their own bids only on confirmed delivery. Losers, eligible cancellations and expired undelivered pre-dispatch bids receive legitimate credit refunds and release operating holds. Dispatched/ambiguous delivery retains both exposure and escrow. Escrow cannot be drained through generic wallet transfers. Credits originate in a finite treasury; task utility is not minted as rewards.

Native gateway bidding charges 2 modeled operating units once per request in addition to the credit bid. Mandatory authorization is not an auction commodity. Lexicographic tie IDs are deterministic but user-influenceable; this is not a strategy-proof mechanism or Sybil-resistant market.

## 10. Baselines and cost model

`equal` rotates equal access; `priority` orders deadlines/importance; `evcost` schedules expected verified value per estimated cost; `central` solves a multiple-choice knapsack over current observed task/resource alternatives and capacity. The market and baselines use common corpus/seed, budget, resource conditions and adaptive population. No labels or future shocks are supplied to central.

Modeled unit costs: cheap 4, premium 14, optional consultation 24, planning 1, bidding 2, verification 2, mandatory review 3. Actual cash expenditure is zero. Metrics include all these settled charges and retry attempts, with unresolved exposure separately visible. Coordination aggregates planning, bidding, verification and mandatory review; planning/bidding is also reported separately. Host CPU time, database I/O and optimizer complexity are not separately metered; this is a declared resource-cost model, not measured operating expenditure.

Full-workload utility/coverage and final deadline non-service prevent abandonment from looking like perfect efficiency. Latency is conditional on completion and separately accompanied by terminal decision latency and unserved counts. Access/verified-outcome Jain indices, premium utilization and review demand expose distribution effects.

## 11. Dashboard validation

Actual Chromium opened the running service, authenticated, created an outage run, stepped and completed it, matched **36 displayed cases** to the API snapshot, inspected an unresolved transaction, exercised four views, refreshed persisted state, and checked a 390px mobile viewport. **Zero console/page errors; no document-level mobile overflow.** Both generated screenshots were opened and visually inspected during this build.

Evidence: `BROWSER.txt`, `screenshots/financial-debugger.png`, `screenshots/financial-debugger-mobile.png`. The captured outage has 450 funded, 368 settled, 28 reserved/unresolved and 54 headroom; unresolved is a subset of reserved, not another debit. Its utility is 4037/4329. System totals also include other persisted root scopes and therefore intentionally differ from selected-run cards.

The expenditure register opens task-associated quote/accounting history. The task inspector links observations, decision, exact approvals/allocation, attempts, settlement or uncertainty, verification and durable events. UI projections come from persisted backend state; no mock arrays are substituted. Global totals are root-only to avoid hierarchical double counting.

## 12. Integration paths

`make integration` launches `examples/passive_agent.py` and `examples/economic_native_agent.py` as separate processes with distinct capabilities. Observed results: **passive SETTLED; economic-native BID → ALLOCATED → SETTLED**. The harness, not either agent, holds operator authority to open/clear capacity. `INTEGRATION.txt` records the result.

The native SDK handles typed HTTP failures without automatic unbounded retries. Registered tasks have immutable operation requirements. Approvals bind request ID, parameters, operation, resource, policy and quote and expire. Optional consultation is distinct from protected mandatory oversight. The adapter protocol has typed quotes/receipts and supports lower actual usage and bound-breach accounting. Only the deterministic adapter actually executes; the integer local cost calculator does not run a model. No OpenAI-compatible route or live commercial adapter is claimed.

## 13. Failure and recovery evidence

`STRESS.json` reports 40 simultaneous requests of 7 units across 8 descendants under a 100-unit root: **14 admitted, 26 denied, 98 reserved, 182 unfunded exposure prevented**. Restart retained 7 uncertain units; timeout refund was rejected. Repeated retry pressure retained 97 units, five malformed requests were denied, suspended spawning was denied, hoarding expired and credit conservation passed.

Seed-7 market/adaptive scenario results (`SCENARIOS.json`), all with consistent ledger and funding audits:

| Scenario | Utility / 4329 | Settled cost | Unresolved | Abandoned | Lost utility |
| --- | ---: | ---: | ---: | ---: | ---: |
| ordinary | 4329 | 384 | 0 | 0 | 0 |
| tight (cap 180) | 2085 | 180 | 0 | 18 | 2244 |
| burst | 4329 | 396 | 0 | 0 | 0 |
| outage | 4037 | 368 | 28 | 0 | 292 |
| review-collapse | 3843 | 348 | 0 | 4 | 486 |
| throttling | 4329 | 393 | 0 | 0 | 0 |
| retry-pressure | 3752 | 336 | 112 | 2 | 577 |

Outage unserved cases remain unresolved, not abandoned. Retry-pressure settled plus unresolved is 448, below its 450 authority. Throttling increases coordination cost without losing final utility in this seed; this is not described as a catastrophic outage.

Tests kill actual child processes after dispatch and inside prepare/market clearing/execution/trace/checkpoint phases, then restore persisted identity, plans and liabilities. Separate-process resume matches uninterrupted economic digests. A dispatched request without a durable receipt is not executed twice after restart. A receipt saved before a crash is reconciled once.

## 14. Exact verification and observed results

All commands are from the repository root unless stated otherwise. Local runtime: Python 3.14.6; isolated installed-wheel runtime: Python 3.12.13; Node 22.22.1; Ruff 0.16.6; Playwright 1.62.1. Runtime dependency installation is not needed for `make demo`/`make serve`.

| Command actually executed | Result/evidence |
| --- | --- |
| `make check` | compileall, **91 tests in 12.950s**, Ruff all checks passed; `VERIFICATION.txt` |
| `npm run check` | browser JavaScript and smoke-script syntax passed; `VERIFICATION.txt` |
| `uv build` | wheel and sdist built, including browser assets; `VERIFICATION.txt` |
| `make demo` | ordinary and outage persisted; inspected actual metrics, not only exit status |
| `make showcase` | five common-seed persisted allocator runs available to comparison view |
| `PYTHONPATH=src python3 -m aecp serve` | actual loopback service used for all browser/client checks |
| `make integration` | both independent example paths settled; `INTEGRATION.txt` |
| `make browser` | actual Chromium, four views, 36 cases, unresolved trace, refresh and mobile assertions; `BROWSER.txt` |
| `PYTHONPATH=src python3 -m aecp benchmark --output docs/reports/benchmarks` | 75 trials; every funding, ledger and credit-conservation audit passed |
| `uv run --locked ruff check scripts/release_evidence.py` | passed |
| `PYTHONPATH=src python3 scripts/release_evidence.py` | seven scenarios, three policies, stress and complete sample provenance regenerated at `3f43161` |
| `uv venv /tmp/aecp-release-wheel --python 3.12` | fresh isolated environment created |
| `uv pip install --python /tmp/aecp-release-wheel/bin/python --no-deps dist/agent_economic_control_plane-0.1.0-py3-none-any.whl` | installed one package, no runtime dependencies |
| `cd /tmp && env -u PYTHONPATH /tmp/aecp-release-wheel/bin/python -m aecp demo --db /tmp/aecp-release-wheel/demo.sqlite3 --artifact /tmp/aecp-release-wheel/result.json` | 36 verified, utility 4329, cost 384, healthy audit, outside checkout |
| `git diff --check` | passed |
| `gh repo view kabbersokhi-boop/agent-economic-control-plane --json isPrivate,url,defaultBranchRef` | private visibility verified before push |
| `gh run view 34203162647 --json jobs --jq '.jobs[] \| {name,conclusion}'` | all five remote jobs successful |

Installed-wheel `importlib.resources` assertions also confirmed `index.html`, `app.js`, `style.css`, `favicon.svg` are present. Bootstrap safety is covered by seven tests in `tests/test_bootstrap.py`, including refusal of public/unrelated targets and preservation of unrelated uncommitted work; real private creation/push/PR additionally succeeded.

No standalone type checker is configured; none is claimed. Static assets need no bundler: wheel packaging and real browser execution are their build/validation path. Sandbox-restricted socket/network checks initially failed and were rerun with approved access. One intermediate Ruff line-length failure was fixed; the final checks above passed. A stale service caused one address-in-use start failure; the owned process was stopped, restarted and revalidated. No unresolved external blocker remains.

## 15. Acceptance A01–A16

PASS means the stated local/reference capability was observed, not production certification. Optional extensions remain explicitly unavailable.

| ID | Status | Concrete evidence |
| --- | --- | --- |
| A01 | PASS | Fresh isolated wheel demo; `make demo`, actual `make serve`/Chromium; no provider keys or runtime external services |
| A02 | PASS | `SAMPLE_TRACE.json`; `test_dashboard_serves_real_backend_trace`; browser task/expenditure inspector and funded premium case |
| A03 | PASS | `test_processes_share_transactional_admission`, `test_randomized_lifecycle_sequences_preserve_invariants`, `test_process_crash_after_dispatch_keeps_liability_without_reexecution` |
| A04 | PASS | `test_siblings_race_one_parent_cap`, `test_descendant_cannot_mint_and_units_cannot_cross`; stress 98/100 aggregate reservation |
| A05 | PASS | `test_first_price_ties_and_conservation`, `test_escrow_cannot_be_reused_across_auctions`, `test_ambiguous_delivery_retains_escrow_after_expiry`, cancellation/hoarding tests |
| A06 | PASS | `test_agent_cannot_fund_settle_approve_admin_or_read_evaluator_state`, owner-isolation and wrong-credential tests; no agent settlement route |
| A07 | PASS | `test_exact_approval_cannot_authorize_changed_or_retried_operation`, `test_approval_absence_and_self_approval_cannot_be_bought`, operation-downgrade test |
| A08 | PASS | Three-policy `POLICIES.json`; both adaptive evidence-change tests; `test_hidden_truth_is_absent_from_observations` |
| A09 | PASS | `test_resume_in_separate_process_matches_uninterrupted`, `test_economic_digest_ignores_run_identity`, `test_process_death_inside_tick_recovers_durable_phases` |
| A10 | PASS | 75 raw paired trials in `benchmarks/benchmark.json`; `test_all_baselines_share_corpus_and_respect_funding`; modeled coordination/retry categories, with unmetered host costs disclosed |
| A11 | PASS | Actual desktop/mobile screenshots and `BROWSER.txt`; real snapshot-backed scopes, market, review, experiment and provenance views |
| A12 | PASS | `make integration`, `INTEGRATION.txt`; independent passive/native processes without DB credentials |
| A13 | PASS | Seven `SCENARIOS.json` results, `STRESS.json`; process-crash/review-collapse tests; lost utility and retained exposure table |
| A14 | PASS | 91 tests, Ruff/compile/JS, wheel/sdist, isolated install, benchmark, local browser and five successful remote CI jobs |
| A15 | PASS | `SECURITY.md`, cost/mode labels, documented trust assumptions and limitations; tracked-secret pattern review, ignored capabilities; zero paid execution |
| A16 | PASS | This report, exact verification records, acceptance matrix, source revisions, private PR and unfavorable benchmark results |

## 16. Benchmark results

Artifact: `benchmarks/benchmark.json`, implementation `3f43161`. Burst demand, seeds 1–5, budgets 180/300/450, all five schedulers, adaptive population: **75 independently executed trials**. All per-trial ledger/authority/conservation checks pass. Raw metrics, corpus hashes, digests, mean/sample SD and paired differences are retained. Five seeds are a bounded demonstration, not a statistical-significance claim.

Cells below are **mean verified utility / mean modeled operating cost**:

| Budget | Market | Equal | Priority/deadline | Expected value/cost | Central |
| --- | ---: | ---: | ---: | ---: | ---: |
| 180 | 1817.4 / 180 | 1889 / 180 | 1901 / 180 | **2151.8 / 180** | 1836.2 / 180 |
| 300 | 2810 / 300 | 2930.6 / 293.4 | 3056.8 / 296 | **3447.6 / 299.2** | 2972 / 300 |
| 450 | 3667.4 / 398.4 | 3721.4 / 380 | **3829.4 / 398.6** | 3708.8 / 365.2 | 3774.2 / 398 |

Market-minus-central mean utility is **−18.8, −162, −106.8** respectively. At budget 300 the market pays mean coordination cost 122 versus central 97.2 and leaves mean 10 cases abandoned versus 8.8; the raw artifact retains other terminal states and full denominators. Extra coordination and decentralized selection can be costly. These experiments do not establish a causal decomposition without further ablations. Central is not always best because exact current-tick optimization is not optimal over future arrivals or imperfect priors.

## 17. Adversarial security/reliability review

The build included independent read-only review plus direct negative tests. Substantive findings were fixed, not deferred:

* Hierarchical cap bypass, sibling execution after ancestor breach and cumulative actual-cost overflow are covered with exact accounting and ancestry tests.
* Reserved execution cannot bypass frozen lifecycle, expired approval, changed quote, resource binding or allocation checks; dispatch claims are atomic.
* Invalid non-premium native bids now fail before reservation. Pending requests expire safely. Failed duplicate bids cannot cancel previously valid authority. Tests check balances/holds, not only an HTTP error.
* Follow-up review found a separate interruption window between bid-fee reservation and dispatch. Fees now inherit auction expiry; `test_interrupted_bid_fee_reservation_expires_after_recovery` reopens storage after that phase boundary and proves both pre-dispatch holds release, restoring all 16 reserved units.
* Result/receipt persistence reconciles actual trusted usage rather than assuming the quote was the invoice. Invalid receipts remain unresolved; provider errors expose only error type, not secret-bearing exception text.
* Independent run clocks no longer expire another run's holds. Process interruptions preserve plans, trace history, approvals, bids and unresolved liabilities.
* Credit escrow is inaccessible to generic transfers; unknown tasks and protected-operation downgrades fail closed. Mandatory approvals cannot be acquired through wealth.
* Policies do not receive hidden truth; baselines share corpora; full-workload metrics prevent selective-abandonment efficiency claims.
* UI root totals avoid double counting, large integers remain exact, and unresolved amounts are explicitly a subset of reserved exposure.

The gateway rejects unauthenticated/foreign-origin/oversized requests and role/owner violations, binds loopback, and does not expose provider URLs, credentials, funding or settlement to agent clients. This is capability-based local access control, not hostile-code process isolation. No claim of tamper-proof audit, public multitenancy or regulatory certification is made.

## 18. Known limitations

* Local POSIX reference service: no distributed worker coordination, production TLS/identity federation/token revocation, hostile-host isolation or Windows locking support.
* All executed resources are synthetic record processors. No live/local LLM, commercial invoice reconciliation or OpenAI drop-in compatibility has been tested. Real adapters require independently defensible charge bounds and reconciliation semantics.
* Synthetic evidence models, values, prices and belief priors are research assumptions. Host CPU/I/O and optimizer effort are not measured cost. Five seeds are insufficient for broad economic conclusions.
* Central allocation is tick-local; no offline oracle or single-agent constrained baseline. Lexicographic ties are strategically influenceable; identities are operator-provisioned, not Sybil-resistant.
* Events are append-oriented application history, not cryptographically tamper-evident storage. Mandatory reviewers are deterministic trusted actors inside simulations; the native reviewer API demonstrates human authority separation without claiming a deployed human operations team.

## 19. Intentionally deferred

OpenAI compatibility and live adapters, additional auction families, distributed infrastructure, formal verification, reward minting, and elaborate model training were not added. They would increase surface area before demonstrating more useful guarantees. The local cost model is implemented honestly without a fake local-model executor. No release tag/package publication/deployment/PR merge was performed.

## 20. Highest-value next actions

1. Add a single optional real adapter with price provenance, bounded output, durable usage reconciliation and mocked contract tests before any paid pilot.
2. Run preregistered sensitivity/ablation studies over costs, priors, credit endowments and tie rules; add an offline synthetic upper bound to characterize allocation regret.
3. Add trusted operator resolution tools for unresolved liabilities with explicit evidence and scoped lifecycle controls in the dashboard.
4. Harden deployment only for a concrete multi-user setting: identity/revocation, TLS, host egress isolation and backup/restore drills.
5. Expand temporal workloads and human-review latency distributions while keeping policy observations separate from evaluator state.
