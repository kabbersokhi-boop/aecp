"""Owner-scoped presentation reads; no authorization or accounting decisions."""

from __future__ import annotations

import json

from aecp.control import Denied
from aecp.ledger import _identifier


def request_trace(control, agent_id: str, request_id: str) -> dict:
    """Read request, receipt and its owner's durable events in one transaction."""
    _identifier(request_id)
    with control.ledger._transaction() as connection:
        row = connection.execute("SELECT agent_id FROM requests WHERE id = ?", (request_id,)).fetchone()
        if row and row[0] != agent_id:
            raise Denied("REQUEST_NOT_FOUND")
        events = [dict(event) for event in connection.execute(
            "SELECT * FROM events WHERE account_id = ? AND hold_id = ? ORDER BY seq", (agent_id, request_id))]
        if not row and not events:
            raise Denied("REQUEST_NOT_FOUND")
        for event in events:
            event["payload"] = json.loads(event["payload"])
        return {"request": control.request(request_id, agent_id, connection=connection) if row else None,
                "events": events, "source": "persisted SQLite request and owner-scoped event journal"}
