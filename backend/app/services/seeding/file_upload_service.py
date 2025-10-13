# backend/app/services/seeding/file_upload_service.py
import logging
import os
from uuid import UUID
from pathlib import Path
from typing import List, Dict, Any, Optional
import json  # --- START OF FIX: Import the json library ---

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..data_validation import CSVProcessor, ENTITY_SCHEMAS

logger = logging.getLogger(__name__)


class FileUploadService:
    """Orchestrates the CSV file upload, detection, validation, and task dispatching."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.csv_processor = CSVProcessor()
        for entity, schema in ENTITY_SCHEMAS.items():
            self.csv_processor.register_schema(entity, schema)

    async def create_file_upload_record(
        self,
        data_seeding_session_id: UUID,
        upload_type: str,
        file_name: str,
        file_path: str,
        total_records: int,
    ) -> UUID:
        """Creates a record in the file_uploads table and returns its ID."""
        query = text(
            """
            INSERT INTO exam_system.file_uploads
            (data_seeding_session_id, upload_type, status, file_name, file_path, total_records)
            VALUES (:dss_id, :type, 'pending', :name, :path, :records)
            RETURNING id;
        """
        )
        result = await self.db_session.execute(
            query,
            {
                "dss_id": data_seeding_session_id,
                "type": upload_type,
                "name": file_name,
                "path": file_path,
                "records": total_records,
            },
        )
        await self.db_session.commit()
        return result.scalar_one()

    async def update_file_upload_status(
        self, upload_id: UUID, status: str, validation_errors: Optional[dict] = None
    ) -> None:
        """Updates the status and errors of a file upload record."""
        query = text(
            """
            UPDATE exam_system.file_uploads
            SET status = :status, validation_errors = :errors
            WHERE id = :upload_id;
        """
        )

        # --- START OF FIX ---
        # Serialize the Python dictionary to a JSON string before passing it to the database.
        # Use json.dumps with `default=str` to handle non-serializable types like exceptions.
        errors_payload = json.dumps(validation_errors or {}, default=str)
        # --- END OF FIX ---

        await self.db_session.execute(
            query,
            {
                "status": status,
                # --- START OF FIX ---
                # Pass the serialized JSON string instead of the raw dictionary.
                "errors": errors_payload,
                # --- END OF FIX ---
                "upload_id": upload_id,
            },
        )
        await self.db_session.commit()

    async def handle_file_uploads_and_dispatch(
        self,
        academic_session_id: UUID,
        data_seeding_session_id: UUID,
        user_id: UUID,
        file_paths: List[Path],
    ) -> Dict[str, Any]:
        """Validates files, creates records, and dispatches Celery tasks."""
        from ...tasks import process_csv_upload_task

        results = {"dispatched_tasks": [], "failed_files": []}
        for file_path in file_paths:
            file_result = {"file_name": file_path.name, "status": "failed"}
            try:
                structure_validation = self.csv_processor.validate_csv_structure(file_path, entity_type=None)  # type: ignore
                if not structure_validation["is_valid"]:
                    file_result["error"] = (
                        f"Invalid file structure: {structure_validation['errors']}"
                    )
                    results["failed_files"].append(file_result)
                    continue

                entity_type = self.csv_processor.detect_entity_type(
                    file_path, structure_validation["columns"]
                )
                if not entity_type:
                    file_result["error"] = "Could not determine entity type."
                    results["failed_files"].append(file_result)
                    continue

                file_upload_id = await self.create_file_upload_record(
                    data_seeding_session_id=data_seeding_session_id,
                    upload_type=entity_type,
                    file_name=file_path.name,
                    file_path=str(file_path),
                    total_records=structure_validation["row_count"],
                )

                task = process_csv_upload_task.delay(
                    file_upload_id=str(file_upload_id),
                    file_path=str(file_path),
                    entity_type=entity_type,
                    user_id=str(user_id),
                    academic_session_id=str(academic_session_id),
                )

                file_result["status"] = "dispatched"
                file_result["task_id"] = task.id
                file_result["entity_type"] = entity_type
                results["dispatched_tasks"].append(file_result)
                logger.info(
                    f"Dispatched task {task.id} for file {file_path.name} (entity: {entity_type})"
                )
            except Exception as e:
                logger.error(
                    f"Failed to dispatch task for {file_path.name}: {e}", exc_info=True
                )
                file_result["error"] = f"An unexpected server error occurred: {e}"
                results["failed_files"].append(file_result)
                if os.path.exists(file_path):
                    os.unlink(file_path)
        return results
