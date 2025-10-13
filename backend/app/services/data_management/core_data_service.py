# backend/app/services/data_management/core_data_service.py
"""
Service for core data management (CRUD operations).
All operations are delegated to dedicated PostgreSQL functions to ensure
data integrity, consistency, and proper auditing.
"""

import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import json

logger = logging.getLogger(__name__)


class CoreDataService:
    """Provides CRUD operations for core entities via PostgreSQL functions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _execute_cud_function(
        self, function_name: str, params: Dict[str, Any], entity_name: str
    ) -> Dict[str, Any]:
        """
        Generic helper for Create, Update, Delete (CUD) operations.
        """
        try:
            # Log params before potential modification
            logger.info(
                f"Executing {function_name} for {entity_name} with params: {params}"
            )
            if "p_data" in params and isinstance(params["p_data"], dict):
                params["p_data"] = json.dumps(params["p_data"])

            query = text(
                f"SELECT exam_system.{function_name}({', '.join(':' + k for k in params.keys())})"
            )
            result = await self.session.execute(query, params)
            cud_result = result.scalar_one()
            await self.session.commit()
            return cud_result
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Error in {function_name} for {entity_name}: {e}", exc_info=True
            )
            return {
                "success": False,
                "error": f"An internal error occurred while processing the {entity_name}.",
            }

    # --- Course Management ---
    async def create_course(
        self, course_data: Dict[str, Any], user_id: UUID, session_id: UUID
    ) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "create_course",
            {"p_data": course_data, "p_user_id": user_id, "p_session_id": session_id},
            "course",
        )

    async def update_course(
        self,
        course_id: UUID,
        course_data: Dict[str, Any],
        user_id: UUID,
        session_id: UUID,
    ) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "update_course",
            {
                "p_course_id": course_id,
                "p_data": course_data,
                "p_user_id": user_id,
                "p_session_id": session_id,
            },
            "course",
        )

    async def delete_course(
        self, course_id: UUID, user_id: UUID, session_id: UUID
    ) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "delete_course",
            {
                "p_course_id": course_id,
                "p_user_id": user_id,
                "p_session_id": session_id,
            },
            "course",
        )

    # --- Room/Venue Management ---
    async def create_room(
        self, room_data: Dict[str, Any], user_id: UUID, session_id: UUID
    ) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "create_room",
            {"p_data": room_data, "p_user_id": user_id, "p_session_id": session_id},
            "room",
        )

    async def update_room(
        self, room_id: UUID, room_data: Dict[str, Any], user_id: UUID, session_id: UUID
    ) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "update_room",
            {
                "p_room_id": room_id,
                "p_data": room_data,
                "p_user_id": user_id,
                "p_session_id": session_id,
            },
            "room",
        )

    async def delete_room(
        self, room_id: UUID, user_id: UUID, session_id: UUID
    ) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "delete_room",
            {"p_room_id": room_id, "p_user_id": user_id, "p_session_id": session_id},
            "room",
        )

    # --- Exam Management ---
    async def create_exam(
        self, exam_data: Dict[str, Any], user_id: UUID
    ) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "create_exam", {"p_data": exam_data, "p_user_id": user_id}, "exam"
        )

    async def update_exam(
        self, exam_id: UUID, exam_data: Dict[str, Any], user_id: UUID, session_id: UUID
    ) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "update_exam",
            {
                "p_exam_id": exam_id,
                "p_data": exam_data,
                "p_user_id": user_id,
                "p_session_id": session_id,
            },
            "exam",
        )

    async def delete_exam(
        self, exam_id: UUID, user_id: UUID, session_id: UUID
    ) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "delete_exam",
            {"p_exam_id": exam_id, "p_user_id": user_id, "p_session_id": session_id},
            "exam",
        )

    # --- User Management (NEW) ---
    async def update_user(
        self, user_id: UUID, user_data: Dict[str, Any], admin_user_id: UUID
    ) -> Dict[str, Any]:
        """Calls the `update_user` DB function."""
        return await self._execute_cud_function(
            "update_user",
            {
                "p_user_id": user_id,
                "p_data": user_data,
                "p_admin_user_id": admin_user_id,
            },
            "user",
        )

    async def delete_user(self, user_id: UUID, admin_user_id: UUID) -> Dict[str, Any]:
        """Calls the `delete_user` DB function for a soft delete."""
        return await self._execute_cud_function(
            "delete_user",
            {"p_user_id": user_id, "p_admin_user_id": admin_user_id},
            "user",
        )
