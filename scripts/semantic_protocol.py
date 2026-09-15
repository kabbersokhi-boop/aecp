"""Freeze and validate a reviewable V3 live-study contract, not a security signature."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from aecp.nim import DEFAULT_BASE
from aecp.semantic_corpus_v3 import manifest


def git(root: Path, *arguments: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *arguments], stderr=subprocess.PIPE)


def source_hashes(root: Path) -> dict:
    paths = git(root, "ls-files", "src/aecp/*.py", "examples/semantic_consumer/*.py",
                "scripts/semantic_validate.py", "scripts/semantic_protocol.py",
                "scripts/isolation_validate.py").decode().splitlines()
    if not paths:
        raise ValueError("study source files must be tracked")
    return {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths}


def freeze(root: Path, output: Path, model: str, base_url: str) -> dict:
    if git(root, "status", "--porcelain").strip():
        raise ValueError("commit development changes before freezing the final protocol")
    if not model or not base_url.startswith("https://"):
        raise ValueError("explicit probed model and HTTPS endpoint required")
    record = {"version": "semantic-live-protocol.v3.1",
              "source_commit": git(root, "rev-parse", "HEAD").decode().strip(),
              "sources": source_hashes(root), "corpus": manifest("heldout"), "model": model,
              "base_url": base_url, "split": "heldout", "provider_call_limit": 60,
              "policy": "one final execution; retain failures, no tuning or replacement after inspection"}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        stream.write(json.dumps(record, indent=2) + "\n")
    return record


def validate(root: Path, path: Path, model: str, base_url: str) -> dict:
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    data = path.read_bytes()
    if git(root, "show", "HEAD:" + relative) != data:
        raise ValueError("final protocol must be committed and unchanged")
    if git(root, "status", "--porcelain").strip():
        raise ValueError("final execution requires a clean reviewed worktree")
    record = json.loads(data)
    if record.get("version") != "semantic-live-protocol.v3.1":
        raise ValueError("unsupported final protocol")
    if record["sources"] != source_hashes(root) or record["corpus"] != manifest("heldout"):
        raise ValueError("source or corpus changed after freeze")
    if (record["model"], record["base_url"], record["split"], record["provider_call_limit"]) != (
            model, base_url, "heldout", 60):
        raise ValueError("runtime differs from frozen provider contract")
    subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", record["source_commit"], "HEAD"],
                   check=True, capture_output=True)
    return {**record, "protocol_sha256": hashlib.sha256(data).hexdigest()}


def claim(path: Path, record: dict, output: Path) -> None:
    """Exclusive local marker survives crashes and prevents accidental output-path retries."""
    with path.with_suffix(path.suffix + ".started").open("x") as stream:
        stream.write(json.dumps({"protocol_sha256": record["protocol_sha256"],
                                 "output_name": output.name}) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    result = freeze(Path(__file__).resolve().parents[1], arguments.output, arguments.model, arguments.base_url)
    print(json.dumps({"source_commit": result["source_commit"], "model": result["model"],
                      "next_step": "review and commit protocol before the single held-out run"}))
