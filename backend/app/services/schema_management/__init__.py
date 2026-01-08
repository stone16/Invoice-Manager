"""Schema management services."""

from app.services.schema_management.config_service import (
    archive_config,
    create_config,
    get_config,
    get_config_by_slug,
    list_configs,
    update_config,
)
from app.services.schema_management.pydantic_generator import (
    DataSource,
    FieldWithSource,
    generate_pydantic_model,
    inject_data_source_fields,
)
from app.services.schema_management.schema_parser import parse_yaml_schema
from app.services.schema_management.schema_service import (
    archive_schema,
    create_schema,
    create_schema_from_yaml,
    get_schema,
    get_schema_by_slug,
    list_schemas,
    update_schema,
)
from app.services.schema_management.schema_validator import validate_json_schema
from app.services.schema_management.schema_versioning import next_schema_version

__all__ = [
    # Schema service
    "create_schema",
    "create_schema_from_yaml",
    "get_schema",
    "get_schema_by_slug",
    "list_schemas",
    "update_schema",
    "archive_schema",
    # Config service
    "create_config",
    "get_config",
    "get_config_by_slug",
    "list_configs",
    "update_config",
    "archive_config",
    # Utilities
    "parse_yaml_schema",
    "validate_json_schema",
    "next_schema_version",
    "generate_pydantic_model",
    "inject_data_source_fields",
    "DataSource",
    "FieldWithSource",
]
