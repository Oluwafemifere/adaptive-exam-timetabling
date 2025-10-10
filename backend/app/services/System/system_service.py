# backend/app/services/System/system_service.py
"""
Service for managing system-level configurations, academic sessions, and other administrative tasks.
This service acts as a Python wrapper for the corresponding PostgreSQL functions.
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import date

logger = logging.getLogger(__name__)


class SystemService:
    """Handles system-wide tasks like academic session and notification management."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # --- ACADEMIC SESSION & NOTIFICATION MANAGEMENT ---

    async def set_active_academic_session(
        self, session_id: UUID, user_id: UUID
    ) -> None:
        """
        Sets the globally active academic session.
        Calls `exam_system.set_active_academic_session(:p_session_id, :p_user_id)`.
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
        Creates a new academic session.
        Calls `exam_system.create_academic_session(...)`.
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
        await self.session.commit()
        return result.scalar_one()

    async def mark_notifications_as_read(
        self, notification_ids: List[UUID], admin_user_id: UUID
    ) -> Dict[str, Any]:
        """
        Marks administrative notifications as read.
        Calls `exam_system.mark_notifications_as_read(:p_notification_ids, :p_admin_user_id)`.
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
        await self.session.commit()
        return result.scalar_one()
