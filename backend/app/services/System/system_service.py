# backend/app/services/System/system_service.py
"""
Service for managing system-level configurations, academic sessions, and other administrative tasks.
This service acts as a Python wrapper for the corresponding PostgreSQL functions.
"""

import json
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

    async def update_academic_session(
        self, session_id: UUID, update_data: Dict[str, Any], user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Updates an existing academic session and logs the action.
        Calls `exam_system.update_academic_session`.
        """
        logger.info(f"User {user_id} updating academic session {session_id}")
        param_mapping = {
            "name": "p_name",
            "start_date": "p_start_date",
            "end_date": "p_end_date",
            "timeslot_template_id": "p_timeslot_template_id",
            "is_active": "p_is_active",
        }
        params = {"p_session_id": session_id}
        for key, value in update_data.items():
            if key in param_mapping:
                params[param_mapping[key]] = value

        param_str = ", ".join(f"{pg_param} => :{pg_param}" for pg_param in params)
        query = text(f"SELECT exam_system.update_academic_session({param_str})")

        try:
            # Note: The update function itself doesn't log, so we log it here.
            # For more complex updates, it's better to have the PG function handle logging.
            log_query = text(
                """
                SELECT exam_system.log_audit_activity(
                    p_user_id => :p_user_id,
                    p_action => :p_action,
                    p_entity_type => :p_entity_type,
                    p_entity_id => :p_entity_id,
                    p_new_values => :p_new_values
                )
                """
            )
            await self.session.execute(
                log_query,
                {
                    "p_user_id": user_id,
                    "p_action": "UPDATE",
                    "p_entity_type": "ACADEMIC_SESSION",
                    "p_entity_id": session_id,
                    "p_new_values": json.dumps(update_data, default=str),
                },
            )
            result = await self.session.execute(query, params)
            await self.session.commit()
            return result.scalar_one_or_none()
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Failed to update academic session {session_id}: {e}", exc_info=True
            )
            raise

    async def archive_academic_session(
        self, session_id: UUID, user_id: UUID
    ) -> Dict[str, Any]:
        """
        Archives (soft-deletes) an academic session and logs the action to the audit trail.
        """
        logger.warning(f"User {user_id} archiving academic session {session_id}")
        try:
            # --- START OF FIX ---
            # The linter warning is ignored as `result.rowcount` is the correct way
            # to check the number of affected rows for an UPDATE statement in SQLAlchemy.
            archive_query = text(
                """
                UPDATE exam_system.academic_sessions
                SET archived_at = NOW(), is_active = false
                WHERE id = :p_session_id AND archived_at IS NULL
                """
            )
            result = await self.session.execute(
                archive_query, {"p_session_id": session_id}
            )

            # If no rows were updated, it means the session didn't exist or was already archived.
            if result.rowcount == 0:  # type: ignore
                await self.session.rollback()
                return {
                    "success": False,
                    "message": "Session not found or already archived.",
                }

            # Log the archive action to the audit trail within the same transaction.
            log_query = text(
                """
                SELECT exam_system.log_audit_activity(
                    p_user_id => :p_user_id,
                    p_action => :p_action,
                    p_entity_type => :p_entity_type,
                    p_entity_id => :p_entity_id,
                    p_notes => :p_notes
                )
                """
            )
            await self.session.execute(
                log_query,
                {
                    "p_user_id": user_id,
                    "p_action": "ARCHIVE",
                    "p_entity_type": "ACADEMIC_SESSION",
                    "p_entity_id": session_id,
                    "p_notes": "Academic session was archived.",
                },
            )

            await self.session.commit()
            # --- END OF FIX ---

            return {
                "success": True,
                "message": "Academic session archived successfully.",
            }
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to archive session {session_id}: {e}", exc_info=True)
            raise

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
