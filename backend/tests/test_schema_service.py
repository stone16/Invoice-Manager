"""Tests for schema and config services."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.models.digi_flow import ConfigStatus, DigiFlowConfig, DigiFlowSchema
from app.services.schema_management.default_schemas import (
    get_chinese_invoice_schema,
    get_chinese_invoice_yaml,
)


def test_chinese_invoice_schema_is_valid():
    """Test that the default Chinese invoice schema is valid JSON schema."""
    from app.services.schema_management.schema_validator import validate_json_schema

    schema = get_chinese_invoice_schema()
    assert validate_json_schema(schema) is True


def test_chinese_invoice_schema_has_required_fields():
    """Test that the default schema has all required invoice fields."""
    schema = get_chinese_invoice_schema()
    props = schema["properties"]

    required_fields = [
        "invoice_number",
        "issue_date",
        "buyer_name",
        "seller_name",
        "total_with_tax",
    ]
    for field in required_fields:
        assert field in props, f"Missing required field: {field}"


def test_chinese_invoice_yaml_parses_correctly():
    """Test that the YAML schema parses to a valid dict."""
    from app.services.schema_management.schema_parser import parse_yaml_schema
    from app.services.schema_management.schema_validator import validate_json_schema

    yaml_text = get_chinese_invoice_yaml()
    schema = parse_yaml_schema(yaml_text)
    assert validate_json_schema(schema) is True
    assert "properties" in schema


def test_inject_data_source_handles_nested_objects():
    """Test that data source injection handles nested objects."""
    from app.services.schema_management.pydantic_generator import inject_data_source_fields

    schema = {
        "type": "object",
        "properties": {
            "buyer": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "tax_id": {"type": "string"},
                },
            },
        },
    }
    injected = inject_data_source_fields(schema)
    buyer_props = injected["properties"]["buyer"]
    assert buyer_props["type"] == "object"
    assert "data_source" in buyer_props["properties"]


def test_generate_pydantic_model_handles_optional_fields():
    """Test that generated model handles optional fields correctly."""
    from app.services.schema_management.pydantic_generator import generate_pydantic_model

    schema = {
        "type": "object",
        "properties": {
            "required_field": {"type": "string"},
            "optional_field": {"type": "string"},
        },
        "required": ["required_field"],
    }
    model = generate_pydantic_model(schema, "TestModel")

    # Optional field should default to None
    instance = model(required_field={"value": "test", "data_source": None})
    assert instance.optional_field is None


def test_schema_versioning_with_gaps():
    """Test schema versioning handles gaps in version numbers."""
    from app.services.schema_management.schema_versioning import next_schema_version

    assert next_schema_version([1, 3, 5]) == 6
    assert next_schema_version([10]) == 11
    assert next_schema_version([]) == 1


class TestSchemaServiceUnit:
    """Unit tests for schema service functions."""

    @pytest.mark.asyncio
    async def test_create_schema_validates_schema(self):
        """Test that create_schema validates the JSON schema."""
        from app.services.schema_management.schema_service import create_schema

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Invalid schema should raise ValueError
        invalid_schema = {"type": "invalid-type"}
        with pytest.raises(ValueError):
            await create_schema(
                db=mock_db,
                slug="test",
                name="Test",
                schema=invalid_schema,
            )

    @pytest.mark.asyncio
    async def test_create_schema_from_yaml_parses_correctly(self):
        """Test create_schema_from_yaml parses YAML correctly."""
        from app.services.schema_management.schema_service import create_schema_from_yaml

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        yaml_text = """
        type: object
        properties:
          name:
            type: string
        """

        # Mock the add to capture what was created
        captured_schema = None

        def capture_add(obj):
            nonlocal captured_schema
            captured_schema = obj

        mock_db.add = capture_add

        await create_schema_from_yaml(
            db=mock_db,
            slug="test-yaml",
            name="Test YAML",
            yaml_text=yaml_text,
        )

        assert captured_schema is not None
        assert captured_schema.slug == "test-yaml"
        assert captured_schema.yaml_schema == yaml_text


class TestConfigServiceUnit:
    """Unit tests for config service functions."""

    @pytest.mark.asyncio
    async def test_create_config_with_defaults(self):
        """Test create_config uses default workflow and prompt configs."""
        from app.services.schema_management.config_service import create_config

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        captured_config = None

        def capture_add(obj):
            nonlocal captured_config
            captured_config = obj

        mock_db.add = capture_add

        await create_config(
            db=mock_db,
            slug="test-config",
            name="Test Config",
            schema_id=1,
            schema_version=1,
        )

        assert captured_config is not None
        assert captured_config.workflow_config is not None
        assert "rag" in captured_config.workflow_config
        assert "model" in captured_config.workflow_config
        assert captured_config.prompt_config is not None
        assert "task" in captured_config.prompt_config


def test_field_with_source_model():
    """Test FieldWithSource model structure."""
    from app.services.schema_management.pydantic_generator import (
        DataSource,
        FieldWithSource,
    )

    source = DataSource(
        block_id="1.1.1:1:1",
        confidence=0.95,
        extraction_method="llm",
    )
    field = FieldWithSource(
        value="INV-001",
        data_source=source,
    )

    assert field.value == "INV-001"
    assert field.data_source.block_id == "1.1.1:1:1"
    assert field.data_source.confidence == 0.95
