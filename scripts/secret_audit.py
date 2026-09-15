"""Check tracked history and generated evidence for provider credential leakage without printing values."""

import gzip
import json
import os
import re
import subprocess
from pathlib import Path


def main():
    secret = os.environ.get("NVIDIA_API_KEY", "").encode()
    pattern = re.compile(rb"nvapi-[A-Za-z0-9_-]{20,}")
    matches = []
    checked = 0

    def check(label, payload):
        nonlocal checked
        checked += 1
        if payload.startswith(b"\x1f\x8b"):
            payload = gzip.decompress(payload)
        if (secret and secret in payload) or pattern.search(payload):
            matches.append(label)

    tracked = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    for name in tracked:
        if name and Path(name).is_file():
            check(name, Path(name).read_bytes())
    for root in (Path("var"), Path("docs/reports")):
        if root.exists():
            for path in root.rglob("*"):
                if path.is_file():
                    check(str(path), path.read_bytes())
    objects = subprocess.check_output(["git", "rev-list", "--objects", "--all"]).decode().splitlines()
    for entry in objects:
        identity, _, name = entry.partition(" ")
        if name:
            kind = subprocess.check_output(["git", "cat-file", "-t", identity]).strip()
            if kind == b"blob":
                check("history:" + name, subprocess.check_output(["git", "cat-file", "blob", identity]))
    report = {"checked_files_and_blobs": checked, "exact_runtime_key_available": bool(secret),
              "credential_matches": matches, "pattern": "NVIDIA token-shaped values and exact runtime credential",
              "does_not_print_secrets": True}
    print(json.dumps(report))
    if matches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
