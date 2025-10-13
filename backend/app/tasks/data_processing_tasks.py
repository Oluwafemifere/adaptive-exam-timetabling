# backend/app/tasks/data_processing_tasks.py

import logging
import os
import csv
import io
from uuid import UUID
import asyncpg
import pandas as pd
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import event, text

from ..core.config import settings
from .celery_app import celery_app, _run_coro_in_new_loop
from ..services.seeding.file_upload_service import FileUploadService
from ..services.data_validation.validation_schemas import ENTITY_SCHEMAS
from ..services.data_validation.csv_processor import transform_string_to_array

logger = logging.getLogger(__name__)


def _format_array_for_postgres(value):
    """Formats a list or a comma-separated string for PostgreSQL array literal."""
    if value is None or value == "":
        return None
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
    else:
        return value

    formatted_items = [f'"{str(item).replace("\"", "\"\"")}"' for item in items]
    return f"{{{','.join(formatted_items)}}}"


async def _prepare_csv_and_bulk_load(file_path: str, session_id: str, entity_type: str):
    """
    Reads a CSV file, de-duplicates based on business keys, transforms it,
    and streams it to the corresponding staging table via COPY command.
    """
    schema_name = "staging"
    table_name = entity_type
    logger.info(f"Preparing to bulk load {file_path} into {schema_name}.{table_name}")

    if entity_type not in ENTITY_SCHEMAS:
        raise ValueError(f"No schema defined for entity type: {entity_type}")

    entity_schema = ENTITY_SCHEMAS[entity_type]
    conn = None
    try:
        df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
        original_row_count = len(df)

        column_mappings = entity_schema.get("column_mappings", {})
        rename_dict = {
            csv_col: db_col
            for csv_col, db_col in column_mappings.items()
            if csv_col in df.columns
        }
        df.rename(columns=rename_dict, inplace=True)

        # --- START OF FIX: De-duplicate data before loading ---
        # The business key (e.g., 'code', 'staff_number') is defined in required_columns.
        # We de-duplicate based on this key to prevent unique constraint violations.
        business_key_cols = [
            col
            for col in entity_schema.get("required_columns", [])
            if col in df.columns
        ]

        if business_key_cols:
            df.drop_duplicates(subset=business_key_cols, keep="last", inplace=True)
            deduplicated_row_count = len(df)
            if original_row_count > deduplicated_row_count:
                logger.warning(
                    f"Removed {original_row_count - deduplicated_row_count} duplicate rows "
                    f"from {os.path.basename(file_path)} based on key(s): {business_key_cols}"
                )
        # --- END OF FIX ---

        df["session_id"] = session_id

        transformers = entity_schema.get("transformers", {})
        for col, transformer in transformers.items():
            if col in df.columns:
                if transformer is transform_string_to_array:
                    df[col] = df[col].apply(_format_array_for_postgres)

        asyncpg_dsn = settings.DATABASE_URL.replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        conn = await asyncpg.connect(
            dsn=asyncpg_dsn,
            server_settings={"search_path": "staging,exam_system,public"},
        )

        table_columns_query = f"""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = '{schema_name}' AND table_name = '{table_name}'
            ORDER BY ordinal_position;
        """
        table_cols_records = await conn.fetch(table_columns_query)
        target_columns = [rec["column_name"] for rec in table_cols_records]

        for col in target_columns:
            if col not in df.columns:
                df[col] = None

        df = df[target_columns]

        string_buffer = io.StringIO()
        df.to_csv(string_buffer, index=False, header=True, quoting=csv.QUOTE_MINIMAL)
        string_buffer.seek(0)
        csv_data_bytes = string_buffer.getvalue().encode("utf-8")
        bytes_buffer = io.BytesIO(csv_data_bytes)

        await conn.copy_to_table(
            table_name, source=bytes_buffer, format="csv", header=True
        )
        logger.info(
            f"Successfully loaded {len(df)} rows into {schema_name}.{table_name}"
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


__all__ = ["process_csv_upload_task"]
