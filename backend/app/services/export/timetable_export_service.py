import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from .report_builder import ReportBuilder
from ...services.data_retrieval.data_retrieval_service import DataRetrievalService

logger = logging.getLogger(__name__)


class TimetableExportService:
    """
    Service to handle the logic of exporting timetable data into various formats like PDF and CSV.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.report_builder = ReportBuilder()
        self.data_retrieval_service = DataRetrievalService(session)

    def _process_timetable_data(
        self, timetable_json: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Processes the raw timetable JSON blob into a flat list of dictionaries (rows)
        suitable for tabular export.

        Args:
            timetable_json: The raw dictionary containing timetable solution data.

        Returns:
            A list of processed and sorted dictionaries, where each dictionary is a row.
        """
        # --- START OF FIX ---
        # The assignment data is nested within the 'solution' key of the JSON blob.
        solution_data = timetable_json.get("solution", {})
        assignments = solution_data.get("assignments", {})
        # --- END OF FIX ---

        if not assignments:
            logger.warning("No assignments found in the provided timetable data.")
            return []

        processed_rows = []
        for exam_id, details in assignments.items():
            # Handle cases where multiple rooms are assigned
            room_codes = ", ".join(details.get("room_codes", ["N/A"]))

            row = {
                "date": details.get("date"),
                "start_time": details.get("start_time"),
                "end_time": details.get("end_time"),
                "course_code": details.get("course_code", "N/A"),
                "course_title": details.get("course_title", "N/A"),
                "rooms": room_codes,
                "instructor": details.get("instructor_name", "N/A"),
                "student_count": details.get("student_count", 0),
                "faculty_name": details.get("faculty_name", "Uncategorized"),
                "department_name": details.get("department_name", ""),
            }
            processed_rows.append(row)

        # Sort the data by date and then by start time for a chronological report
        if processed_rows:
            processed_rows.sort(
                key=lambda x: (
                    datetime.strptime(x["date"], "%Y-%m-%d").date(),
                    datetime.strptime(x["start_time"], "%H:%M:%S").time(),
                )
            )

        return processed_rows

    async def export_timetable(
        self, version_id: UUID, output_format: str
    ) -> Optional[bytes]:
        """
        Fetches, processes, and exports a timetable version into the specified format.

        Args:
            version_id: The UUID of the timetable version to export.
            output_format: The desired output format ('pdf' or 'csv').

        Returns:
            The generated report file as bytes, or None if an error occurs.
        """
        try:
            logger.info(
                f"Starting export for version '{version_id}' in '{output_format}' format."
            )

            # 1. Get the job_id from the version_id
            job_id = await self.data_retrieval_service.get_job_id_from_version(
                version_id
            )
            if not job_id:
                logger.warning(f"No job found for timetable version ID '{version_id}'.")
                return None

            # 2. Get the timetable results data from the job
            timetable_data = (
                await self.data_retrieval_service.get_timetable_job_results(
                    job_id=job_id
                )
            )
            if not timetable_data:
                logger.warning(f"No timetable result data found for job ID '{job_id}'.")
                return None

            # 3. Process the data into a tabular format
            rows = self._process_timetable_data(timetable_data)
            if not rows:
                logger.warning(
                    f"Processed data for job '{job_id}' resulted in an empty list."
                )
                return None

            # 4. Define columns and title for the report
            columns = [
                "date",
                "start_time",
                "end_time",
                "course_code",
                "course_title",
                "rooms",
                "instructor",
                "student_count",
            ]
            title = f"Examination Timetable (Version: {version_id})"

            # 5. Build the report using the appropriate builder
            if output_format.lower() == "csv":
                logger.info("Building CSV report.")
                return self.report_builder.build_csv(rows, columns)
            elif output_format.lower() == "pdf":
                logger.info("Building PDF report.")
                return self.report_builder.build_pdf(
                    rows, columns, title, template="timetable"
                )
            else:
                logger.error(f"Unsupported export format requested: {output_format}")
                raise ValueError(f"Unsupported report format: {output_format}")

        except Exception as e:
            logger.error(
                f"Failed to export timetable version '{version_id}': {e}", exc_info=True
            )
            return None
