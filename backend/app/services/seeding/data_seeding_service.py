# backend/app/services/seeding/data_seeding_service.py
import logging
from uuid import UUID
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class DataSeedingService:
    """Service for managing data seeding sessions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_seeding_session_by_academic_session(
        self, academic_session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves the data seeding session linked to an academic session.
        """
        logger.debug(
            f"Fetching data seeding session for academic session {academic_session_id}"
        )
        try:
            query = text(
                """
                SELECT id, academic_session_id, status, created_at, updated_at
                FROM exam_system.data_seeding_sessions
                WHERE academic_session_id = :academic_session_id
                """
            )
            result = await self.session.execute(
                query, {"academic_session_id": academic_session_id}
            )
            session_data = result.mappings().first()
            return dict(session_data) if session_data else None
        except Exception as e:
            logger.error(
                f"Failed to fetch seeding session for academic session {academic_session_id}: {e}",
                exc_info=True,
            )
            return None

    async def get_seeding_session_with_files(
        self, seeding_session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves a seeding session and the status of all its associated file uploads.
        """
        logger.debug(
            f"Fetching seeding session {seeding_session_id} with file statuses"
        )
        try:
            # This function is assumed to exist in the database for this purpose
            query = text(
                "SELECT exam_system.get_seeding_session_status(:p_seeding_session_id)"
            )
            result = await self.session.execute(
                query, {"p_seeding_session_id": seeding_session_id}
            )
            summary_data = result.scalar_one_or_none()
            return summary_data
        except Exception as e:
            logger.error(f"Error fetching seeding session status: {e}", exc_info=True)
            return None
