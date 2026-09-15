# Contributing

Read `AGENTS.md`, the architecture, and the acceptance contract before changing economic or authorization behavior. Keep implementation claims proportional to evidence.

Changes should include tests for failure and negative cases, migration behavior when relevant, updated examples, and documentation of material assumptions. Run the current verification commands from the README. Do not introduce network calls into deterministic tests.

Accounting changes require independent checks of commitments, settlement, idempotency, integer units, and conservation. Economic changes require baseline fairness and a clear statement of observable versus hidden information. UI changes must use the same persisted state as the backend.

Use coherent commits and a reviewable work branch. Do not reformat unrelated files, force-push, commit secrets, change visibility, or publish a release as a side effect of implementing a feature.
