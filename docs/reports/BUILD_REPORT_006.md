# Documentation review: public demonstration copy

## Scope and source

Base revision: `5779f01ca0e40bc01667d2fa6174679cc9b8b9d8`.
Branch: `docs/public-demo-copy`.

The README and demonstration guides now focus on the business problem, observed
behavior and reproduction steps. Voiceover preparation, personal coaching and
publication-process commentary were removed. ADR 0007 describes the asset
storage decision without personal instructions.

No application code, media, experimental results or security boundaries changed.
The synthetic scenarios, modeled costs, absence of hosted calls and limits of
the reference implementation remain explicit. Historical engineering reports
remain provenance rather than current setup instructions.

## Verification

- `npm run check`: JavaScript syntax checks and both presentation tests passed.
- `uv run --locked ruff check .`: passed.
- `git diff --check`: passed.

Foundation acceptance A01–A16, backend tests and browser execution were not
rerun for this prose-only change. Implementation evidence remains in
[report 004](BUILD_REPORT_004.md); media evidence remains in
[report 005](BUILD_REPORT_005.md).
