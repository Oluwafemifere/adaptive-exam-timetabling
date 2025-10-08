# backend/app/tasks/data_processing_tasks.py

import logging
import os
import csv
import io
from uuid import UUID
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import event, text

from ..core.config import settings
from .celery_app import celery_app, _run_coro_in_new_loop
from ..services.uploads.file_upload_service import FileUploadService

logger = logging.getLogger(__name__)


async def _prepare_csv_and_bulk_load(file_path: str, session_id: str, entity_type: str):
    """
    Reads a CSV file, prepends the session_id to each row, and streams it
    to the corresponding staging table using asyncpg's fast COPY command.
    """
    schema = "staging"
    table_name = entity_type
    logger.info(f"Preparing to bulk load {file_path} into {schema}.{table_name}")

    conn = None
    try:
        asyncpg_dsn = settings.DATABASE_URL.replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        conn = await asyncpg.connect(
            dsn=asyncpg_dsn,
            server_settings={"search_path": "staging,exam_system,public"},
        )

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            string_buffer = io.StringIO()
            writer = csv.writer(string_buffer)
            writer.writerow(["session_id"] + header)
            for row in reader:
                writer.writerow([session_id] + row)
            string_buffer.seek(0)
            csv_data_bytes = string_buffer.getvalue().encode("utf-8")
            bytes_buffer = io.BytesIO(csv_data_bytes)
            await conn.copy_to_table(
                table_name, source=bytes_buffer, format="csv", header=True
            )
        logger.info(
            f"Successfully loaded data into {schema}.{table_name} for session {session_id}"
        )
    except Exception as e:
        logger.error(
            f"Bulk load to staging table failed for session {session_id}: {e}",
            exc_info=True,
        )
        raise
    finally:
        if conn:
            await conn.close()


# --- START OF FIX: Updated function signature and logic ---
async def _async_process_csv_upload(
    task_id: str,
    file_upload_id: str,
    file_path: str,
    entity_type: str,
    user_id: str,
    academic_session_id: str,
) -> dict:
    from celery import current_task

    task = current_task._get_current_object()
    update_state_func = (
        task.update_state
        if task and task.request.id == task_id
        else lambda *a, **k: None
    )

    engine = create_async_engine(settings.DATABASE_URL)
    schema_search_path = "staging, exam_system, public"

    @event.listens_for(engine.sync_engine, "connect")
    def set_search_path(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET search_path TO {schema_search_path};")
        cursor.close()

    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    upload_uuid = UUID(file_upload_id)

    async with async_session_factory() as session:
        upload_service = FileUploadService(session)
        try:
            update_state_func(
                state="PROGRESS", meta={"current": 10, "phase": "Loading to Staging"}
            )
            await _prepare_csv_and_bulk_load(
                file_path, academic_session_id, entity_type
            )

            update_state_func(
                state="PROGRESS", meta={"current": 95, "phase": "Finalizing"}
            )

            # The task's responsibility ends after loading data into staging.
            # The final processing is triggered by a separate user action.
            status_details = {"message": "File successfully loaded into staging table."}
            await upload_service.update_file_upload_status(
                upload_uuid, "completed", validation_errors=status_details
            )
            logger.info(
                f"Successfully staged upload {file_upload_id} for entity '{entity_type}'."
            )

            update_state_func(
                state="SUCCESS", meta={"current": 100, "phase": "Completed"}
            )
            return {"success": True, "message": "File staged successfully."}

        except Exception as e:
            await session.rollback()
            error_payload = {"error": str(e)}
            logger.error(
                f"Error in CSV staging task for {file_upload_id}: {error_payload}",
                exc_info=True,
            )
            await upload_service.update_file_upload_status(
                upload_uuid, "failed", validation_errors=error_payload
            )
            raise
        finally:
            if os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                    logger.info(f"Cleaned up temporary file: {file_path}")
                except OSError as e:
                    logger.warning(
                        f"Failed to clean up temporary file {file_path}: {e}"
                    )
            if engine:
                await engine.dispose()


@celery_app.task(bind=True, name="process_csv_upload")
def process_csv_upload_task(
    self,
    file_upload_id: str,
    file_path: str,
    entity_type: str,
    user_id: str,
    academic_session_id: str,
) -> dict:
    try:
        logger.info(
            f"Celery task started for staging CSV upload {file_upload_id} (entity: {entity_type})"
        )
        self.update_state(
            state="PROGRESS", meta={"current": 5, "phase": "Initializing"}
        )
        return _run_coro_in_new_loop(
            _async_process_csv_upload(
                self.request.id,
                file_upload_id,
                file_path,
                entity_type,
                user_id,
                academic_session_id,
            )
        )
    except Exception as exc:
        logger.critical(
            f"Celery task failed catastrophically for {file_upload_id}: {exc}",
            exc_info=True,
        )
        raise


# --- END OF FIX ---

__all__ = ["process_csv_upload_task"]
