# backend\app\services\System\system_service.py
"""
Service for managing system-level configurations, auditing, and reporting.
"""
import logging
import json
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class SystemService:
    """Handles system configuration, reports, and audit logging."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_system_configuration(
        self,
        user_id: UUID,
        config_name: str,
        description: str,
        is_default: bool,
        solver_parameters: Dict[str, Any],
        constraints: List[Dict[str, Any]],
        config_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Creates a new or updates an existing system configuration."""
        action = "Updating" if config_id else "Creating"
        logger.info(f"{action} system configuration '{config_name}' by user {user_id}")
        try:
            query = text(
                """
                SELECT exam_system.create_or_update_system_configuration(
                    :p_user_id, :p_config_name, :p_description, :p_is_default,
                    :p_solver_parameters, :p_constraints, :p_config_id
                )
                """
            )
            result = await self.session.execute(
                query,
                {
                    "p_user_id": user_id,
                    "p_config_name": config_name,
                    "p_description": description,
                    "p_is_default": is_default,
                    "p_solver_parameters": json.dumps(solver_parameters),
                    "p_constraints": json.dumps(constraints),
                    "p_config_id": config_id,
                },
            )
            config_result = result.scalar_one()
            await self.session.commit()
            return config_result
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error saving system configuration: {e}", exc_info=True)
            return {"success": False, "error": "Failed to save configuration."}

    async def generate_report(
        self, report_type: str, session_id: UUID, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generates a system report (e.g., conflict summary, room utilization)."""
        logger.info(f"Generating report '{report_type}' for session {session_id}")
        query = text(
            "SELECT exam_system.generate_report(:p_report_type, :p_session_id, :p_options)"
        )
        result = await self.session.execute(
            query,
            {
                "p_report_type": report_type,
                "p_session_id": session_id,
                "p_options": json.dumps(options),
            },
        )
        return result.scalar_one()

    async def log_audit_activity(
        self,
        user_id: UUID,
        action: str,
        entity_type: str,
        entity_id: Optional[UUID] = None,
        notes: Optional[str] = None,
    ) -> None:
        """Logs an audit trail event."""
        logger.debug(
            f"Logging audit action '{action}' on '{entity_type}' by user {user_id}"
        )
        try:
            # This function returns void, so we just execute it.
            query = text(
                """
                SELECT exam_system.log_audit_activity(
                    :p_user_id, :p_action, :p_entity_type, :p_entity_id, :p_notes
                )
                """
            )
            await self.session.execute(
                query,
                {
                    "p_user_id": user_id,
                    "p_action": action,
                    "p_entity_type": entity_type,
                    "p_entity_id": entity_id,
                    "p_notes": notes,
                },
            )
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to log audit activity: {e}", exc_info=True)
