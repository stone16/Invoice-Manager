"""Pydantic schemas for digi_flow API."""

from datetime import datetime
from enum import IntEnum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConfigStatusEnum(IntEnum):
    """Config status enum for API."""

    ACTIVE = 1
    ARCHIVED = 2


class SourceContentTypeEnum(IntEnum):
    """Source content type enum for API."""

    INVALID = 0
    FILE = 1
    TEXT = 2


# Schema API models


class SchemaCreate(BaseModel):
    """Request to create a new schema."""

    slug: str = Field(..., max_length=64, description="Unique slug identifier")
    name: str = Field(..., max_length=128, description="Human-readable name")
    schema_json: Optional[Dict[str, Any]] = Field(
        None, alias="schema", description="JSON schema definition"
    )
    yaml_schema: Optional[str] = Field(None, description="YAML schema definition")

    class Config:
        populate_by_name = True


class SchemaUpdate(BaseModel):
    """Request to update a schema."""

    name: Optional[str] = Field(None, max_length=128, description="Human-readable name")
    schema_json: Optional[Dict[str, Any]] = Field(
        None, alias="schema", description="JSON schema definition"
    )
    yaml_schema: Optional[str] = Field(None, description="YAML schema definition")
    create_new_version: bool = Field(
        True, description="Whether to create a new version"
    )

    class Config:
        populate_by_name = True


class SchemaResponse(BaseModel):
    """Schema response model."""

    id: int
    slug: str
    name: str
    schema_json: Dict[str, Any] = Field(alias="schema")
    yaml_schema: Optional[str] = None
    version: int
    status: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True

    @classmethod
    def from_orm_model(cls, obj: Any) -> "SchemaResponse":
        """Create from ORM model."""
        return cls(
            id=obj.id,
            slug=obj.slug,
            name=obj.name,
            schema=obj.schema,
            yaml_schema=obj.yaml_schema,
            version=obj.version,
            status=obj.status,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )


class SchemaListResponse(BaseModel):
    """Schema list response model."""

    items: List[SchemaResponse]
    total: int


# Config API models


class WorkflowConfigModel(BaseModel):
    """Workflow configuration model."""

    rag: Optional[Dict[str, Any]] = Field(
        None,
        description="RAG configuration (enabled, distance_threshold, max_examples)",
    )
    model: Optional[Dict[str, Any]] = Field(
        None, description="Model configuration (provider, model_name, temperature)"
    )
    processing: Optional[Dict[str, Any]] = Field(
        None, description="Processing configuration (token_optimization, max_token_budget)"
    )


class PromptConfigModel(BaseModel):
    """Prompt configuration model."""

    task: Optional[str] = Field(None, description="Task description")
    instructions: Optional[str] = Field(None, description="Additional instructions")
    zero_shot_example: Optional[Dict[str, Any]] = Field(
        None, description="Zero-shot example override"
    )


class ConfigCreate(BaseModel):
    """Request to create a new config."""

    slug: str = Field(..., max_length=64, description="Unique slug identifier")
    name: str = Field(..., max_length=128, description="Human-readable name")
    description: Optional[str] = Field(None, description="Config description")
    domain: Optional[str] = Field(None, max_length=64, description="Domain category")
    schema_id: int = Field(..., description="Associated schema ID")
    schema_version: int = Field(..., description="Associated schema version")
    source_content_type: SourceContentTypeEnum = Field(
        SourceContentTypeEnum.FILE, description="Content type"
    )
    workflow_config: Optional[WorkflowConfigModel] = Field(
        None, description="Workflow configuration"
    )
    prompt_config: Optional[PromptConfigModel] = Field(
        None, description="Prompt configuration"
    )
    schema_validation: Optional[Dict[str, Any]] = Field(
        None, description="Schema validation settings"
    )


class ConfigUpdate(BaseModel):
    """Request to update a config."""

    name: Optional[str] = Field(None, max_length=128, description="Human-readable name")
    description: Optional[str] = Field(None, description="Config description")
    domain: Optional[str] = Field(None, max_length=64, description="Domain category")
    schema_id: Optional[int] = Field(None, description="Associated schema ID")
    schema_version: Optional[int] = Field(None, description="Associated schema version")
    workflow_config: Optional[WorkflowConfigModel] = Field(
        None, description="Workflow configuration"
    )
    prompt_config: Optional[PromptConfigModel] = Field(
        None, description="Prompt configuration"
    )
    schema_validation: Optional[Dict[str, Any]] = Field(
        None, description="Schema validation settings"
    )


class ConfigResponse(BaseModel):
    """Config response model."""

    id: int
    slug: str
    name: str
    description: Optional[str] = None
    domain: Optional[str] = None
    schema_id: int
    schema_version: int
    source_content_type: int
    workflow_config: Optional[Dict[str, Any]] = None
    prompt_config: Optional[Dict[str, Any]] = None
    schema_validation: Optional[Dict[str, Any]] = None
    version: int
    status: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConfigListResponse(BaseModel):
    """Config list response model."""

    items: List[ConfigResponse]
    total: int
