# First build: a working economic control plane and deterministic economy

You are implementing the first substantial release of `agent-economic-control-plane`. Work as the responsible engineer: inspect, design briefly, implement, verify, critique, improve, and deliver evidence. Do not stop after planning, scaffolding, the first feature, or a list of suggestions. Complete the largest coherent, tested vertical slice you can in this run.

## Context and autonomy

The project is an economic control plane for autonomous agents. Its reference environment is a multi-agent economy for verified synthetic financial-operations work under non-negotiable resource budgets. It should demonstrate engineering depth through enforceable accounting, realistic uncertainty and failure handling, meaningful agent policies, fair experiments, and an unusually useful dashboard.

The repository is private; all code, documentation, interfaces, and evidence must be suitable for external technical review. Do not fill public-facing documentation with recruiting ambitions, hype, fabricated benchmarks, or unsupported assurance claims.

Read `AGENTS.md`, the README, `docs/ARCHITECTURE.md`, `docs/DETERMINISTIC_ENGINE.md`, `docs/INTEGRATION.md`, `docs/ACCEPTANCE.md`, `docs/REVIEW_PROTOCOL.md`, and the existing implementation/tests. Establish what actually exists by running the foundation checks. The existing kernel is a deliberate narrow reference, not a complete platform. You may improve or replace its internals when justified, preserving the tested safety semantics and documenting changes.

Use your own judgment to fix omissions, improve architecture, simplify overcomplicated parts, and add a high-value capability when it directly strengthens this milestone. You do not need approval for ordinary implementation decisions. Do not turn a small ambiguity into a blocker; make a reasonable, documented assumption. Never relax safety or fabricate evidence to finish faster.

## Authorized scope

Work in this repository on a review branch such as `build/deterministic-economy-v1`. Preserve unrelated changes. If starting from a downloaded starter with an authenticated CLI and no remote, creation is authorized only for the private target in `docs/BOOTSTRAP.md`. If creation/push is unavailable, build locally and report that accurately; do not stop engineering work for that reason.

No paid model usage, public deployment, repository visibility change, external payment execution, credential disclosure, force-push, release publication, or automatic merge is authorized. Do not disable tool sandboxing/approval controls to meet the mission. No LLM key may be required for the default system.

## Deliver a complete default experience

A developer should be able to follow short verified setup instructions, start the application, run a deterministic scenario, open the dashboard, observe resource contention and failures, inspect a transaction, compare allocation policies, and run a standalone example agent against the gateway. The data shown must come from the actual backend run, not unrelated mock arrays.

Prefer Python 3.11+ for the economic core and one local transactional application. FastAPI plus SQLite and a modest TypeScript dashboard are reasonable defaults, not mandatory theology. Use a small standard frontend stack if it improves the result; do not add a second backend, message broker, workflow platform, distributed cache, container cluster, or generic plugin system without a concrete need. Choose and lock real dependency versions after checking current documentation. Avoid unnecessary dependencies. The first working system should remain easy to understand and run.

## Workstream 1: trustworthy economic execution

Extend the reference kernel into a usable control boundary:

- Represent funded run/workflow/agent scopes. Reserve against every applicable parent atomically. Agent creation and delegation cannot create funded authority. Separate actual transactions from parent aggregate views so rollups are not double-counted.
- Keep integer operating-cost units separate from internal credits. In default mode operating expenses are explicitly modeled. Fund market balances and reward treasury once; use balanced, independently checkable journal movements for transfers/escrow/rewards.
- Bind a resource request, server-derived bounded quote, principal, immutable parameters, operation, and attempt identity. Never treat an agent-provided maximum willingness to pay as proof of a real provider cost cap.
- Handle admission, one-winner dispatch claim, settlement, pre-dispatch cancellation, unresolved execution, trusted no-charge reconciliation, retries, and suspension. Unknown outcomes remain liabilities. Each potentially billed retry needs distinct funding.
- Preserve actual bound violations, freeze affected execution, and surface incidents. Do not truncate actual charges or refund ambiguity to keep the UI green. Database unavailability must not authorize spending.
- Add small, explicit schema versioning/migration and restart behavior. Independent projections should reconcile to authoritative records.

Tests must include concurrent races, duplicate requests with changed parameters, aggregate parent oversubscription, spawning descendants, duplicate settlement, stale approvals, crash/timeout ambiguity, and attempts to reuse escrow. A useful model-based/property test should cover lifecycle transitions beyond a few happy paths.

## Workstream 2: advanced deterministic agents without pretending they are LLMs

Implement the economy in `docs/DETERMINISTIC_ENGINE.md` as real executable behavior, not just configuration classes.

Generate coherent synthetic records with hidden ground truth and useful but partial evidence. Agents propose structured case resolutions; a separate evaluator checks them. Resources must materially change observations or capabilities, so good decisions affect outcomes. Avoid an arbitrary success coin flip detached from the task.

Use at least three policy styles with genuine differences in risk tolerance, valuation, deadline sensitivity, or resource strategy. Include one small adaptive belief/reliability model with uncertainty and observable updates; demonstrate a test where those updates change behavior. Keep it transparent and proportional. Do not use heavyweight RL or train a model.

Agents should react to available budget, expected incremental value, task evidence, price, queue pressure, and remaining deadline. They can request cheap execution, bid for premium capacity, wait, defer, or seek consultation. They must not receive hidden labels, future faults, privileged difficulty, or evaluator randomness.

Use versioned semantic randomness and logical time. Shared exogenous task/provider outcomes must not change simply because a policy consumed more random numbers. Test repeatability across processes and event scheduling. Store decision explanations as structured observable inputs and computed estimates, not invented private reasoning transcripts.

## Workstream 3: one correct market and meaningful oversight

Implement one sealed-bid first-price auction for fixed-size premium execution slots. Specify bid admission, stable tie-breaking, funded escrow, winner count, each winner's payment, allocation expiry, failed delivery, cancellation, and refund semantics. Do not invent a uniform clearing price for a pay-as-bid mechanism.

The market buys capacity, not authority to overspend. Lost bids release market holds; delivered work may still incur operating cost. Agent rewards transfer from a finite treasury; they never replenish operating budget. Do not claim lending or insolvency mechanics unless implemented. Use accurate budget-exhausted/suspended/winding-down states.

Mandatory human authorization stays outside the auction. Optional consultation may be allocatable, but approval itself is non-tradable and bound to an immutable action and expiry. A simulated reviewer is clearly labeled simulated. Exhausted review capacity must block mandatory actions rather than silently waive review.

## Workstream 4: real integration boundary

Implement a small authenticated/scoped resource gateway and thin Python client. Separate agent, operator, reviewer, and trusted adapter authority. Do not authenticate from a caller-supplied agent ID. Do not allow agents to fund, settle, approve themselves, or choose an unrestricted external execution URL.

Provide two standalone examples: an ordinary agent that simply requests a resource and handles typed denial, and a budget-aware agent that checks its scope and bids. Both should operate through the same real gateway without direct database access or a rewrite of the core simulator.

Return bounded, structured outcomes. Do not use infinite automatic retries. Default to localhost, restricted origins, sanitized inputs/errors, and no committed token. A local demo is not hardened public multitenancy. Document bypass risks if a future caller retains raw provider credentials.

Do not implement a fake commercial adapter to tick a box. Optional OpenAI-compatible support comes only after the native path works; its supported subset must be documented and tested. No invented model names or universal compatibility claims.

## Workstream 5: a financial debugger, not a decorative dashboard

Build an actual dashboard in this run. Prefer a restrained technical interface: strong typography, accessible contrast, deliberate spacing, useful density, clear units, loading/empty/error states, and no meaningless motion. Use a coherent visual identity rather than a generic wall of cards.

It needs an overview with funded/spent/reserved/unresolved amounts; agent states and budget headroom; live market bids/allocations; review queue; a task/transaction inspector; and experiment comparison. Provide bounded live updates through a simple mechanism such as polling or server-sent events. Avoid competing client and server sources of truth.

The defining interaction is clicking a charge and following task -> decision -> principal/policy -> quote -> reservation -> allocation -> execution attempt -> settlement -> verified outcome. Explain denied requests and why the agent changed course. Display simulated versus actual costs and immutable experiment config/seed prominently.

Include usable controls for scenario selection, seed, and starting/pausing/stepping a run if supported by the backend. Persist state across refreshes. Inspect the running UI in an available browser and fix substantive visual/interaction issues. Screenshots must depict real runs. If no browser is available, report that and still perform route/build/data checks.

## Workstream 6: empirical evidence and failure demonstrations

Ship named deterministic scenarios: ordinary workload, tight operating budget, demand burst, provider outage with ambiguous completion, and unavailable reviewer capacity. A price-shock scenario is useful if it changes future quotes without rewriting committed liabilities. Include a bounded restart/resume test against an uninterrupted reference. Persist policy beliefs, pending events, escrow, and unresolved attempts as needed.

Compare the market with equal allocation, a sensible priority/deadline scheduler, and a centralized estimated-value-per-cost allocator using comparable information and the same task distribution. Do not make baselines intentionally weak. Generate raw per-seed outputs across several budget regimes and an affordable paired-seed set; provide a configurable larger experiment. Count planning, bidding, retries, verification, and optional review under explicit cost assumptions. Distinguish synthetic utility, modeled operating cost, and actual cash spend.

Report utility, completion/coverage, deadlines, budget/credit integrity, coordination overhead, and review demand. Include uncertainty estimates appropriate to the repeated paired runs and document their method. A market losing is a valid result. Do not tune the seeds or task scores to manufacture market superiority.

Recorded replay, deterministic rerun, and changed-policy re-execution must be labeled differently. Do not replay an old trace and call it a new policy outcome. Hashing events is not proof against a malicious host.

## Finish the run with evidence

Use `docs/ACCEPTANCE.md` as the completion contract, not a suggestion to write more plans. Run the full relevant unit/integration/security/failure suite, lint/type checks where configured, frontend/backend builds, documented quickstart, client examples, one restart scenario, and a bounded benchmark. Correct significant findings before reporting.

Review your own code for accounting bypasses, cross-agent authorization leaks, floating-point balances, unbounded retry, lost uncertainty, unsupported UI claims, hidden-label access, unfair baseline information, and duplicated/missing costs. Prefer fixing these over adding a cosmetic extra.

Update the README to distinguish implemented/tested/planned and give commands you actually exercised. Add concise ADRs only for material decisions. Save real sample artifacts small enough for the repository and make larger outputs reproducible outside git. Do not leave dummy buttons, fabricated screenshots, or TODOs in the critical demonstration path.

Commit coherent changes and push a review branch/open a pull request when allowed. Do not merge. Write `docs/reports/BUILD_REPORT_001.md` following the review protocol. Return branch/commit, what works, exact verification results, benchmark findings including unfavorable outcomes, demo commands, acceptance gaps, and at most five prioritized remaining improvements.

If a genuine tool/network/context limit intervenes, leave the deepest complete runnable checkpoint possible, record what was and was not tested, and identify the next concrete action. Do not silently redefine incomplete work as done. Do not ask whether to continue after each internal phase: continue within this run until the milestone is substantially implemented and verified or an actual limit prevents it.
