# Build report 004: an inspectable, story-led portfolio demonstration

## Summary and maturity

The demonstration now has a visible agent request origin, readable durable event
order and a controlled-failure evidence view. It executes local HTTP requests
against the real SQLite control plane. Fault evidence comes from the existing
independent fake-provider harness, including actual worker process exits.

This remains a local reference implementation with synthetic invoice work and
modeled `SIM_COST_MICRO` accounting, not commercial billing or production adoption.
No hosted inference or external business-system writes were made for this build.

## Source checkpoint

- Branch: `portfolio/aecp-demo-story`.
- Base: public `4d5120529659d9e182fbddb1a565e3f7fe6730fd`.
- Implementation checkpoint: the commit containing this report; resolve it with
  `git log -1 --format=%H -- docs/reports/BUILD_REPORT_004.md`. No self-referential
  SHA is asserted here. Any later report-only commit is separately visible in Git.
- Work branch / pull request only; no self-merge is authorized.

## Architecture and authority

See [ADR 0006](../adr/0006-inspectable-demo-boundary.md). New presentation reads
are isolated in `inspection.py`; economic primitives and adapter behavior are
unchanged. Agent credentials remain in page memory. Trace reads check ownership
and filter persisted events by account and attempt in one transaction.

The report viewer reads only a user-selected local file, with format, exact-integer,
file-size and journal-count checks. It escapes displayed values and labels each
scenario as independent. Hashes identify bytes; they do not attest truth or time.
Report-supplied audit facts are not a fresh live audit of an operational ledger.

## Presentation acceptance

| Requirement | Result | Evidence |
| --- | --- | --- |
| Visible independent request origin | PASS | `agent.html`, actual HTTP browser flow |
| Durable reservation → dispatch → receipt → settlement | PASS | `test_owner_trace_is_durable_ordered_and_read_only`, browser trace |
| Cross-agent and cross-role trace isolation | PASS | Gateway negative tests |
| Same-ID replay without another event/charge | PASS | Gateway and portfolio browser assertions |
| Protected action remains separately approved | PASS | `APPROVAL_REQUIRED` and `PENDING` in browser; existing policy tests |
| Budget denial before dispatch is inspectable | PASS | Denial-only owner trace test and browser flow |
| Definitive execution survives failed inspection | PASS | Browser aborts subsequent budget read and retains `SETTLED` / original HTTP response |
| Controlled evidence is not presented as live authority | PASS | Versioned file import, provenance labels, separate-scenario caption and guide |
| Desktop/mobile rendering | PASS | 1600×1000 and 390×844 Chromium checks, zero page errors or overflow |

Foundation A01–A16 are not redefined by this presentation change. Regression
coverage follows the existing [foundation acceptance mapping](BUILD_REPORT_001.md#15-acceptance-a01a16):

| Foundation IDs | Status in this build | Scope |
| --- | --- | --- |
| A01–A09 | PASS | Offline demos, full core suite, stress, replay, hierarchy and approval tests |
| A10 | PASS | Existing fairness tests plus fresh seeds 1/2, budgets 180/450 benchmark and 540-trial allocation smoke study; not a full new research replication |
| A11–A12 | PASS | Legacy and new browser paths; passive/native independent HTTP consumer integration |
| A13 | NOT RUN in full | Stress and failure harness rerun; all seven standalone scenario exports were not regenerated |
| A14 | PASS locally | Compilation, 189 Python tests, property test, Ruff, JS tests, wheel/sdist and real browser checks; remote CI status belongs to the PR |
| A15 | PASS within this scope | Credential-free assets, exact accounting projections, read-only evidence import, zero hosted calls; no new external security assessment |
| A16 | PASS | This report, source checkpoint, ADR, demo guide and bounded evidence claims |

## Verification actually run

Environment: Python 3.14.7 for stdlib tests; uv selected Python 3.12.13 for locked
development dependencies; Node 22.22.1; installed Google Chrome driven by
Playwright; FFmpeg n9.0.1. Commands ran against disposable databases outside the
repository, never the owner's earlier HVAC/SaaS environments.

- `make check`: compile, **189 tests PASS**, Ruff PASS. Rerun after fixes.
- `make property`: **1 Hypothesis state machine PASS**.
- `npm run check`: JavaScript syntax checks and **2 presentation tests PASS**.
- `uv build`: wheel and source distribution PASS; existing setuptools license-table
  deprecation warning remains (unrelated packaging migration not included).
- `PYTHONPATH=src python3 -m aecp demo-ledger`: PASS; retained uncertainty,
  trusted settlement and denied overspend; internally consistent audit.
- `PYTHONPATH=src python3 -m aecp demo --db <isolated-db> --run-id ordinary`:
  36 verified, 384 settled, 0 reserved, 450 funded.
- Same command with `--run-id outage --scenario outage`: 34 verified, 368 settled,
  28 reserved, 450 funded. No timed-out liability refund.
- `PYTHONPATH=src python3 scripts/failure_conformance.py benchmark --output <report>`:
  **12 scenarios, 17 simulated executions, 0 external provider calls**.
- `PYTHONPATH=src python3 -m aecp stress`: PASS; 40 competing descendant requests,
  14 admitted / 26 denied, 98 reserved within 100 funded; restart exposure retained.
- `PYTHONPATH=src python3 -m aecp benchmark --seeds 1 2 --budgets 180 450 --output <directory>`:
  completed; this smoke benchmark is not relabelled a new favorable market result.
- `PYTHONPATH=src python3 -m aecp allocation-study --seeds 2 --output <report>`:
  completed, 540 trials / 27 groups; existing historical research remains unchanged.
- `PYTHONPATH=src python3 scripts/integration_smoke.py --url http://127.0.0.1:8769 --tokens <private-capabilities>`:
  passive SETTLED; native BID → ALLOCATED → SETTLED; zero provider spend.
- `node scripts/browser_smoke.cjs` with explicit local URL, private capabilities,
  screenshot directory and installed Chrome: PASS; 36 outage cases, 28 unresolved
  exposure, semantic V3 registration/read, refresh persistence, zero console errors
  and no mobile document overflow. Initial default browser launch could not find
  Playwright's downloaded executable; explicit `AECP_CHROME` resolved it without
  weakening tests.
- `node scripts/portfolio_browser.cjs` with the same isolated instance and fresh
  fault report: PASS, including follow-up read failure, immutable replay, approval
  denial/request, exhausted cap, invalid report rejection and mobile layout.
- `git diff --check`: PASS before handoff.

CI now runs the new portfolio browser regression with a freshly generated offline
fault report. Its eventual remote result is not inferred from editing the workflow.

## Security and failure review

The bounded read-only reviewer found no direct authority/accounting vulnerability.
Three presentation findings were fixed: a post-execution inspection failure no
longer overwrites the definitive API response; the original response is retained
separately from the persisted trace; successful replays do not incorrectly display
an approval-wait reminder. Busy actions are guarded and disconnect clears old
principal data. A mobile provenance selector overflow was also fixed.

No credentials appear in static assets or selected screenshots. Viewer and agent
roles remain separate. The browser cannot settle uncertain attempts, approve
itself, replenish funding or use a report as a trusted receipt.

## Demo and experiment evidence

The shortest path is [PORTFOLIO_DEMO.md](../PORTFOLIO_DEMO.md). Screenshot assets
are native captures of the running application: `screenshots/agent-request-console.png`
and `screenshots/failure-retained-liability.png`. The latter shows provider fixture
execution with charge 3 but no delivered response; AECP retains a 4-unit liability.

Large source recordings, the silent edited MP4, chapter map and review frames are
outside Git in the local `aecp-demo-video` deliverable directory. The video presents
real local requests first, then clearly separate controlled fault scenarios. It
does not claim fresh NVIDIA inference, human reviewer approval, commercial cost
control, or exactly-once billing. Authentication and personal desktop content are
excluded from the edit. A caption was corrected during review: the bound-breach
fixture records actual 7 and FROZEN status but still has positive headroom 5; the
video does not falsely claim a funding breach in that fixture.

## Remaining work

1. Review the PR before merge; repository instructions prohibit self-merge.
2. Add a separately labelled live NIM chapter only after confirming allowance and
   explicitly authorizing bounded hosted calls; integration already exists.
3. Add an owner-scoped durable approval-status read if this console becomes a
   regularly used client. Current browser approval tracking is connection-local.
4. Migrate the existing setuptools license table before its deprecation deadline.
5. Keep public video hosting separate from source; no release/deployment was made.
