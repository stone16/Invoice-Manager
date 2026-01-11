"""API router for schema and config management."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.digi_flow import ConfigStatus
from app.schemas.digi_flow import (
    ConfigCreate,
    ConfigListResponse,
    ConfigResponse,
    ConfigUpdate,
    SchemaCreate,
    SchemaListResponse,
    SchemaResponse,
    SchemaUpdate,
)
from app.services.schema_management import (
    archive_config,
    archive_schema,
    create_config,
    create_schema,
    create_schema_from_yaml,
    get_config,
    get_schema,
    list_configs,
    list_schemas,
    update_config,
    update_schema,
)

router = APIRouter()


# Schema endpoints


import logging as _logging

_logger = _logging.getLogger(__name__)


@router.post("/schemas", response_model=SchemaResponse)
async def create_schema_endpoint(
    schema_data: SchemaCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new schema."""
    try:
        # Debug: log the incoming data
        _logger.warning(f"=== POST /schemas ===")
        _logger.warning(f"slug: {schema_data.slug}")
        _logger.warning(f"name: {schema_data.name}")
        _logger.warning(f"yaml_schema: {schema_data.yaml_schema[:100] if schema_data.yaml_schema else None}...")
        _logger.warning(f"schema_json: {schema_data.schema_json}")
        
        # Use explicit 'is not None' checks because empty dict {} is falsy in Python
        has_yaml = schema_data.yaml_schema is not None and schema_data.yaml_schema.strip()
        has_json = schema_data.schema_json is not None
        
        _logger.warning(f"has_yaml: {has_yaml}, has_json: {has_json}")

        if has_yaml and not has_json:
            # Only YAML provided - parse it to JSON
            result = await create_schema_from_yaml(
                db=db,
                slug=schema_data.slug,
                name=schema_data.name,
                yaml_text=schema_data.yaml_schema,
            )
        elif has_json:
            # JSON schema provided (may also have YAML for display)
            result = await create_schema(
                db=db,
                slug=schema_data.slug,
                name=schema_data.name,
                schema=schema_data.schema_json,
                yaml_schema=schema_data.yaml_schema,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Either schema or yaml_schema must be provided",
            )
        await db.commit()
        return SchemaResponse.from_orm_model(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/schemas", response_model=SchemaListResponse)
async def list_schemas_endpoint(
    status: Optional[int] = Query(None, description="Status filter (1=ACTIVE, 2=ARCHIVED)"),
    include_all_versions: bool = Query(False, description="Include all versions"),
    db: AsyncSession = Depends(get_db),
):
    """List all schemas."""
    status_enum = ConfigStatus(status) if status is not None else None
    schemas = await list_schemas(
        db=db,
        status=status_enum,
        include_all_versions=include_all_versions,
    )
    return SchemaListResponse(
        items=[SchemaResponse.from_orm_model(s) for s in schemas],
        total=len(schemas),
    )


@router.get("/schemas/{schema_id}", response_model=SchemaResponse)
async def get_schema_endpoint(
    schema_id: int,
    version: Optional[int] = Query(None, description="Specific version"),
    db: AsyncSession = Depends(get_db),
):
    """Get a schema by ID."""
    result = await get_schema(db=db, schema_id=schema_id, version=version)
    if not result:
        raise HTTPException(status_code=404, detail="Schema not found")
    return SchemaResponse.from_orm_model(result)


@router.put("/schemas/{schema_id}", response_model=SchemaResponse)
async def update_schema_endpoint(
    schema_id: int,
    schema_data: SchemaUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a schema."""
    try:
        result = await update_schema(
            db=db,
            schema_id=schema_id,
            schema=schema_data.schema_json,
            yaml_schema=schema_data.yaml_schema,
            name=schema_data.name,
            create_new_version=schema_data.create_new_version,
        )
        if not result:
            raise HTTPException(status_code=404, detail="Schema not found")
        await db.commit()
        return SchemaResponse.from_orm_model(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/schemas/{schema_id}")
async def delete_schema_endpoint(
    schema_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Archive a schema (soft delete)."""
    success = await archive_schema(db=db, schema_id=schema_id)
    if not success:
        raise HTTPException(status_code=404, detail="Schema not found")
    await db.commit()
    return {"message": "Schema archived successfully"}


# Config endpoints


@router.post("/configs", response_model=ConfigResponse)
async def create_config_endpoint(
    config_data: ConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new config."""
    result = await create_config(
        db=db,
        slug=config_data.slug,
        name=config_data.name,
        schema_id=config_data.schema_id,
        schema_version=config_data.schema_version,
        source_content_type=config_data.source_content_type,
        description=config_data.description,
        domain=config_data.domain,
        workflow_config=config_data.workflow_config.model_dump() if config_data.workflow_config else None,
        prompt_config=config_data.prompt_config.model_dump() if config_data.prompt_config else None,
        schema_validation=config_data.schema_validation,
    )
    await db.commit()
    return ConfigResponse.model_validate(result)


@router.get("/configs", response_model=ConfigListResponse)
async def list_configs_endpoint(
    status: Optional[int] = Query(None, description="Status filter (1=ACTIVE, 2=ARCHIVED)"),
    domain: Optional[str] = Query(None, description="Domain filter"),
    schema_id: Optional[int] = Query(None, description="Schema ID filter"),
    include_all_versions: bool = Query(False, description="Include all versions"),
    db: AsyncSession = Depends(get_db),
):
    """List all configs."""
    status_enum = ConfigStatus(status) if status is not None else None
    configs = await list_configs(
        db=db,
        status=status_enum,
        domain=domain,
        schema_id=schema_id,
        include_all_versions=include_all_versions,
    )
    return ConfigListResponse(
        items=[ConfigResponse.model_validate(c) for c in configs],
        total=len(configs),
    )


@router.get("/configs/{config_id}", response_model=ConfigResponse)
async def get_config_endpoint(
    config_id: int,
    version: Optional[int] = Query(None, description="Specific version"),
    db: AsyncSession = Depends(get_db),
):
    """Get a config by ID."""
    result = await get_config(db=db, config_id=config_id, version=version)
    if not result:
        raise HTTPException(status_code=404, detail="Config not found")
    return ConfigResponse.model_validate(result)


@router.put("/configs/{config_id}", response_model=ConfigResponse)
async def update_config_endpoint(
    config_id: int,
    config_data: ConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a config."""
    result = await update_config(
        db=db,
        config_id=config_id,
        name=config_data.name,
        description=config_data.description,
        domain=config_data.domain,
        schema_id=config_data.schema_id,
        schema_version=config_data.schema_version,
        workflow_config=config_data.workflow_config.model_dump() if config_data.workflow_config else None,
        prompt_config=config_data.prompt_config.model_dump() if config_data.prompt_config else None,
        schema_validation=config_data.schema_validation,
        create_new_version=config_data.create_new_version,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Config not found")
    await db.commit()
    return ConfigResponse.model_validate(result)


@router.delete("/configs/{config_id}")
async def delete_config_endpoint(
    config_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Archive a config (soft delete)."""
    success = await archive_config(db=db, config_id=config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Config not found")
    await db.commit()
    return {"message": "Config archived successfully"}
