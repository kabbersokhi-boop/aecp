# Gated stronger outcome-study protocol

**Status: NOT RUN.** The final study is blocked on independently contributed cases
and a separately authorized provider-call/token/resource budget. This document does
not authorize live inference or modify the frozen V3 study.

## Admission gates

Before freezing the protocol, obtain cases from contributors who did not author
AECP or this protocol. Record contributor permission and provenance. Do not accept
confidential customer material without appropriate authorization. Validate candidate
files with:

```bash
python3 scripts/validate_outcome_cases.py cases.json --require-independent
```

`examples/outcome_study_cases.fixture.json` tests ingestion only. It is explicitly
project-authored and ineligible for final evaluation.

Each case must declare its observation and acceptable outcomes before any worker
answer is evaluated. Outcome classes are correct resolution, appropriate abstention,
or appropriate escalation. Evaluation additionally records incorrect action, actual
reviewer effort, simulated reviewer effort, model usage, settled modeled cost, and
uncertain liability as distinct fields.

## Freeze and budget

Freeze case hashes, policies, prompts, models, scoring code, reviewer instructions,
and the execution-order seed before the final run. The owner must then approve an
explicit maximum for provider calls, input/output tokens, reviewer sessions, and
modeled authority. Absence of that approval means zero live calls.

Use five predeclared paired repetitions per case and policy. Randomize/interleave
execution in predeclared blocks using the frozen order seed so provider-time effects
do not align with one policy. Stop after the fixed repetitions or when the approved
resource ceiling is reached, whichever comes first. A ceiling stop is reported as
incomplete; unfavorable cases are not rerun until they pass.

## Review measurement and consent

Human reviewers opt in to timing collection. Record task-open and decision-submit
timestamps, subtract declared breaks, and retain reviewer minutes separately from
any simulated tariff. Store only the minimum consented reviewer identifier. A
configured review price is a model parameter, not measured human cost.

## Reporting

Publish seed/block-level results, every failed or unresolved case, settled and
outstanding liabilities, usage, reviewer minutes, stopping reason, missing data, and
all deviations from the frozen protocol. Do not describe project-authored fixtures,
automated agents, or the owner as independent contributors.
