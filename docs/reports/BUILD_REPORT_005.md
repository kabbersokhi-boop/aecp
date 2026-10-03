# Build report 005: publish the recorded portfolio story

## Summary and source checkpoint

The owner explicitly requested adding the finished video to GitHub, explaining
the steps in pointers, updating screenshots and telling a story. This update
publishes the existing privacy-reviewed edit; it does not rerun the experiment
or change the application's economic, authorization or provider behavior.

- Branch: `portfolio/aecp-demo-story`; existing PR #3 remains open, not self-merged.
- Starting implementation: `4482f0b9ecde9104a6905823f59bebe9f4b41bc1`.
- Media checkpoint: `393dd3ee463b5cfe84f83b71253f7d4d4f1b8527`.
- Documentation checkpoint: resolve with `git log -1 --format=%H -- docs/reports/BUILD_REPORT_005.md`.
- [ADR 0007](../adr/0007-owner-requested-demo-media.md) records the owner-authorized
  exception to keeping large demo artifacts outside Git. Raw recordings and
  credentials remain unpublished.

## Acceptance and presentation

| Requested change | Result | Evidence |
| --- | --- | --- |
| Add the main video to GitHub | PASS in work branch | `docs/assets/portfolio/AECP-Portfolio-Demo.mp4`; same SHA-256 as delivered edit |
| Explain steps in pointers | PASS | Six timestamped README bullets matched to the chapter map |
| Update screenshots | PASS | Exact final-video frames at 0:32 and 1:52 replace the earlier native captures |
| Tell the business story | PASS | Bounded mandate → useful work → authority limits → uncertainty → evidence-based recovery |
| Avoid overstating scope | PASS | Local request vs independent fault fixture labels, modeled units, no hosted calls or real payments |
| Keep video links stable | PASS | Download URLs pin the media commit; relative preview/image links follow the viewed branch |

Foundation A01–A16 were not re-executed for this documentation/media-only update.
The full implementation verification remains in [build report 004](BUILD_REPORT_004.md).
No new claim about production readiness, commercial billing, human approval,
outside adoption or exactly-once external effects is introduced.

## Verification actually run

- `sha256sum docs/assets/portfolio/AECP-Portfolio-Demo.mp4`: matches the delivered
  edit, `024ac20400b1d3254a515accc496c2b49a8790fa96ff62f3a30da3f2e247c899`.
- `ffprobe` on the MP4: H.264, 1920×1080, 30 fps, 189.233008 seconds,
  8,660,957 bytes; no audio stream, with embedded chapter metadata.
- `ffmpeg -hide_banner -loglevel error -i docs/assets/portfolio/AECP-Portfolio-Demo.mp4 -map 0:v:0 -f null -`:
  full video decode completed without reported errors.
- Preview `ffprobe`: 720×405, nine seconds, 416,849 bytes. It samples final-video
  intervals 0:28–0:31, 1:50–1:53 and 2:38–2:41 at six frames per second.
- Screenshot extraction: FFmpeg single-frame reads at 32 and 112 seconds from the
  published MP4. Both frames were visually inspected for legibility, correct
  accounting facts, scenario labels and absence of credentials/personal screens.
- `npm run check`: JavaScript syntax and two presentation tests PASS.
- `uv run --locked ruff check .`: PASS.
- `git diff --check`: PASS before publication.

## Story and remaining boundary

The opening is a plain-English business problem, followed immediately by an
animated preview and one full-video link. Short pointers guide viewers through
useful work and then the failure boundary. Only two focused screenshots appear
in the README; the reproduction guide carries the additional detail. The existing
unfavorable research results and historical live evidence remain intact.

The published response-loss frame has provider fixture charge 3 but AECP reserved
liability 4. The quote-breach fixture has actual charge 7 and FROZEN status while
headroom remains positive at 5; the guide explicitly distinguishes that from a
funding breach. A failed connection is not treated as a free request.

Public readback and the latest PR's CI status are checked after pushing. No
website deployment, release creation, hosted inference or automatic merge is
performed. The default-branch README changes only after the PR is merged.
