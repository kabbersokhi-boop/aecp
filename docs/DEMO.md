# 5–7 minute offline interview demonstration

This path runs entirely from the public repository. It requires no provider
credentials and makes no NVIDIA, hosted-model, or other external inference calls.
It demonstrates the control plane with deterministic resources and simulated
external uncertainty; frozen live evidence is inspected, not rerun.

## Prepare

```bash
make demo
make serve
```

Open `http://127.0.0.1:8765` and paste `operator.token` from
`var/local-capabilities.json`. Keep that local file off-screen: it contains several
demo capabilities and is ignored by Git.

## 0:00–1:00 — problem and architecture

Start with the question: **How much useful autonomy can a fixed resource budget
safely purchase?**

Explain the boundary: an agent proposes an action using a scoped AECP credential;
AECP checks authority and policy, reserves the maximum liability, mediates the
provider/tool call, settles or retains uncertainty, and writes provenance. Provider
credentials stay at the trusted adapter boundary. The agent is never its own bank,
approver, or settlement authority.

## 1:00–2:00 — connect an existing agent

Show `examples/openai_consumer.py` and `docs/INTEGRATION.md`. An OpenAI-compatible
client changes its base URL to AECP and uses a scoped AECP token. The operator has
already registered the task and allowed operation class. Unknown or unauthorized
tasks fail closed.

## 2:00–4:00 — successful and uncertain execution

In **Overview**, select the `ordinary` run created by `make demo`:

1. Show funded authority and the trace for a verified case.
2. Follow task → proposal → authorization → reservation → dispatch → receipt →
   settlement → independently verified outcome.
3. Point out that reservation precedes the controlled external operation.

Switch to the `outage` run:

1. Select an **UNRESOLVED** trace.
2. Show that the attempt was dispatched but its external result is ambiguous.
3. Confirm the upper-bound liability remains reserved after the run completes; it
   is not released as if the failed connection proved a free operation.

For a public-API denial using a scoped agent, run this separately while the server
is up:

```bash
PYTHONPATH=src python3 scripts/integration_smoke.py \
  --url http://127.0.0.1:8765 --tokens var/local-capabilities.json
```

The harness retains operator authority while example subprocesses receive only
their own agent capabilities. It exercises allowed work and denied overspend/
unauthorized behavior without provider calls.

## 4:00–5:00 — economic result

Open `docs/RESULTS.md` or `docs/reports/BUILD_REPORT_003.md` and show the frozen V3
result: **6 / 12 / 9 / 11 / 15** verified cases for rules-only, rules+reviewer,
always-LLM, selective-LLM, and selective+reviewer.

The correct reading is:

- selective inference added coverage;
- rules remained cheaper per verified value;
- selective+reviewer had the highest verified coverage in this experiment;
- eight provider timeout/connection uncertainties retained 5,604 modeled units;
- this does not establish universal LLM superiority.

## 5:00–6:00 — intelligence is not authority

Return to one trace and distinguish the untrusted proposal from deterministic
authorization, reservation, dispatch, and settlement. Explain that a valid model
response can still earn no verified value, while a timeout can still consume
authority. Safety accounting follows possible external effects, not model intent.

## 6:00–7:00 — markets were allowed to lose

Open the allocation comparison in `docs/RESULTS.md`. Private information can help,
but bid and coordination costs can erase that gain. In the tested synthetic market,
the stronger shared-information central allocator often won. This is an experimental
result, not a claim that markets or central allocation are universally superior.

Finish with the limitations: synthetic tasks, one live replication, modeled—not
commercial—inference costs, and no outside-human adoption validation.

## Optional verification before an interview

```bash
make check
make property
uv build
npm ci && npm run check
```

On Linux with Bubblewrap, `make isolation` exercises a wheel-installed consumer,
scoped API, budget denial, and fake-provider ambiguity without source-tree imports
or provider access. The frozen V3 recomputation is covered by
`tests/test_semantic_evidence.py`; it decompresses the committed artifacts into a
temporary directory and performs no provider calls.

## Owner practice exercises

Codex executed these exercises during the failure-conformance build. That verifies
the path, not the owner's mastery; the owner should answer aloud without reading a
script.

### 1. Explain a successful transaction

Run `make demo`, open the `ordinary` run, and select a verified case. Explain the
actual task, principal, operation class, quote, `SIM_COST_MICRO` upper bound,
reservation, dispatch, receipt actual, released headroom, settlement, and verified
outcome. Then locate the implementation: authorization/quote binding in
`src/aecp/control.py:175`, dispatch and receipt handling in
`src/aecp/control.py:227`, reservation in `src/aecp/ledger.py:213`, and settlement
in `src/aecp/ledger.py:298`.

Questions: Which value is authority rather than money? Why is reservation visible
before the adapter runs? Which stored identity makes a duplicate immutable? Answers:
the integer `SIM_COST_MICRO` balance is modeled authority; pre-dispatch reservation
prevents overlapping commitments; request ID plus the request/quote fingerprint
binds the attempt.

### 2. Diagnose uncertain execution

Open an `UNRESOLVED` case in the `outage` run. AECP knows dispatch was durably
claimed and the upper bound remains outstanding. It does not know whether the
external effect occurred or its final charge. A valid durable receipt permits
settlement; independently validated provider evidence of no execution permits
`reconcile_no_charge` at `src/aecp/ledger.py:332`. A timeout or lease expiry is not
that evidence. A fresh possibly billable retry needs a distinct ID and reservation.

Questions: Why not refund after 300 seconds? Can the agent reconcile itself? Why
does a retry consume more headroom? Answers: elapsed time says nothing about provider
billing; reconciliation is trusted authority, not an agent API; both attempts may
have external charges.

### 3. Make a disposable defect

In a detached temporary worktree, change `ControlPlaneError.code` in
`src/aecp/client.py:10` to a wrong constant. Run:

```bash
PYTHONPATH=src python3 -m unittest tests/test_external_challenge.py -v
```

The typed-denial regression must fail. Discard the temporary worktree, then run the
same test on the research branch and confirm it passes. Never commit the defect or
weaken the assertion.
