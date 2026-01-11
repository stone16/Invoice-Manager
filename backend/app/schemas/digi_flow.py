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
    create_new_version: bool = Field(
        True, description="Create a new config version"
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


# Flow API models


class FileContentTypeEnum(IntEnum):
    """File content type enum for API."""

    INVALID = 0
    PDF = 1
    EXCEL = 2
    IMAGE = 3


class MainStatusEnum(IntEnum):
    """Main status enum for API."""

    PENDING = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    FAILED = 3


class DataServiceStatusEnum(IntEnum):
    """Data service status enum for API."""

    NONE = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    FAILED = 3


class AuditReasonCodeEnum(IntEnum):
    """Audit reason code enum for API."""

    INCORRECT = 1
    MISSING = 2
    EXTRA = 3
    FORMAT = 4
    DATA_SOURCE = 5
    OTHER = 99


class FeedbackSourceEnum(IntEnum):
    """Feedback source enum for API."""

    UI = 1
    API = 2
    AUTO = 3


class ContentContextModel(BaseModel):
    """Content context model."""

    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    text: Optional[str] = None
    pages: Optional[int] = None


class FlowCreate(BaseModel):
    """Request to create a new flow."""

    config_id: int = Field(..., description="Configuration ID")
    config_version: Optional[int] = Field(None, description="Configuration version")
    content_type: FileContentTypeEnum = Field(..., description="Content type")
    content_context: ContentContextModel = Field(..., description="Content context")


class FlowResponse(BaseModel):
    """Flow response model."""

    id: int
    config_id: int
    config_version: int
    schema_id: int
    schema_version: int
    content_type: int
    content_context: Dict[str, Any]
    content_metadata: Optional[Dict[str, Any]] = None
    langsmith_trace_id: Optional[str] = None
    main_status: int
    data_service_status: int
    schema_validation_status: int
    schema_validation_result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FlowResultResponse(BaseModel):
    """Flow result response model."""

    id: int
    flow_id: int
    data: Dict[str, Any]
    plain_data: Optional[Dict[str, Any]] = None
    text_blocks: Optional[List[Dict[str, Any]]] = None
    data_origin: int
    version: int
    updated_at: datetime

    class Config:
        from_attributes = True


class FlowWithResultResponse(FlowResponse):
    """Flow with result response model."""

    result: Optional[FlowResultResponse] = None
    config: Optional[ConfigResponse] = None
    schema_obj: Optional[SchemaResponse] = Field(None, alias="schema")

    class Config:
        from_attributes = True
        populate_by_name = True


class FlowListResponse(BaseModel):
    """Flow list response model."""

    items: List[FlowWithResultResponse]
    total: int


class FieldCorrectionModel(BaseModel):
    """Field correction model for feedback."""

    field_path: str = Field(..., description="Path to the field")
    new_value: Any = Field(..., description="New value for the field")
    reason_code: AuditReasonCodeEnum = Field(
        AuditReasonCodeEnum.INCORRECT, description="Reason code"
    )
    reason_text: Optional[str] = Field(None, description="Reason text")


class FeedbackSubmission(BaseModel):
    """Request to submit feedback corrections."""

    corrections: List[FieldCorrectionModel] = Field(..., description="List of corrections")
    source: FeedbackSourceEnum = Field(
        FeedbackSourceEnum.UI, description="Feedback source"
    )


class FeedbackResponse(BaseModel):
    """Feedback submission response."""

    success: bool
    message: str
    result_version: int
    audits_created: int


class AuditRecordResponse(BaseModel):
    """Audit record response model."""

    id: int
    flow_id: int
    result_id: int
    result_version: int
    field_path: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    reason_code: int
    reason_text: Optional[str] = None
    audited_at: datetime

    class Config:
        from_attributes = True


class AuditHistoryResponse(BaseModel):
    """Audit history response model."""

    items: List[AuditRecordResponse]
    total: int
