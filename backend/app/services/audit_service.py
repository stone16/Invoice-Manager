"""Audit logging service for tracking all system changes."""

import logging
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


async def log_audit(
    db: AsyncSession,
    entity_type: str,
    entity_id: int,
    action: str,
    old_value: Optional[Dict[str, Any]] = None,
    new_value: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[str] = None,
) -> AuditLog:
    """Log an audit event.

    Args:
        db: Database session
        entity_type: Type of entity (e.g., 'invoice', 'parsing_diff')
        entity_id: ID of the entity
        action: Action performed (e.g., 'create', 'update', 'delete', 'resolve')
        old_value: Previous state (dict, optional)
        new_value: New state (dict, optional)
        user_id: ID of the user who performed the action (optional)
        ip_address: IP address of the request (optional)
        user_agent: User agent of the request (optional)
        details: Human-readable description (optional)

    Returns:
        Created AuditLog record
    """
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details,
    )

    db.add(audit_log)
    await db.commit()

    logger.debug(f"Audit: {action} on {entity_type}:{entity_id}")
    return audit_log


async def log_audit_no_commit(
    db: AsyncSession,
    entity_type: str,
    entity_id: int,
    action: str,
    old_value: Optional[Dict[str, Any]] = None,
    new_value: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[str] = None,
) -> AuditLog:
    """Log an audit event without committing (for use within transactions).

    Same as log_audit but does not commit - caller is responsible for commit.
    """
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details,
    )

    db.add(audit_log)
    logger.debug(f"Audit (pending): {action} on {entity_type}:{entity_id}")
    return audit_log


def get_client_info(request) -> Dict[str, Optional[str]]:
    """Extract client information from a FastAPI request.

    Args:
        request: FastAPI Request object

    Returns:
        Dict with ip_address and user_agent
    """
    # Get IP address (handle proxies)
    ip_address = None
    if hasattr(request, 'headers'):
        # Check for forwarded headers (common with proxies/load balancers)
        ip_address = request.headers.get('X-Forwarded-For')
        if ip_address:
            # X-Forwarded-For can contain multiple IPs, take the first one
            ip_address = ip_address.split(',')[0].strip()
        else:
            ip_address = request.headers.get('X-Real-IP')

    if not ip_address and hasattr(request, 'client') and request.client:
        ip_address = request.client.host

    # Get user agent
    user_agent = None
    if hasattr(request, 'headers'):
        user_agent = request.headers.get('User-Agent')

    return {
        'ip_address': ip_address,
        'user_agent': user_agent[:500] if user_agent else None,  # Truncate if too long
    }
