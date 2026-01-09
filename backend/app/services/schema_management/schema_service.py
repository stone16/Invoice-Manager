"""Schema management service for CRUD operations."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.digi_flow import ConfigStatus, DigiFlowSchema, _utc_now
from app.services.schema_management.schema_parser import parse_yaml_schema
from app.services.schema_management.schema_validator import validate_json_schema
from app.services.schema_management.schema_versioning import next_schema_version

logger = logging.getLogger(__name__)


async def create_schema(
    db: AsyncSession,
    slug: str,
    name: str,
    schema: Dict[str, Any],
    yaml_schema: Optional[str] = None,
    created_by: Optional[Dict[str, Any]] = None,
) -> DigiFlowSchema:
    """Create a new schema.

    Args:
        db: Database session
        slug: Unique slug identifier
        name: Human-readable name
        schema: JSON schema definition
        yaml_schema: Optional YAML representation
        created_by: Optional creator info

    Returns:
        Created schema record

    Raises:
        ValueError: If schema is invalid
    """
    validate_json_schema(schema)

    new_schema = DigiFlowSchema(
        slug=slug,
        name=name,
        schema=schema,
        yaml_schema=yaml_schema,
        version=1,
        status=ConfigStatus.ACTIVE,
        created_at=_utc_now(),
        created_by=created_by,
    )
    db.add(new_schema)
    await db.flush()
    await db.refresh(new_schema)
    return new_schema


async def create_schema_from_yaml(
    db: AsyncSession,
    slug: str,
    name: str,
    yaml_text: str,
    created_by: Optional[Dict[str, Any]] = None,
) -> DigiFlowSchema:
    """Create a new schema from YAML text.

    Args:
        db: Database session
        slug: Unique slug identifier
        name: Human-readable name
        yaml_text: YAML schema definition
        created_by: Optional creator info

    Returns:
        Created schema record
    """
    schema = parse_yaml_schema(yaml_text)
    return await create_schema(
        db=db,
        slug=slug,
        name=name,
        schema=schema,
        yaml_schema=yaml_text,
        created_by=created_by,
    )


async def get_schema(
    db: AsyncSession,
    schema_id: int,
    version: Optional[int] = None,
) -> Optional[DigiFlowSchema]:
    """Get a schema by ID and optional version.

    Args:
        db: Database session
        schema_id: Schema ID
        version: Optional specific version (defaults to latest)

    Returns:
        Schema record or None
    """
    query = select(DigiFlowSchema).where(DigiFlowSchema.id == schema_id)
    if version is not None:
        query = query.where(DigiFlowSchema.version == version)
    else:
        query = query.order_by(DigiFlowSchema.version.desc())
    result = await db.execute(query)
    return result.scalar_one_or_none() if version is not None else result.scalars().first()


async def get_schema_by_slug(
    db: AsyncSession,
    slug: str,
    version: Optional[int] = None,
) -> Optional[DigiFlowSchema]:
    """Get a schema by slug and optional version.

    Args:
        db: Database session
        slug: Schema slug
        version: Optional specific version (defaults to latest)

    Returns:
        Schema record or None
    """
    query = select(DigiFlowSchema).where(DigiFlowSchema.slug == slug)
    if version is not None:
        query = query.where(DigiFlowSchema.version == version)
    else:
        query = query.order_by(DigiFlowSchema.version.desc())
    result = await db.execute(query)
    return result.scalar_one_or_none() if version is not None else result.scalars().first()


async def list_schemas(
    db: AsyncSession,
    status: Optional[ConfigStatus] = None,
    include_all_versions: bool = False,
) -> List[DigiFlowSchema]:
    """List all schemas.

    Args:
        db: Database session
        status: Optional status filter
        include_all_versions: Whether to include all versions

    Returns:
        List of schema records
    """
    query = select(DigiFlowSchema)
    if status is not None:
        query = query.where(DigiFlowSchema.status == status)

    query = query.order_by(DigiFlowSchema.id, DigiFlowSchema.version.desc())
    result = await db.execute(query)
    schemas = list(result.scalars().all())

    if not include_all_versions:
        seen_ids = set()
        latest_schemas = []
        for schema in schemas:
            if schema.id not in seen_ids:
                seen_ids.add(schema.id)
                latest_schemas.append(schema)
        return latest_schemas

    return schemas


async def update_schema(
    db: AsyncSession,
    schema_id: int,
    schema: Optional[Dict[str, Any]] = None,
    yaml_schema: Optional[str] = None,
    name: Optional[str] = None,
    create_new_version: bool = True,
    updated_by: Optional[Dict[str, Any]] = None,
) -> Optional[DigiFlowSchema]:
    """Update a schema.

    Args:
        db: Database session
        schema_id: Schema ID to update
        schema: New JSON schema (optional)
        yaml_schema: New YAML schema (optional)
        name: New name (optional)
        create_new_version: Whether to create new version
        updated_by: Optional updater info

    Returns:
        Updated schema record or None
    """
    existing = await get_schema(db, schema_id)
    if not existing:
        return None

    if schema is not None:
        validate_json_schema(schema)

    if create_new_version:
        query = select(DigiFlowSchema.version).where(
            DigiFlowSchema.id == schema_id
        )
        result = await db.execute(query)
        versions = [row[0] for row in result.all()]
        new_version = next_schema_version(versions)

        new_schema = DigiFlowSchema(
            id=schema_id,
            slug=existing.slug,
            name=name or existing.name,
            schema=schema or existing.schema,
            yaml_schema=yaml_schema or existing.yaml_schema,
            version=new_version,
            status=ConfigStatus.ACTIVE,
            created_at=existing.created_at,
            created_by=existing.created_by,
            updated_at=_utc_now(),
            updated_by=updated_by,
        )
        db.add(new_schema)
        await db.flush()
        await db.refresh(new_schema)
        return new_schema
    else:
        if schema is not None:
            existing.schema = schema
        if yaml_schema is not None:
            existing.yaml_schema = yaml_schema
        if name is not None:
            existing.name = name
        existing.updated_at = _utc_now()
        existing.updated_by = updated_by
        await db.flush()
        await db.refresh(existing)
        return existing


async def archive_schema(
    db: AsyncSession,
    schema_id: int,
    deleted_by: Optional[Dict[str, Any]] = None,
) -> bool:
    """Archive a schema (soft delete).

    Args:
        db: Database session
        schema_id: Schema ID to archive
        deleted_by: Optional deleter info

    Returns:
        True if archived, False if not found
    """
    query = select(DigiFlowSchema).where(DigiFlowSchema.id == schema_id)
    result = await db.execute(query)
    schemas = list(result.scalars().all())

    if not schemas:
        return False

    for schema in schemas:
        schema.status = ConfigStatus.ARCHIVED
        schema.deleted_at = _utc_now()
        schema.deleted_by = deleted_by

    await db.flush()
    return True
