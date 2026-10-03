# ADR 0007: recorded demonstration assets

Status: implemented.

The demonstration assets are committed alongside the walkthrough so readers can
inspect the complete journey without running a local instance. The assets consist
of an 8.3 MiB MP4, a 408 KiB preview and two screenshots. Credentials and runtime
databases are not demonstration assets and must never be committed.

Screenshots are exact frames at 0:32 and 1:52 of the recording, not generated mockups. A nine-second
preview samples settlement, response loss and trusted reconciliation, with the
same visible provenance labels as the full video.

Media lives in `docs/assets/portfolio`. README download links use the immutable
media commit rather than a disposable branch name.
No runtime, economic, provider or authorization behavior changes.
