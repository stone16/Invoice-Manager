"""API router for digitization flow management."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.digi_flow import (
    DigiFlow,
    DigiFlowConfig,
    DigiFlowResult,
    DigiFlowResultFieldAudit,
    DigiFlowSchema,
    MainStatus,
)
from app.schemas.digi_flow import (
    AuditHistoryResponse,
    AuditRecordResponse,
    ConfigResponse,
    FlowListResponse,
    FlowResponse,
    FlowResultResponse,
    FlowWithResultResponse,
    SchemaResponse,
)

router = APIRouter()


@router.get("/flows", response_model=FlowListResponse)
async def list_flows(
    config_id: Optional[int] = Query(None, description="Filter by config ID"),
    status: Optional[int] = Query(None, description="Filter by main status"),
    limit: int = Query(50, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
):
    """List digitization flows with optional filtering."""
    # Build query
    query = select(DigiFlow).order_by(desc(DigiFlow.created_at))

    if config_id is not None:
        query = query.where(DigiFlow.config_id == config_id)
    if status is not None:
        query = query.where(DigiFlow.main_status == status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    flows = result.scalars().all()

    # Build response with results
    items = []
    for flow in flows:
        # Get latest result for this flow
        result_query = (
            select(DigiFlowResult)
            .where(DigiFlowResult.flow_id == flow.id)
            .order_by(desc(DigiFlowResult.version))
            .limit(1)
        )
        result_result = await db.execute(result_query)
        flow_result = result_result.scalar_one_or_none()

        flow_response = FlowWithResultResponse(
            id=flow.id,
            config_id=flow.config_id,
            config_version=flow.config_version,
            schema_id=flow.schema_id,
            schema_version=flow.schema_version,
            content_type=flow.content_type,
            content_context=flow.content_context or {},
            content_metadata=flow.content_metadata,
            langsmith_trace_id=flow.langsmith_trace_id,
            main_status=flow.main_status,
            data_service_status=flow.data_service_status,
            schema_validation_status=flow.schema_validation_status,
            schema_validation_result=flow.schema_validation_result,
            created_at=flow.created_at,
            updated_at=flow.updated_at,
            result=FlowResultResponse(
                id=flow_result.id,
                flow_id=flow_result.flow_id,
                data=flow_result.data or {},
                plain_data=flow_result.plain_data,
                text_blocks=flow_result.text_blocks,
                data_origin=flow_result.data_origin,
                version=flow_result.version,
                updated_at=flow_result.updated_at,
            ) if flow_result else None,
        )
        items.append(flow_response)

    return FlowListResponse(items=items, total=total)


@router.get("/flows/{flow_id}", response_model=FlowWithResultResponse)
async def get_flow(
    flow_id: int,
    include_config: bool = Query(False, description="Include config details"),
    include_schema: bool = Query(False, description="Include schema details"),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific flow with its latest result."""
    # Get flow
    query = select(DigiFlow).where(DigiFlow.id == flow_id)
    result = await db.execute(query)
    flow = result.scalar_one_or_none()

    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    # Get latest result
    result_query = (
        select(DigiFlowResult)
        .where(DigiFlowResult.flow_id == flow_id)
        .order_by(desc(DigiFlowResult.version))
        .limit(1)
    )
    result_result = await db.execute(result_query)
    flow_result = result_result.scalar_one_or_none()

    # Build response
    response_data = {
        "id": flow.id,
        "config_id": flow.config_id,
        "config_version": flow.config_version,
        "schema_id": flow.schema_id,
        "schema_version": flow.schema_version,
        "content_type": flow.content_type,
        "content_context": flow.content_context or {},
        "content_metadata": flow.content_metadata,
        "langsmith_trace_id": flow.langsmith_trace_id,
        "main_status": flow.main_status,
        "data_service_status": flow.data_service_status,
        "schema_validation_status": flow.schema_validation_status,
        "schema_validation_result": flow.schema_validation_result,
        "created_at": flow.created_at,
        "updated_at": flow.updated_at,
        "result": FlowResultResponse(
            id=flow_result.id,
            flow_id=flow_result.flow_id,
            data=flow_result.data or {},
            plain_data=flow_result.plain_data,
            text_blocks=flow_result.text_blocks,
            data_origin=flow_result.data_origin,
            version=flow_result.version,
            updated_at=flow_result.updated_at,
        ) if flow_result else None,
    }

    # Optionally include config
    if include_config:
        config_query = (
            select(DigiFlowConfig)
            .where(
                DigiFlowConfig.id == flow.config_id,
                DigiFlowConfig.version == flow.config_version,
            )
        )
        config_result = await db.execute(config_query)
        config = config_result.scalar_one_or_none()
        if config:
            response_data["config"] = ConfigResponse.model_validate(config)

    # Optionally include schema
    if include_schema:
        schema_query = (
            select(DigiFlowSchema)
            .where(
                DigiFlowSchema.id == flow.schema_id,
                DigiFlowSchema.version == flow.schema_version,
            )
        )
        schema_result = await db.execute(schema_query)
        schema = schema_result.scalar_one_or_none()
        if schema:
            response_data["schema"] = SchemaResponse.from_orm_model(schema)

    return FlowWithResultResponse(**response_data)


@router.get("/flows/{flow_id}/audit", response_model=AuditHistoryResponse)
async def get_flow_audit_history(
    flow_id: int,
    field_path: Optional[str] = Query(None, description="Filter by field path"),
    limit: int = Query(100, le=500, description="Maximum results"),
    db: AsyncSession = Depends(get_db),
):
    """Get audit history for a flow."""
    # Verify flow exists
    flow_query = select(DigiFlow.id).where(DigiFlow.id == flow_id)
    flow_result = await db.execute(flow_query)
    if not flow_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Flow not found")

    # Build audit query
    query = (
        select(DigiFlowResultFieldAudit)
        .where(DigiFlowResultFieldAudit.flow_id == flow_id)
        .order_by(desc(DigiFlowResultFieldAudit.audited_at))
    )

    if field_path:
        query = query.where(DigiFlowResultFieldAudit.field_path == field_path)

    query = query.limit(limit)

    result = await db.execute(query)
    audits = result.scalars().all()

    items = [
        AuditRecordResponse(
            id=audit.id,
            flow_id=audit.flow_id,
            result_id=audit.result_id,
            result_version=audit.result_version,
            field_path=audit.field_path,
            old_value=audit.old_value,
            new_value=audit.new_value,
            reason_code=audit.reason_code,
            reason_text=audit.reason_text,
            audited_at=audit.audited_at,
        )
        for audit in audits
    ]

    return AuditHistoryResponse(items=items, total=len(items))
