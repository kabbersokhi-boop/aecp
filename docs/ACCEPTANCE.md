# First-build acceptance contract

Report each ID as PASS, FAIL, or NOT RUN with a command, test, or artifact. A file existing does not make a capability pass. Foundation-only checks do not establish the complete milestone.

## Essential vertical slice

| ID | Observable acceptance condition |
| --- | --- |
| A01 | A fresh documented setup runs a deterministic economic scenario and opens a working dashboard with no provider key or runtime network dependency. |
| A02 | A task causes a real policy decision, resource request, funded allocation, execution, trusted settlement, and ground-truth-scored outcome; the UI can trace this chain. |
| A03 | Integer operating-cost reservations cover outstanding attempts; concurrent requests cannot reuse budget; unresolved attempts survive restart. |
| A04 | Parent caps cover aggregate descendant commitments; spawning a child or racing two children does not create authority. |
| A05 | Market credit debits/credits balance; bid escrow prevents oversubscription across auctions; winners, payments, capacity, expiry, and refunds match the documented mechanism. |
| A06 | Agent, admin, reviewer, and adapter permissions are separated; spoofed IDs, self-funding, self-settlement, and self-approval are rejected. |
| A07 | Mandatory approval is bound to the exact action and expires; an absent reviewer blocks the action, regardless of market wealth. |
| A08 | At least three nontrivial policies operate on partial observations; behavior changes under a tested capability, budget, uncertainty, or deadline intervention. |
| A09 | Same versioned config/seed yields the same canonical economic digest in separate processes; resume matches uninterrupted execution; no hidden labels reach policy observations. |
| A10 | Multiple policies/baselines run against common task distributions/seeds; all runtime coordination costs are counted and raw per-seed results are retained. |
| A11 | Dashboard displays backend-backed budgets, unresolved exposure, agent activity, market allocations, approval queue, transaction evidence, and a comparison view with clear units/modes. |
| A12 | Standalone passive and budget-aware example agents interact with the running gateway without database access or changes to core code. |
| A13 | Fault scenarios exercise outage/ambiguous completion, exhausted review capacity, and demand/budget stress; safe behavior and lost utility are both reported. |
| A14 | Unit/integration/failure tests, lint/type checks where configured, backend/frontend builds, and a bounded benchmark run are executed; failed or unavailable checks are disclosed. |
| A15 | No unsupported live-cost, real-LLM, production, security, economic-optimality, or certification claims; no committed secrets or fabricated evidence. |
| A16 | A complete build report maps these IDs to evidence, records meaningful design deviations, lists exact run commands, and names the source checkpoint/commit. |

## Stop conditions and priority

Work through the full milestone. Resolve substantive accounting and authorization defects before adding optional features. Do not stop after the reference kernel or an attractive UI mockup.

If an actual environment or execution limit prevents full completion, preserve the deepest runnable path in this order: accounting and deterministic end-to-end execution; usable dashboard and native client boundary; markets and oversight; fair benchmark/recovery evidence; optional adapters. Report any missing essential IDs honestly. Do not evade the milestone by marking requirements out of scope without explanation.

## Extensions only after essentials

An OpenAI-compatible adapter route, live/local provider adapter, formal state model, richer economic mechanisms, sensitivity studies, and more dashboards can follow when essentials are passing. Do not create empty modules, disabled buttons, or fake samples merely to claim these exist.
