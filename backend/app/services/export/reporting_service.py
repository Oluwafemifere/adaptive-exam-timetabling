# backend/app/services/export/reporting_service.py
"""
Service for generating downloadable reports in various formats (CSV, PDF).
"""
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json

from .report_builder import ReportBuilder

logger = logging.getLogger(__name__)


class ReportingService:
    """Generates reports by calling the `generate_report` DB function."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.report_builder = ReportBuilder()

    async def generate_system_report(
        self,
        report_type: str,
        session_id: UUID,
        options: Dict[str, Any],
        output_format: str = "pdf",
    ) -> Optional[bytes]:
        """
        Generates a system report by calling the central `generate_report` function
        and then formatting the output.

        Args:
            report_type: The type of report to generate (e.g., 'full_timetable', 'conflict_summary').
            session_id: The academic session for the report.
            options: A dictionary of report-specific options.
            output_format: The desired output format ('pdf' or 'csv').

        Returns:
            The report file as bytes, or None on failure.
        """
        try:
            logger.info(
                f"Generating '{report_type}' report in '{output_format}' for session {session_id}"
            )

            # Call the generic report generation function in the database
            query = text(
                "SELECT exam_system.generate_report(:p_report_type, :p_session_id, :p_options)"
            )
            result = await self.session.execute(
                query,
                {
                    "p_report_type": report_type,
                    "p_session_id": session_id,
                    "p_options": json.dumps(options),
                },
            )
            report_data = result.scalar_one_or_none()

            if not report_data or not report_data.get("rows"):
                logger.warning(f"No data returned for report type '{report_type}'")
                return None

            rows = report_data["rows"]
            columns = report_data.get("columns", list(rows[0].keys()) if rows else [])
            title = report_data.get(
                "title", f"{report_type.replace('_', ' ').title()} Report"
            )

            if output_format.lower() == "csv":
                return self.report_builder.build_csv(rows, columns)
            elif output_format.lower() == "pdf":
                return self.report_builder.build_pdf(rows, columns, title)
            else:
                raise ValueError(f"Unsupported report format: {output_format}")

        except Exception as e:
            logger.error(
                f"Failed to generate report '{report_type}': {e}", exc_info=True
            )
            return None
