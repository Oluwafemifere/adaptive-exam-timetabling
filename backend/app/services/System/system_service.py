# backend/app/services/system_service.py
"""
Service for managing system-level configurations, academic sessions, and notifications.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import date

logger = logging.getLogger(__name__)


class SystemService:
    """Handles system configuration, sessions, and administrative notifications."""

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
        """
        Creates or updates a system configuration by calling `create_or_update_system_configuration`.
        """
        action = "Updating" if config_id else "Creating"
        logger.info(f"{action} system configuration '{config_name}' by user {user_id}")
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
        return result.scalar_one()

    async def update_system_configuration_constraints(
        self, config_id: UUID, user_id: UUID, constraints_payload: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Updates only the constraints for a specific system configuration by calling
        `update_system_configuration_constraints`.
        """
        logger.info(
            f"User {user_id} updating constraints for configuration {config_id}"
        )
        query = text(
            "SELECT exam_system.update_system_configuration_constraints(:p_config_id, :p_user_id, :p_constraints_payload)"
        )
        result = await self.session.execute(
            query,
            {
                "p_config_id": config_id,
                "p_user_id": user_id,
                "p_constraints_payload": json.dumps(constraints_payload),
            },
        )
        await self.session.commit()
        return result.scalar_one()

    async def set_active_academic_session(
        self, session_id: UUID, user_id: UUID
    ) -> None:
        """
        Sets the globally active academic session by calling `set_active_academic_session`.
        """
        logger.info(f"User {user_id} setting active academic session to {session_id}")
        query = text(
            "SELECT exam_system.set_active_academic_session(:p_session_id, :p_user_id)"
        )
        await self.session.execute(
            query, {"p_session_id": session_id, "p_user_id": user_id}
        )
        await self.session.commit()

    async def create_academic_session(
        self,
        p_name: str,
        p_start_date: date,
        p_end_date: date,
        p_timeslot_template_id: Optional[UUID],
        p_template_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Creates a new academic session by calling the corresponding DB function.
        """
        logger.info(f"Creating new academic session: {p_name}")
        query = text(
            """
            SELECT exam_system.create_academic_session(
                :p_name, :p_start_date, :p_end_date, :p_timeslot_template_id, :p_template_id
            )
            """
        )
        result = await self.session.execute(
            query,
            {
                "p_name": p_name,
                "p_start_date": p_start_date,
                "p_end_date": p_end_date,
                "p_timeslot_template_id": p_timeslot_template_id,
                "p_template_id": p_template_id,
            },
        )
        return result.scalar_one()

    async def mark_notifications_as_read(
        self, notification_ids: List[UUID], admin_user_id: UUID
    ) -> Dict[str, Any]:
        """
        Marks administrative notifications as read by calling `mark_notifications_as_read`.
        """
        logger.info(
            f"Admin {admin_user_id} marking {len(notification_ids)} notifications as read"
        )
        query = text(
            "SELECT exam_system.mark_notifications_as_read(:p_notification_ids, :p_admin_user_id)"
        )
        result = await self.session.execute(
            query,
            {"p_notification_ids": notification_ids, "p_admin_user_id": admin_user_id},
        )
        return result.scalar_one()
