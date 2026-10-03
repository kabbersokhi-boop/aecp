# ADR 0007: owner-requested public demo media

Status: implemented after explicit owner authorization to add the video to GitHub.

The review protocol normally keeps large artifacts outside Git. The owner has
now specifically requested publication of the completed demo video alongside its
story, short steps and refreshed screenshots. This is a narrow exception for the
8.3 MiB edited MP4 and a 408 KiB preview, not authorization to publish raw recordings,
capabilities, local databases, account pages or provider keys.

The video bytes match the previously delivered privacy-reviewed file. Screenshots
are exact frames at 0:32 and 1:52 of that same edit, not generated mockups. A nine-second
preview samples settlement, response loss and trusted reconciliation, with the
same visible provenance labels as the full video.

Media lives in `docs/assets/portfolio`. README download links use the immutable
media commit rather than a disposable branch name. Updates remain on the existing
work branch and PR; publication of these assets does not authorize self-merging.
No runtime, economic, provider or authorization behavior changes.
