# backend/app/services/export/reporting_service.py
"""
Service for generating downloadable reports in various formats (CSV, PDF).
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from .report_builder import ReportBuilder
from ..data_retrieval import DataRetrievalService

logger = logging.getLogger(__name__)


class ReportingService:
    """Generates reports by fetching data and using format-specific builders."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.data_service = DataRetrievalService(session)
        self.report_builder = ReportBuilder()

    async def generate_full_timetable_report(
        self, version_id: UUID, format: str = "pdf"
    ) -> Optional[bytes]:
        """
        Generates a full timetable report for a given version.

        Args:
            version_id: The ID of the timetable version.
            format: The desired output format ('pdf' or 'csv').

        Returns:
            The report file as bytes, or None if data cannot be fetched.
        """
        try:
            logger.info(
                f"Generating '{format}' timetable report for version {version_id}"
            )
            timetable_data = await self.data_service.get_full_timetable(version_id)

            if not timetable_data or not timetable_data.get("assignments"):
                logger.warning(f"No data found for timetable version {version_id}")
                return None

            rows = timetable_data["assignments"]
            title = (
                f"Exam Timetable for {timetable_data.get('session_name', 'Session')}"
            )
            columns = [
                "exam_date",
                "time_slot",
                "course_code",
                "course_title",
                "room_code",
                "student_count",
                "invigilators",
            ]

            if format.lower() == "csv":
                return self.report_builder.build_csv(rows, columns)
            elif format.lower() == "pdf":
                return self.report_builder.build_pdf(rows, columns, title)
            else:
                raise ValueError(f"Unsupported report format: {format}")

        except Exception as e:
            logger.error(
                f"Failed to generate timetable report for version {version_id}: {e}",
                exc_info=True,
            )
            return None
