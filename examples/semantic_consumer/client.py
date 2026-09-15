"""Independent standard-library consumer: only the documented HTTP contract is used."""

from __future__ import annotations

import http.client
import json
import socket
from urllib.parse import urlsplit


class GatewayError(Exception):
    def __init__(self, status: int, payload: dict):
        super().__init__(f"gateway returned HTTP {status}")
        self.status = status
        self.payload = payload


class Client:
    def __init__(self, base_url: str, token: str, unix_socket: str | None = None):
        address = urlsplit(base_url)
        if address.scheme != "http" or address.hostname not in {"127.0.0.1", "localhost"}:
            raise ValueError("reference consumer requires a loopback HTTP gateway")
        self.host = address.hostname
        self.port = address.port or 80
        self.token = token
        self.unix_socket = unix_socket

    def request(self, method: str, path: str, body: dict | None = None):
        connection = http.client.HTTPConnection(self.host, self.port, timeout=90)
        if self.unix_socket:
            connection.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            connection.sock.settimeout(90)
            connection.sock.connect(self.unix_socket)
        try:
            connection.request(method, path, body=json.dumps(body) if body is not None else None,
                               headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"})
            response = connection.getresponse()
            payload = json.loads(response.read())
            if response.status >= 400:
                raise GatewayError(response.status, payload)
            return payload
        finally:
            connection.close()
