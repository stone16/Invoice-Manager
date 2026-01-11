"""API router for digitization flow management."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.digi_flow import (
    DataOrigin,
    DigiFlow,
    DigiFlowConfig,
    DigiFlowResult,
    DigiFlowResultFieldAudit,
    DigiFlowSchema,
    FileContentType,
    MainStatus,
)
from app.schemas.digi_flow import (
    AuditHistoryResponse,
    AuditRecordResponse,
    ConfigResponse,
    FeedbackResponse,
    FeedbackSubmission,
    FlowCreate,
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


def _detect_content_type(file_name: str) -> FileContentType:
    """Detect file content type from filename extension."""
    ext = file_name.split(".")[-1].lower()
    if ext == "pdf":
        return FileContentType.PDF
    if ext in {"xlsx", "xls"}:
        return FileContentType.EXCEL
    if ext in {"png", "jpg", "jpeg", "bmp", "tiff"}:
        return FileContentType.IMAGE
    return FileContentType.INVALID


def _get_nested_value(data: Dict[str, Any], path: str) -> Any:
    """Get a nested value from a dict using dot notation path."""
    keys = path.split(".")
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    return current


def _set_nested_value(data: Dict[str, Any], path: str, value: Any) -> None:
    """Set a nested value in a dict using dot notation path."""
    keys = path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


@router.post("/flows", response_model=FlowWithResultResponse)
async def create_flow(
    flow_data: FlowCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a flow from content context (text or file reference).

    This endpoint is useful for:
    - Processing pre-extracted text content
    - Testing extraction with sample text
    - Integration with other systems that provide text directly
    """
    config_id = flow_data.config_id
    content_type = flow_data.content_type.value
    content_context = flow_data.content_context

    # Extract text from content context
    text = content_context.text
    file_name = content_context.file_name or "document.txt"

    # Get config and validate
    config_query = (
        select(DigiFlowConfig)
        .where(DigiFlowConfig.id == config_id)
        .order_by(desc(DigiFlowConfig.version))
        .limit(1)
    )
    config_result = await db.execute(config_query)
    config = config_result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    # Get schema
    schema_query = select(DigiFlowSchema).where(
        DigiFlowSchema.id == config.schema_id,
        DigiFlowSchema.version == config.schema_version,
    )
    schema_result = await db.execute(schema_query)
    schema_obj = schema_result.scalar_one_or_none()

    if not schema_obj:
        raise HTTPException(status_code=404, detail="Schema not found")

    # Create flow record
    flow = DigiFlow(
        config_id=config.id,
        config_version=config.version,
        schema_id=config.schema_id,
        schema_version=config.schema_version,
        content_type=content_type,
        content_context={
            "file_path": content_context.file_path,
            "file_name": file_name,
            "file_type": content_context.file_type,
            "text": text[:1000] if text else None,  # Store preview
            "pages": content_context.pages,
        },
        main_status=MainStatus.IN_PROGRESS.value,
    )
    db.add(flow)
    await db.flush()

    flow_result = None
    try:
        # Initialize services
        from app.services.llm.client_factory import create_llm_client
        from app.services.llm.executor import DigitizationExecutor
        from app.services.rag.rag_service import RAGService
        from app.services.rag.vector_repository import VectorRepository

        vector_repo = VectorRepository(db)
        rag_service = RAGService(vector_repo=vector_repo)

        # Get configs
        workflow_config = config.workflow_config or {}
        model_config = workflow_config.get("model", {})
        rag_config = workflow_config.get("rag", {})
        prompt_config = config.prompt_config or {}

        llm_client = create_llm_client(model_config)
        executor = DigitizationExecutor(llm_client=llm_client, rag_service=rag_service)

        # Build content for executor
        content = {
            "plain_text": text or "",
            "text_blocks": [],
            "file_name": file_name,
            "content_type": content_type,
        }

        # Execute LLM extraction
        extraction_result = await executor.execute(
            content=content,
            schema=schema_obj.schema,
            config_id=config.id,
            prompt_config=prompt_config,
            rag_config=rag_config,
            document_name=file_name,
        )

        # Update flow metadata
        flow.langsmith_trace_id = extraction_result.get("trace_id")

        # Determine status
        if extraction_result.get("status") == "success":
            flow.main_status = MainStatus.COMPLETED.value
        elif extraction_result.get("status") == "review_required":
            flow.main_status = MainStatus.COMPLETED.value
        else:
            flow.main_status = MainStatus.FAILED.value

        # Create result record
        flow_result = DigiFlowResult(
            flow_id=flow.id,
            data=extraction_result.get("data", {}),
            plain_data={"plain_text": (text or "")[:5000]},
            text_blocks=[],
            data_origin=DataOrigin.SYSTEM.value,
            version=1,
        )
        db.add(flow_result)

    except Exception as e:
        flow.main_status = MainStatus.FAILED.value
        flow.content_metadata = {"error": str(e)}

    await db.flush()
    await db.commit()

    # Build response
    return FlowWithResultResponse(
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


@router.post("/flows/upload", response_model=List[FlowWithResultResponse])
async def upload_flows(
    config_id: int = Form(..., description="Configuration ID to use"),
    files: List[UploadFile] = File(..., description="Files to process"),
    db: AsyncSession = Depends(get_db),
):
    """Upload files and create digitization flows.

    This endpoint:
    1. Validates the config exists and gets schema
    2. For each file: normalizes content, runs LLM extraction, stores result
    3. Returns created flows with their extraction results
    """
    # Get config and validate
    config_query = (
        select(DigiFlowConfig)
        .where(DigiFlowConfig.id == config_id)
        .order_by(desc(DigiFlowConfig.version))
        .limit(1)
    )
    config_result = await db.execute(config_query)
    config = config_result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    # Get schema
    schema_query = select(DigiFlowSchema).where(
        DigiFlowSchema.id == config.schema_id,
        DigiFlowSchema.version == config.schema_version,
    )
    schema_result = await db.execute(schema_query)
    schema_obj = schema_result.scalar_one_or_none()

    if not schema_obj:
        raise HTTPException(status_code=404, detail="Schema not found")

    # Initialize services
    from app.services.content_normalizer.normalizer import ContentNormalizer
    from app.services.llm.client_factory import create_llm_client
    from app.services.llm.executor import DigitizationExecutor
    from app.services.rag.rag_service import RAGService
    from app.services.rag.vector_repository import VectorRepository

    normalizer = ContentNormalizer()
    vector_repo = VectorRepository(db)
    rag_service = RAGService(vector_repo=vector_repo)

    # Get model config from workflow config
    workflow_config = config.workflow_config or {}
    model_config = workflow_config.get("model", {})
    rag_config = workflow_config.get("rag", {})
    prompt_config = config.prompt_config or {}

    llm_client = create_llm_client(model_config)
    executor = DigitizationExecutor(llm_client=llm_client, rag_service=rag_service)

    results = []

    for idx, file in enumerate(files):
        # Read file content
        file_bytes = await file.read()
        file_name = file.filename or f"document_{idx}"
        file_object_fid = str(uuid.uuid4())

        # Detect content type
        content_type = _detect_content_type(file_name)
        if content_type == FileContentType.INVALID:
            continue  # Skip unsupported files

        # Create flow record
        flow = DigiFlow(
            config_id=config.id,
            config_version=config.version,
            schema_id=config.schema_id,
            schema_version=config.schema_version,
            content_type=content_type.value,
            content_context={
                "file_name": file_name,
                "file_object_fid": file_object_fid,
            },
            main_status=MainStatus.IN_PROGRESS.value,
        )
        db.add(flow)
        await db.flush()  # Get flow.id

        try:
            # Normalize content
            metadata = normalizer.normalize(
                file_bytes=file_bytes,
                file_name=file_name,
                file_object_fid=file_object_fid,
                doc_index=idx + 1,
            )

            # Build content for executor
            text_blocks = []
            plain_text_parts = []

            if hasattr(metadata.file_content, "pages"):
                for page in metadata.file_content.pages:
                    for box in page.bounding_boxes:
                        text_blocks.append({
                            "block_id": box.id,
                            "text": box.raw_value,
                            "page": page.id,
                        })
                        plain_text_parts.append(box.raw_value)
            elif hasattr(metadata.file_content, "sheets"):
                for sheet in metadata.file_content.sheets:
                    for box in sheet.bounding_boxes:
                        text_blocks.append({
                            "block_id": box.id,
                            "text": box.raw_value,
                            "sheet": sheet.name,
                        })
                        plain_text_parts.append(box.raw_value)

            content = {
                "plain_text": "\n".join(plain_text_parts),
                "text_blocks": text_blocks,
                "file_name": file_name,
                "content_type": content_type.value,
            }

            # Execute LLM extraction
            extraction_result = await executor.execute(
                content=content,
                schema=schema_obj.schema,
                config_id=config.id,
                prompt_config=prompt_config,
                rag_config=rag_config,
                document_name=file_name,
            )

            # Update flow metadata
            flow.content_metadata = {
                "file_bytes_size": metadata.file_bytes_size,
                "pages": len(metadata.file_content.pages) if hasattr(metadata.file_content, "pages") else 0,
                "sheets": len(metadata.file_content.sheets) if hasattr(metadata.file_content, "sheets") else 0,
            }
            flow.langsmith_trace_id = extraction_result.get("trace_id")

            # Determine status
            if extraction_result.get("status") == "success":
                flow.main_status = MainStatus.COMPLETED.value
            elif extraction_result.get("status") == "review_required":
                flow.main_status = MainStatus.COMPLETED.value
            else:
                flow.main_status = MainStatus.FAILED.value

            # Create result record
            flow_result = DigiFlowResult(
                flow_id=flow.id,
                data=extraction_result.get("data", {}),
                plain_data={"plain_text": content["plain_text"][:5000]},
                text_blocks=text_blocks,
                data_origin=DataOrigin.SYSTEM.value,
                version=1,
            )
            db.add(flow_result)

        except Exception as e:
            flow.main_status = MainStatus.FAILED.value
            flow.content_metadata = {"error": str(e)}
            flow_result = None

        await db.flush()

        # Build response
        response = FlowWithResultResponse(
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
        results.append(response)

    await db.commit()
    return results


@router.post("/flows/{flow_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    flow_id: int,
    feedback: FeedbackSubmission,
    store_to_rag: bool = Query(True, description="Store confirmed data to RAG training"),
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback/corrections for a flow's extraction result.

    This endpoint:
    1. Creates a new result version with corrections applied
    2. Logs field-level audit records for each correction
    3. Optionally stores the confirmed data to VectorDB for RAG training
    """
    # Get flow
    flow_query = select(DigiFlow).where(DigiFlow.id == flow_id)
    flow_result = await db.execute(flow_query)
    flow = flow_result.scalar_one_or_none()

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
    current_result = result_result.scalar_one_or_none()

    if not current_result:
        raise HTTPException(status_code=404, detail="No result found for this flow")

    # Apply corrections and create new version
    new_data = dict(current_result.data) if current_result.data else {}
    audits_created = 0

    for correction in feedback.corrections:
        old_value = _get_nested_value(new_data, correction.field_path)
        _set_nested_value(new_data, correction.field_path, correction.new_value)

        # Create audit record
        audit = DigiFlowResultFieldAudit(
            flow_id=flow_id,
            result_id=current_result.id,
            result_version=current_result.version,
            field_path=correction.field_path,
            old_value=old_value,
            new_value=correction.new_value,
            reason_code=correction.reason_code.value,
            reason_text=correction.reason_text,
        )
        db.add(audit)
        audits_created += 1

    # Create new result version
    new_version = current_result.version + 1
    new_result = DigiFlowResult(
        flow_id=flow_id,
        data=new_data,
        plain_data=current_result.plain_data,
        text_blocks=current_result.text_blocks,
        data_origin=DataOrigin.USER.value,
        version=new_version,
    )
    db.add(new_result)

    # Update flow timestamp
    flow.updated_at = datetime.utcnow()

    await db.flush()

    # Store to RAG if requested
    if store_to_rag:
        try:
            from app.services.rag.rag_service import RAGService
            from app.services.rag.vector_repository import VectorRepository

            vector_repo = VectorRepository(db)
            rag_service = RAGService(vector_repo=vector_repo)

            # Get plain text from result
            plain_text = ""
            if current_result.plain_data:
                plain_text = current_result.plain_data.get("plain_text", "")

            await rag_service.store_training_data(
                flow_id=flow_id,
                config_id=flow.config_id,
                content=plain_text,
                extraction_result=new_data,
                text_blocks=current_result.text_blocks,
                schema_id=flow.schema_id,
                schema_version=flow.schema_version,
                result_id=new_result.id,
                result_version=new_version,
            )
        except Exception:
            # Don't fail the feedback submission if RAG storage fails
            pass

    await db.commit()

    return FeedbackResponse(
        success=True,
        message=f"Applied {audits_created} corrections, created result version {new_version}",
        result_version=new_version,
        audits_created=audits_created,
    )
