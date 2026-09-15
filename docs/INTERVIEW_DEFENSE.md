# Engineering defense: what the implementation actually guarantees

## V3 controller and evidence distinctions

**What is autonomous?** The separate consumer runs a bounded observation/action
loop. Deterministic code checks references, purchases available evidence, decides
whether a semantic call or optional consultation is affordable and worthwhile, and
finalizes, escalates or abstains. The model interprets visible documents; it does not
choose arbitrary task IDs, create resources or perform authoritative arithmetic.
Recoverable source/capacity denials remove choices; authority denials stop rather
than triggering attempts to evade policy.

**Did the model earn its cost?** It bought incremental coverage, not universal
cost efficiency. Selective inference verifies 11/36 versus rules-only's 6/36;
selective+reviewer reaches 15/36 versus rules+reviewer's 12/36 with the same six
consultations. Rules remain cheapest per verified value, and eight live timeouts
retain their liabilities. The controller's priors are declared assumptions, not
calibrated probabilities. V2.1's negative result is unchanged. V3 used a new frozen
holdout once; sequential provider variability limits causal quality comparisons.

**Is central reporting free?** Not in the V3 reporting study. Central can purchase
a subset of current reports under explicit costs before observing their contents.
That decision uses a public prior and approximate future demand, not hidden future
outcomes. Selective reporting wins or ties twelve of eighteen tested cell means;
the private market wins none. A matched private-request rotation control separates
the auction package from differing fallback resource policies. This is a bounded
synthetic finding, not a theorem about markets or strategic equilibrium.

**What does fairness guarantee?** Authenticated agents have concurrent-request
caps in addition to global bounded admission. In the measured noisy-agent test,
each of three steady agents completed 75/75 requests. Raw socket admission happens
before identity is known, so this is not Internet denial-of-service protection.

## Preserved execution guarantees

1. **Why reserve again for a retry?** A timeout may have followed a successful remote
   execution. A new attempt creates a second possible liability. Reusing the same
   request ID returns the existing state; it does not authorize another provider call.
2. **Death between execution and settlement:** `ControlPlane.execute` persists a
   receipt before settlement. Reopen and execute can settle that receipt without a
   provider adapter. If death loses the receipt, the dispatch becomes unresolved.
   The live demonstration kills real subprocesses at both boundaries.
3. **Timeout is not no charge.** Expiry releases only undispatched reservations.
   Dispatched/unknown holds survive. Only trusted evidence supports no-charge
   reconciliation. HTTP 429/5xx are conservatively uncertain here, not refund signals.
4. **Credits are not authority.** Market balances and operating scopes have different
   units. Winning a bid cannot fund a provider reservation or multiply root funding.
5. **Why central won V1:** agents largely shared the same useful information; auctions
   added bidding overhead. That result is not tuned away. Central also now models
   mandatory-review capacity explicitly in its planning state.
6. **When might markets help?** Private signals can convey information through bids.
   Compare private-market with public-central *and* shared-signal-central. A gain over
   the former alone cannot establish that prices beat centralized information sharing.
7. **The dashboard is not authoritative.** It reads persisted requests, holds,
   receipts and events. Editing JavaScript or a displayed balance grants nothing.
   Provider snapshots use one transaction so their records share a consistent view.
8. **Hard-budget assumptions:** trusted code, filesystem and operator credentials;
   transactional SQLite; every expensive action routed through the boundary; adapter
   upper bounds valid. This is not a sandbox for hostile code with database access.
9. **A provider exceeds its quote:** record actual usage/cost, do not clip the receipt;
   freeze affected authority and retain a bound-breach incident. A violated adapter
   assumption cannot truthfully be repaired by pretending the invoice was smaller.
10. **Prompt injection cannot grant authority.** Task identity comes from authenticated
    request metadata, not model text. Unknown tasks, changed operations, self-approval,
    model switches and unfunded requests fail outside the prompt. Tests deliberately
    make a fake model comply with malicious text: denial does not rely on refusal.
11. **Replay is not replication.** Reading a stored receipt reproduces recorded facts.
    Deterministic re-execution requires the same controlled configuration. Calling a
    model again is fresh execution, incurs new exposure, and may vary.
12. **SQLite:** atomic durable local accounting and restart recovery with WAL/FULL.
    It serializes writers, does not provide distributed authorization or hosted
    multitenancy, and its tail latency depends on filesystem and concurrency.
13. **Facts versus assumptions:** provider-reported tokens and measured latency are
    observations. Utility is synthetic hidden-bank scoring. NIM modeled cost is
    `ceil(canonical_message_bytes/16) + 2 * output_tokens`; the upper bound substitutes
    authorized `max_tokens`. It is neither a tokenization bound nor a dollar invoice.
    Actual cash is declared zero for this free prototype access, not verified billing.

The strongest honest story is not “markets win” or “LLMs solve finance.” It is that
untrusted decisions can be measured, denied, recovered and criticized without giving
the agent accounting authority. The live sample remains too small and too synthetic
to establish model quality or real-world economic value.

## V2.1 questions to defend with actual evidence

**What is autonomous?** The independent consumer runs a bounded action loop rather
than one prompt-to-answer call. It checks references, buys an attachment or inference,
acts on a model's proposed next step, consults, abstains, escalates or finalizes.
Deterministic gates decide whether that action is permitted and funded. Initial
selective purchasing uses a transparent heuristic, not learned/calibrated value.

**Why not just Python?** For arithmetic and explicit allocation patterns, use Python.
Narrative linking can require semantic interpretation, but that does not establish
an LLM advantage. Our held-out model repeatedly asked to retrieve evidence already
visible or unavailable. No-LLM resolved six cases (two with modeled consultation),
selective four and always-LLM zero. We cannot claim model-added economic usefulness.
The next policy must earn that claim on a new frozen corpus, not a retuned old test.

**When should the agent buy inference?** Only when the expected improvement exceeds
its cost and alternatives, subject to authority and deadline. Our selective rule
uses half task value versus 600 units and at least 1000 headroom. Those assumptions
were frozen, not empirically calibrated. Their failure is visible: five calls cost
resources without improving verified value beyond deterministic resolutions.

**What if the model hallucinates or follows malicious documents?** Valid JSON is not
permission or truth. Eight unavailable-source proposals were denied; redundant
fetches did not become verified outcomes. A model cannot change the authenticated
agent, operation-bound task policy, reviewer decision, quote or settlement receipt.
The namespace consumer lacks the key/database and cannot reach external networks.
We test authority denial, not whether the model politely refuses an injected instruction.

**Why private-no-market and paced central?** Private market originally had both
better information and different local fallback choices. The rotating private
control shares those local signals/rules without auction payments. Paced central
values remaining budget using a public future-demand prior. Private market does not
beat paced shared central in any of 45 cell means. Ranking sometimes improves on
rotation, but that contrast includes prices, credit limits and overhead together;
it does not prove a causal benefit from prices alone. Shared central assumes honest
direct reporting; that assumption is not an incentive-compatibility result.

**What does NIM cost mean?** Integer modeled input-byte/output-allowance units,
including the closed schema in structured request size. Provider tokens are observed
separately. Free access cash is declared zero, not verified from an invoice. The
offline billing contract can represent token/non-token prices and invoice status,
but no commercial adapter with validated dollar bounds has been executed.

**Can the agent steal credentials?** Not through the demonstrated Bubblewrap mount,
PID and network namespace: only its token and a fixed-destination gateway socket
are exposed. Same-user agents launched outside that boundary remain unsandboxed.
The trusted host/kernel and server are in the threat model; kernel exploits and
multi-tenant hostile Internet hosting are not covered.

**What happens under overload?** Admission bounds connection threads before financial
authorization; overload returns 503. Existing admitted handlers may wait on the
mutation lock, so bounded is not the same as fair. At 80 offered/s, 232/1200 completed
in 15 seconds and 968 were refused, with no unresolved leftovers. Recovery completed
all requests. SQLite acquisition p99 was 0.106 ms versus mutation-lock wait 204.17 ms:
replacing SQLite would not fix that dominant serialization bottleneck by itself.
