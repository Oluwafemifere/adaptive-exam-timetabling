# backend/app/services/configuration_service.py
"""
Service dedicated to managing system and constraint configurations.
This provides a clean API for the frontend to interact with the powerful
PostgreSQL functions for configuration management.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class ConfigurationService:
    """Handles all CRUD operations for System and Constraint Configurations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_system_configuration_list(self) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves a lightweight list of all system configurations.
        Calls `get_system_configuration_list()`.
        """
        logger.info("Fetching list of all system configurations.")
        query = text("SELECT exam_system.get_system_configuration_list()")
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_system_configuration_details(
        self, config_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves the full details for a single system configuration.
        Calls `get_system_configuration_details(:p_config_id)`.
        """
        logger.info(f"Fetching details for system configuration {config_id}.")
        query = text(
            "SELECT exam_system.get_system_configuration_details(:p_config_id)"
        )
        result = await self.session.execute(query, {"p_config_id": config_id})
        return result.scalar_one_or_none()

    async def save_system_configuration(
        self, payload: Dict[str, Any], user_id: UUID
    ) -> Dict[str, Any]:
        """
        Creates or updates a configuration from a full JSON payload.
        Calls the atomic `save_system_configuration` PG function.
        """
        config_id = payload.get("id")
        action = "Updating" if config_id else "Creating new"
        logger.info(f"{action} system configuration by user {user_id}.")
        try:
            query = text(
                "SELECT exam_system.save_system_configuration(:p_payload, :p_user_id)"
            )
            result = await self.session.execute(
                query,
                {
                    "p_payload": json.dumps(payload, default=str),
                    "p_user_id": user_id,
                },
            )
            await self.session.commit()
            return result.scalar_one()
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to save system configuration: {e}", exc_info=True)
            raise

    async def delete_system_configuration(self, config_id: UUID) -> Dict[str, Any]:
        """
        Deletes a system configuration.
        Calls `delete_system_configuration(:p_config_id)`.
        """
        logger.info(f"Attempting to delete system configuration {config_id}.")
        try:
            query = text("SELECT exam_system.delete_system_configuration(:p_config_id)")
            result = await self.session.execute(query, {"p_config_id": config_id})
            await self.session.commit()
            return result.scalar_one()
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Failed to delete system configuration {config_id}: {e}", exc_info=True
            )
            raise

    async def set_default_system_configuration(self, config_id: UUID) -> Dict[str, Any]:
        """
        Sets a specific system configuration as the default.
        Calls `set_default_system_configuration(:p_config_id)`.
        """
        logger.info(f"Setting system configuration {config_id} as default.")
        try:
            query = text(
                "SELECT exam_system.set_default_system_configuration(:p_config_id)"
            )
            result = await self.session.execute(query, {"p_config_id": config_id})
            await self.session.commit()
            return result.scalar_one()
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Failed to set default system configuration: {e}", exc_info=True
            )
            raise
