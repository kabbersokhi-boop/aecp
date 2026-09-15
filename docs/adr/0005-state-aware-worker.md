# ADR 0005: state-aware interpretation and evidence-backed V3

Status: implementation in progress. Starting commit:
`0574137da429af9985f84bd964bcda1bc2ffe2b5`.

The V2.1 corpus, policy and evidence remain historical. V3 uses a new versioned
36-case development corpus and a separate 36-case held-out corpus, committed before
worker tuning. Composition crosses payment topology and evidence access, with
independent language, references, entities, noise, document ordering and injection
draws. This is still an authored synthetic generator, not independent human data.

The model will interpret payment linkage, not invent workflow actions. The trusted
controller already knows which evidence sources exist, what has been retrieved,
whether approval is mandatory, and which payment/document identities are visible.
These facts will condition a closed interpretation schema. The consumer chooses
resource purchases using only public state; AECP independently authorizes every
purchase. Interpretation confidence is not permission or evaluator truth.

Compare rules, rules plus modeled reviewer, always-model, selective-model and
selective-model plus modeled reviewer. Do not call simulated reviewer results human
validation. Freeze policy, prompt and schema construction before live evaluation;
unfavorable results do not justify retuning or rerunning the holdout.

Performance changes must target measured gateway serialization, not replace SQLite
without evidence. Preserve a global pre-authentication connection bound; evaluate
authenticated principal caps separately from protection against raw socket abuse.
Economic extensions must price central reporting and preserve the V2.1 study.

Public history audit is a gate, not permission to rewrite historical commits or
infer an owner's license choice. Actual external-human validation remains a human
dependency. The branch remains private and must not be self-merged.
