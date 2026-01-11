"""Config management service for CRUD operations."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.digi_flow import ConfigStatus, DigiFlowConfig, SourceContentType
from app.services.schema_management.schema_versioning import next_schema_version

logger = logging.getLogger(__name__)


async def create_config(
    db: AsyncSession,
    slug: str,
    name: str,
    schema_id: int,
    schema_version: int,
    source_content_type: SourceContentType = SourceContentType.FILE,
    description: Optional[str] = None,
    domain: Optional[str] = None,
    workflow_config: Optional[Dict[str, Any]] = None,
    prompt_config: Optional[Dict[str, Any]] = None,
    schema_validation: Optional[Dict[str, Any]] = None,
    created_by: Optional[Dict[str, Any]] = None,
) -> DigiFlowConfig:
    """Create a new config.

    Args:
        db: Database session
        slug: Unique slug identifier
        name: Human-readable name
        schema_id: Associated schema ID
        schema_version: Associated schema version
        source_content_type: Content type (FILE or TEXT)
        description: Optional description
        domain: Optional domain category
        workflow_config: Workflow configuration (RAG, model, processing)
        prompt_config: Prompt configuration (task, instructions)
        schema_validation: Schema validation settings
        created_by: Optional creator info

    Returns:
        Created config record
    """
    existing = await get_config_by_slug(db, slug)
    if existing:
        raise ValueError(f"Config with slug '{slug}' already exists")

    new_config = DigiFlowConfig(
        slug=slug,
        name=name,
        description=description,
        domain=domain,
        schema_id=schema_id,
        schema_version=schema_version,
        source_content_type=source_content_type,
        workflow_config=workflow_config or _default_workflow_config(),
        prompt_config=prompt_config or _default_prompt_config(),
        schema_validation=schema_validation,
        version=1,
        status=ConfigStatus.ACTIVE,
        created_at=datetime.utcnow(),
        created_by=created_by,
    )
    db.add(new_config)
    await db.flush()
    await db.refresh(new_config)
    return new_config


def _default_workflow_config() -> Dict[str, Any]:
    """Return default workflow configuration."""
    return {
        "rag": {
            "enabled": True,
            "distance_threshold": 0.3,
            "max_examples": 3,
        },
        "model": {
            "provider": "openai",
            "model_name": "gpt-4o",
            "temperature": 0.0,
            "max_tokens": 4096,
        },
        "processing": {
            "token_optimization": True,
            "max_token_budget": 8000,
        },
    }


def _default_prompt_config() -> Dict[str, Any]:
    """Return default prompt configuration."""
    return {
        "task": "Extract structured data from the document",
        "instructions": "",
        "zero_shot_example": None,
    }


async def get_config(
    db: AsyncSession,
    config_id: int,
    version: Optional[int] = None,
) -> Optional[DigiFlowConfig]:
    """Get a config by ID.

    Args:
        db: Database session
        config_id: Config ID
        version: Optional specific version (defaults to latest)

    Returns:
        Config record or None
    """
    query = select(DigiFlowConfig).where(DigiFlowConfig.id == config_id)
    if version is not None:
        query = query.where(DigiFlowConfig.version == version)
    else:
        query = query.order_by(DigiFlowConfig.version.desc())
    result = await db.execute(query)
    return result.scalar_one_or_none() if version is not None else result.scalars().first()


async def get_config_by_slug(
    db: AsyncSession,
    slug: str,
    version: Optional[int] = None,
) -> Optional[DigiFlowConfig]:
    """Get a config by slug.

    Args:
        db: Database session
        slug: Config slug
        version: Optional specific version (defaults to latest)

    Returns:
        Config record or None
    """
    query = select(DigiFlowConfig).where(DigiFlowConfig.slug == slug)
    if version is not None:
        query = query.where(DigiFlowConfig.version == version)
    else:
        query = query.order_by(DigiFlowConfig.version.desc())
    result = await db.execute(query)
    return result.scalar_one_or_none() if version is not None else result.scalars().first()


async def list_configs(
    db: AsyncSession,
    status: Optional[ConfigStatus] = None,
    domain: Optional[str] = None,
    schema_id: Optional[int] = None,
    include_all_versions: bool = False,
) -> List[DigiFlowConfig]:
    """List all configs.

    Args:
        db: Database session
        status: Optional status filter
        domain: Optional domain filter
        schema_id: Optional schema ID filter
        include_all_versions: Whether to include all versions

    Returns:
        List of config records
    """
    query = select(DigiFlowConfig)

    if status is not None:
        query = query.where(DigiFlowConfig.status == status)
    if domain is not None:
        query = query.where(DigiFlowConfig.domain == domain)
    if schema_id is not None:
        query = query.where(DigiFlowConfig.schema_id == schema_id)

    query = query.order_by(DigiFlowConfig.id, DigiFlowConfig.version.desc())
    result = await db.execute(query)
    configs = list(result.scalars().all())

    if include_all_versions:
        return configs

    seen_ids = set()
    latest_configs = []
    for config in configs:
        if config.id not in seen_ids:
            seen_ids.add(config.id)
            latest_configs.append(config)
    return latest_configs


async def update_config(
    db: AsyncSession,
    config_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    domain: Optional[str] = None,
    schema_id: Optional[int] = None,
    schema_version: Optional[int] = None,
    workflow_config: Optional[Dict[str, Any]] = None,
    prompt_config: Optional[Dict[str, Any]] = None,
    schema_validation: Optional[Dict[str, Any]] = None,
    create_new_version: bool = True,
    updated_by: Optional[Dict[str, Any]] = None,
) -> Optional[DigiFlowConfig]:
    """Update a config.

    Args:
        db: Database session
        config_id: Config ID to update
        name: New name (optional)
        description: New description (optional)
        domain: New domain (optional)
        schema_id: New schema ID (optional)
        schema_version: New schema version (optional)
        workflow_config: New workflow config (optional)
        prompt_config: New prompt config (optional)
        schema_validation: New validation settings (optional)
        create_new_version: Whether to create a new version
        updated_by: Optional updater info

    Returns:
        Updated config record or None
    """
    existing = await get_config(db, config_id)
    if not existing:
        return None

    if create_new_version:
        query = select(DigiFlowConfig.version).where(
            DigiFlowConfig.id == config_id
        )
        result = await db.execute(query)
        versions = [row[0] for row in result.all()]
        new_version = next_schema_version(versions)

        new_config = DigiFlowConfig(
            id=config_id,
            slug=existing.slug,
            name=name or existing.name,
            description=description if description is not None else existing.description,
            domain=domain if domain is not None else existing.domain,
            schema_id=schema_id if schema_id is not None else existing.schema_id,
            schema_version=schema_version if schema_version is not None else existing.schema_version,
            source_content_type=existing.source_content_type,
            workflow_config=workflow_config if workflow_config is not None else existing.workflow_config,
            prompt_config=prompt_config if prompt_config is not None else existing.prompt_config,
            schema_validation=schema_validation if schema_validation is not None else existing.schema_validation,
            version=new_version,
            status=ConfigStatus.ACTIVE,
            created_at=existing.created_at,
            created_by=existing.created_by,
            updated_at=datetime.utcnow(),
            updated_by=updated_by,
        )
        db.add(new_config)
        await db.flush()
        await db.refresh(new_config)
        return new_config

    if name is not None:
        existing.name = name
    if description is not None:
        existing.description = description
    if domain is not None:
        existing.domain = domain
    if schema_id is not None:
        existing.schema_id = schema_id
    if schema_version is not None:
        existing.schema_version = schema_version
    if workflow_config is not None:
        existing.workflow_config = workflow_config
    if prompt_config is not None:
        existing.prompt_config = prompt_config
    if schema_validation is not None:
        existing.schema_validation = schema_validation

    existing.updated_at = datetime.utcnow()
    existing.updated_by = updated_by

    await db.flush()
    await db.refresh(existing)
    return existing


async def archive_config(
    db: AsyncSession,
    config_id: int,
    deleted_by: Optional[Dict[str, Any]] = None,
) -> bool:
    """Archive a config (soft delete).

    Args:
        db: Database session
        config_id: Config ID to archive
        deleted_by: Optional deleter info

    Returns:
        True if archived, False if not found
    """
    query = select(DigiFlowConfig).where(DigiFlowConfig.id == config_id)
    result = await db.execute(query)
    configs = list(result.scalars().all())

    if not configs:
        return False

    for config in configs:
        config.status = ConfigStatus.ARCHIVED
        config.deleted_at = datetime.utcnow()
        config.deleted_by = deleted_by

    await db.flush()
    return True
