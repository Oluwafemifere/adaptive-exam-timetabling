# backend/app/services/data_management/session_management_service.py
"""
A service layer dedicated to managing session-scoped entities by invoking
the session-aware PL/pgSQL API functions. This service handles the CRUD
operations for core academic and infrastructure data.
"""

import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class SessionManagementService:
    """
    Provides methods to create, read, update, and delete session-scoped
    entities such as courses, buildings, and rooms. It serves as a Python
    interface to the `api_*` functions in the database.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _execute_api_function(
        self, function_name: str, params: Dict[str, Any]
    ) -> Any:
        """
        Generic helper to execute a session-aware API function in PostgreSQL.

        Args:
            function_name: The name of the function to call (e.g., 'api_create_course').
            params: A dictionary of parameters to pass to the function.

        Returns:
            The JSONB result from the PostgreSQL function.
        """
        # Ensure all function calls are properly namespaced
        full_function_name = f"exam_system.{function_name}"
        logger.info(
            f"Executing API function '{full_function_name}' with params: {list(params.keys())}"
        )
        try:
            # Use PostgreSQL's named argument syntax (arg_name => :param_name)
            # to ensure correct parameter mapping.
            param_placeholders = ", ".join(f"{key} => :{key}" for key in params.keys())
            query_str = f"SELECT {full_function_name}({param_placeholders})"
            query = text(query_str)

            result = await self.session.execute(query, params)
            await self.session.commit()
            return result.scalar_one_or_none()
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"API function '{full_function_name}' failed: {e}", exc_info=True
            )
            # Return a consistent error structure for the API route to handle
            return {"success": False, "error": f"Database operation failed: {e}"}

    # =========================================================================
    # Course Management
    # =========================================================================

    async def create_course(self, session_id: UUID, payload: Dict[str, Any]) -> Dict:
        """Calls api_create_course to add a new course to a session."""
        return await self._execute_api_function(
            "api_create_course", {"p_session_id": session_id, "p_payload": payload}
        )

    async def update_course(
        self, session_id: UUID, course_id: UUID, payload: Dict[str, Any]
    ) -> Dict:
        """Calls api_update_course to modify an existing course in a session."""
        return await self._execute_api_function(
            "api_update_course",
            {
                "p_session_id": session_id,
                "p_course_id": course_id,
                "p_payload": payload,
            },
        )

    async def delete_course(self, session_id: UUID, course_id: UUID) -> Dict:
        """Calls api_delete_course to remove a course from a session."""
        return await self._execute_api_function(
            "api_delete_course", {"p_session_id": session_id, "p_course_id": course_id}
        )

    async def get_paginated_courses(
        self, session_id: UUID, page: int, page_size: int, search_term: Optional[str]
    ) -> Dict:
        """Calls api_get_paginated_courses to retrieve a list of courses."""
        return await self._execute_api_function(
            "api_get_paginated_courses",
            {
                "p_session_id": session_id,
                "p_page": page,
                "p_page_size": page_size,
                "p_search_term": search_term,
            },
        )

    # =========================================================================
    # Building Management
    # =========================================================================

    async def create_building(self, session_id: UUID, payload: Dict[str, Any]) -> Dict:
        """Calls api_create_building to add a new building to a session."""
        return await self._execute_api_function(
            "api_create_building", {"p_session_id": session_id, "p_payload": payload}
        )

    async def update_building(
        self, session_id: UUID, building_id: UUID, payload: Dict[str, Any]
    ) -> Dict:
        """Calls api_update_building to modify an existing building in a session."""
        return await self._execute_api_function(
            "api_update_building",
            {
                "p_session_id": session_id,
                "p_building_id": building_id,
                "p_payload": payload,
            },
        )

    async def delete_building(self, session_id: UUID, building_id: UUID) -> Dict:
        """Calls api_delete_building to remove a building from a session."""
        return await self._execute_api_function(
            "api_delete_building",
            {"p_session_id": session_id, "p_building_id": building_id},
        )

    # =========================================================================
    # Room Management
    # =========================================================================

    async def create_room(self, session_id: UUID, payload: Dict[str, Any]) -> Dict:
        """Calls api_create_room to add a new room to a session."""
        return await self._execute_api_function(
            "api_create_room", {"p_session_id": session_id, "p_payload": payload}
        )

    async def update_room(
        self, session_id: UUID, room_id: UUID, payload: Dict[str, Any]
    ) -> Dict:
        """Calls api_update_room to modify an existing room in a session."""
        return await self._execute_api_function(
            "api_update_room",
            {"p_session_id": session_id, "p_room_id": room_id, "p_payload": payload},
        )

    async def delete_room(self, session_id: UUID, room_id: UUID) -> Dict:
        """Calls api_delete_room to remove a room from a session."""
        return await self._execute_api_function(
            "api_delete_room", {"p_session_id": session_id, "p_room_id": room_id}
        )

    # =========================================================================
    # Staff Management
    # =========================================================================

    async def create_staff(self, session_id: UUID, payload: Dict[str, Any]) -> Dict:
        """Calls api_create_staff to add a new staff member to a session."""
        return await self._execute_api_function(
            "api_create_staff", {"p_session_id": session_id, "p_payload": payload}
        )

    async def update_staff(
        self, session_id: UUID, staff_id: UUID, payload: Dict[str, Any]
    ) -> Dict:
        """Calls api_update_staff to modify an existing staff member."""
        return await self._execute_api_function(
            "api_update_staff",
            {"p_session_id": session_id, "p_staff_id": staff_id, "p_payload": payload},
        )

    async def delete_staff(self, session_id: UUID, staff_id: UUID) -> Dict:
        """Calls api_delete_staff to remove a staff member from a session."""
        return await self._execute_api_function(
            "api_delete_staff", {"p_session_id": session_id, "p_staff_id": staff_id}
        )

    async def get_paginated_staff(
        self, session_id: UUID, page: int, page_size: int, search_term: Optional[str]
    ) -> Dict:
        """Calls api_get_paginated_staff to retrieve a list of staff."""
        return await self._execute_api_function(
            "api_get_paginated_staff",
            {
                "p_session_id": session_id,
                "p_page": page,
                "p_page_size": page_size,
                "p_search_term": search_term,
            },
        )

    # =========================================================================
    # Exam Management
    # =========================================================================

    async def create_exam(self, session_id: UUID, payload: Dict[str, Any]) -> Dict:
        """Calls api_create_exam to add a new exam to a session."""
        return await self._execute_api_function(
            "api_create_exam", {"p_session_id": session_id, "p_payload": payload}
        )

    async def update_exam(
        self, session_id: UUID, exam_id: UUID, payload: Dict[str, Any]
    ) -> Dict:
        """Calls api_update_exam to modify an existing exam."""
        return await self._execute_api_function(
            "api_update_exam",
            {"p_session_id": session_id, "p_exam_id": exam_id, "p_payload": payload},
        )

    async def delete_exam(self, session_id: UUID, exam_id: UUID) -> Dict:
        """Calls api_delete_exam to remove an exam from a session."""
        return await self._execute_api_function(
            "api_delete_exam", {"p_session_id": session_id, "p_exam_id": exam_id}
        )

    async def get_paginated_exams(
        self, session_id: UUID, page: int, page_size: int, search_term: Optional[str]
    ) -> Dict:
        """Calls api_get_paginated_exams to retrieve a list of exams."""
        return await self._execute_api_function(
            "api_get_paginated_exams",
            {
                "p_session_id": session_id,
                "p_page": page,
                "p_page_size": page_size,
                "p_search_term": search_term,
            },
        )

    # =========================================================================
    # Department Management
    # =========================================================================

    async def create_department(
        self, session_id: UUID, payload: Dict[str, Any]
    ) -> Dict:
        """Calls api_create_department to add a new department to a session."""
        return await self._execute_api_function(
            "api_create_department", {"p_session_id": session_id, "p_payload": payload}
        )

    async def update_department(
        self, session_id: UUID, department_id: UUID, payload: Dict[str, Any]
    ) -> Dict:
        """Calls api_update_department to modify an existing department."""
        return await self._execute_api_function(
            "api_update_department",
            {
                "p_session_id": session_id,
                "p_department_id": department_id,
                "p_payload": payload,
            },
        )

    async def delete_department(self, session_id: UUID, department_id: UUID) -> Dict:
        """Calls api_delete_department to remove a department from a session."""
        return await self._execute_api_function(
            "api_delete_department",
            {"p_session_id": session_id, "p_department_id": department_id},
        )

    async def get_paginated_departments(
        self, session_id: UUID, page: int, page_size: int, search_term: Optional[str]
    ) -> Dict:
        """Calls api_get_paginated_departments to retrieve a list of departments."""
        return await self._execute_api_function(
            "api_get_paginated_departments",
            {
                "p_session_id": session_id,
                "p_page": page,
                "p_page_size": page_size,
                "p_search_term": search_term,
            },
        )

    # =========================================================================
    # Staff Unavailability Management
    # =========================================================================

    async def create_staff_unavailability(
        self, session_id: UUID, payload: Dict[str, Any]
    ) -> Dict:
        """Calls api_create_staff_unavailability to add an unavailability record."""
        return await self._execute_api_function(
            "api_create_staff_unavailability",
            {"p_session_id": session_id, "p_payload": payload},
        )

    async def get_staff_unavailability(self, session_id: UUID, staff_id: UUID) -> Dict:
        """Calls api_get_staff_unavailability to retrieve unavailability for a staff member."""
        return await self._execute_api_function(
            "api_get_staff_unavailability",
            {"p_session_id": session_id, "p_staff_id": staff_id},
        )

    async def delete_staff_unavailability(
        self, session_id: UUID, unavailability_id: UUID
    ) -> Dict:
        """Calls api_delete_staff_unavailability to remove an unavailability record."""
        return await self._execute_api_function(
            "api_delete_staff_unavailability",
            {"p_session_id": session_id, "p_unavailability_id": unavailability_id},
        )

    # =========================================================================
    # Paginated Data Retrieval
    # =========================================================================

    async def get_paginated_students(
        self, session_id: UUID, page: int, page_size: int, search_term: Optional[str]
    ) -> Dict:
        """Calls api_get_paginated_students to retrieve a list of students."""
        return await self._execute_api_function(
            "api_get_paginated_students",
            {
                "p_session_id": session_id,
                "p_page": page,
                "p_page_size": page_size,
                "p_search_term": search_term,
            },
        )

    # =========================================================================
    # Full Data Graph Retrieval
    # =========================================================================

    async def get_session_data_graph(self, session_id: UUID) -> Dict:
        """
        Calls the main `api_get_session_data_graph` function to retrieve a
        comprehensive, nested JSON object of all data for a given session.
        """
        return await self._execute_api_function(
            "api_get_session_data_graph", {"p_session_id": session_id}
        )
