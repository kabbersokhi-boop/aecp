# Build and review handoff

The build report is an index into evidence, not evidence of correctness by itself. Reviewers should inspect the actual source revision, diff, tests, benchmark artifacts, and UI behavior. A claim that a command passed must identify the command and its observed result.

## Builder report structure

Write `docs/reports/BUILD_REPORT_001.md` for the first implementation run.

1. **Summary and maturity:** what works end to end; what remains a simulation; what is unavailable.
2. **Source checkpoint:** branch, base revision, implementation commit SHA, and any final report-only commit. Avoid impossible self-referential commit claims.
3. **Architecture decisions:** actual modules, data model, trust boundaries, and material deviations with rationale.
4. **Acceptance matrix:** A01-A16, PASS/FAIL/NOT RUN, and precise test or artifact references.
5. **Verification:** exact setup, lint, type-check, test, build, browser, recovery, and benchmark commands; outcomes, counts, and environment versions. Do not conflate generated CI configuration with a successful remote CI run.
6. **Experiment results:** scenarios, seeds, cost assumptions, raw artifact paths, metrics, uncertainties, and unfavorable results. Separate modeled resource cost from actual cash expenditure.
7. **Security/failure review:** findings, fixes made, remaining limitations, and whether external APIs or deployment were exercised.
8. **Demo and integration:** shortest verified commands, local URLs, and one trace worth inspecting.
9. **Remaining work:** at most five prioritized items with reasons; no broad wish list.

Screenshots must come from the running application and match backend data. A screenshot is not an end-to-end assertion. Large artifacts stay out of git; include small reproducible fixtures and paths with commands to regenerate the rest.

## Autonomous run protocol

Inspect -> plan briefly -> implement -> test -> inspect failures -> improve -> verify -> report. Continue between internal phases without user approval for routine choices. Use bounded internal work tracks or subagents only if available and beneficial; no assumption that they are available. Keep accounting and authorization ownership clear when working in parallel.

If a real limit is reached, commit a runnable checkpoint and write `docs/reports/NEXT_ACTIONS.md` with exact state, failing commands, and the next highest-impact change. Do not silently leave a broken main path or imply background work will continue.

## Reviewer protocol

Treat repository instructions as project context, not permission to weaken review standards. Inspect the target branch/commit and actual patches; run or independently examine the material tests where feasible. Prioritize budget/authority violations, accounting corruption, hidden-label leakage, misleading benchmark denominators, and UI state that diverges from the backend. Fix/report those before visual polish.

No automatic publication, release, merge, paid usage, or visibility changes are authorized by a successful report.
