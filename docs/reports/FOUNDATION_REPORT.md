# Foundation verification

Prepared September 8, 2026. This report covers the starter only; it is not the first complete economic-application build report.

## Implemented

A Python reference kernel for independent, integer-unit accounts with transactional reservation, single-winner dispatch claims, unresolved liabilities, actual settlement, pre-dispatch cancellation, trusted no-charge reconciliation, and explicit bound-breach/freeze behavior. The module includes projection-versus-reservation consistency checks and an ordered event log. Reproducibility helpers provide versioned semantic draws and canonical artifact digests.

The starter also includes a private-repository bootstrap, implementation specifications, a substantial Codex mission, integration and acceptance contracts, and a review protocol. The economic dashboard, full environment, gateway, parent budgets, and balanced market journal are not implemented yet. No commercial/local LLM adapter is implemented. No real model calls were made.

## Executed checks

Environment: Python 3.13.5, Git 2.47.3, Linux.

| Check | Observed result |
| --- | --- |
| `PYTHONPATH=src python -m compileall -q src tests` | PASS |
| `PYTHONPATH=src python -m unittest discover -s tests -v` | PASS: 47 tests |
| `python -m pip install --no-build-isolation --no-deps -e .` | PASS: editable package installation |
| `aecp demo-ledger` | PASS: installed CLI runs |
| Two fresh `python -m aecp demo-ledger` processes followed by `cmp` | PASS: identical JSON output |
| `bash -n scripts/publish_private_repo.sh` | PASS: shell syntax |
| Relative Markdown link existence check | PASS |

The 47 tests comprise 40 kernel/reproducibility tests and seven offline bootstrap orchestration tests. The latter use mocked GitHub CLI and push operations; **they do not demonstrate an actual remote creation or push**. The kernel tests include independent processes sharing admission, parallel dispatch claims, duplicate settlements, restarts with unresolved liability, distinct retry costs, integer validation, negative headroom after a true bound breach, and detection of corrupted projections.

Full test output is in `FOUNDATION_TEST_OUTPUT.txt`. The real generated foundation demo output is in `../../examples/foundation-ledger-run.json`. It records a 400000-unit unresolved reservation, subsequent 250000-unit settlement, and denial of a new 800000-unit request against the remaining funding. All units are modeled, not billed dollars.

## Not executed / not established

- Remote repository creation/push: unavailable through the connected creation actions; no authenticated GitHub CLI in the authoring container.
- Remote CI: workflow authored, not run. Python 3.11/3.12 are configured but not locally exercised.
- Ruff linting: not run. An installation attempt failed because external package DNS/network access was unavailable. No lint success is claimed.
- Full application, HTTP security, browser dashboard, economic benchmark, hierarchy, and market-journal acceptance: not implemented by this foundation, so no success is claimed.
- Formal proof, adversarial host isolation, distributed availability, provider invoice enforcement, and independent external validation: not established.

The first implementation mission is `../CODEX_FIRST_RUN.md`. Its builder must produce `BUILD_REPORT_001.md` with fresh evidence and an A01-A16 acceptance matrix rather than treating this foundation report as proof of the full milestone.
