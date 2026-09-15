"""Create a private, history-free publication candidate; never publish or rewrite the source repository."""

import argparse
import gzip
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

from public_audit import PATTERNS, SECRET_CATEGORIES

SAFE_EMAIL_FIXTURES = {b"LOGIN@users.noreply.github.com", b"integrate.api.nvidia.com@attacker.example",
                      b"git@github.com"}


def sanitize(name: str, data: bytes) -> tuple[bytes, dict | None]:
    compressed = data.startswith(b"\x1f\x8b")
    payload = gzip.decompress(data) if compressed else data
    if payload.startswith(b"SQLite format 3\x00"):
        raise ValueError("refusing database in publication candidate")
    for category in SECRET_CATEGORIES & PATTERNS.keys():
        if PATTERNS[category].search(payload):
            raise ValueError("credential-shaped content requires private review: " + name)
    if any(match.group() not in SAFE_EMAIL_FIXTURES for match in PATTERNS["email_address"].finditer(payload)):
        raise ValueError("unreviewed email-like content: " + name)
    count = len(PATTERNS["personal_home_path"].findall(payload))
    if not count:
        return data, None
    if not name.startswith("docs/reports/") or not name.endswith((".txt", ".md", ".json", ".json.gz")):
        raise ValueError("personal path outside report requires source correction: " + name)
    corrected = PATTERNS["personal_home_path"].sub(b"/workspace/", payload)
    output = gzip.compress(corrected, mtime=0) if compressed else corrected
    return output, {"path": name, "kind": "personal home-prefix redaction", "count": count,
                    "original_sha256": hashlib.sha256(data).hexdigest(),
                    "publication_sha256": hashlib.sha256(output).hexdigest()}


def snapshot(output: Path, reference: str = "HEAD") -> dict:
    if output.exists():
        raise ValueError("refusing to overwrite publication candidate")
    revision = subprocess.check_output(["git", "rev-parse", "--verify", reference + "^{commit}"], text=True).strip()
    entries = subprocess.check_output(["git", "ls-tree", "-rz", "--full-tree", revision]).split(b"\0")
    files = {}
    redactions = []
    for entry in entries:
        if not entry:
            continue
        metadata, encoded_name = entry.split(b"\t", 1)
        mode, kind, identity = metadata.decode().split()
        name = encoded_name.decode()
        if kind != "blob" or mode not in {"100644", "100755"} or name.startswith("/") or ".." in Path(name).parts:
            raise ValueError("unsupported publication entry")
        data = subprocess.check_output(["git", "cat-file", "blob", identity])
        transformed, redaction = sanitize(name, data)
        files[name] = (transformed, int(mode, 8) & 0o777)
        if redaction:
            redactions.append(redaction)
    manifest = {"version": "sanitized-publication-candidate.v1", "private_source_commit": revision,
                "includes_git_history": False, "published": False, "redactions": redactions,
                "files": {name: hashlib.sha256(data).hexdigest() for name, (data, _) in sorted(files.items())},
                "notice": "Privacy-redacted copy. Original private history and evidence remain unchanged. "
                          "Redacted files have distinct hashes; this is not a byte-identical historical archive."}
    files["PUBLICATION_MANIFEST.json"] = ((json.dumps(manifest, indent=2) + "\n").encode(), 0o644)
    output.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, (data, mode) in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = mode
            info.mtime = 0
            archive.addfile(info, io.BytesIO(data))
    output.write_bytes(gzip.compress(buffer.getvalue(), mtime=0))
    return {"source_commit": revision, "files": len(files), "redacted_files": len(redactions),
            "archive_sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "published": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ref", default="HEAD")
    arguments = parser.parse_args()
    print(json.dumps(snapshot(arguments.output, arguments.ref)))
