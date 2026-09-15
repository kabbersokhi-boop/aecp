"""Exercise both standalone example agents against an already-running gateway."""

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

from aecp.client import Client

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8765")
parser.add_argument("--tokens", type=Path, default=Path("var/local-capabilities.json"))
args = parser.parse_args()
principals = json.loads(args.tokens.read_text())
operator = Client(args.url, principals["operator"]["token"])
environment = {key: os.environ[key] for key in ("PATH", "HOME", "LANG", "PYTHONPATH", "LD_LIBRARY_PATH")
               if key in os.environ}
environment.update(AECP_URL=args.url, AECP_AGENT_TOKEN=principals["passive"]["token"])
passive = subprocess.run([sys.executable, "examples/passive_agent.py"], env=environment,
                         capture_output=True, text=True, check=True, timeout=20)
assert json.loads(passive.stdout)["reservation"]["state"] == "SETTLED", passive.stdout
identity = f"smoke-{uuid.uuid4().hex}"
operator.call("/api/v1/admin/auctions", {"auction_id": identity, "capacity": 1})
environment.update(AECP_AGENT_TOKEN=principals["native"]["token"], AECP_AUCTION_ID=identity,
                   AECP_REQUEST_ID=identity)
bid = subprocess.run([sys.executable, "examples/economic_native_agent.py"], env=environment,
                     capture_output=True, text=True, check=True, timeout=20)
assert "ESCROWED" in bid.stdout, bid.stdout
operator.call("/api/v1/admin/clear", {"auction_id": identity})
del environment["AECP_AUCTION_ID"]
native = subprocess.run([sys.executable, "examples/economic_native_agent.py"], env=environment,
                        capture_output=True, text=True, check=True, timeout=20)
assert json.loads(native.stdout)["reservation"]["state"] == "SETTLED", native.stdout
print(json.dumps({"passive_example": "SETTLED", "economic_native_example": "BID -> ALLOCATED -> SETTLED",
                  "real_provider_spend": 0}))
