# backend\app\services\user_management\user_profile_service.py
"""
Service for managing user-specific data like preferences and presets.
"""
import logging
import json
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class UserProfileService:
    """Handles CRUD operations for user profiles and settings via PG functions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_or_update_preset(
        self, user_id: UUID, preset_name: str, preset_type: str, filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calls the `create_or_update_user_preset` DB function."""
        logger.info(
            f"User {user_id} saving preset '{preset_name}' for type '{preset_type}'."
        )
        try:
            query = text(
                "SELECT exam_system.create_or_update_user_preset(:p_user_id, :p_preset_name, :p_preset_type, :p_filters)"
            )
            result = await self.session.execute(
                query,
                {
                    "p_user_id": user_id,
                    "p_preset_name": preset_name,
                    "p_preset_type": preset_type,
                    "p_filters": json.dumps(filters),
                },
            )
            db_result = result.scalar_one()
            await self.session.commit()
            return db_result
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error saving preset for user {user_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": "An internal error occurred while saving the preset.",
            }

    async def delete_preset(self, user_id: UUID, preset_id: UUID) -> Dict[str, Any]:
        """Calls the `delete_user_preset` DB function."""
        logger.info(f"User {user_id} deleting preset {preset_id}.")
        try:
            query = text(
                "SELECT exam_system.delete_user_preset(:p_user_id, :p_preset_id)"
            )
            result = await self.session.execute(
                query,
                {"p_user_id": user_id, "p_preset_id": preset_id},
            )
            db_result = result.scalar_one()
            await self.session.commit()
            return db_result
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Error deleting preset {preset_id} for user {user_id}: {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "error": "An internal error occurred while deleting the preset.",
            }
