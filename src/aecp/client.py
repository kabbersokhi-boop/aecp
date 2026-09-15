"""Small native HTTP SDK. No settlement, funding or unbounded retries."""

from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class ControlPlaneError(Exception):
    def __init__(self, status: int, payload: dict):
        self.status, self.payload = status, payload
        super().__init__(payload.get("error", "REQUEST_FAILED"))


class Client:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def call(self, path: str, body: dict | None = None):
        request = Request(self.base_url + path, data=json.dumps(body).encode() if body is not None else None,
                          headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as error:
            with error:
                payload = json.load(error)
            raise ControlPlaneError(error.code, payload) from error

    def budget(self) -> dict:
        return self.call("/api/v1/me/budget")

    def execute(self, request_id: str, task_id: str, resource: str, parameters: dict,
                *, operation: str = "reconcile") -> dict:
        return self.call("/api/v1/resource-requests", {"request_id": request_id, "task_id": task_id,
                         "resource": resource, "parameters": parameters, "operation": operation})

    def bid(self, bid_id: str, auction_id: str, price: int, request_id: str, task_id: str,
            parameters: dict) -> dict:
        return self.call("/api/v1/market/bids", {"bid_id": bid_id, "auction_id": auction_id, "price": price,
                         "request_id": request_id, "task_id": task_id, "resource": "premium", "parameters": parameters})
