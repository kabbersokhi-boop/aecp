"""Namespace entry point; emit only public task/action data, never capability contents."""

import json
import sys
from pathlib import Path

from client import Client
from main import run

configuration = json.loads(Path(sys.argv[1]).read_text())
client = Client(configuration["url"], Path("/agent-token").read_text().strip(), "/gateway.sock")
print(json.dumps(run(client, configuration["policy"])))
