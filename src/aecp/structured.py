"""Small closed JSON-schema contract shared by provider admission and independent validation."""

from __future__ import annotations

import json

from aecp.control import Denied
from aecp.determinism import canonical_json, stable_digest


def response_schema(response_format: dict) -> dict:
    if (not isinstance(response_format, dict) or set(response_format) != {"type", "json_schema"}
            or response_format["type"] != "json_schema"):
        raise Denied("UNSUPPORTED_RESPONSE_FORMAT")
    contract = response_format["json_schema"]
    if (not isinstance(contract, dict) or set(contract) != {"name", "strict", "schema"}
            or contract["strict"] is not True or not isinstance(contract["name"], str)
            or not contract["name"].isascii() or not contract["name"].replace("_", "").isalnum()
            or not 1 <= len(contract["name"]) <= 64 or len(canonical_json(response_format).encode()) > 4096):
        raise Denied("INVALID_SCHEMA_CONTRACT")
    schema = contract["schema"]
    validate_schema(schema, root=True)
    return schema


def validate_schema(schema: dict, *, root: bool = False, depth: int = 0) -> None:
    if not isinstance(schema, dict) or depth > 2:
        raise Denied("UNSUPPORTED_SCHEMA")
    kind = schema.get("type")
    if root and kind != "object":
        raise Denied("SCHEMA_ROOT_MUST_BE_OBJECT")
    if kind == "object":
        properties = schema.get("properties")
        if (not root or set(schema) != {"type", "properties", "required", "additionalProperties"}
                or schema["additionalProperties"] is not False or not isinstance(properties, dict)
                or not 1 <= len(properties) <= 12 or not isinstance(schema["required"], list)
                or any(not isinstance(key, str) for key in schema["required"])
                or len(schema["required"]) != len(properties) or set(schema["required"]) != set(properties)):
            raise Denied("UNSUPPORTED_OBJECT_SCHEMA")
        for key, value in properties.items():
            if not isinstance(key, str) or not key or len(key) > 64:
                raise Denied("INVALID_SCHEMA_PROPERTY")
            validate_schema(value, depth=depth + 1)
    elif kind == "string":
        if set(schema) - {"type", "enum", "maxLength"}:
            raise Denied("UNSUPPORTED_STRING_SCHEMA")
        if "enum" in schema and (not isinstance(schema["enum"], list) or not 1 <= len(schema["enum"]) <= 24
                                 or any(not isinstance(value, str) or len(value) > 128 for value in schema["enum"])):
            raise Denied("UNBOUNDED_ENUM")
        if "maxLength" in schema and (type(schema["maxLength"]) is not int or not 1 <= schema["maxLength"] <= 512):
            raise Denied("UNBOUNDED_STRING")
    elif kind == "integer":
        if (set(schema) != {"type", "minimum", "maximum"} or type(schema["minimum"]) is not int
                or type(schema["maximum"]) is not int or not -100000000 <= schema["minimum"] <= schema["maximum"]
                <= 100000000):
            raise Denied("UNBOUNDED_INTEGER_SCHEMA")
    elif kind == "array":
        if (set(schema) != {"type", "items", "maxItems"} or type(schema["maxItems"]) is not int
                or not 0 <= schema["maxItems"] <= 16):
            raise Denied("UNBOUNDED_ARRAY_SCHEMA")
        validate_schema(schema["items"], depth=depth + 1)
    elif kind != "boolean" or set(schema) != {"type"}:
        raise Denied("UNSUPPORTED_SCHEMA_TYPE")


def matches_schema(value, schema: dict) -> bool:
    kind = schema["type"]
    if kind == "object":
        return (isinstance(value, dict) and set(value) == set(schema["properties"])
                and all(matches_schema(value[key], child) for key, child in schema["properties"].items()))
    if kind == "array":
        return (isinstance(value, list) and len(value) <= schema["maxItems"]
                and all(matches_schema(item, schema["items"]) for item in value))
    if kind == "string":
        return (isinstance(value, str) and len(value) <= schema.get("maxLength", 65536)
                and ("enum" not in schema or value in schema["enum"]))
    if kind == "integer":
        return type(value) is int and schema["minimum"] <= value <= schema["maximum"]
    return type(value) is bool


def validate_content(content: str, response_format: dict) -> bool:
    def unique_fields(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON field")
            result[key] = value
        return result
    try:
        value = json.loads(content, object_pairs_hook=unique_fields)
    except (ValueError, TypeError, RecursionError):
        return False
    return matches_schema(value, response_schema(response_format))


def schema_identity(response_format: dict) -> str:
    response_schema(response_format)
    return stable_digest(response_format)
