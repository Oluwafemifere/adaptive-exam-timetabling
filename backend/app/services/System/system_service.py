# backend/app/services/system_service.py
"""
Service for managing system-level configurations, academic sessions, and other administrative tasks.
This service acts as a Python wrapper for the corresponding PostgreSQL functions.
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
    """Handles system configuration, sessions, and administrative tasks."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # --- CONSTRAINT & SYSTEM CONFIGURATION MANAGEMENT ---

    async def get_all_constraint_configurations(self) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves a list of all CONSTRAINT configuration profiles.
        Calls `get_all_constraint_configurations`.
        """
        logger.info("Fetching all CONSTRAINT configurations.")
        query = text("SELECT exam_system.get_all_constraint_configurations()")
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all_system_configurations(self) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves a list of all SYSTEM configurations.
        Calls `get_all_system_configurations`.
        """
        logger.info("Fetching all SYSTEM configurations.")
        query = text("SELECT exam_system.get_all_system_configurations()")
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    # Renamed for clarity from get_configuration_details
    async def get_constraint_configuration_details(
        self, config_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves the detailed rules and settings for a specific configuration profile.
        Calls `exam_system.get_constraint_configuration_details(:p_configuration_id)`.
        """
        logger.info(f"Fetching details for constraint configuration {config_id}.")
        try:
            query = text(
                "SELECT exam_system.get_constraint_configuration_details(:p_configuration_id)"
            )
            result = await self.session.execute(
                query, {"p_configuration_id": config_id}
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                f"Failed to fetch configuration details for {config_id}: {e}",
                exc_info=True,
            )
            return None

    async def clone_configuration(
        self,
        source_config_id: UUID,
        new_name: str,
        new_description: str,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Creates a new configuration profile by cloning an existing one.
        Calls `exam_system.clone_constraint_configuration(...)`.
        """
        logger.info(
            f"User {user_id} cloning configuration {source_config_id} into new config '{new_name}'."
        )
        try:
            query = text(
                """
                SELECT exam_system.clone_constraint_configuration(
                    :p_source_config_id, :p_new_name, :p_new_description, :p_user_id
                )
                """
            )
            result = await self.session.execute(
                query,
                {
                    "p_source_config_id": source_config_id,
                    "p_new_name": new_name,
                    "p_new_description": new_description,
                    "p_user_id": user_id,
                },
            )
            await self.session.commit()
            return result.scalar_one()
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to clone configuration: {e}", exc_info=True)
            return {
                "success": False,
                "error": "Database operation failed during cloning.",
            }

    async def update_configuration_rules(
        self, config_id: UUID, rules_payload: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Updates multiple rule settings for a specific configuration in a single transaction.
        Calls `exam_system.update_configuration_rules(:p_configuration_id, :p_updates)`.
        """
        logger.info(f"Updating rules for configuration {config_id}.")
        try:
            query = text(
                "SELECT exam_system.update_configuration_rules(:p_configuration_id, :p_updates)"
            )
            result = await self.session.execute(
                query,
                {
                    "p_configuration_id": config_id,
                    "p_updates": json.dumps(rules_payload, default=str),
                },
            )
            await self.session.commit()
            return result.scalar_one()
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Failed to update configuration rules for {config_id}: {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "error": "Database operation failed during update.",
            }

    async def set_default_configuration(self, config_id: UUID) -> Dict[str, Any]:
        """
        Sets a configuration profile as the system-wide default.
        Calls `exam_system.set_default_constraint_configuration(:p_configuration_id)`.
        """
        logger.info(f"Setting constraint configuration {config_id} as default.")
        try:
            query = text(
                "SELECT exam_system.set_default_constraint_configuration(:p_configuration_id)"
            )
            result = await self.session.execute(
                query, {"p_configuration_id": config_id}
            )
            await self.session.commit()
            return result.scalar_one()
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to set default configuration: {e}", exc_info=True)
            return {"success": False, "error": "Failed to set default configuration."}

    async def delete_configuration(
        self, config_id: UUID, user_id: UUID
    ) -> Dict[str, Any]:
        """
        Deletes a non-default and unused constraint configuration profile.
        Calls `exam_system.delete_constraint_configuration(:p_configuration_id)`.
        (Note: user_id is passed for logging and potential future auditing).
        """
        logger.info(f"User {user_id} attempting to delete configuration {config_id}.")
        try:
            query = text(
                "SELECT exam_system.delete_constraint_configuration(:p_configuration_id)"
            )
            result = await self.session.execute(
                query, {"p_configuration_id": config_id}
            )
            await self.session.commit()
            return result.scalar_one()
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Failed to delete configuration {config_id}: {e}", exc_info=True
            )
            return {"success": False, "error": str(e)}

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
