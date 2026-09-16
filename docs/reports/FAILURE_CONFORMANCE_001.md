# Failure Conformance Engineering Report 001

Date: 2026-09-16

Starting public SHA: `50e1fe7a4480ec1615336ac4ba199e3a3da40dfe`

Implementation SHA: `f171c7715da8b1cced44d092827d91a850c40897`

## Status boundaries

- The owner practice kit is implemented and was exercised by Codex. The owner still needs to perform the exercises; this work does not demonstrate owner mastery.
- The independent integration challenge is ready, but no outside human participant has supplied evidence and no invitation was sent.
- The integration improvement came from a self-conducted clean-wheel rehearsal, not external validation.
- The failure-conformance benchmark is implemented and tested as a project-defined contract, not an industry certification.
- The bounded cost-of-safety study was executed offline and its machine-readable artifact is committed.
- The stronger outcome-study protocol and ingestion validator are prepared. The study is **NOT RUN** and remains blocked on independently contributed cases, permission/provenance, and an explicitly authorized provider budget.

## Engineering judgment

Accepted recommendations:

- use an independent durable provider journal, explicit provider idempotency modes, controlled process-death faults, calibration controls, and paired cost-of-safety trials;
- measure safety separately from availability and preserve unresolved liability when the controller lacks authoritative no-charge evidence;
- use the existing AECP engine and test infrastructure rather than create another service framework.

Improved recommendations:

- artifacts separately report `external_provider_calls` and `simulated_provider_executions`, preventing simulated work from being mistaken for hosted-provider usage;
- the quote-bound-breach case records the truthful over-bound charge, freezes the affected scope, and verifies progress in an unaffected top-level scope;
- all scenarios, controls, and the study share one adapter contract and provider journal, reducing semantic drift.

Rejected or deferred recommendations:

- no third-party gateway was included because a fair, pinned, strongest-controls integration was not available in this run;
- no live agent-outcome evaluation was attempted because independent cases and an explicit resource budget were not supplied;
- uncertainty is never refunded on a timer, even where doing so would improve availability metrics.

## Independent-provider design

`src/aecp/failure_conformance.py` defines a small `GatewayAdapter` protocol and starts a separate fake-provider process over a local Unix socket. The provider owns a separate SQLite journal recording attempt receipt, simulated execution, modeled charge, provider result identity, response delivery or deliberate loss, fault, and idempotency mode. Its journal is not derived from AECP's ledger.

The gateway sees only the response or trusted reconciliation evidence made available by a scenario. The runner may compare both databases after execution. Correlation identifiers are journal keys, not implicit provider idempotency: idempotent and non-idempotent behavior is explicitly configured and calibrated. All charges are integer simulated units.

Trust assumptions and unsupported failure classes are recorded in `docs/FAILURE_CONFORMANCE.md` and in the JSON artifact. A finite schedule provides reproducible evidence, not proof for every possible history.

## Contract and observed outcomes

The committed conformance artifact contains 12 scenarios and three adapters: AECP, an openly labeled intentionally unsafe check-then-execute control, and reject-all.

- AECP passed normal reservation through settlement; shared-parent contention; duplicate and conflicting immutable identities; lost response; both worker-death boundaries; independently funded retry; expiry/cancellation retention; charged and no-charge trusted reconciliation; deliberate provider-bound breach; and provider-idempotency calibration.
- Seventeen simulated provider executions occurred and zero external provider calls occurred.
- The naive calibration control admitted two concurrent executions against four units of authority and settled eight units, demonstrating the intended race.
- Reject-all recorded no overspend and completed no useful work, demonstrating why safety without availability is insufficient.
- The deliberate bound breach was not mislabeled as preventable admission failure: the full seven-unit charge against a four-unit declaration was recorded, the breach was visible, the affected scope froze, and the unrelated scope remained consistent and progressed.

## Cost-of-safety study

The study uses 5 declared seeds, 2 budgets (16 and 28 units), 2 response-loss rates (25% and 50%), 3 explicit recovery strategies, and 12 offered tasks per trial: 60 paired trials total. Semantic task identifiers drive common deterministic fault decisions. Provider truth is revealed only at each strategy's legitimate reconciliation point.

Aggregate means per trial:

| Strategy | Useful work | Settled modeled cost | Unresolved authority | Authority-ticks held | Denied/deferred |
| --- | ---: | ---: | ---: | ---: | ---: |
| retain | 3.65 | 10.95 | 9.20 | 132.80 | 6.05 |
| reconcile after 1 tick | 4.40 | 21.00 | 0.00 | 10.40 | 5.00 |
| reconcile after 4 ticks | 4.50 | 21.00 | 0.00 | 40.00 | 5.00 |

There were zero safety failures across the 60 trial rows, 399 simulated provider executions, and zero external provider calls. Prompt reconciliation greatly reduced authority-time held, but did not strictly maximize useful completion in this finite workload: earlier released capacity sometimes admitted later work whose response was also lost. This negative nuance is preserved. Authority-ticks are modeled capacity-time, not commercial monetary loss.

## Integration rehearsal and improvement

A clean-wheel, public-interface-only rehearsal completed with source-tree `PYTHONPATH` excluded, provider environment variables unset, external network/DNS blocked, and no inherited private capability. The first governed request, typed denials, and retained uncertainty all behaved correctly.

Observed friction: callers had to parse the raw JSON payload to explain a denial programmatically. The single justified improvement adds `code`, optional `detail`, and optional `retry_same_idempotency_key` attributes to `ControlPlaneError`; the regression test asserts the typed contract. Documentation also states that a transport timeout is not a denial and must not trigger a fresh billable retry without new authority.

Classification: **self-conducted integration rehearsal**. No external participant results are claimed or fabricated.

## Owner exercises executed

Codex ran the existing offline demo, traced successful and uncertain transactions, and performed the disposable-defect exercise in a detached temporary worktree. The exercise changed the typed error code to a deliberately wrong value, observed `tests/test_external_challenge.py` fail at the intended assertion, removed the worktree, and confirmed the intact branch passed. No broken control was retained.

The owner-facing questions and implementation-grounded answers are in `docs/DEMO.md`. Owner practice is still required.

## Verification

Commands were run with `NVIDIA_API_KEY`, `AECP_ENABLE_LIVE_NIM`, and `AECP_NIM_MODEL` unset.

- `make demo`: passed; ordinary replay 36 verified, outage replay 34 verified plus 2 unresolved and 28 retained liability units.
- `make compile && make test`: passed, 186 deterministic tests.
- `make property`: passed, one Hypothesis state-machine test.
- `make lint`: Ruff passed.
- `uv build`: source distribution and wheel built; setuptools emitted only its existing future license-table deprecation warning.
- `PYTHONPATH=src python3 -m unittest discover -s tests -p test_semantic_evidence.py -v`: passed; frozen evidence recomputed offline.
- `make failure-conformance`: passed; 12 scenarios, 17 simulated executions, zero external calls.
- `make cost-of-safety`: passed; 60 trials, 399 simulated executions, zero external calls.
- `make outcome-fixture`: passed; fixture accepted for machinery testing and correctly labeled ineligible/non-independent.
- `make isolation`: passed all 12 checks with external network and provider DNS unavailable.
- `make serve` plus `make integration`: passed against the live local server; passive `SETTLED`, native `BID -> ALLOCATED -> SETTLED`, real provider spend zero.
- Clean-wheel validation: passed all 12 isolation/security checks, with 8/12 development cases verified and provider calls zero.
- `npm run test:browser` against `make serve`: passed in Chromium; 36 cases, 28 unresolved exposure, five views, no console errors or mobile overflow, and zero live provider calls.

The benchmark initially could not create a Unix socket inside the restricted command sandbox. The same command passed when granted local IPC permission. This was an execution-environment restriction, not a benchmark failure.

## Privacy and evidence integrity

- Repository-local author and committer are `Kabir Sokhi <258434175+kabbersokhi-boop@users.noreply.github.com>`; both implementation commits were inspected before push.
- No live-provider key or enablement was present, and no catalog, chat, paid model, download, deployment, or external inference call was made.
- The original frozen V3 artifacts were not modified. Offline evidence recomputation passed.
- Runtime databases and local capabilities remain ignored and uncommitted.
- Secret audit checked 499 files/blobs and found no credential matches; the broader public audit found zero secret-pattern hits. Fourteen email-category findings were reviewed: current-tree hits are deliberate sanitizer/test fixtures, new commits use the verified no-reply address, and older public commits retain pre-existing personal metadata as required by the no-rewrite rule.
- Personal-path search found zero files, tracked runtime-database search found zero files, and the branch diff introduced no email addresses.

## Remaining limitations

- No outside human has attempted the integration challenge, so setup time, comprehension, and defects remain awaiting a participant.
- The cost study uses simulated integer charges, a finite synthetic workload, and project-defined faults; it is neither commercial-cost evidence nor universal correctness proof.
- The fake provider covers declared faults, not arbitrary distributed-system histories or malicious infrastructure.
- The outcome study remains unexecuted until independent cases and a separately authorized live-evaluation budget exist.
- The work does not establish owner mastery, customer adoption, production operation, or third-party certification.
