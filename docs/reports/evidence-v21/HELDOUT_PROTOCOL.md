# Frozen semantic evaluation protocol — before live evaluation

This protocol is committed before the first held-out execution. The corpus was
already frozen at commit `510fe50`, before worker development. Twelve held-out cases:
full SHA-256 `1ba8a9d152970ded5cf42fc5a8b883166f83ea6f7eb5638ef04e515c9f4fcdbc`.
Development cases were used for rule/parser/protocol debugging. These are authored
synthetic templates, not external, blinded, naturally sampled bank documents.

Three scoped namespace-isolated consumers run in the fixed order deterministic-only,
always-LLM, selective. Each gets the same corpus order and 4,000 modeled operating
units under one funded 12,000-unit root. Each has two optional modeled consultations,
costing 600 units, and an eight-action task deadline. Each task may buy at most two
model calls. The whole runner has a hard cap of 32 chat attempts. No implicit retry
is allowed; denial or unresolved execution stops that task. Fixed sequential policy
order is a threat to live comparability, not randomized replication.

Selected model: `nvidia/nemotron-3.5-lightning-30b-a3b`, validated in the prior live
catalog/probes and the V2.1 one-call strict-schema probe. Request: hosted NVIDIA
`/v1/chat/completions`, temperature zero, maximum output 256 tokens, closed JSON schema
`semantic_action_v21`. Independent server validation is retained. Quote provenance
binds model, messages and schema. The frozen worker is
`semantic-consumer.v2.1.frozen-1`; system prompt `semantic-worker.v2.1.initial`.

The deterministic baseline recognizes explicit invoice references, allocation,
installment and returned/replacement patterns developed on the development corpus;
it fetches remittance when available and buys scarce consultation when rules fail.
All arithmetic is deterministic. Always-LLM purchases interpretation for every
autonomously resolvable case. Selective uses deterministic evidence first, fetching
missing evidence before inference; its heuristic assumes a 50% potential value gain,
compares half task value with 600 units and requires 1,000 headroom. These are declared
heuristic assumptions, not fitted/calibrated probabilities. Mandatory cases escalate;
unrecoverably missing evidence abstains in every policy. Neither receives verified
task value merely for escalating or abstaining.

Primary outcomes: independently verified allocation/value and modeled spend.
Also retain schema validity, separate payment linking and arithmetic correctness,
fetches, consultations, abstentions, escalations, inappropriate confident actions,
unfinished cases, denials, provider tokens and unresolved exposure. Initial deterministic
links followed by inference are separately counted as potentially unnecessary calls.
Actual cash spend is declared zero for prototype access, not a provider invoice.

One final run is allowed. Do not inspect held-out failures and retune rules/prompt/schema
to improve the same evaluation. An implementation failure may invalidate a run only
with a recorded concrete defect and preserved original artifacts; unfavourable schema
or semantic model results are NOT invalidation reasons. A provider outage/timeout
remains a result with liability retained, not permission to try until it passes.

Offline development runner attempt one found a missing `base_url` on the transport
wrapper (zero provider attempts). Attempt two fixed the protocol and executed eight
fake schema-valid receipts. Those fixture outputs are not live model quality evidence.
No held-out evaluation or additional live call occurred during runner development.
