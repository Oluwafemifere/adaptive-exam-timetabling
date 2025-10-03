# backend/app/services/user_management/authorization_service.py
"""
Service for Role-Based Access Control (RBAC).
Delegates permission checking and role management to PostgreSQL functions.
"""

import logging
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import json

logger = logging.getLogger(__name__)


class AuthorizationService:
    """Handles user roles and permissions by calling database functions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def assign_role_to_user(
        self, user_id: UUID, role_name: str
    ) -> Dict[str, Any]:
        """
        Assigns a role to a user by calling the `assign_role_to_user` function.
        """
        try:
            logger.info(f"Assigning role '{role_name}' to user {user_id}")
            query = text(
                "SELECT exam_system.assign_role_to_user(p_user_id => :user_id, p_role_name => :role_name)"
            )
            result = await self.session.execute(
                query, {"user_id": user_id, "role_name": role_name}
            )
            assignment_result = result.scalar_one()
            await self.session.commit()
            return assignment_result
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error assigning role to user {user_id}: {e}", exc_info=True)
            return {"success": False, "error": "An internal error occurred."}

    async def check_user_permission(self, user_id: UUID, permission: str) -> bool:
        """
        Checks if a user has a specific permission by calling the `check_user_permission` function.
        """
        try:
            logger.debug(f"Checking permission '{permission}' for user {user_id}")
            query = text(
                "SELECT exam_system.check_user_permission(p_user_id => :user_id, p_permission => :permission)"
            )
            result = await self.session.execute(
                query, {"user_id": user_id, "permission": permission}
            )
            has_permission = result.scalar_one_or_none()
            return has_permission is True
        except Exception as e:
            logger.error(
                f"Error checking permission for user {user_id}: {e}", exc_info=True
            )
            return False

    async def get_user_roles(self, user_id: UUID) -> List[str]:
        """
        Retrieves all roles for a given user by calling `get_user_roles`.
        """
        try:
            query = text("SELECT exam_system.get_user_roles(p_user_id => :user_id)")
            result = await self.session.execute(query, {"user_id": user_id})
            roles = result.scalar_one_or_none()
            return roles if roles is not None else []
        except Exception as e:
            logger.error(f"Error getting roles for user {user_id}: {e}", exc_info=True)
            return []

    async def update_role_permissions(
        self, role_name: str, permissions: List[str], admin_user_id: UUID
    ) -> Dict[str, Any]:
        """
        Updates the permissions for a specific role by calling the `update_role_permissions` function.
        """
        try:
            logger.info(
                f"Admin {admin_user_id} updating permissions for role '{role_name}'"
            )
            query = text(
                "SELECT exam_system.update_role_permissions(:p_role_name, :p_permissions, :p_admin_user_id)"
            )
            result = await self.session.execute(
                query,
                {
                    "p_role_name": role_name,
                    "p_permissions": json.dumps(permissions),
                    "p_admin_user_id": admin_user_id,
                },
            )
            update_result = result.scalar_one()
            await self.session.commit()
            return update_result
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Error updating permissions for role {role_name}: {e}", exc_info=True
            )
            return {"success": False, "error": "An internal error occurred."}
