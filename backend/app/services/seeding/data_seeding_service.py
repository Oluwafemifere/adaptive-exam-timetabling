# backend/app/services/seeding/data_seeding_service.py
import logging
from uuid import UUID
from typing import Dict, Any, Optional, List
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import inspect, text, VARCHAR
from sqlalchemy.engine import RowMapping
from sqlalchemy.dialects.postgresql import UUID as UUIDType, ARRAY


logger = logging.getLogger(__name__)


# Define a whitelist of allowed staging tables to prevent SQL injection
ALLOWED_STAGING_TABLES = [
    "faculties",
    "departments",
    "programmes",
    "buildings",
    "rooms",
    "courses",
    "staff",
    "students",
    "course_instructors",
    "course_departments",
    "course_faculties",
    "staff_unavailability",
    "course_registrations",
]


class DataSeedingService:
    """Service for managing data seeding sessions and writing to staging tables."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_seeding_session_by_academic_session(
        self, academic_session_id: UUID
    ) -> Optional[RowMapping]:
        """Retrieves a data seeding session linked to an academic session."""
        query = text(
            "SELECT id, status FROM exam_system.data_seeding_sessions WHERE academic_session_id = :session_id"
        )
        result = await self.session.execute(query, {"session_id": academic_session_id})
        return result.mappings().first()

    async def get_seeding_session_with_files(
        self, seeding_session_id: UUID
    ) -> Optional[RowMapping]:
        """Retrieves a seeding session with details of all its file uploads."""
        query = text(
            """
            SELECT
                dss.id,
                dss.status,
                dss.created_at,
                COALESCE(jsonb_agg(
                    jsonb_build_object(
                        'id', fu.id,
                        'file_name', fu.file_name,
                        'upload_type', fu.upload_type,
                        'status', fu.status,
                        'total_records', fu.total_records,
                        'processed_records', fu.processed_records,
                        'updated_at', fu.updated_at
                    )
                ) FILTER (WHERE fu.id IS NOT NULL), '[]'::jsonb) AS files
            FROM exam_system.data_seeding_sessions dss
            LEFT JOIN exam_system.file_uploads fu ON dss.id = fu.data_seeding_session_id
            WHERE dss.id = :session_id
            GROUP BY dss.id;
            """
        )
        result = await self.session.execute(query, {"session_id": seeding_session_id})
        return result.mappings().first()

    async def get_staged_data(
        self, session_id: UUID, entity_type: str
    ) -> Dict[str, Any]:
        """Fetches all staged data for a given session and entity type."""
        query = text(
            "SELECT exam_system.get_staged_data(:p_session_id, :p_entity_type)"
        )
        result = await self.session.execute(
            query, {"p_session_id": session_id, "p_entity_type": entity_type}
        )
        return result.scalar_one()

    async def update_staged_record(
        self, entity_type: str, record_pk: str, update_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Updates a single record in a staging table."""
        query = text(
            "SELECT exam_system.update_staged_record(:p_entity_type, :p_record_pk, :p_payload)"
        )
        result = await self.session.execute(
            query,
            {
                "p_entity_type": entity_type,
                "p_record_pk": record_pk,
                "p_payload": update_payload,
            },
        )
        return result.scalar_one()
