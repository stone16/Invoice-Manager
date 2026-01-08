from __future__ import annotations

from datetime import datetime
from enum import IntEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import Identity, PrimaryKeyConstraint

from app.database import Base

try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover - dependency added in requirements
    Vector = None


class FileContentType(IntEnum):
    INVALID = 0
    PDF = 1
    EXCEL = 2
    IMAGE = 3


class SourceContentType(IntEnum):
    INVALID = 0
    FILE = 1
    TEXT = 2


class MainStatus(IntEnum):
    PENDING = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    FAILED = 3


class DataServiceStatus(IntEnum):
    NONE = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    FAILED = 3


class DataOrigin(IntEnum):
    SYSTEM = 0
    USER = 1


class ConfigStatus(IntEnum):
    ACTIVE = 1
    ARCHIVED = 2


class FeedbackSource(IntEnum):
    UI = 1
    API = 2
    AUTO = 3


class AuditReasonCode(IntEnum):
    INCORRECT = 1
    MISSING = 2
    EXTRA = 3
    FORMAT = 4
    DATA_SOURCE = 5
    OTHER = 99


class DigiFlowSchema(Base):
    __tablename__ = "digi_flow_schema"

    id = Column(BigInteger, Identity(), nullable=False)
    slug = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False, default="Unnamed Schema")
    yaml_schema = Column(Text, nullable=True)
    schema = Column(JSONB, nullable=False, default=dict)
    version = Column(Integer, nullable=False, default=1)
    status = Column(Integer, nullable=False, default=ConfigStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(JSONB, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(JSONB, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(JSONB, nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint("id", "version"),
    )


class DigiFlowConfig(Base):
    __tablename__ = "digi_flow_config"

    id = Column(BigInteger, Identity(), primary_key=True)
    slug = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    domain = Column(String(64), nullable=True)
    schema_id = Column(BigInteger, nullable=False)
    schema_version = Column(Integer, nullable=False)
    source_content_type = Column(Integer, nullable=False)
    workflow_config = Column(JSONB, nullable=True)
    prompt_config = Column(JSONB, nullable=True)
    schema_validation = Column(JSONB, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    status = Column(Integer, nullable=False, default=ConfigStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(JSONB, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(JSONB, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(JSONB, nullable=True)


class DigiFlow(Base):
    __tablename__ = "digi_flow"

    id = Column(BigInteger, Identity(), primary_key=True)
    config_id = Column(BigInteger, nullable=False)
    config_version = Column(Integer, nullable=False)
    schema_id = Column(BigInteger, nullable=False)
    schema_version = Column(Integer, nullable=False)
    content_type = Column(Integer, nullable=False)
    content_context = Column(JSONB, nullable=False, default=dict)
    content_metadata = Column(JSONB, nullable=True)
    langsmith_trace_id = Column(String, nullable=True)
    langsmith_metadata = Column(JSONB, nullable=True)
    main_status = Column(Integer, nullable=False, default=MainStatus.PENDING)
    data_service_status = Column(Integer, nullable=False, default=DataServiceStatus.NONE)
    schema_validation_status = Column(Integer, nullable=False, default=0)
    schema_validation_result = Column(JSONB, nullable=True)
    extra_attributes = Column(JSONB, nullable=True)
    metadata_json = Column("metadata", JSONB, nullable=True)
    is_sampled = Column(Boolean, nullable=True, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(JSONB, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(JSONB, nullable=True)


class DigiFlowResult(Base):
    __tablename__ = "digi_flow_result"

    id = Column(BigInteger, Identity(), primary_key=True)
    flow_id = Column(BigInteger, nullable=False)
    data = Column(JSONB, nullable=False, default=dict)
    plain_data = Column(JSONB, nullable=True)
    text_blocks = Column(JSONB, nullable=True)
    data_origin = Column(Integer, nullable=False, default=DataOrigin.SYSTEM)
    version = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_by = Column(JSONB, nullable=True)


class RagTrainingDataVector(Base):
    __tablename__ = "rag_training_data_vector"

    id = Column(BigInteger, Identity(), primary_key=True)
    flow_id = Column(BigInteger, nullable=False)
    config_id = Column(BigInteger, nullable=False)
    schema_id = Column(BigInteger, nullable=False)
    schema_version = Column(Integer, nullable=False)
    result_id = Column(BigInteger, nullable=False)
    result_version = Column(Integer, nullable=False)
    source_content_context = Column(JSONB, nullable=False, default=dict)
    source_content_context_idx = Column(Integer, nullable=False, default=0)
    reference_input = Column(JSONB, nullable=False)
    reference_output = Column(JSONB, nullable=False)
    embedding = Column(Vector(1536) if Vector is not None else String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(JSONB, nullable=True)


class DigiFlowResultFieldAudit(Base):
    __tablename__ = "digi_flow_result_field_audit"

    id = Column(BigInteger, Identity(), primary_key=True)
    flow_id = Column(BigInteger, nullable=False)
    result_id = Column(BigInteger, nullable=False)
    result_version = Column(Integer, nullable=False)
    field_path = Column(String, nullable=False)
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    reason_code = Column(Integer, nullable=False)
    reason_text = Column(String, nullable=True)
    audited_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    audited_by = Column(JSONB, nullable=True)
