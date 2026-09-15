"""An ordinary agent changing only its expensive-action transport."""

import json
import os
import uuid

from aecp.client import Client, ControlPlaneError

client = Client(os.environ.get("AECP_URL", "http://127.0.0.1:8765"), os.environ["AECP_AGENT_TOKEN"])
try:
    result = client.execute(f"passive-{uuid.uuid4().hex}", "external-invoice-1", "cheap",
                            {"invoice_cents": 12500, "payments": [12500]})
    print(json.dumps({"result": result["result"], "reservation": result["reservation"]}, indent=2))
except ControlPlaneError as error:
    print(json.dumps({"denied": error.payload}))
