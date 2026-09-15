# Build report 003 — V3 evidence and release review

## Final post-merge status — 2026-09-12

PR #3 merged into `main` at `6cc47a84101bd9c13e2328cae77cd82481254882`.
Local and remote main matched that checkpoint; the repository remained PRIVATE.
[Post-merge main CI](https://github.com/kabbersokhi-boop/agent-economic-control-plane/actions/runs/34655936860)
passed. Earlier draft/unmerged/pending statements below are chronological records,
not current merge status. This hygiene pass requires no additional provider calls,
and all frozen experimental evidence and numerical results remain unchanged.

The historical V3 artifact contains a mislabeled `semantic-hidden-allocation.v2.1`
evaluator field. Grading already loaded each persisted V3 case's own hidden truth;
the metadata defect did not select the V2.1 corpus or affect scores. Future evaluations
derive the identifier from persisted workload identity: legacy cases keep the V2.1
label and V3 frozen-1 cases use `semantic-hidden-allocation.v3.frozen-1`. Regression
tests compare correct/incorrect grades with only the version changed. Archived
results are deliberately not patched or rerun; the offline analysis still recomputes.

The PolyForm Noncommercial 1.0.0 license text and file-based package declaration are
retained. Setuptools deprecates the table form, but it still includes the exact
chosen license; this pass does not invent an SPDX expression or change legal intent
just to suppress a warning. No package is published.

Public release still requires review/approval of the separate sanitized candidate,
not exposure of the original private Git history. Outside-human validation and a
commercial dollar-billing guarantee remain absent. Hygiene verification and the
candidate's source/hash are recorded in the associated small PR.

## Current executive summary

V3 now demonstrates incremental model-assisted semantic coverage under deterministic
authority, rather than merely successful provider calls. A new frozen 36-case live
comparison verifies 6/12/9/11/15 cases for rules/rules+reviewer/always-model/selective/
selective+reviewer. It retains all eight uncertain provider attempts and 5604 modeled
liability units. The model improves coverage, but rules remain cheapest per verified
value and simulated reviewers remain strong alternatives. No dollar savings, real
human review, production deployment or external-human adoption is claimed.

The research contribution is stronger controls, not a market victory: among 3960
paired policy trials, selective report-buying central allocation wins or ties twelve
of eighteen cell means; the private market wins none. Matched private-request rotation
isolates more of the auction package from fallback policy differences. Same-host
bounded gateway saturation improves from 13.5 to 39.2 completions/second; all three
steady agents complete 225/225 combined requests under noisy-agent load.

Branch `build/public-exceptional-v3`, private draft PR #3, remains unmerged. The final
live evidence checkpoint is `97c0c48`. Final independent review and newest-commit CI
confirmation are still in progress. Historical sections below are explicitly
chronological: earlier missing-key and pending-study notes describe those checkpoints,
not the current state. V2.1 files and original unfavorable results are unchanged.

## Release gate evidence

| Gate | Current evidence / qualification |
| --- | --- |
| Fresh install and offline demo | Clean wheel/isolated consumer artifact; extracted sanitized copy passes check/property/build/demo |
| Secret-safe opt-in live path | One catalog, 42 chat calls; scoped isolated agents; exact runtime key audit zero matches |
| State-aware worker | Interpretation/controller tests; finite actions and calls; terminal authority denials |
| New frozen evaluation | Corpus `896af82`, protocol `ebd42a9`, unchanged hashes; one completed live study |
| Strong practical alternatives | Five policies, all 36 tasks retained; reviewer and rules advantages reported |
| Negative evidence retained | Original V2.1 untouched; GPT-OSS empty responses and eight live uncertainties preserved |
| Economic causal controls | 3960 paired trials, report costs/subsets/noise/overstatement, matched no-market and oracle |
| Measured performance/fairness | Same-host before/after artifacts, bounded admission and per-agent fairness artifact |
| Isolation and public interface | Thirteen namespace/authority checks; clean wheel consumer; no operator credentials |
| CI | Python 3.11–3.14 and browser passed at `8f7b580`; latest checkpoint confirmation pending |
| Privacy and public exposure | Original stays private; separately sanitized archive tested; final refreshed audit required |
| Public claims and docs | Results and portfolio guide state synthetic utility, modeled reviewer/cost and provider variability |
| Outside-human validation | Challenge ready; no outside engineer has completed it yet |

This is evidence for a technically serious local reference project, not a hostile
Internet service or commercially validated spending guarantee. Public readiness
applies only to a reviewed sanitized copy, never to flipping the original private
history public. Package metadata remains 0.2.0; V3 names the evidence/engineering
iteration, not a published package release.

## Starting checkpoint

- Reviewed merged main: `0574137da429af9985f84bd964bcda1bc2ffe2b5`.
- Branch: `build/public-exceptional-v3`; repository verified private via GitHub API.
- PR #2 verified merged. No V3 PR or release yet; no self-merge is authorized.
- Baseline `make check && make property` passed outside the restricted execution
  sandbox: 149 deterministic tests, Ruff and the Hypothesis state machine. The
  initial sandbox attempt failed because socket/process fixtures lacked permission;
  this is not counted as a product failure or passing verification.

## Corpus freeze checkpoint

New `semantic-finops.v3.frozen-1`: 36 development and 36 held-out cases. Manifest:
`evidence-v3/heldout-manifest.json`. Held-out full hash:
`7325b43b0dffd0d82c1a8a4f0c48c007ad4648d6de0b8c2158396767da6c6cd7`.
Two corpus tests pass, including a fixed hash assertion preserving V2.1's holdout.
Only structural validation has run; no V3 worker tuning or live evaluation yet.

The generator crosses single/split/replaced payment topology with visible,
purchasable, missing and conflicting evidence. Language, noise, vendor, document
order, references, values and deadlines vary independently. It remains synthetic,
authored and bounded; these cases cannot establish general finance competence.

## Remaining required work

State-aware worker and tests; development-only model selection; frozen five-policy
evaluation; priced/strategic information study; measured concurrency/fairness;
clean-wheel and isolated integration; public documentation and full history audit;
final adversarial review, verification, CI and a new unmerged PR. This checkpoint
does not claim public readiness, useful model-added work or completion.

Independent parallel review was attempted; both reviewer agents failed due to the
workspace credit service before returning findings. No independent review is claimed.
Local implementation/review continues; external-human validation is not fabricated.

## Worker development checkpoint (not final quality evidence)

The trusted registry now supports explicit `workload: v3` registration without
changing V2.1's default. V3 observations enumerate available actions and actual
modeled quote bounds. Source retrieval is single-use, inference is capped at two
attempts per case, and optional consultation at one per case/six per policy. The
model receives only an interpretation schema: visible payment/document IDs,
assessment and confidence. It cannot propose a task, source, tool or approval.
Schema identities change when purchased documents change the evidence context.

The separate HTTP consumer runs five policies and retries only the two explicitly
recoverable source/capacity denials within the task's fixed action deadline. Its
current value-of-information rule uses declared, **uncalibrated** 60% model and 98%
reviewer success priors, expected 128 output tokens, actual quote affordability and
task value. These assumptions are development choices, not measured calibration.

Executed provider-free namespace study:
`PYTHONPATH=src python3 scripts/semantic_validate.py --workload v3 --output var/evidence-v3/development-2.json`.
The first attempt was blocked by sandbox socket permissions before any consumer or
provider execution; the second ran with approved loopback/namespace access.
36 development cases per policy, all terminal, no incorrect confident actions or
remaining exposure: rules 12 verified/cost234; rules+reviewer 18/cost3858 (six modeled
consultations); always-model protocol fixture 12/cost4925 (18 fixture calls);
selective fixture 12/cost1802 (six fixture calls); selective+reviewer 18/cost3858
(six consultations, no inference). **Fixture tokens are not real provider usage and
these scores do not establish model usefulness.** The artifact was generated from
the in-progress worker, before final policy freeze.

Seven new development-only regressions pass: visible schema identities, schema
fingerprint changes, mandatory-review exclusion, bounded inference with retained
usage, easy-case bypass, unsupported identity rejection and bounded denial behavior.
Ruff passes. Corpus hash is unchanged after formatting-only edits.

The current environment has no `NVIDIA_API_KEY`; no V3 live calls have been made.
The owner was asked to restore it privately, never through chat. Offline work is
not blocked by its absence. Final model selection and held-out live quality remain
unverified until the server-side capability is restored.

## Gateway concurrency and fairness checkpoint

Global serialization remains around market/operator mutations. Independent cheap
execution and read routes now run without that lock; SQLite still owns reservation,
dispatch and settlement atomicity. Three dedicated race regressions pass: independent
provider calls overlap while operator reads succeed, a noisy authenticated agent
cannot consume another agent's execution allowance, and duplicate request IDs invoke
the adapter once. Ruff passes. These do not claim distributed exactly-once billing.

Matched local open-loop workload, four connections and the same 50 ms fake provider,
15 seconds at each offered rate (5/20/80/5 requests per second):

| Offered/s | Before completions/rejections | After completions/rejections |
| --- | --- | --- |
| 5 | 75 / 0 | 75 / 0 |
| 20 | 203 / 97 | 300 / 0 |
| 80 | 203 / 997 | 588 / 612 |
| 5 recovery | 75 / 0 | 75 / 0 |

Saturated completion rate rose from 13.53/s to 39.2/s on this development host.
Both runs have zero transport errors/generator drops and consistent within-funding
audits at every drain. Artifacts: `var/evidence-v3/overload-before.json` and
`overload-after.json`. These are same-host reference measurements, not production SLOs.

`scripts/fairness_validate.py --seconds 15` used 16 total connections, a cap of two
concurrent authenticated requests per agent, and independent scheduled arrivals.
The noisy agent completed 299/1200, with 901 explicit rejections; three steady agents
each completed 75/75. All 75 dashboard reads succeeded, followed by 15/15 recovery
requests. No transport errors, no remaining reserved liability, and accounting audit
consistent/within funding. This protects authenticated execution capacity, not raw
socket flooding before identity is available. The global connection cap still bounds
unauthenticated work; it cannot promise per-agent fairness before authentication.

## Information-cost study development

`aecp.reporting_study` keeps V2.1 unchanged and uses its paired hidden financial
truth with independently drawn, publicly announced per-agent cheap/premium/reviewer
tariffs. All allocators and the exact relaxed oracle face identical physical
capacities and tariffs. Reporting fees and bidding fees consume operating budget;
auction revenue remains conserved internal credits. Attempted-but-wrong cases are
separate from never-attempted cases.

Controls include paced public, truthful shared, noisy shared (the planner knows the
noise rate and adjusts its posterior), strategic shared (agent zero always claims
unposted evidence), private-no-market, private auction and heterogeneous-cost
heuristics. This is a bounded reporting intervention, not an equilibrium model.

An initial 3240-run development study showed that mandatory purchase of all reports
can make shared central worse as reporting cost rises. Treating this as the strongest
central policy would be unfair. A new `shared-selective` control therefore evaluates
ex-ante information value over eight possible public-prior signal combinations,
including remaining-budget opportunity cost, before deciding whether to buy reports.
It never observes actual reports before purchase. Forced sharing remains a labeled
ablation. Five research tests pass, including budget/oracle/conservation, public
information boundary, reporting charges and refusal of unaffordable reports.

The pilot is retained as `var/evidence-v3/reporting-study.json`; a fresh final study
must include the stronger selective-reporting control. No V2.1 finding is relabeled
as a V3 result, and no market-win claim follows from these pilot runs.

## Owner-directed licensing and public exposure

The owner authorized choosing a license that permits review but does not grant
commercial exploitation rights. Selected the unmodified PolyForm Noncommercial
License 1.0.0 from the official project, rather than MIT/Apache or a bespoke legal
text. `LICENSE`, package metadata and README now identify noncommercial
source-available licensing. The license's permitted-organization and fair-use
provisions remain intact; it is not a technical anti-copying mechanism or a blanket
claim over independently implemented ideas. Separate commercial permission remains
the owner's decision. Repository visibility is unchanged.

`uv build` passed after approved build-dependency access. The wheel contains the
license and its bytes match the source file. This was verified by reading the wheel
archive, not inferred from configuration alone.

The expanded public audit currently finds no credential patterns, but flags personal
home paths in historical blobs and email addresses in reachable history/metadata.
These require classified review and owner publication decisions; no history has
been rewritten and no public-ready claim is made. The current namespace probe no
longer hard-codes a personal username. Runtime/generated NVIDIA-pattern scanning
checked 571 files/blobs with zero hits; exact runtime-key comparison was unavailable
because the current environment does not contain the key.

## Independent review amendments

The concurrency reviewer executed three gateway regressions and found no new
overspend or duplicate-dispatch defect in the inspected changes. It correctly
distinguished post-authentication fairness from raw socket denial of service.
Following its recommendation, the duplicate test now blocks the original provider
execution, submits duplicates while it is definitely dispatched, checks retained
exposure, then proves one receipt, one charge and final settlement. All three tests
pass. GET routes may still trigger transactional expiry maintenance; removal of the
Python mutation lock does not make every GET a read-only SQLite transaction.

The independent mechanism reviewer found no invalid oracle, overspending or credit
creation, but identified two important comparison weaknesses. The amended study
now includes a matched `private-request-rotation` control with the same premium
request and fallback policy as the market, removing auction ranking, credit payments
and bidding fees. This identifies an auction-package contrast, not a price-only effect.
The central buyer now selects among all eight subsets of current reports, rather
than buying every report or none, and enumerates signals only for purchased reports.
It cannot inspect actual reports before deciding. Future information acquisition is
still approximated by the public-prior continuation, not a Bayes-optimal scheduler.

Tariff and reporting-noise coordinates remain versioned independently from the
amended policy implementation, preserving paired workloads across the V3 development
studies. Eight research regressions pass, including independent exhaustive two-round
oracle enumeration and matched fallback behavior. Per-agent verified value and
premium access are now recorded so fixed overstatement effects can be inspected
without claiming equilibrium behavior or profitable lying.

## Privacy decision implemented

The owner delegated the historical-identifier decision. Preserve the original
private history; prepare a separate history-free publication candidate. The snapshot
builder refuses credentials/databases and implementation-path redaction, permits
only explicitly reviewed email-like fixtures, and redacts personal home prefixes
only in copied report text. A manifest records original/redacted hashes. This avoids
publicly exposing unnecessary personal metadata without rewriting frozen evidence.
No repository has been published or rewritten. Three export-policy regressions pass.
See `docs/PUBLICATION.md` for the exact procedure and detector limitations.

The genericized namespace isolation probe also ran successfully: all thirteen
checks pass and its accounting audit remains consistent and within funding.

## Clean installation and integration checkpoint

Executed `scripts/clean_install_validate.py` against the built wheel: fresh virtual
environment, package imported from installed site-packages, separately copied public
consumer with no internal imports, no source-tree PYTHONPATH or provider environment.
All thirteen namespace/authority/recovery checks pass; 8/12 development tasks verified,
consistent accounting and zero provider calls. Cached local wheel installation took
0.140 seconds and the complete automated proof 1.365 seconds; these are not human
setup or time-to-first-request measurements. Evidence: `clean-install.json.gz` in
the V3 evidence directory. An outside human still has not participated.

The operator provisioning command and rewritten external challenge now give a
consumer eight modeled units, one preexisting four-unit fake uncertainty, a useful
invoice task, a predictable second-request denial and a public restart trace. An
HTTP integration test executes those documented outcomes through the SDK and passes.
No operator/provider credential is supplied to that consumer. OpenAI-compatible
integration is a separate opt-in alternative, not an implied offline NIM endpoint.

The reviewed reporting study completed 3960 paired policy trials. Selective-report
central wins or ties twelve cell means; private market wins none. The new public
results page distinguishes information purchase, auction-package effects, modeled
costs and negative historical quality. Six executed offline evidence artifacts are
archived with compressed/uncompressed hashes, without replacing V2.1 evidence.

## Workflow recovery review finding

The spending kernel already recovered trusted receipts without a provider adapter,
but the semantic wrapper tried to construct a new live request first. That made
workflow-level recovery unnecessarily depend on live adapter configuration. The
wrapper now recognizes its existing immutable execution, checks task/resource/
operation/parameters against the recorded semantic action, and asks the kernel to
recover it rather than reauthorize it. Reserved work still goes through the kernel's
current quote/authorization checks before dispatch.

A new fake-provider regression crashes after durable inference receipt persistence,
reopens the database with no NIM adapter, and settles the workflow without redispatch.
All eight interpretation regressions and the existing semantic recovery tests pass;
known usage remains charged and missing evidence does not imply a refund. No fresh
NIM crash call was consumed for this offline regression.

## Verification and dashboard checkpoint

Executed `make check`, `make property`, `npm run check`, and `uv build` after
the receipt-recovery and workload-label regressions: **175 deterministic tests
pass** (23.485 seconds), **one Hypothesis state-machine test passes** (7.093 seconds),
Ruff/JavaScript checks pass, and source/wheel packages build. The initial restricted
attempt failed on nineteen socket/process permission errors; rerunning with local
socket/process permission succeeds. This is local verification, not a CI claim.

Fixed a provenance labeling defect: semantic snapshots now derive workload versions
from persisted observations, report mixed corpora explicitly, and preserve the
legacy V2.1 label for legacy cases. A regression covers V3 and mixed snapshots.

Updated the normal Chromium regression to register the 36-case V3 development
corpus and require state-aware action sets. Executed against a fresh loopback
gateway on port 8873: five views, 36 semantic cases, refresh persistence, zero page
errors and no mobile overflow. The simulation retains 28 modeled unresolved units.
The mobile screenshot was visually inspected; historical screenshots were not
overwritten. New captures are in `var/evidence-v3/browser-review`, and the machine
result is `var/browser-smoke.json`. This browser run makes zero provider calls and
does not establish live V3 semantic quality.

`NVIDIA_API_KEY` remains absent from the trusted runtime environment. No V3 live
catalog or chat calls were made in this checkpoint. Final model selection, policy
freeze and held-out live execution therefore remain outstanding, not passed.

## Final-evaluation procedural guard

Added `scripts/semantic_protocol.py` and a required V3 live `--protocol` argument.
The final contract must be committed, with an unchanged clean code tree, corpus,
model and endpoint. It binds core, controller, prompt/schema and harness source
hashes and the bounded request limit. An exclusive attempt marker prevents silently
repeating the same protocol under a new output name. Three offline regressions pass
for dirty/uncommitted freezes, source/provider mutation and repeated attempt claims;
Ruff passes. No final protocol was generated yet, because development-only provider
selection and final policy review are still outstanding. See
`docs/SEMANTIC_PROTOCOL.md`; this is an experiment-discipline guard, not a claim that
an operator cannot manipulate history or inspect test data.

## Remote review and credential audit checkpoint

After commit `405700b`, `scripts/secret_audit.py` inspected 719 files/blobs with
zero credential-pattern matches; the exact runtime key was unavailable.
`scripts/public_audit.py` inspected 537 objects/files with zero secret-pattern hits.
It retains three historical personal-path findings and fifty email-like findings
(including commit metadata and fixtures). These are not a claim that the original
history is publication-safe: the separate sanitized-copy procedure remains required.

GitHub access was retried outside the restricted network environment. Both
repository visibility lookup and V3 PR lookup fail with **HTTP 401 Bad credentials**.
Current visibility and remote PR state cannot be reverified until authentication is
restored. No push, merge or visibility change was performed. The last independently
verified repository visibility was private. A new V3 PR remains an outstanding
deliverable, not a completed action.

The full post-guard local verification also passes: **178 deterministic tests**
(22.346 seconds), Ruff and the separate Hypothesis state-machine suite. Command:
`make check && make property`. This does not substitute for the unavailable remote
CI run or the pending final live semantic evaluation.

## Extracted publication candidate verification

Generated a separate history-free candidate from `e4812fc` with 178 archive entries,
including the publication manifest. SHA-256:
`762896bd65620b5c0b8444fe07f90ae98e07f2488a784e2db8155142ffe7e135`.
Verified all 177 source-file hashes, absence of `.git`, and one explicitly recorded
report redaction. Executed `make check && make property && uv build && make demo`
inside the extracted copy, not through repository PYTHONPATH: all pass. The ordinary
demo verifies 4329 modeled value with zero unresolved exposure; the outage demo
verifies 4037 with 28 units retained across two unresolved tasks. The state-machine
run passes in 7.549 seconds. No archive was published.

At the owner's request GitHub was retried again: both repository and PR lookups
still return HTTP 401. No environment token override is present. Authentication
must be restored before remote review can be completed; no credential was printed.

## Restored capabilities and development model selection

GitHub authentication and the server-side NIM credential were restored; the repository
was reverified **PRIVATE**, with no existing V3 PR. Executed the new governed
development-only compatibility probe from `f301fc7`: one catalog request, six chat
requests, 3470 input / 1198 output / 4668 total provider-reported tokens. All modeled
liabilities settled, audit consistent and within funding, no bound breach. Actual
cash remains operator-declared zero free-prototype usage, not an invoice claim.

Nemotron `nvidia/nemotron-3.5-lightning-30b-a3b` was catalog-present and produced
three schema-valid, correctly linked answers across single, split and replacement
development cases. `openai/gpt-oss-20b` was present but returned empty completion
content at the 256-token limit in all three cases; its known usage still settled.
`meta/llama-3.3-70b-instruct` was absent. The declared selection rule chooses Nemotron.
This tiny probe establishes compatibility for this run, not broad reliability or a
held-out quality result. The source commit precedes the live calls; no prompt or
controller tuning followed inspection of these development answers.

Metrics now explicitly separate offline fixture receipts/tokens from provider
receipts/tokens. A regression confirms malformed live answers still retain usage,
while fixture token values cannot be presented as measured provider consumption.

## Frozen final live study — executed once

The 36-case held-out full hash remains
`7325b43b0dffd0d82c1a8a4f0c48c007ad4648d6de0b8c2158396767da6c6cd7`.
Protocol commit `ebd42a9` binds source `3c9e041`, prompt/schema/controller hashes,
the selected Nemotron model and hosted endpoint. No policy/prompt/evaluator changes
followed the freeze. A browser-harness-only commit occurred during execution; the
artifact's end-of-run code revision is `8f7b580`, while frozen source hashes identify
the actual experimental code. No failure was retried or substituted.

All five policies ran as separate Bubblewrap-isolated consumers through the public
gateway. Each had 12000 modeled units and the same 36 tasks. Outcomes:

| Policy | Verified | Value | Settled | Outstanding | Calls | Reviews |
| --- | --- | --- | --- | --- | --- | --- |
| rules-only | 6 | 12876 | 216 | 0 | 0 | 0 |
| rules-reviewer | 12 | 29058 | 3840 | 0 | 0 | 6 |
| always-llm | 9 | 19199 | 6439 | 3491 | 18 | 0 |
| selective-llm | 11 | 23681 | 5071 | 1405 | 12 | 0 |
| selective-reviewer | 15 | 34899 | 6471 | 708 | 6 | 6 |

Final study: 36 provider attempts, 28 responses, eight timeout/connection outcomes,
18434 known input / 4262 output / 22696 total tokens. Missing timeout usage is unknown,
not zero. Including development selection, V3 used **one catalog and 42 chat calls**,
21904 known input / 5460 output / 27364 total tokens. Actual cash remains declared
zero prototype access, not an invoice. All accounting audits are consistent and
within funding; 5604 units remain reserved for uncertain external effects.

No incorrect confident finalization occurred. Twenty-five of 28 responses passed
the independent schema validator. Five/two/one cases remain unfinished under
always/selective/selective-reviewer; they are not dropped from denominators.
Each policy correctly abstains on nine missing-evidence tasks and escalates nine
mandatory-review tasks. Escalation is not counted as successful resolution.

Selective inference buys five additional correct cases beyond rules, but rules
retain the lowest cost per verified value. Selective+reviewer adds three cases
with unchanged reviewer demand versus rules+reviewer. The model complements rules
and scarce reviewers; it does not establish universal cost superiority. Reviewer
truth is simulated, corpora are authored/compositional, confidence priors uncalibrated,
and sequential policy execution is confounded by changing provider conditions.
No statistical significance or real financial savings is claimed.

Post-run `scripts/semantic_analyze_v3.py` grades linkage/confidence against hidden
truth only after evaluation, retaining journal hashes, known usage, outstanding
exposure and all original outputs. It is not imported by the worker. Commands:
`scripts/semantic_probe_v3.py`, `scripts/semantic_protocol.py`, and the single
`scripts/semantic_validate.py --workload v3 --live --protocol ...` invocation are
documented in `docs/SEMANTIC_PROTOCOL.md`. Prefreeze verification: 180 deterministic
tests, Ruff and Hypothesis pass. Exact runtime key scanning found zero matches.

Private draft PR: https://github.com/kabbersokhi-boop/agent-economic-control-plane/pull/3.
At `8f7b580`, GitHub Actions passed Chromium and Python 3.11/3.12/3.13/3.14 checks
(push and pull-request runs). Later commits require their own CI confirmation.
No merge, publication or visibility change occurred.

Reopened the final SQLite study without a NIM adapter and executed the Chromium
semantic inspector against its actual persisted state: 180 cases, 36 attempts,
28 trusted receipts, zero page errors, refresh persistence and no mobile overflow.
Desktop screenshot was visually inspected. The comparison reconciles settled and
reserved balances to the study, including all 5604 unresolved units. This dashboard
inspection made no new provider call. Compressed final study, post-run analysis,
provider journal and browser evidence are archived with hashes alongside the
unchanged historical V2.1 artifacts.

## Final review handoff

At `97c0c48`, all GitHub checks passed: Python 3.11–3.14 plus Chromium, for both
push and PR runs. The final clean-wheel rerun passes all thirteen isolation and
authority checks, verifies 8/12 legacy development tasks, and makes zero provider
calls. A new offline regression exactly recomputes the archived V3 analysis from
its captured results/journal, preserving all eight uncertainties. Ruff passes.

Independent release review accepted the qualified experimental claims and flagged
privacy scope. Annotated tags are now included in the history scan. The suggestion
to hide the intentional GitHub project identity was rejected: the owner requested
a portfolio repository, not anonymity. Publication documentation now explicitly
distinguishes email/home-path minimization from the intended public project identity.
Private PR links are provenance, not substitutes for the committed evidence.

The project is resume-ready as a measured reference system, not evidence of
production deployment or a hiring guarantee. The original repository must remain
private; a refreshed sanitized candidate and owner publication approval remain
necessary. PR #3 stays draft/unmerged for final review. Latest handoff changes
require their own CI run; earlier green checks are not relabeled as current.

Highest-value next actions:
1. Have an outside engineer complete the integration challenge and publish unedited feedback.
2. Obtain independently authored/licensed financial cases and pre-register a new paired study.
3. Improve deterministic semantic competitors and test robustness across models/provider conditions.
4. Validate real reviewer effort and commercial billing bounds before making savings claims.
5. Complete the sanitized-publication review and record a short reproducible demonstration.
