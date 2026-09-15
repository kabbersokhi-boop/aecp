"""Review reachable history for public-exposure risks without printing matched values."""

import argparse
import gzip
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path

PATTERNS = {
    "provider_secret": re.compile(rb"nvapi-[A-Za-z0-9_-]{20,}"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    "literal_bearer": re.compile(rb"Bearer [A-Za-z0-9_-]{28,}"),
    "literal_capability": re.compile(rb'"token"\s*:\s*"[A-Za-z0-9_-]{32,}"'),
    "personal_home_path": re.compile(rb"/(?:home|Users)/[A-Za-z0-9_.-]+(?:/|\b)"),
    "email_address": re.compile(rb"[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
}
SECRET_CATEGORIES = {"provider_secret", "private_key", "literal_bearer", "literal_capability", "runtime_secret"}


def audit() -> dict:
    findings = []
    checked = 0
    secret = os.environ.get("NVIDIA_API_KEY", "").encode()

    def inspect(label, payload, *, history=False):
        nonlocal checked
        checked += 1
        if payload.startswith(b"\x1f\x8b"):
            payload = gzip.decompress(payload)
        categories = {name for name, pattern in PATTERNS.items() if pattern.search(payload)}
        if secret and secret in payload:
            categories.add("runtime_secret")
        if payload.startswith(b"SQLite format 3\x00"):
            categories.add("tracked_database")
        if categories:
            findings.append({"location": label, "historical": history, "categories": sorted(categories)})

    tracked = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    for name in tracked:
        if name and Path(name).is_file():
            inspect(name, Path(name).read_bytes())
    entries = subprocess.check_output(["git", "rev-list", "--objects", "--all"]).decode().splitlines()
    entries += subprocess.check_output(
        ["git", "for-each-ref", "--format=%(objectname)", "refs/tags"]).decode().splitlines()
    inspected = set()
    for entry in entries:
        identity, _, name = entry.partition(" ")
        if identity in inspected:
            continue
        inspected.add(identity)
        kind = subprocess.check_output(["git", "cat-file", "-t", identity]).strip()
        if kind in {b"blob", b"commit", b"tag"}:
            inspect("history:" + (name or identity[:12]),
                    subprocess.check_output(["git", "cat-file", kind.decode(), identity]), history=True)
    counts = Counter(category for row in findings for category in row["categories"])
    return {"version": "public-exposure-audit.v1", "checked_objects_and_files": checked,
            "categories": dict(counts), "findings": findings, "exact_runtime_secret_available": bool(secret),
            "secret_pattern_hits": sum(counts[category] for category in SECRET_CATEGORIES),
            "privacy_review_required": bool(findings), "license_file_present": Path("LICENSE").is_file(),
            "scope": "tracked files, reachable blobs, commits and annotated tags; compressed blobs decompressed",
            "limitations": "heuristic detector; synthetic examples may match. Findings require review, not automatic "
                           "history rewriting. Runtime/generated secret scanning is a separate command."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("var/evidence-v3/public-audit.json"))
    arguments = parser.parse_args()
    result = audit()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "findings"}))
    raise SystemExit(1 if result["secret_pattern_hits"] else 0)
