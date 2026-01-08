from __future__ import annotations

from typing import Any, Dict

from jsonschema import Draft7Validator, SchemaError


def validate_json_schema(schema: Dict[str, Any]) -> bool:
    try:
        Draft7Validator.check_schema(schema)
    except SchemaError as exc:
        raise ValueError("Invalid JSON schema") from exc
    return True
