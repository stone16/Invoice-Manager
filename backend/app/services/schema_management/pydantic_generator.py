from __future__ import annotations

import copy
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, create_model


class DataSource(BaseModel):
    """Data source tracking for extracted field values."""

    block_id: Optional[str] = None
    confidence: Optional[float] = None
    extraction_method: Optional[str] = None


class FieldWithSource(BaseModel):
    """Field value with data source tracking."""

    value: Any = None
    data_source: Optional[DataSource] = None


def inject_data_source_fields(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Inject data_source tracking into schema properties.

    Transforms each property from a simple type to an object with
    'value' and 'data_source' fields for lineage tracking.

    Args:
        schema: JSON schema dict with properties

    Returns:
        New schema dict with data_source fields injected
    """
    result = copy.deepcopy(schema)

    if "properties" not in result:
        return result

    new_properties = {}
    for prop_name, prop_schema in result["properties"].items():
        new_properties[prop_name] = {
            "type": "object",
            "properties": {
                "value": prop_schema,
                "data_source": {
                    "type": "object",
                    "properties": {
                        "block_id": {"type": "string"},
                        "confidence": {"type": "number"},
                        "extraction_method": {"type": "string"},
                    },
                },
            },
        }

    result["properties"] = new_properties
    return result


def generate_pydantic_model(
    schema: Dict[str, Any], model_name: str
) -> Type[BaseModel]:
    """Generate a Pydantic model from JSON schema with data source tracking.

    Each field in the generated model is wrapped with data_source tracking
    to enable field-level lineage information.

    Args:
        schema: JSON schema dict
        model_name: Name for the generated model class

    Returns:
        Generated Pydantic model class
    """
    if "properties" not in schema:
        return create_model(model_name)

    field_definitions = {}
    for prop_name, prop_schema in schema["properties"].items():
        is_required = prop_name in schema.get("required", [])
        if is_required:
            field_definitions[prop_name] = (FieldWithSource, ...)
        else:
            field_definitions[prop_name] = (Optional[FieldWithSource], None)

    return create_model(model_name, **field_definitions)
