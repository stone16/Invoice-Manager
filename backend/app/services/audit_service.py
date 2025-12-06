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
    """
    Create and persist a new audit log entry for a specific entity and action.
    
    Constructs an AuditLog from the provided fields, adds it to the given database session, and commits the transaction.
    
    Parameters:
        db (AsyncSession): Database session used to persist the record.
        entity_type (str): Type of the entity (e.g., "invoice", "parsing_diff").
        entity_id (int): Identifier of the entity.
        action (str): Action performed on the entity (e.g., "create", "update", "delete", "resolve").
        old_value (Optional[Dict[str, Any]]): Previous state of the entity, if applicable.
        new_value (Optional[Dict[str, Any]]): New state of the entity, if applicable.
        user_id (Optional[str]): Identifier of the user who performed the action.
        ip_address (Optional[str]): Client IP address associated with the action.
        user_agent (Optional[str]): Client user agent string associated with the action.
        details (Optional[str]): Optional human-readable description or metadata.
    
    Returns:
        AuditLog: The created and persisted AuditLog record.
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
    """
    Create an AuditLog instance and add it to the provided session without committing the transaction.
    
    Parameters:
        entity_type (str): Type or category of the audited entity.
        entity_id (int): Identifier of the audited entity.
        action (str): Action performed on the entity.
        old_value (Optional[Dict[str, Any]]): State of the entity before the action.
        new_value (Optional[Dict[str, Any]]): State of the entity after the action.
        user_id (Optional[str]): Identifier of the user who performed the action.
        ip_address (Optional[str]): Client IP address associated with the action.
        user_agent (Optional[str]): Client user-agent string.
        details (Optional[str]): Additional contextual information about the audit event.
    
    Returns:
        AuditLog: The created AuditLog instance (added to the session but not committed).
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
    """
    Extract client IP address and User-Agent from a FastAPI request.
    
    Prefers proxy headers (X-Forwarded-For, then X-Real-IP) for the IP address and falls back to request.client.host if headers are unavailable. Returns the User-Agent header truncated to 500 characters when present.
    
    Parameters:
        request: FastAPI Request object to read headers and client info from.
    
    Returns:
        dict: A dictionary with keys:
            - 'ip_address' (str | None): The client's IP address determined from headers or request.client.host, or None if unavailable.
            - 'user_agent' (str | None): The User-Agent header value truncated to 500 characters, or None if unavailable.
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