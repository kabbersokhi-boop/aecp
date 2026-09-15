# Deterministic economy specification

## Goal

Build a rigorous, inspectable reference economy that works with no model key. It must exercise actual decision-making, resource contention, learning, accounting, and recovery. It must not pretend that canned responses are an LLM or that a synthetic utility score is a real monetary return.

Deterministic means identical versioned inputs produce identical canonical economic events and outcomes. A seeded stochastic environment can meet this definition. It does not mean all tasks are identical or agents cannot adapt.

## Grounded workload

Use synthetic financial-operations exceptions: invoices, transfers, account mappings, duplicate entries, currency/unit mismatches, missing evidence, and deadline-sensitive discrepancies. Generate coherent records and latent facts first; expose only the allowed records to each agent. Grade a structured proposed resolution against hidden facts. Prose is explanatory metadata, never the sole correctness criterion.

There should be a cheap deterministic path for straightforward cases and genuine information/resource trade-offs for harder cases. A resource can reveal an additional noisy or accurate observation, perform a calculation, retrieve a record, or obtain optional reviewer input. Make the confidence/cost/latency trade-off explicit and configurable. Do not simply assign a random success score after an unrelated action.

Generate stable task IDs, types, deadlines, synthetic values, evidence availability, and evaluation labels. Observation objects must not contain hidden answers, latent difficulty, future outages, or outcome seeds unless that information is explicitly part of the experimental regime. Treat outcome seeds as evaluator-only. This is an API separation, not a sandbox for hostile Python.

## Small but meaningfully different policy population

Implement three or four distinct policy styles, not differently named copies:

1. A conservative policy favoring cheap evidence, low exposure, and escalation under uncertainty.
2. A value-aware policy estimating incremental task benefit per resource and remaining budget.
3. An adaptive policy updating calibrated beliefs about resource reliability by case type from allowed feedback.
4. Optionally, a deadline-sensitive policy balancing queue delay against premium cost.

A small Bayesian update, reliability estimator, or explicit uncertainty model is enough if it changes decisions and can be tested. Do not add deep RL, opaque learned weights, or a new language to manufacture sophistication. Separate capability heterogeneity from strategic objective heterogeneity. The default can use cooperative task objectives; adversarial incentives must be a named scenario.

Agents should choose among investigate, bid, cheap execution, wait, defer, and escalation. Planning, bidding, retries, and verification consume documented modeled resources. Explain each decision using structured inputs, estimated incremental benefit, policy state, constraints, and chosen action, not a fabricated chain of thought.

## Resource and market design

Start with premium-inference slots per logical tick, metered execution/compute cost, and constrained reviewer capacity. Each allocation has identity, quantity, expiry, owner, and a defined service. Premium access grants no additional spending authority.

Use one sealed-bid first-price auction for homogeneous unit slots. Rank admissible bids by price; winners pay their own bids. Resolve ties with a documented stable/fair rule, and expose any bias from that rule. Every winning bid must be funded. Escrow submitted bids or reserve their worst-case simultaneous liability so a bidder cannot reuse credits across auctions. Release losing holds. Specify delivery, expiry, outage, refund, and cancellation semantics; execution costs already incurred never disappear.

Do not name a uniform clearing price unless the mechanism actually has one. Allocation capacity and winners must agree. Task rewards transfer from treasury; they do not create operating budget. All policies share the same execution and oversight boundaries.

## Randomness and event ordering

Use semantic, versioned streams keyed by run seed plus stable coordinates. Shared exogenous variables should be keyed independently of the scheduling policy, event loop call count, global Python hash, dictionary order, and wall-clock time. Separate policy-private draws from task generation, provider behavior, and faults.

For paired comparisons, re-use exogenous task arrivals and comparable potential-outcome draws. Changed decisions still cause changed paths; describe the coupling rather than claiming identical trajectories. Avoid allocating different random draws simply because one baseline made more bids. Deterministic event ordering and tie rules must be defined and tested.

Include a canonical digest over normalized economic events, outcomes, scenario, policy version, and entropy schema. Exclude UI refresh time, filesystem paths, and process identifiers. A different seed need not guarantee a different digest in every trivial case, but sensitivity should hold over representative workloads.

## Stress scenarios

Ship named, configured scenarios for budget scarcity, demand burst, provider outage/ambiguous completion, price-schedule shock, and reviewer unavailability. Price changes affect future quotes; do not retroactively rewrite committed quotes. If a provider violates a quote, use an explicit bound-breach incident scenario.

Include an unfunded spending attempt and an identity-spawning attempt against the gateway. Malicious document content is data; the demo must not pretend to prove prompt-injection resistance without executing and evaluating an actual language-model boundary.

Add hoarding/expiry or strategic misreporting only after the basic market is correct. Label observations about synthetic agents as such.

## Evaluation

Implement equal allocation, a deadline/priority scheduler, and a centralized estimated-value-per-cost allocator with comparable information. A policy cannot get hidden truth simply because it is a baseline. An optional offline oracle must be explicitly labeled privileged and limited to tractable cases.

Run a bounded paired-seed benchmark over common workloads and several budget regimes. Report per-seed raw metrics, aggregate uncertainty, total modeled operating cost, verified utility, completion/coverage, deadline failures, prohibited actions, coordination overhead, review consumption, and credit conservation. Report real provider cash spend as zero in deterministic mode, not as the modeled operating cost.

The market is allowed to lose. Do not make the central baseline intentionally weak, choose only favorable seeds, or change task scoring between policies. Attribute synthetic assumptions clearly. A deterministic reference testbed is not empirical evidence of real LLM negotiation quality.

## Replay and recovery

A recorded replay displays persisted events without pretending to rerun agents. A deterministic rerun recomputes decisions from versioned inputs. A changed-policy counterfactual executes a new run. Restart/resume must preserve learning state, logical queue, market escrow, and unresolved execution liabilities; test against an uninterrupted reference run.
