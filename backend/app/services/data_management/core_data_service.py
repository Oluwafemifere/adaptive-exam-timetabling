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

        Args:
            function_name: The name of the PostgreSQL function to call.
            params: A dictionary of parameters for the function.
            entity_name: The name of the entity for logging.

        Returns:
            The result from the database function.
        """
        try:
            logger.info(
                f"Executing {function_name} for {entity_name} with params: {params}"
            )
            # The payload is passed as a JSON string to a JSONB parameter in PostgreSQL
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
        self, course_data: Dict[str, Any], user_id: UUID
    ) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "create_course", {"p_data": course_data, "p_user_id": user_id}, "course"
        )

    async def update_course(
        self, course_id: UUID, course_data: Dict[str, Any], user_id: UUID
    ) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "update_course",
            {"p_course_id": course_id, "p_data": course_data, "p_user_id": user_id},
            "course",
        )

    async def delete_course(self, course_id: UUID, user_id: UUID) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "delete_course", {"p_course_id": course_id, "p_user_id": user_id}, "course"
        )

    # --- Room/Venue Management ---
    async def create_room(
        self, room_data: Dict[str, Any], user_id: UUID
    ) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "create_room", {"p_data": room_data, "p_user_id": user_id}, "room"
        )

    async def update_room(
        self, room_id: UUID, room_data: Dict[str, Any], user_id: UUID
    ) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "update_room",
            {"p_room_id": room_id, "p_data": room_data, "p_user_id": user_id},
            "room",
        )

    async def delete_room(self, room_id: UUID, user_id: UUID) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "delete_room", {"p_room_id": room_id, "p_user_id": user_id}, "room"
        )

    # --- Exam Management ---
    async def create_exam(
        self, exam_data: Dict[str, Any], user_id: UUID
    ) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "create_exam", {"p_data": exam_data, "p_user_id": user_id}, "exam"
        )

    async def update_exam(
        self, exam_id: UUID, exam_data: Dict[str, Any], user_id: UUID
    ) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "update_exam",
            {"p_exam_id": exam_id, "p_data": exam_data, "p_user_id": user_id},
            "exam",
        )

    async def delete_exam(self, exam_id: UUID, user_id: UUID) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "delete_exam", {"p_exam_id": exam_id, "p_user_id": user_id}, "exam"
        )

    # --- Time Slot Management ---
    async def create_time_slot(
        self, time_slot_data: Dict[str, Any], user_id: UUID
    ) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "create_time_slot",
            {"p_data": time_slot_data, "p_user_id": user_id},
            "time_slot",
        )

    async def update_time_slot(
        self, time_slot_id: UUID, time_slot_data: Dict[str, Any], user_id: UUID
    ) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "update_time_slot",
            {
                "p_time_slot_id": time_slot_id,
                "p_data": time_slot_data,
                "p_user_id": user_id,
            },
            "time_slot",
        )

    async def delete_time_slot(
        self, time_slot_id: UUID, user_id: UUID
    ) -> Dict[str, Any]:
        return await self._execute_cud_function(
            "delete_time_slot",
            {"p_time_slot_id": time_slot_id, "p_user_id": user_id},
            "time_slot",
        )
