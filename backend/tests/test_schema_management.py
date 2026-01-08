from __future__ import annotations

import pytest

from app.services.schema_management.schema_parser import parse_yaml_schema  # noqa: E402
from app.services.schema_management.schema_validator import validate_json_schema  # noqa: E402
from app.services.schema_management.schema_versioning import next_schema_version  # noqa: E402
from app.services.schema_management.pydantic_generator import (  # noqa: E402
    generate_pydantic_model,
    inject_data_source_fields,
)


def test_validate_json_schema_accepts_valid_schema():
    schema = {
        "type": "object",
        "properties": {"invoice_number": {"type": "string"}},
        "required": ["invoice_number"],
    }
    assert validate_json_schema(schema) is True


def test_validate_json_schema_rejects_invalid_schema():
    schema = {
        "type": "object",
        "properties": {"invoice_number": {"type": "invalid-type"}},
    }
    with pytest.raises(ValueError):
        validate_json_schema(schema)


def test_parse_yaml_schema_to_dict():
    yaml_text = """
    type: object
    properties:
      invoice_number:
        type: string
    """
    parsed = parse_yaml_schema(yaml_text)
    assert parsed["properties"]["invoice_number"]["type"] == "string"


def test_schema_versioning_increments():
    assert next_schema_version([]) == 1
    assert next_schema_version([1, 2, 4]) == 5


def test_inject_data_source_fields_wraps_properties():
    schema = {
        "type": "object",
        "properties": {"invoice_number": {"type": "string"}},
    }
    injected = inject_data_source_fields(schema)
    invoice_props = injected["properties"]["invoice_number"]
    assert invoice_props["type"] == "object"
    assert "data_source" in invoice_props["properties"]


def test_generate_pydantic_model_with_data_source():
    schema = {
        "type": "object",
        "properties": {"invoice_number": {"type": "string"}},
        "required": ["invoice_number"],
    }
    model = generate_pydantic_model(schema, "InvoiceSchema")
    instance = model(
        invoice_number={"value": "123", "data_source": {"block_id": "1.1.1:1:1"}}
    )
    assert instance.invoice_number.value == "123"
