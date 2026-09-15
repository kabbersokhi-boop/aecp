# Public snapshot policy

This public source repository is a sanitized, history-free snapshot derived from a
separate private engineering repository. The private repository, its development
history, pull requests, and local runtime artifacts remain private and unchanged.

The snapshot exporter reads only committed files from the recorded source revision.
It excludes `.git`, untracked/runtime files, SQLite databases, provider credentials,
private keys, capability tokens, and unreviewed personal paths or email-like values.
One historical verification report required a publication-copy-only home-prefix
redaction; its original and public hashes are recorded in
`PUBLICATION_MANIFEST.json`. Frozen numerical evidence was not rewritten.

The manifest records the private source commit, every exported file hash, explicit
redactions, and public-copy presentation changes. This is privacy minimization, not
anonymous publication: the project owner and public repository identity are visible.

Publication used zero provider/catalog/chat calls and did not rerun the frozen live
experiment. Review [PUBLIC_PROVENANCE.md](../PUBLIC_PROVENANCE.md) for the release
checkpoint and limitations.

Licensing is [PolyForm Noncommercial 1.0.0](../LICENSE). This is a public
source-available repository, not permissively licensed OSI open-source software.
