"""Opt-in hosted NIM transport and bounded modeled-resource accounting; never dollar billing."""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from aecp.control import Denied, Quote, Receipt
from aecp.determinism import canonical_json
from aecp.structured import schema_identity, validate_content

DEFAULT_BASE = "https://integrate.api.nvidia.com/v1"
VERSION = "nim-chat.v1"
COST_VERSION = "request-bytes-output-allowance.v1"
PREFERENCES = ("nvidia/nemotron-3.5-lightning-30b-a3b", "meta/llama-3.3-70b-instruct", "openai/gpt-oss-20b")


class ProviderFailure(Exception):
    """Only safe classifications cross the transport boundary, never HTTP bodies or headers."""

    def __init__(self, category: str):
        self.category = category
        super().__init__(category)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderFailure("redirect_forbidden")


def hosted_base(value: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or parsed.hostname != "integrate.api.nvidia.com"
            or parsed.port not in (None, 443) or parsed.username or parsed.password
            or parsed.path.rstrip("/") != "/v1" or parsed.query or parsed.fragment):
        raise ValueError("NIM credentials may only be sent to the approved hosted HTTPS /v1 endpoint")
    return value.rstrip("/")


class NimTransport:
    def __init__(self, *, base_url: str = DEFAULT_BASE, timeout: float = 40,
                 journal: Path = Path("var/nim-requests.jsonl")):
        if os.environ.get("AECP_ENABLE_LIVE_NIM") != "1" or not os.environ.get("NVIDIA_API_KEY"):
            raise Denied("LIVE_NIM_REQUIRES_OPT_IN_AND_SERVER_KEY")
        self.base_url = hosted_base(base_url)
        self.timeout = timeout
        self.journal = journal

    def record(self, entry: dict) -> None:
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        with self.journal.open("a") as stream:
            stream.write(canonical_json(entry) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def request(self, path: str, body: dict | None = None) -> dict:
        if path not in {"/models", "/chat/completions"}:
            raise ValueError("unsupported provider endpoint")
        attempt = uuid.uuid4().hex
        started = time.perf_counter()
        entry = {"attempt": attempt, "endpoint": path, "model": body.get("model") if body else None,
                 "started_at": datetime.now(UTC).isoformat(), "phase": "dispatch"}
        self.record(entry)
        request = Request(self.base_url + path, data=canonical_json(body).encode() if body else None,
                          headers={"Authorization": "Bearer " + os.environ["NVIDIA_API_KEY"],
                                   "Content-Type": "application/json", "Accept": "application/json"})
        category = "success"
        result = None
        try:
            with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=self.timeout) as response:
                payload = response.read(1048577)
                if len(payload) > 1048576:
                    raise ProviderFailure("response_too_large")
                result = json.loads(payload)
                if not isinstance(result, dict):
                    raise ProviderFailure("response_shape")
            return result
        except HTTPError as error:
            category = ({401: "authentication", 403: "authentication", 404: "model_unavailable",
                         400: "invalid_request", 422: "invalid_request", 429: "rate_limit"}.get(
                             error.code, "transient_5xx" if error.code >= 500 else "http_error"))
            error.close()
            raise ProviderFailure(category) from None
        except (TimeoutError, URLError):
            category = "timeout_or_connection"
            raise ProviderFailure(category) from None
        except (ValueError, KeyError):
            category = "response_shape"
            raise ProviderFailure(category) from None
        except ProviderFailure as error:
            category = error.category
            raise
        finally:
            usage = result.get("usage", {}) if result else {}
            safe_usage = {name: usage[name] for name in ("prompt_tokens", "completion_tokens", "total_tokens")
                          if isinstance(usage, dict) and type(usage.get(name)) is int and usage[name] >= 0}
            self.record({**entry, "phase": "returned", "category": category, "usage": safe_usage,
                         "latency_ms": round((time.perf_counter() - started) * 1000, 3)})


class NimAdapter:
    """One HTTP attempt per dispatch. Retries require a new control-plane reservation."""

    def __init__(self, model: str, transport: NimTransport):
        if not isinstance(model, str) or not model or len(model) > 160:
            raise ValueError("model must be a discovered, probed identifier")
        self.model = model
        self.transport = transport

    def quote(self, resource: str, parameters: dict) -> Quote:
        allowed = {"model", "messages", "max_tokens", "temperature", "response_format"}
        if (resource != "nim_chat" or set(parameters) - allowed
                or not {"model", "messages", "max_tokens", "temperature"} <= set(parameters)):
            raise Denied("INVALID_NIM_PARAMETERS")
        if parameters["model"] != self.model:
            raise Denied("MODEL_NOT_CONFIGURED")
        maximum = parameters["max_tokens"]
        if type(maximum) is not int or not 1 <= maximum <= 256 or parameters["temperature"] not in (0, 0.1):
            raise Denied("UNBOUNDED_OR_UNSUPPORTED_GENERATION")
        messages = parameters["messages"]
        if not isinstance(messages, list) or not 1 <= len(messages) <= 8:
            raise Denied("INVALID_MESSAGES")
        for message in messages:
            if (not isinstance(message, dict) or set(message) != {"role", "content"}
                    or message["role"] not in {"system", "user", "assistant"}
                    or not isinstance(message["content"], str)):
                raise Denied("INVALID_MESSAGES")
        size = len(canonical_json(messages).encode("utf-8"))
        if size > 8192:
            raise Denied("INPUT_TOO_LARGE")
        structured = parameters.get("response_format")
        schema_id = schema_identity(structured) if "response_format" in parameters else None
        if structured:
            size += len(canonical_json(structured).encode("utf-8"))
        base = (size + 15) // 16
        return Quote(base + 2 * maximum, mode="live_provider_modeled_cost",
                     version="nim-chat.v2" if schema_id else VERSION,
                     details={"provider": "nvidia-hosted-nim", "model": self.model,
                              "base_url": self.transport.base_url, "input_bytes": size, "max_output_tokens": maximum,
                              "cost_model": "request-bytes-output-allowance.v2" if schema_id else COST_VERSION,
                              "input_allocation": base, "per_output_token": 2,
                              "formula": ("ceil((canonical_message_bytes + response_format_bytes)/16)"
                                          " + 2 * output_tokens"
                                          if schema_id else "ceil(canonical_message_bytes/16) + 2 * output_tokens"),
                              "bound_assumption": "provider completion_tokens <= authorized max_tokens",
                              "thinking_enabled": False if "nemotron-3.5-lightning" in self.model else None,
                              **({"response_format": structured, "schema_id": schema_id,
                                  "input_basis": "canonical messages plus response_format bytes"} if schema_id else {}),
                              "actual_cash_spend": 0,
                              "cash_basis": "operator-declared free prototype access; no invoice",
                              "usage_is_not_a_dollar_bound": True})

    def execute(self, resource: str, parameters: dict) -> Receipt:
        quote = self.quote(resource, parameters)
        started_at = datetime.now(UTC).isoformat()
        started = time.perf_counter()
        body = {**parameters, "stream": False}
        if "nemotron-3.5-lightning" in self.model:
            body["chat_template_kwargs"] = {"enable_thinking": False}
        response = self.transport.request("/chat/completions", body)
        usage = response.get("usage")
        if (not isinstance(usage, dict) or any(type(usage.get(name)) is not int or usage[name] < 0
                for name in ("prompt_tokens", "completion_tokens", "total_tokens"))
                or usage["total_tokens"] != usage["prompt_tokens"] + usage["completion_tokens"]):
            raise ProviderFailure("missing_or_invalid_usage")
        actual = quote.details["input_allocation"] + 2 * usage["completion_tokens"]
        choices = response.get("choices")
        shape_valid = isinstance(choices, list) and bool(choices) and isinstance(choices[0], dict)
        choice = choices[0] if shape_valid else {}
        message = choice.get("message", {})
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            content = ""
        completion = {"id": str(response.get("id", "provider-id-unavailable"))[:200],
                      "object": "chat.completion", "created": int(time.time()), "model": self.model,
                      "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                                   "finish_reason": str(choice.get("finish_reason", "unknown"))[:40]}],
                      "usage": {name: usage[name] for name in ("prompt_tokens", "completion_tokens", "total_tokens")}}
        reported_model = response.get("model")
        return Receipt({"completion": completion, "provider": "nvidia-hosted-nim", "model": self.model,
                        "provider_reported_model": str(response.get("model", "unreported"))[:200],
                        "model_identity_status": ("unreported" if reported_model is None else
                                                  "exact" if reported_model == self.model else "unexpected"),
                        "schema_id": quote.details.get("schema_id"),
                        "schema_valid": (validate_content(content, parameters["response_format"])
                                         if "response_format" in parameters else None),
                        "response_shape_valid": shape_valid and isinstance(content, str) and bool(content),
                        "adapter_version": quote.version, "provider_started_at": started_at,
                        "provider_latency_ms": round((time.perf_counter() - started) * 1000, 3),
                        "provider_usage": completion["usage"], "usage_basis": "provider_reported",
                        "modeled_cost": actual, "cost_model": quote.details["cost_model"], "actual_cash_spend": 0,
                        "cash_basis": quote.details["cash_basis"], "settlement_basis": quote.details["formula"]},
                       actual, source=quote.version)


def discover(output: Path, candidates: tuple[str, ...] = PREFERENCES) -> dict:
    if len(candidates) > 3:
        raise ValueError("at most three discovery candidates per bounded probe")
    transport = NimTransport(base_url=os.environ.get("AECP_NIM_BASE_URL", DEFAULT_BASE))
    catalog = transport.request("/models")
    models = sorted(item["id"] for item in catalog.get("data", []) if isinstance(item, dict)
                    and isinstance(item.get("id"), str))
    probes = []
    selected = None
    for model in candidates:
        if model not in models:
            probes.append({"model": model, "catalog_present": False})
            continue
        adapter = NimAdapter(model, transport)
        attempts = []
        for _attempt in range(3):
            parameters = {"model": model, "messages": [{"role": "system", "content":
                "Return JSON only, no markdown or explanation."}, {"role": "user", "content":
                'Invoice 100 cents, payments [100]. Return only {"resolution":"matched"}.'}],
                "max_tokens": 48, "temperature": 0}
            try:
                receipt = adapter.execute("nim_chat", parameters)
                content = receipt.payload["completion"]["choices"][0]["message"]["content"]
                valid = json.loads(content) == {"resolution": "matched"}
                attempts.append({"success": valid, "usage": receipt.payload["provider_usage"],
                                 "latency_ms": receipt.payload["provider_latency_ms"]})
            except (ProviderFailure, ValueError) as error:
                attempts.append({"success": False, "category": error.category if isinstance(error, ProviderFailure)
                                 else "structured_output_incompatible"})
                break
        probes.append({"model": model, "catalog_present": True, "attempts": attempts})
        if len(attempts) == 3 and all(attempt["success"] for attempt in attempts):
            selected = model
            break
    result = {"created_at": datetime.now(UTC).isoformat(), "base_url": transport.base_url,
              "catalog": models, "candidates": candidates, "probes": probes, "selected_model": selected,
              "selection_rule": "first preferred catalog model with three valid structured/usage responses",
              "automatic_retries": 0, "actual_cash_spend": 0}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    return result
