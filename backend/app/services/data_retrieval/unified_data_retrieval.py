# backend/app/services/data_retrieval/unified_data_retrieval.py

import logging
from typing import Dict, Any, Optional
from uuid import UUID
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Set up logger
logger = logging.getLogger(__name__)


class UnifiedDataService:
    """
    A unified service for retrieving pre-structured data sets from the database
    by calling dedicated PostgreSQL functions. This approach offloads complex
    data aggregation and JSON building to the database layer.
    """

    def __init__(self, session: AsyncSession):
        """
        Initializes the data service with a database session.
        Args:
            session: An active SQLAlchemy AsyncSession.
        """
        self.session = session
        logger.debug("UnifiedDataService initialized")

    async def _execute_pg_function(
        self, function_name: str, params: Dict[str, Any]
    ) -> Any:
        """
        Generic helper to execute a PostgreSQL function and return its result.
        Handles JSON parsing and basic error checking.
        """
        logger.info(
            f"Executing PostgreSQL function '{function_name}' with params: {params}"
        )
        try:
            # Construct the SQL query to call the function with named parameters
            query = text(
                f"SELECT exam_system.{function_name}({', '.join(':' + k for k in params.keys())})"
            )
            result = await self.session.execute(query, params)

            # The function returns a single row with a single column containing the JSONB
            raw_data = result.scalar_one_or_none()

            if raw_data is None:
                logger.warning(f"PostgreSQL function '{function_name}' returned NULL.")
                return None

            # asyncpg automatically decodes JSONB to a Python dict/list.
            # If it's a string, it needs parsing (fallback).
            if isinstance(raw_data, str):
                return json.loads(raw_data)

            return raw_data

        except Exception as e:
            logger.error(
                f"Failed to execute PostgreSQL function '{function_name}': {e}",
                exc_info=True,
            )
            raise

    async def get_scheduling_dataset(self, session_id: UUID) -> Dict[str, Any]:
        """
        Retrieves the complete, structured dataset required for the scheduling engine
        by calling the `get_scheduling_dataset` PostgreSQL function.
        """
        dataset = await self._execute_pg_function(
            "get_scheduling_dataset", {"p_session_id": session_id}
        )

        if not dataset:
            raise ValueError(
                f"PostgreSQL function returned no data for session {session_id}."
            )

        # Validate the structure of the returned dataset
        critical_components = ["exams", "rooms", "students", "invigilators"]
        missing_components = [
            comp for comp in critical_components if not dataset.get(comp)
        ]

        if missing_components:
            error_msg = f"Dataset from PG function is missing critical components: {missing_components}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(
            f"Successfully retrieved scheduling dataset for session {session_id}: "
            f"{len(dataset.get('exams', []))} exams, "
            f"{len(dataset.get('rooms', []))} rooms, "
            f"{len(dataset.get('students', []))} students."
        )
        return dataset

    async def get_student_schedule(
        self, student_id: UUID, session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves the complete exam schedule for a specific student in a given session
        by calling the `get_student_schedule` PostgreSQL function.
        """
        schedule = await self._execute_pg_function(
            "get_student_schedule",
            {"p_student_id": student_id, "p_session_id": session_id},
        )
        if schedule:
            logger.info(f"Successfully retrieved schedule for student {student_id}")
        return schedule

    async def get_room_schedule(
        self, room_id: UUID, session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves the exam schedule for a specific room in a given session
        by calling the `get_room_schedule` PostgreSQL function.
        """
        schedule = await self._execute_pg_function(
            "get_room_schedule", {"p_room_id": room_id, "p_session_id": session_id}
        )
        if schedule:
            logger.info(f"Successfully retrieved schedule for room {room_id}")
        return schedule

    async def get_invigilator_schedule(
        self, staff_id: UUID, session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves the invigilation schedule for a specific staff member in a given session
        by calling the `get_invigilator_schedule` PostgreSQL function.
        """
        schedule = await self._execute_pg_function(
            "get_invigilator_schedule",
            {"p_staff_id": staff_id, "p_session_id": session_id},
        )
        if schedule:
            logger.info(f"Successfully retrieved schedule for invigilator {staff_id}")
        return schedule

    async def get_full_timetable(self, version_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieves a fully structured and aggregated timetable for a specific timetable version
        by calling the `get_full_timetable` PostgreSQL function.
        """
        timetable = await self._execute_pg_function(
            "get_full_timetable", {"p_version_id": version_id}
        )
        if timetable:
            logger.info(
                f"Successfully retrieved full timetable for version {version_id}"
            )
        return timetable
