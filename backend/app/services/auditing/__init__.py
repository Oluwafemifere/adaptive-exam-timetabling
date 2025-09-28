# backend/app/services/auditing/__init__.py
"""
Auditing Services Package.

Provides services for logging user actions and system events.
"""
from .audit_service import AuditService

__all__ = ["AuditService"]
