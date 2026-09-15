# V3 final semantic evaluation protocol

The 36-case corpus was frozen at `896af82`, the final protocol at `ebd42a9`, and
the single live run is complete. [Results](RESULTS.md) preserves all five outcomes
and eight uncertain attempts. The procedure below documents how that run was
frozen; do not repeat it or retune on the now-inspected holdout. Historical V2.1
outcomes are not the new test set and must not be relabeled.

Before a final run:

1. Complete development-only model/catalog and structured-schema compatibility
   probes. Preserve failures and exact request/token counts. Select a working model
   on that evidence, not on held-out outcomes.
2. Finish development policy, prompt, schema and evaluator review. Commit all code.
3. Create a protocol using the selected model and actual trusted endpoint:

```bash
PYTHONPATH=src python3 scripts/semantic_protocol.py --model "$AECP_NIM_MODEL" \
  --output docs/reports/evidence-v3/final-semantic-protocol.json
git add docs/reports/evidence-v3/final-semantic-protocol.json
git commit -m 'Freeze final V3 semantic evaluation protocol'
```

If using a nondefault endpoint, pass `--base-url` when freezing and set the matching
`AECP_NIM_BASE_URL` in the trusted runtime. The adapter independently restricts
endpoint safety. Never place a key in the protocol or command arguments.

4. From the clean reviewed worktree, with the provider credential only in the
   trusted environment, execute once:

```bash
AECP_ENABLE_LIVE_NIM=1 PYTHONPATH=src python3 scripts/semantic_validate.py \
  --workload v3 --live --model "$AECP_NIM_MODEL" \
  --protocol docs/reports/evidence-v3/final-semantic-protocol.json \
  --output var/evidence-v3/final-semantic-live.json
```

The guard verifies the committed protocol, held-out identity, tracked core/worker/
harness hashes, model, endpoint and 60-call maximum. It writes an exclusive local
`.started` marker next to the protocol before consumer execution. A different output
filename does not permit a second run. Retain the marker and partial database after
failure; do not delete them to obtain more favorable results. A genuine invalidating
implementation defect requires a separate reviewed amendment preserving the original
attempt. Poor model quality is not such a defect.

The marker is a procedural guard against accidental reruns, not protection against
an operator modifying files, copying the repository or changing running code. Git
history and provider journals remain necessary evidence. The guard does not certify
model quality, freshness of model selection, calibration or absence of human test-set
inspection. Those claims require the recorded review and experiment evidence.

Offline development execution is unchanged, requires no freeze and does not access
the held-out split. Fake transport token counts are fixture values, not provider use.
