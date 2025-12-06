"""Audit log model for tracking all system changes."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON

from app.database import Base


class AuditLog(Base):
    """Audit log table for tracking all entity changes.

    Records who changed what, when, and the before/after values.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Entity identification
    entity_type = Column(String(50), nullable=False, index=True)  # 'invoice', 'parsing_diff', etc.
    entity_id = Column(Integer, nullable=False, index=True)

    # Action tracking
    action = Column(String(50), nullable=False, index=True)  # 'create', 'update', 'delete', 'resolve', 'confirm', etc.

    # Change details (stored as JSON for flexibility)
    old_value = Column(JSON, nullable=True)  # Previous state (null for create)
    new_value = Column(JSON, nullable=True)  # New state (null for delete)

    # Context
    user_id = Column(String(100), nullable=True)  # For future auth integration
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)

    # Additional metadata
    details = Column(Text, nullable=True)  # Human-readable description

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
