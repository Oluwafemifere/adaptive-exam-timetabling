# backend/app/services/user_management/authentication_service.py
"""
Service for user authentication, including registration and login.
All operations are delegated to PostgreSQL functions.
"""

import logging
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
            user_data: A dictionary containing user details like email,
                       first_name, last_name, and a plain-text password.

        Returns:
            A dictionary with the result from the database function, typically
            containing the new user's ID and a success status.
        """
        try:
            logger.info(f"Attempting to register user: {user_data.get('email')}")
            query = text("SELECT exam_system.register_user(p_user_data => :user_data)")
            result = await self.session.execute(query, {"user_data": user_data})
            registration_result = result.scalar_one()
            await self.session.commit()
            logger.info(
                f"Registration result for {user_data.get('email')}: {registration_result}"
            )
            return registration_result
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error during user registration: {e}", exc_info=True)
            return {
                "success": False,
                "error": "An internal error occurred during registration.",
            }

    async def authenticate_user(
        self, email: str, password: str
    ) -> Optional[Dict[str, Any]]:
        """
        Authenticates a user by calling the `authenticate_user` PostgreSQL function.

        Args:
            email: The user's email address.
            password: The user's plain-text password.

        Returns:
            A dictionary containing user details and token information upon successful
            authentication, or None if authentication fails.
        """
        try:
            logger.info(f"Attempting to authenticate user: {email}")
            query = text(
                "SELECT exam_system.authenticate_user(p_email => :email, p_password => :password)"
            )
            result = await self.session.execute(
                query, {"email": email, "password": password}
            )
            auth_result = result.scalar_one_or_none()

            if auth_result and auth_result.get("success"):
                logger.info(f"Successfully authenticated user: {email}")
                return auth_result
            else:
                logger.warning(f"Failed authentication attempt for user: {email}")
                return None
        except Exception as e:
            logger.error(f"Error during user authentication: {e}", exc_info=True)
            return None
