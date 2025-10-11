# backend/app/services/user_management/user_management_service.py
"""
Service for managing user profiles, including updates and deletions by administrators.
"""

import logging
from typing import Dict, Any
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import json

logger = logging.getLogger(__name__)


class UserManagementService:
    """Handles CRUD operations for user management via PostgreSQL functions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def update_user(
        self, user_id: UUID, update_data: Dict[str, Any], admin_user_id: UUID
    ) -> Dict[str, Any]:
        """
        Updates a user's details by calling the `update_user` PostgreSQL function.
        Requires an administrator's ID for auditing.
        """
        logger.info(f"Admin {admin_user_id} updating user {user_id}")
        try:
            query = text(
                """
                SELECT exam_system.update_user(
                    p_user_id => :user_id,
                    p_data => :data,
                    p_admin_user_id => :admin_user_id
                )
                """
            )
            result = await self.session.execute(
                query,
                {
                    "user_id": user_id,
                    "data": json.dumps(update_data),
                    "admin_user_id": admin_user_id,
                },
            )
            update_result = result.scalar_one()
            await self.session.commit()
            return update_result
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating user {user_id}: {e}", exc_info=True)
            return {"success": False, "error": "An internal error occurred."}

    async def delete_user(self, user_id: UUID, admin_user_id: UUID) -> Dict[str, Any]:
        """
        Deletes a user by calling the `delete_user` PostgreSQL function.
        Requires an administrator's ID for auditing.
        """
        logger.warning(f"Admin {admin_user_id} is deleting user {user_id}")
        try:
            query = text(
                """
                SELECT exam_system.delete_user(
                    p_user_id => :user_id,
                    p_admin_user_id => :admin_user_id
                )
                """
            )
            result = await self.session.execute(
                query, {"user_id": user_id, "admin_user_id": admin_user_id}
            )
            delete_result = result.scalar_one()
            await self.session.commit()
            return delete_result
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting user {user_id}: {e}", exc_info=True)
            return {"success": False, "error": "An internal error occurred."}
