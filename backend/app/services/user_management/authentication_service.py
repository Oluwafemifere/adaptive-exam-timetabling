# backend/app/services/user_management/authentication_service.py
"""
Service for user authentication, including registration and login.
All operations are delegated to PostgreSQL functions.
"""

import logging
import json
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AuthenticationService:
    """Handles user authentication by calling database functions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registers a new user by calling the `register_user` PostgreSQL function.

        Args:
            user_data: A dictionary containing user details, including 'role'.

        Returns:
            A dictionary with the result from the database function.
        """
        try:
            logger.info(f"Attempting to register user: {user_data.get('email')}")
            user_data_json = json.dumps(user_data)
            query = text("SELECT exam_system.register_user(p_user_data => :user_data)")
            result = await self.session.execute(query, {"user_data": user_data_json})
            registration_result = result.scalar_one()
            await self.session.commit()
            return registration_result
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error during user registration: {e}", exc_info=True)
            return {
                "success": False,
                "error": "An internal error occurred during registration.",
            }

    async def login_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticates a user by calling the `user_login` PostgreSQL function.
        This function is designed to return the user's role for frontend routing.

        Args:
            email: The user's email address.
            password: The user's plain-text password.

        Returns:
            A dictionary with user details, including role, on success.
        """
        try:
            logger.info(f"Attempting to log in user: {email}")
            # MODIFIED: Changed function name to match the updated SQL script
            query = text(
                "SELECT exam_system.user_login(p_email => :email, p_password => :password)"
            )
            result = await self.session.execute(
                query, {"email": email, "password": password}
            )
            auth_result = result.scalar_one_or_none()
            return auth_result
        except Exception as e:
            logger.error(f"Error during user login: {e}", exc_info=True)
            return None
