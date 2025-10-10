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

    # --- NEW: Method for student self-registration ---
    async def self_register_student(
        self, matric_number: str, email: str, password: str
    ) -> Dict[str, Any]:
        """
        Registers a user account for an existing student record.
        Calls the `student_self_register` PostgreSQL function.
        """
        try:
            logger.info(
                f"Attempting self-registration for student with matric #: {matric_number}"
            )
            query = text(
                """
                SELECT exam_system.student_self_register(
                    p_matric_number => :matric_number,
                    p_email => :email,
                    p_password => :password
                )
                """
            )
            result = await self.session.execute(
                query,
                {"matric_number": matric_number, "email": email, "password": password},
            )
            registration_result = result.scalar_one()

            if not registration_result.get("success"):
                raise Exception(
                    registration_result.get("message", "Registration failed.")
                )

            await self.session.commit()
            return registration_result
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error during student self-registration: {e}", exc_info=True)
            # Return a consistent error format
            return {"success": False, "message": str(e)}

    # --- NEW: Method for staff self-registration ---
    async def self_register_staff(
        self, staff_number: str, email: str, password: str
    ) -> Dict[str, Any]:
        """
        Registers a user account for an existing staff record.
        Calls the `staff_self_register` PostgreSQL function.
        """
        try:
            logger.info(
                f"Attempting self-registration for staff with staff #: {staff_number}"
            )
            query = text(
                """
                SELECT exam_system.staff_self_register(
                    p_staff_number => :staff_number,
                    p_email => :email,
                    p_password => :password
                )
                """
            )
            result = await self.session.execute(
                query,
                {"staff_number": staff_number, "email": email, "password": password},
            )
            registration_result = result.scalar_one()

            if not registration_result.get("success"):
                raise Exception(
                    registration_result.get("message", "Registration failed.")
                )

            await self.session.commit()
            return registration_result
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error during staff self-registration: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    # ... (existing methods: register_user, admin_create_user, login_user)
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
            # Ensure role is either 'student' or 'staff' for this public endpoint
            role = user_data.get("role")
            if role not in ["student", "staff"]:
                raise ValueError(
                    "Self-registration is only available for students and staff."
                )

            user_data_json = json.dumps(user_data)
            query = text("SELECT exam_system.register_user(p_user_data => :user_data)")
            result = await self.session.execute(query, {"user_data": user_data_json})
            registration_result = result.scalar_one()

            if not registration_result.get("success"):
                raise Exception(
                    registration_result.get(
                        "message", "Registration failed in database."
                    )
                )

            await self.session.commit()
            return registration_result
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error during user registration: {e}", exc_info=True)
            return {
                "success": False,
                "message": str(e),
            }

    # NEW: Method to handle user creation by an administrator
    async def admin_create_user(
        self, admin_user_id: UUID, user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Creates a new user via an admin-only function.
        Delegates to the `admin_create_and_register_user` PostgreSQL function.
        """
        try:
            logger.info(
                f"Admin {admin_user_id} is creating a new user: {user_data.get('email')}"
            )

            query = text(
                """
                SELECT exam_system.admin_create_and_register_user(
                    p_admin_user_id => :p_admin_user_id,
                    p_user_type => :p_user_type,
                    p_email => :p_email,
                    p_first_name => :p_first_name,
                    p_last_name => :p_last_name,
                    p_password => :p_password,
                    p_session_id => :p_session_id,
                    p_matric_number => :p_matric_number,
                    p_programme_code => :p_programme_code,
                    p_entry_year => :p_entry_year
                )
            """
            )

            params = {
                "p_admin_user_id": admin_user_id,
                "p_user_type": user_data.get("user_type"),
                "p_email": user_data.get("email"),
                "p_first_name": user_data.get("first_name"),
                "p_last_name": user_data.get("last_name"),
                "p_password": user_data.get("password"),
                "p_session_id": user_data.get("session_id"),
                "p_matric_number": user_data.get("matric_number"),
                "p_programme_code": user_data.get("programme_code"),
                "p_entry_year": user_data.get("entry_year"),
            }

            result = await self.session.execute(query, params)
            creation_result = result.scalar_one_or_none()

            if not creation_result or creation_result.get("status") != "success":
                raise Exception(
                    creation_result.get("message", "User creation failed in database.")  # type: ignore
                )

            await self.session.commit()
            return creation_result

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error during admin user creation: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

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
