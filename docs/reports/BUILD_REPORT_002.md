# Build report 002 — evidence-backed reference V2

Date: 2026-09-09. Status: review candidate; not production-ready and not a model-quality success.

**V2.1 closure, 2026-09-10:** engineering/evidence pass completed for review; no claim
of exceptional model usefulness and no merge recommendation without owner review.
The latest audit and results are in the final V2.1 section below. Historical V2
and intermediate checkpoint sections are retained rather than rewritten.

## Executive summary

V1's kernel, simulator, market and loopback debugger remain intact. V2 adds a governed
real NVIDIA adapter, a narrow OpenAI-compatible endpoint, independent SDK-only
consumer processes, real provider crash checkpoints, property-based accounting
sequences, private-information/oracle experiments, and measured local latency.

The strongest results are enforcement and honest failure evidence. The real model
failed strict output validation in the final workload. The hybrid preserved four
correct deterministic outcomes but did not improve on the visible-only deterministic
baseline. Markets help in some synthetic regimes, lose under higher overhead, and
do not generally beat a shared-information central control. These negative findings
are retained in [EVIDENCE_STUDY_002](EVIDENCE_STUDY_002.md).

## Git and review

- Repository: `kabbersokhi-boop/agent-economic-control-plane`; GitHub visibility
  explicitly verified **PRIVATE**. Base main: `7535a4a` (merged V1).
- Branch: `build/exceptional-evidence-v2`; no direct main push or self-merge.
- Implementation/evidence machinery: `2b740d8`, the source revision of the final
  live, deterministic-study and performance artifacts.
- Subsequent fixes cover non-scalar output validation, durable dynamically provisioned
  capabilities, baseline review regression, stripped legacy consumer environments,
  provider card styling and evidence export. Their commit is identifiable through
  `git log --oneline --first-parent main..build/exceptional-evidence-v2`.
- Review/evidence checkpoint: `5173fed`; packaged version **0.2.0**. A clean Python
  3.12 virtual environment installed the built wheel offline and ran the outage demo:
  34/36 verified, 4,037/4,329 synthetic value, 368 settled and 28 unresolved modeled
  units; projection/funding audits passed and the digest matched browser reproduction.
- PR and remote CI status are recorded in the closing review-status section. This
  report's containing commit is discoverable with `git log -1 -- docs/reports/BUILD_REPORT_002.md`.

## What changed from V1, and review decisions

| Review input | Decision and actual implementation |
|---|---|
| Unknown task permitted by primitive | Accepted: authoritative `validate_task` in prepare and pre-dispatch execution; HTTP callers reuse it |
| Stronger invariant evidence | Accepted: Hypothesis state machine with mirrored durable holds/projections and lifecycle/restart actions |
| Real model and proxy | Accepted narrowly: NIM chat only, configured model, bounded messages/output, no tools or streaming |
| Real provider failure | Accepted: actual subprocess deaths before/after trusted receipt persistence; no speculative refunds |
| Mandatory-review planning fairness | Accepted: central DP gains mandatory dimension; existing 75-run conclusions unchanged |
| Private signals and oracle | Accepted as separately versioned pure research model, explicitly not V1 ledger replay |
| Truthful strategic bidders | Modified: unshaded value bids and controlled perturbations; no payoff model means no truthfulness/equilibrium claim |
| Offline attainable oracle | Qualified: exact relaxed bound, excluding bidding and empty-round planning tax, not deployable equal-cost performance |
| More HTTP infrastructure / SSE | Rejected: keep loopback server and five-second polling; remove live inference from global mutation lock |
| Large live study | Rejected: 32 total chat attempts including discovery/failure evidence; retain poor outputs rather than retrying for a positive result |

Fresh adversarial review also fixed malformed choices hiding known over-bound usage,
ambient proxy credential redirection, inconsistent multi-transaction provider snapshots,
and an experimental auction that indirectly let bids influence mandatory-review
eligibility. Review eligibility now rotates before all allocators, including the oracle.

## Implemented boundary and assumptions

`ControlPlane` owns identity/task policy, immutable quote/fingerprint, reservation,
durable dispatch, receipt and settlement. Model text owns none of these. The same
hierarchical integer kernel governs simulated and NIM modeled cost. Child caps share
ancestor funding; market credits remain a separate unit. A potentially billable retry
needs a new hold; duplicate IDs return existing state without another provider call.

`NimTransport` admits only the approved NVIDIA HTTPS origin/path, disables redirects
and ambient proxies, performs one attempt and stores safe request-count/usage/error
classifications. It reads the credential only in trusted infrastructure. No provider
key, HTTP error body or reasoning field is persisted. Quote details bind model,
adapter version, request-byte size, output allowance, formula and cost-model version.

The guarantee is **conditional modeled-resource exposure**, not a dollar bound:
`ceil(canonical_message_bytes/16) + 2 * authorized_max_output_tokens`. Settlement uses
provider-reported completion tokens. Tokens and latency are observations; modeled
allocation is an assumption. Free prototype cash spend is declared zero, not an
invoice. Missing usage retains uncertainty. Valid usage on malformed answers settles.
Usage exceeding the quote is recorded honestly and freezes affected authority.

Trust assumptions remain complete mediation, trusted operator/execution/filesystem,
SQLite durability, and valid adapter bounds. The server is loopback-only, not hosted
multitenancy; the UI is non-authoritative; local models have a cost model but no
inference runtime. No bank payments, paid deployment or commercial invoice settlement.

## Property and regression evidence

`tests/property/test_ledger_machine.py` runs 35 derandomized examples with up to 60
steps each, including hierarchy/delegation, reservations, concurrent pressure,
dispatch, uncertainty, retry, cancellation, settlement/breach, duplicate attempts,
trusted no-charge reconciliation, expiry, statuses and reopen. Independent modeled
holds are compared with account projections continuously. This is bounded randomized
testing, not formal proof or exhaustive schedule exploration.

Key regressions: unknown task/wrong operation at the primitive; no model switch after
quote; no user settlement/approval authority; injected complying model still denied;
no usage loss for malformed choices; no refund on timeout/429/5xx; saved receipt
recovers without provider; invalid output schema earns no value; mandatory capacity
planned before execution; new HTTP identities persist without new root funding.

## NVIDIA discovery, workload and integration

Selected **`nvidia/nemotron-3.5-lightning-30b-a3b`**, present in the live 81-ID catalog
and successful on three repeated tiny JSON/usage probes after documented thinking
disablement. Preferred llama was absent; catalog-listed fallback models returned
404. Compatibility is configuration-specific, not a blanket reliability claim.

Across this run: **32 chat POSTs + 3 catalog GETs**. Provider-reported totals: **3,487
input, 442 output, 3,929 total tokens**. Three model-unavailable HTTP results; no
automatic retries. Transport successes include semantically invalid model answers.
Diagnostic dispatch/return journal and discovery artifacts are committed without keys.

The final source-pinned suite makes eight consumer NIM calls plus two real crash calls.
An SDK-only OpenAI 3.9.0 consumer runs in a clean Python 3.12.13 environment from `/tmp`,
without AECP imports, provider key or operator capability; it neither receives a
database path nor accesses SQLite. This is not OS filesystem isolation between hostile
processes running as the same user. The server
is Python 3.14.6. Authentication supplies agent identity; task/idempotency headers bind
the operation. A one-unit agent gets HTTP 409 before provider execution.

Six LLM-first cases: **0/6 verified**, 512 modeled units. Six paired hybrid cases:
**4/6 verified**, 487/602 value, 182 modeled units. Visible deterministic logic also
gets 4/6 at 24 execution-only units. The model added a prohibited `sum` field despite
the exact schema prompt. Evaluation rejects rather than silently repairs it. Hidden
bank evidence was never sent to the model. The initial pilot's 2/12 result is retained,
with its underspecified prompt and dirty-worktree provenance disclosed.

The small `/v1/chat/completions` surface is verified with the actual OpenAI SDK and
offline HTTP regression. Unsupported features fail closed. It is **independent
consumer integration, not external adoption**. The protected operation class is not
supported by chat; native request-bound approval remains available. Integration
instructions and the external challenge do not require reading implementation source.

## Real crash, persistence and injection evidence

The final suite kills a worker after a real response has become a durable receipt
(exit 73); reopened execution settles it without any adapter configured. It also kills
a worker after real provider return but before receipt persistence (exit 74); restart
and expiry preserve **106 unresolved modeled units**, without redispatch.

Final provider journal usage totals 1,720 tokens; persisted request-linked dashboard
usage is 1,670. The missing 50 tokens belong to the deliberately lost receipt, retained
only in diagnostic transport evidence. That journal is not silently promoted into
settlement authority. The default adapter's timeout, 429 and 5xx paths are injected
offline; NVIDIA's service was not abused to cause failures.

Prompt-injection regression deliberately makes a fake model emit approval/task-changing
instructions. The next unauthorized call is denied independently of model refusal.
No live adversarial-refusal score or arbitrary hostile-code isolation is claimed.

## Economic and performance evidence

- V1: 75 regenerated ledger-backed trials exactly preserve all grouped utility means.
  Central beats market at all budgets, but evcost/priority can beat central.
- V2: **5,670** paired pure-model trials over 27 cells; **120** bid perturbations.
  Public/evaluator/signal hashes, costs, access, unserved cases and conserved credits
  are recorded. Mandatory review eligibility cannot be purchased.
- At budget 180, 90% signal and bid cost 2, mean private-market utility **1013.3** versus
  public-central **947.2**, shared-central **980.8**, relaxed oracle **1493.4**. Mean
  private-market/oracle ratio is **0.674**. At budget 300 shared-central wins; at bid
  cost 6 public-central beats private-market. Dispersion and confounds are disclosed.
- The three simple heuristics collapse to identical outcomes in this small V2 grid;
  they are not three independent empirical findings. V1 distinguishes their behavior.
- Load: **2,700 operations, zero observed errors**, all audits pass. One worker:
  reservations **2010.6/s**, p99 **1.23 ms**; governed cheap HTTP **120.7/s**, p99
  **14.22 ms**. Sixteen workers: HTTP **116.9/s**, p99 **230.47 ms**. This exposes
  contention rather than implying linear scale. Closed-loop, no warmup or production SLO.
- Final live provider round-trip median **718.2 ms**, maximum **17,059.2 ms**. Local
  control measurements and provider latency are separate; exact per-call subtraction
  is not claimed. Developer-host contention and sample limitations are documented.

## Dashboard and demo evidence

The existing debugger remains; the provider view adds modeled quote, provider/model,
real tokens, zero cash, receipt/state, permitted observations and independent outcome
with request-linked events. Provider snapshots use one transaction. Polling refreshes
without blocking on an in-flight model call. The live SQLite database is local and
ignored, not substituted with mock dashboard arrays.

Chromium opened the running backend, checked ten persisted real-provider requests,
one unresolved liability, 1,670 tokens and $0 cash, exercised the inspector, reloaded,
and checked mobile overflow. Screenshots were actually captured and visually reviewed;
a missing provider-card style was fixed and recaptured. The original browser regression
also passed with 36 outage cases, 28 unresolved units, four views and no console errors.
`docs/DEMO.md` was rehearsed through live preparation, recovery, provider browser,
standalone agents and study inspection; it was not stopwatch-certified at five minutes.

## Verification commands and outcomes

Executed from repository root; temporary environment secret values are deliberately omitted.

```bash
make check
make property
npm run check
uv build
PYTHONPATH=src python3 -m aecp allocation-study --seeds 30 --output var/evidence-v2/study-final.json
PYTHONPATH=src python3 -m aecp performance --operations 300 --output var/evidence-v2/performance-final.json
PYTHONPATH=src python3 -m aecp benchmark --seeds 1 2 3 4 5 --budgets 180 300 450 --output var/benchmark-v2
PYTHONPATH=src python3 -m aecp stress
AECP_ENABLE_LIVE_NIM=1 AECP_NIM_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b PYTHONPATH=src python3 scripts/live_validate.py --db var/live-v2-final.sqlite3 --output var/evidence-v2/live-final.json --consumer-python /tmp/aecp-v2-consumer/bin/python
PYTHONPATH=src python3 -m aecp serve --db var/live-v2-final.sqlite3 --tokens var/live-v2-final.capabilities.json --port 8766
PYTHONPATH=src python3 scripts/integration_smoke.py --url http://127.0.0.1:8766 --tokens var/live-v2-final.capabilities.json
node scripts/provider_browser.cjs
AECP_URL=http://127.0.0.1:8766 AECP_TOKENS=var/live-v2-final.capabilities.json AECP_SCREENSHOT_DIR=var/browser-v2 npm run test:browser
python3 scripts/export_evidence_v2.py
python3 scripts/secret_audit.py
git diff --check
```

Discovery used `aecp.nim.discover` with default preferences and a bounded fallback
candidate tuple; exact candidates/catalog/probe outcomes are in the three discovery
artifacts. Initial JSON failures and 404s were not retried indefinitely. Final execution
used the selected catalog model with thinking disabled in the trusted adapter.

Local results: **116 unit/integration tests pass**, the separate state machine passes,
Ruff passes, JavaScript syntax checks pass, wheel/sdist build succeeds, both standalone
agents settle, full browser and provider browser pass. Baseline was 91 passing tests.
No type checker is configured; no claim of a type-check run. First socket-restricted
test attempt failed, then passed with approved loopback access. Isolated build initially
could not resolve PyPI, then succeeded with approved network access. An early performance
harness underfunded its 300 requests; it was corrected and the final zero-error run
replaces that invalid load setup. Test/format failures during development were fixed.

CI keeps live execution absent, uses API-key-free fake adapters, adds property and
small-study checks, and pins checkout/setup-python/setup-node to immutable upstream
SHAs with version comments. Live validation without explicit opt-in fails before calls.
This was also executed under `python3 -O`: it exited with the opt-in error and created
no database, so the guard does not depend on assertions being enabled.

## V2 acceptance A–Q

| Item | Status | Concrete evidence |
|---|---|---|
| A real independent LLM consumer governed | PASS | Clean SDK subprocesses, `live-final.json.gz`; quality failure explicitly retained |
| B no provider/settlement authority in agent | PASS | Whitelisted child environment; HTTP negative-role tests; consumer key-presence false |
| C usage auditable | PASS | Receipt/quote/provider usage and journal; 3,929 total reported tokens |
| D real failure preserves liability | PASS | Actual exits 73/74; no-adapter settlement versus 106 unresolved units |
| E stronger state-machine evidence | PASS | 35 examples × up to 60 steps; mirrored projections and lifecycle transitions |
| F trusted unknown task fails closed | PASS | `test_unknown_task_and_wrong_operation_fail_at_trusted_primitive` and HTTP regression |
| G OpenAI-compatible path | PASS | Actual OpenAI 3.9.0 consumer plus offline chat HTTP test; bounded subset only |
| H offline oracle | PASS, qualified | Exact relaxed DP, exhaustive two-round comparison; not deployable attainable-cost claim |
| I meaningful private-information regime | PASS | Public/private/truth types, separate corpus hashes and leakage/quality tests |
| J conditional allocation findings | PASS | 27-cell paired table and both information ablations; unfavorable outcomes retained |
| K comparable hard constraints | PASS | Public pre-auction mandatory eligibility; all policies/oracle constrained; V1 DP regression |
| L tail-latency evidence | PASS | Nine cells, 2,700 operations, raw p50/p95/p99, zero-error audits |
| M real provider debugger | PASS | Persisted NIM DB, Chromium inspector, tokens/cash, actual screenshots |
| N injection cannot grant authority | PASS | Complying fake model followed by denied protected action; not refusal-dependent |
| O key-free CI | PASS | Fake transport tests, opt-in guard, and successful remote Python/browser jobs |
| P no leaked credential found | PASS within scan scope | Exact runtime key and token-shaped scan of worktree, DB/artifacts and git blobs, including gzip |
| Q honest cost/utility claims | PASS | Explicit modeled formula, zero declared cash/no invoice, negative strict-schema scores |

## Security review, limitations and next actions

The secret audit checks exact runtime key bytes without displaying them, token-shaped
values, generated SQLite/log/evidence files and tracked history (including decompressed
gzip evidence). A separate filename-only search reviewed credential/header references;
those are environment accesses and authentication code, not exposed credentials. No
provider secret match was found. Capability files remain ignored and local mode 0600.
The user's temporary key should still be rotated after testing as planned.

Important remaining limits: poor structured model compliance; no actual third-party
adoption; no commercial billing bound; no hostile multitenant sandbox; no sustained
production load/SLO; simple synthetic observations; non-equilibrium bids; myopic central
allocation; relaxed oracle; coincident simple baselines in the bounded V2 grid. Current
source persists newly created capabilities; the earlier live capture predates that
fixture correction and proves worker recovery, not gateway reauthentication by those
two newly created consumers. A dedicated offline regression covers durable provisioning.

Ranked next actions (maximum five):

1. Add provider-supported strict structured output and richer permitted documents;
   rerun a preregistered bounded quality test without relaxing the evaluator.
2. Add a paced central policy and heterogeneous arrivals to isolate mechanism gains
   from myopic spending and separate the coincident simple heuristics.
3. Have an outside engineer complete `EXTERNAL_VALIDATION.md`; record actual friction.
4. Measure open-loop sustained load and instrument SQLite lock wait on an isolated host
   before choosing a different persistence/backend design.
5. Specify a commercial provider invoice/upper-bound contract before claiming a hard
   cash budget or enabling paid execution.

## Closing review status

Review-ready as a local evidence-backed reference, not on the basis of a positive
model-quality result. [Private PR #2](https://github.com/kabbersokhi-boop/agent-economic-control-plane/pull/2)
is open against main and **not merged**. The branch was pushed without force.

[Implementation CI run 34281976327](https://github.com/kabbersokhi-boop/agent-economic-control-plane/actions/runs/34281976327)
completed successfully at `5173fed`: Python 3.11, 3.12, 3.13, 3.14 and Chromium/browser
jobs, all API-key-free. Confirmed with `gh run watch 34281976327 --exit-status --interval 20`
and `gh run view`. This closing report update changes documentation only. The final
report commit can be found with `git log -1 -- docs/reports/BUILD_REPORT_002.md`.
Main remains the V1 merge `7535a4a`; no V2 self-merge was performed.

## V2.1 closure amendment — in progress

This amendment preserves all original V2 findings above. PR #2 is not yet declared
merge-ready under the stricter closure brief and must not be self-merged.

Reverified `8131eba`: 116 tests (15.765 s), original property machine (4.755 s), Ruff,
and successful remote CI. `3d8842a` adds a closed structured-output schema contract,
schema-bound authorization/quote provenance, exact/unreported/unexpected model-label
provenance, and scope-aware property assertions. Updated NIM tests: 17 passed; full
suite after that checkpoint: 119 passed (14.790 s). Refined property machine passed
(6.268 s); unrelated scopes continue to enforce funding after another subtree breaches.

One additional funded live compatibility probe on
`nvidia/nemotron-3.5-lightning-30b-a3b` accepted strict `response_format.json_schema`.
The prompt requested an extra field, but the returned object obeyed the closed schema.
Independent validation passed. Usage: 44 input + 14 output = 58 tokens, modeled cost
50, declared free-prototype cash 0; no catalog call or retry. This is one compatibility
observation, not a semantic-quality result. The artifact is
`evidence-v21/structured-probe.json`. Historical V2 live calls were not repeated.

The new `semantic-finops.v2.1` corpus has 12 development and 12 held-out cases with
opaque payment/task IDs and permuted display/arrival order. It contains PO-linked split
payments, returned/replacement instructions, purchasable remittance attachments,
conflicting documents, unavailable evidence and malicious email instructions. Equal
payment sums can correspond to different allocations, so arithmetic cannot establish
link correctness. Python remains responsible for arithmetic. Separate public and full
corpus manifests are frozen in `evidence-v21/` before policy implementation/tuning.
No held-out live evaluation has begun at this checkpoint. Template-authored synthetic
cases are not a claim of fully blinded external benchmark construction.

Linux namespace availability was executed successfully using Bubblewrap; this is
only an environment prerequisite, not yet the completed isolated consumer proof.
Required remaining closure work includes the autonomous loop and held-out study,
matched private-no-market/paced-central controls, bounded open-loop overload,
clean-wheel isolated public-interface consumer, cost contract, dashboard, and final
evidence/CI. The original V2 limitations are not marked solved by this checkpoint.

### Governed semantic worker development checkpoint

The persisted action service now binds evidence tools to the authenticated agent
and task in the control-plane primitive, charges planning and tool use, separates
optional consultation from mandatory authorization, and exposes scoped public
observations/provenance without evaluator labels. Terminal results and evaluation
are written atomically. A regression interrupts evaluation after resource
settlement, reopens the database, and finishes without another charge.

`examples/semantic_consumer/` is an independent standard-library HTTP application
with deterministic-only, always-LLM and selective policies. Development rules
recognize all three currently available allocation templates rather than being
deliberately restricted to amount matching. A separate-process HTTP regression
completed all 12 development tasks: eight verified allocations, two mandatory
escalations and two missing-evidence abstentions. No live model was called by this
regression. This is not held-out evidence and not yet namespace isolation.

Executed: `make check` (136 tests, 15.223 seconds, Ruff passed), then additional
consumer response-contract and HTTP regressions; `test_gateway.py` passed all
13 tests in 7.520 seconds. The new live count remains one structured-output probe,
58 provider-reported tokens; no held-out execution has begun. Full verification
will be repeated after the remaining closure work.

### Executed clean-wheel namespace isolation

`scripts/isolation_validate.py` runs the independent consumer under Bubblewrap with
new user/mount/PID/network namespaces, an empty environment and no host home mount.
A bounded eight-connection Unix relay has one fixed loopback destination. The agent
has its own capability only; the provider key and database stay outside its namespace.
This replaces the same-user-process limitation for this demonstrated Linux path,
not for arbitrary agents launched outside the sandbox or a compromised host/kernel.

After `uv build`, the wheel installed without dependencies into a fresh Python 3.12
environment. The server imported AECP from that environment's `site-packages`, not
the repository source path. The namespaced consumer passed 13 explicit checks,
including database/capability unreadability, absent key, blocked external network,
denied privilege changes, budget denial and retained unresolved exposure after
database reopen. All 12 development tasks completed (eight verified, two escalated,
two abstained); accounting audit was consistent and within funding. Consumer runtime
including probes was 0.636 seconds on this host, not an installation-time benchmark.

Evidence: `var/evidence-v21/isolation-wheel.json` and its generated summary; commands
are in `docs/EXTERNAL_VALIDATION.md`. No live call was used. Secret audit checked 402
files/blobs with zero matches. Full worker suite previously passed 138 tests in
16.324 seconds. This clean-room integration remains self-produced; actual outside
human participation is still absent. Held-out quality, causal economics, overload,
dashboard and final CI remain unfinished.

### Executed causal allocation amendment

Commit `d7570f4` adds paced public/shared central allocation and a private rotating
no-market control while preserving the V2 corpus generator and historical artifacts.
It also corrects `unserved` to exclude attempted-but-wrong cases. All 142 tests passed
in 16.119 seconds; Ruff passed. New regressions cover horizon pacing, absence of
future/private leakage, tax-free no-market credit conservation and outcome partitions.

Executed 8,100 primary trials plus 120 strategic trials and 3,600 reliability/scarcity
extension trials. Private market wins against paced shared central in zero of 45
cell means. At budget 180 and 90% signal quality with zero bid tax: myopic public
947.2, paced public 1151.2, paced shared 1316.0, rotating private 1003.1, market private
1097.9, relaxed oracle 1493.4 verified value. These are synthetic utility, not dollars.
The detailed causal interpretation and qualifications are in the V2.1 amendment to
`EVIDENCE_STUDY_002.md`. Market effects are not reduced to private-information gains.
The no-market control removes ranking/prices/endowment constraints/tax together;
it is explicitly not a pure price-only intervention. No live calls were made.

### Frozen held-out live result

The isolated runner and protocol were committed at `6738ec7`. Development fake
execution found and fixed a missing wrapper endpoint attribute before any live
evaluation. The final live run was executed once; no prompt/policy tuning followed.
All 15 NIM responses were schema-valid, but the model repeatedly requested absent
or already-loaded evidence and never proposed finalization. Deterministic-only
resolved 6/12 (two with modeled consultation), always-LLM 0/12, selective 4/12.
Modeled costs were 1292 / 3261 / 1766 respectively. This is negative economic-quality
evidence, not a successful useful-autonomy claim. The full interpretation and exact
commands appear in the live amendment to `EVIDENCE_STUDY_002.md`.

Additional held-out usage: 15 chats, 11,027 tokens. Closure total including the schema
probe: 16 chats, zero catalog calls, 11,085 tokens (10,095 input / 990 output). Model:
`nvidia/nemotron-3.5-lightning-30b-a3b`. All calls reported transport success and
settled; audit remained consistent/within funding. The unavailable-source actions
were denied without granting access, approvals or spending authority. Namespace
isolation kept the provider key/database outside every live consumer.

`billing.py` adds an offline integer/rational provider contract covering versioned
pricing, SKU, currency, units, output and non-token dimensions, unsupported dimensions
and invoice status. Missing dimensions cannot establish a complete bound; observed
breaches are not clipped. A confirmed invoice requires an explicit trusted invoice
amount rather than manufacturing cash from rate-card arithmetic. This is tested
future-adapter vocabulary, **not** a validated commercial adapter or dollar guarantee.
The NIM modeled quote/receipt accounting remains unchanged by this offline contract.

The useful-model improvement acceptance remains unmet by evidence. Do not mark PR #2
merge-ready merely because schema, accounting and isolation work. Overload,
dashboard, complete final checks and remaining documentation still need completion.

### Bounded admission and open-loop development evidence

Commit `3e1bb09` bounds admitted HTTP connections (default 32, configurable 1–128)
before creating handler threads. Saturation returns explicit 503 before any resource
reservation. There is no application waiting queue; admitted handlers can still
wait on the existing mutation lock, and the operating system has a TCP backlog.
Unauthenticated slow connections are also bounded and receive a five-second socket
read timeout. This bounds work, not fairness or production denial-of-service risk.

The first 60-second development experiment offered 5, 20, 80, then 5 requests/second,
15 seconds each, with a fixed 50 ms fake provider and four admitted connections.
It completed/rejected 75/0, 236/64, 224/976, 75/0 respectively. No generator drops,
transport errors or unresolved reservations occurred; all phase audits passed.
This pilot revealed saturation near 15 completed requests/second, reflecting the
serialized gateway execution path rather than a raw SQLite throughput ceiling.
Successful p99 latency rose from 75.25 ms to 341.82 ms under peak offered load and
returned to 78.10 ms. This is local development-host evidence, not a production SLO.

Opt-in bounded diagnostics now measure `BEGIN IMMEDIATE` acquisition separately
from transaction duration, and mutation-lock wait separately from route execution.
The pilot's SQLite acquisition p99 was 0.135 ms with zero recorded transaction
failures; attributing the whole HTTP tail to SQLite would have been incorrect.
A source-pinned run with direct mutation-lock attribution and final verification
is in progress; retain the pilot as pilot evidence rather than relabeling it final.

Final source-pinned run (`3e1bb09`) completed after tests stopped. A preceding run
overlapped tests and is retained separately, not used for final latency claims.
At 5/20/80/5 offered requests per second, final completions were 75/234/232/75 and
503 rejections 0/66/968/0. Successful p99 latencies were 77.84/269.67/279.94/105.85 ms.
All 616 completed requests settled exactly four modeled units; rejected connections
created no reservations. Every phase drained with zero reserved exposure and a
consistent funded audit. No generator drops or transport failures were observed.
Across the run, mutation-lock wait p99 was 204.17 ms, route execution p99 74.62 ms,
SQLite acquisition p99 0.106 ms and transaction-plus-close p99 1.197 ms. The dominant
queue is the bounded admitted-handler wait on serialized execution, not SQLite busy
failure. The fake provider deliberately contributes 50 ms of route time.

`make check` after admission changes: 148 tests passed in 21.847 seconds and Ruff
passed. The final load command was `PYTHONPATH=src python3 scripts/overload_validate.py
--seconds 15` (one line). Raw scheduled-arrival latencies, launch lag, admission
counters, lock timings and audits are in the archived `overload.json.gz` artifact.

### Executed semantic dashboard and documentation

The new Semantic autonomy view reads persisted task/action/receipt data, not a
hand-authored results table. It shows policy authority, verified/all cases, value,
modeled spend/reservations, provider receipt/schema counts, tokens, abstentions and
escalations. A task inspector includes the exact permitted view at each decision,
planning execution, immutable quote, usage receipt, denial and independent outcome.
Current-process admission telemetry is labeled separately from historical overload.

Chromium was opened against the persisted frozen NIM database on port 8767.
`node scripts/semantic_browser.cjs` inspected all 36 cases and 15 real receipts,
expanded the provenance fields, checked cash labeling, reloaded the session and
validated a 390-pixel mobile viewport: zero page errors and no horizontal document
overflow. Desktop screenshot was visually inspected; screenshots are
`screenshots/semantic-v21.png` and `screenshots/semantic-v21-mobile.png` relative to
this report directory. README, DEMO and INTERVIEW_DEFENSE now explain the actual
negative quality result rather than promising a successful live-model showcase.

Latest local checks: 148 tests in 17.958 seconds; Ruff and JavaScript syntax checks
passed; the scope-aware Hypothesis machine passed in 8.441 seconds; source and wheel
build succeeded. Prior pushed CI was green on Python 3.11–3.14 and Chromium. The
new dashboard/admission commits still require their own final remote CI verification.

## V2.1 final acceptance audit — 2026-09-10

### Disposition

The requested engineering experiments and closure deliverables are implemented and
executed. The central empirical question has a **negative answer for this model and
frozen policy**: selective inference did not improve verified work or cost efficiency.
That is a completed experiment, not proof of useful model-added autonomy. We did not
weaken the evaluator or retune after inspecting the holdout. The project is stronger
as a tested control/evaluation system, but this pass does not justify claiming an
exceptional autonomous financial worker or guaranteed recruiting outcomes.

PR #2 remains private and unmerged on `build/exceptional-evidence-v2`. The owner later
authorized merging only if fully confident. I do not recommend automatic merging
under that condition: owner review should explicitly accept the negative quality
result and remaining research limitations. There are no known unfixed accounting
or authorization defects from this pass, but that is not a proof of bug absence.

### Recommendations accepted or modified

- Meaningful language workload, frozen corpus and three scoped worker policies were
  implemented. Provider-supported closed-schema output replaced prompt-only syntax
  enforcement without replacing independent semantic evaluation. Its benefit was
  syntactic only; the unfavorable outcome remains visible.
- Strong central planning uses a public-prior continuation-value DP, not access to
  realized future cases. It improves the baseline without pretending to be an oracle.
- Private-no-market uses matched local information/fallback and rotating capacity.
  Its contrast estimates an auction package, not a pure price treatment. This is a
  deliberately narrower causal claim than “the market adds value.”
- Bubblewrap namespaces and a fixed-destination relay replace same-user-process
  isolation claims. No Docker service or orchestration stack was necessary.
- Bounded connection admission with explicit 503 replaces unbounded thread creation.
  Direct measurements identify mutation-lock serialization rather than blaming SQLite.
- Commercial billing is an offline typed/rational contract, not paid execution or
  a validated dollar guarantee. Existing NIM modeled accounting was not migrated
  merely to change terminology.

### Five upgrade outcomes

| Upgrade | Evidence-backed outcome |
|---|---|
| Useful budget-constrained work | Experiment complete; model benefit NOT DEMONSTRATED. Frozen no-LLM/always/selective: 6/0/4 verified of 12; costs 1292/3261/1766. Semantic work and governed decisions are real, but the model policy failed economically. |
| Stronger baseline and causal controls | Implemented/executed: 8100 primary + 3600 extension policy trials, 120 strategic trials; paced shared central wins 43 cell means and ties two. Private market wins none. |
| Independent integration | Clean-wheel server and separate namespace consumer passed 13 boundary/API probes and completed 12 development tasks. Actual outside-human participation remains absent. |
| Predictable overload | Four 15-second open-loop phases; bounded admission, explicit rejection, no generator loss/transport error, consistent audits and full recovery. |
| Concrete security/billing boundary | Executed mount/PID/network isolation; scoped API authority and unknown-task enforcement; offline non-token billing dimensions and invoice semantics tested. No commercial cash guarantee claimed. |

### Foundation acceptance retained and rechecked

| ID | Result and evidence |
|---|---|
| A01 | PASS: final wheel install, deterministic outage command, offline Chromium and isolated consumer; no provider key required. |
| A02 | PASS: deterministic task-to-decision-to-settlement-to-outcome flow; semantic inspector additionally traces actual NIM decisions and denials. Not a positive LLM-quality assertion. |
| A03 | PASS: ledger unit/recovery tests and scope-aware state machine; stress timeout refund prevention and retained liability. |
| A04 | PASS: concurrent descendants admitted 14/40, reserved 98 under funded 100; 26 denied, no delegated authority minting. |
| A05 | PASS: market unit/stress conservation, escrow expiry and standalone native bid/allocation/settlement. |
| A06 | PASS: unknown-task trusted-boundary regression, HTTP role tests and thirteen isolated consumer probes. |
| A07 | PASS: action-bound approval tests; semantic optional consultation cannot grant mandatory approval. |
| A08 | PASS: existing conservative/value/adaptive policies and evidence-updating regressions retained; distinct semantic buying policies executed. |
| A09 | PASS: separate-process reproducibility and resume tests; frozen corpus identity, typed private/public controls and future-leakage tests. |
| A10 | PASS, modeled-cost qualification: paired workloads and raw results retained; planning/bidding/tool costs included; DP CPU time is not a measured cash expense. |
| A11 | PASS: offline five-view Chromium plus actual persisted NIM semantic inspector, desktop/mobile; current admission telemetry labeled separately. |
| A12 | PASS: standalone passive SETTLED and economic-native BID → ALLOCATED → SETTLED; clean isolated public-interface consumer. |
| A13 | PASS: final outage has 34 verified/36, value 4037/4329, cost 368, unresolved exposure 28; stress/recovery and open-loop evidence retained. |
| A14 | PASS: 149 tests, scope-aware Hypothesis, Ruff, JavaScript checks, source/wheel build, browser suites, benchmarks and remote CI. No type checker is configured. |
| A15 | PASS within audit scope: exact runtime-key/token-pattern scan found no leaks; negative results, synthetic utility and zero declared cash remain explicit. |
| A16 | PASS: this report, EVIDENCE_STUDY_002 and archived artifacts identify commands, source checkpoints, deviations and limitations. |

### Final adversarial finding and verification

Review found a stale duplicate workflow result could overwrite a completed action
after another process had finalized it. `b82601c` adds a durable result guard and
`test_stale_duplicate_cannot_downgrade_a_completed_workflow`: two independent control
plane instances, a deliberately delayed stale response, one settled result retained.
This does not alter any frozen model prompt or evaluation and required no live retry.

After this fix, `make check && make property && uv build` passed: 149 deterministic
tests, Hypothesis state machine, Ruff, source distribution and wheel. An earlier
verification process disappeared during an environment change; it was not counted
as completed and the full command was rerun. `npm run check`, both browser suites,
standalone integrations, deterministic outage and stress commands also passed.
The clean-wheel namespace rerun completed eight verified development cases with
all 13 probes passing and no provider calls. Archived study checks verified bounds,
outcome partitions, holdout hash and overload recovery independently of the prose.

Remote CI for implementation commit `b82601c2d223cfcb5adf2f9ee3f44eeb29527902` passed
all ten checks (push/PR duplicates): Python 3.11–3.14 plus Chromium. Runs:
`34390016270` and `34390009597`. CI remains API-key-free and SHA-pinned. The final
documentation checkpoint is on the same review branch; PR status is authoritative
for checks on that head. Secret audit most recently checked 518 files/blobs, with
the exact runtime key available, and found zero matches. No secret is included here.

### Remaining limitations and at most five next actions

The tested LLM policy has not earned its modeled cost. The corpus is small and
authored, reviewers are simulated, and the live comparison is one fixed-order
replication. Simple scheduling heuristics still collapse in the fixed-cost economy.
Information sharing is assumed honest; auction effects are not price-only causal
identification. Isolation trusts the kernel/server; admission is bounded but not
per-agent fair. There is no genuine outside adoption, commercial invoice validation,
production SLO or hostile multitenant deployment. These are not hidden behind PASS
labels for the engineering controls.

1. Develop a better semantic action policy on development data, then freeze a **new**
   evaluation corpus; never retune the now-inspected holdout until it looks positive.
2. Have an actual outside engineer complete EXTERNAL_VALIDATION and publish their
   consented friction/bug findings, without pretending self-produced integration is adoption.
3. Test heterogeneous costs/arrivals and strategic information reporting to separate
   incentive effects from the current transparent but narrow auction-package comparison.
4. If a real consumer needs concurrent service, measure per-agent fair admission and
   read/write isolation before changing the database or HTTP stack.
5. Validate a commercial adapter's complete billing dimensions only with explicit
   funding/consent; keep modeled resource authority distinct from cash invoices.
