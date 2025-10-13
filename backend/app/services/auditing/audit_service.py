# backend/app/services/auditing/audit_service.py
"""
Service for logging audit trails.
Provides a simple interface to the `log_audit_activity` PostgreSQL function.
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import json

logger = logging.getLogger(__name__)


class AuditService:
    """Handles the creation of audit log entries by calling the DB function."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        user_id: UUID,
        action: str,
        entity_type: str,
        entity_id: Optional[UUID] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[UUID] = None,
    ) -> None:
        """
        Logs an audit activity by calling the `log_audit_activity` PostgreSQL function.

        Args:
            user_id: The ID of the user performing the action.
            action: The action being performed (e.g., 'create', 'update', 'login').
            entity_type: The type of entity being affected (e.g., 'course', 'user').
            session_id: The academic session ID related to the action, if any.
            ... and other audit parameters.
        """
        try:
            logger.debug(
                f"Logging audit: user={user_id}, action='{action}', entity='{entity_type}'"
            )
            query = text(
                """
                SELECT exam_system.log_audit_activity(
                    p_user_id => :user_id, p_action => :action, p_entity_type => :entity_type,
                    p_entity_id => :entity_id, p_old_values => :old_values,
                    p_new_values => :new_values, p_notes => :notes,
                    p_ip_address => :ip_address, p_user_agent => :user_agent,
                    p_session_id => :session_id
                )
                """
            )
            params = {
                "user_id": user_id,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "notes": notes,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "session_id": str(session_id) if session_id else None,
                "old_values": (
                    json.dumps(old_values, default=str) if old_values else None
                ),
                "new_values": (
                    json.dumps(new_values, default=str) if new_values else None
                ),
            }
            await self.session.execute(query, params)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to log audit activity: {e}", exc_info=True)
