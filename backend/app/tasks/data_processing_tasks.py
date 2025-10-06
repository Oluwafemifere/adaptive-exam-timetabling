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
from ..services.uploads.data_upload_service import DataUploadService

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

        # Use server_settings to define search_path at connection time
        conn = await asyncpg.connect(
            dsn=asyncpg_dsn,
            server_settings={"search_path": "staging,exam_system,public"},
        )

        # Verify actual search path
        current_search_path = await conn.fetchval("SHOW search_path")
        logger.info(
            f"Asyncpg connection established. Current search_path: {current_search_path}"
        )

        # Prepare the CSV data with an added session_id column
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

            # copy_to_table should only take the table name, not schema-qualified
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


async def _async_process_csv_upload(
    task_id: str,
    upload_session_id: str,
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
        else lambda *args, **kwargs: None
    )

    engine = create_async_engine(settings.DATABASE_URL)
    schema_search_path = "staging, exam_system, public"

    @event.listens_for(engine.sync_engine, "connect")
    def set_search_path(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET search_path TO {schema_search_path};")
        cursor.close()

    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    session_uuid = UUID(upload_session_id)
    academic_session_uuid = UUID(academic_session_id)

    async with async_session_factory() as session:
        upload_service = DataUploadService(session)
        try:
            update_state_func(
                state="PROGRESS", meta={"current": 10, "phase": "Loading to Staging"}
            )
            await _prepare_csv_and_bulk_load(
                file_path, academic_session_id, entity_type
            )

            update_state_func(
                state="PROGRESS",
                meta={"current": 50, "phase": "Processing Staged Data"},
            )

            db_func_result = await session.execute(
                text("SELECT exam_system.process_all_staged_data(:p_session_id)"),
                {"p_session_id": academic_session_uuid},
            )

            processing_report = db_func_result.scalar_one()

            if not processing_report.get("success"):
                raise Exception(
                    f"Database processing failed: {processing_report.get('message', 'Unknown error')}"
                )

            update_state_func(
                state="PROGRESS", meta={"current": 95, "phase": "Finalizing"}
            )

            await upload_service.update_upload_session_status(
                session_uuid, "completed", processing_report
            )
            logger.info(
                f"Successfully processed upload {upload_session_id} for entity '{entity_type}'."
            )

            update_state_func(
                state="SUCCESS", meta={"current": 100, "phase": "Completed"}
            )
            return processing_report

        except Exception as e:
            await session.rollback()
            error_payload = {"error": str(e)}
            logger.error(
                f"Error in CSV processing task for {upload_session_id}: {error_payload}",
                exc_info=True,
            )
            await upload_service.update_upload_session_status(
                session_uuid, "failed", error_payload
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
    upload_session_id: str,
    file_path: str,
    entity_type: str,
    user_id: str,
    academic_session_id: str,
) -> dict:
    try:
        logger.info(
            f"Celery task started for staging CSV upload {upload_session_id} (entity: {entity_type})"
        )
        self.update_state(
            state="PROGRESS", meta={"current": 5, "phase": "Initializing"}
        )

        return _run_coro_in_new_loop(
            _async_process_csv_upload(
                self.request.id,
                upload_session_id,
                file_path,
                entity_type,
                user_id,
                academic_session_id,
            )
        )

    except Exception as exc:
        logger.critical(
            f"Celery task failed catastrophically for {upload_session_id}: {exc}",
            exc_info=True,
        )
        raise


__all__ = ["process_csv_upload_task"]
