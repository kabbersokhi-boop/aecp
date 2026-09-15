"""Archive selected executed V3 evidence without overwriting historical studies."""

import gzip
import hashlib
import json
from pathlib import Path

from public_snapshot import sanitize

FILES = ("overload-before.json", "overload-after.json", "fairness.json", "clean-install.json",
         "reporting-reviewed.json", "reporting-reviewed.trials.json.gz", "model-selection-1.json",
         "final-semantic-live.json", "final-semantic-analysis.json", "final-semantic-live.provider-journal.jsonl",
         "live-browser.json", "clean-install-final.json")


def main():
    source = Path("var/evidence-v3")
    destination = Path("docs/reports/evidence-v3")
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    for name in FILES:
        data = (source / name).read_bytes()
        payload = gzip.decompress(data) if name.endswith(".gz") else data
        if name.endswith(".jsonl"):
            for line in payload.splitlines():
                json.loads(line)
        else:
            json.loads(payload)
        safe, redaction = sanitize("docs/reports/evidence-v3/" + name, data)
        if redaction or safe != data:
            raise ValueError("new release evidence must not require privacy redaction")
        output_name = name if name.endswith(".gz") else name + ".gz"
        compressed = data if name.endswith(".gz") else gzip.compress(payload, mtime=0)
        target = destination / output_name
        if target.exists() and target.read_bytes() != compressed:
            raise ValueError("refusing to overwrite existing evidence: " + output_name)
        target.write_bytes(compressed)
        records.append({"path": output_name, "sha256": hashlib.sha256(compressed).hexdigest(),
                        "uncompressed_sha256": hashlib.sha256(payload).hexdigest()})
    selection = json.loads((source / "model-selection-1.json").read_text())
    study = json.loads((source / "final-semantic-live.json").read_text())
    manifest = {"version": "v3-evidence-checkpoint", "files": records,
                "live_v3_chat_calls": selection["chat_calls"] + study["provider_calls"],
                "live_v3_catalog_calls": selection["catalog_calls"],
                "scope": "offline controls, development model probe and single frozen live semantic evaluation"}
    (destination / "OFFLINE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"archived_files": len(records), "live_v3_chat_calls": manifest["live_v3_chat_calls"]}))


if __name__ == "__main__":
    main()
