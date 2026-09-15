"""A budget-aware agent bids, waits for allocation, and executes under the same authority."""

import json
import os
import uuid

from aecp.client import Client, ControlPlaneError

client = Client(os.environ.get("AECP_URL", "http://127.0.0.1:8765"), os.environ["AECP_AGENT_TOKEN"])
parameters = {"invoice_cents": 12500, "payments": [12500, 12500]}
request_id = os.environ.get("AECP_REQUEST_ID", f"native-{uuid.uuid4().hex}")
try:
    if "AECP_AUCTION_ID" in os.environ and client.budget()["budget"]["effective_headroom"] < 16:
        print(json.dumps({"decision": "defer", "reason": "preserve remaining authority"}))
    elif "AECP_AUCTION_ID" in os.environ:
        print(json.dumps(client.bid(f"{request_id}-bid", os.environ["AECP_AUCTION_ID"], 20,
                                    request_id, "external-invoice-2", parameters), indent=2))
        print(json.dumps({"next": "operator clears auction; rerun with AECP_REQUEST_ID and without AECP_AUCTION_ID",
                          "request_id": request_id}))
    else:
        print(json.dumps(client.execute(request_id, "external-invoice-2", "premium", parameters), indent=2))
except ControlPlaneError as error:
    print(json.dumps({"decision": "defer", "denied": error.payload}))
