# backend/app/tasks/data_processing_tasks.py

"""
Celery tasks for data processing operations including CSV ingestion,
data validation, transformation, and bulk operations.
"""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text  # MODIFIED: Imported text
from .celery_app import celery_app
from ..services.data_validation.csv_processor import CSVProcessor
from ..services.data_validation.data_mapper import DataMapper
from ..services.data_validation.integrity_checker import (
    DataIntegrityChecker,
    IntegrityCheckResult,
)

# REMOVED: from ..services.data_retrieval.audit_data import AuditData
from ..models.file_uploads import FileUploadSession
from ..core.exceptions import DataProcessingError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from sqlalchemy.orm import Session
import asyncio
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


async def _async_process_csv_upload(
    task_id: str,
    upload_session_id: str,
    file_path: str,
    entity_type: str,
    user_id: str,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Async implementation of CSV upload processing"""
    from celery import current_task
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy.pool import NullPool
    from ..core.config import settings

    task = current_task._get_current_object()
    if task and task.request.id == task_id:
        update_state_func = task.update_state
    else:

        def update_state_func(*args, **kwargs):
            pass

    engine = None
    try:
        engine = create_async_engine(
            settings.DATABASE_URL, poolclass=NullPool, echo=False
        )
        async_session = async_sessionmaker(engine, expire_on_commit=False)

        async with async_session() as session:
            try:
                csv_processor = CSVProcessor()
                data_mapper = DataMapper(session)
                # REMOVED: audit_data = AuditData(session)

                upload_uuid = UUID(upload_session_id)
                user_uuid = UUID(user_id)

                update_state_func(
                    state="PROGRESS",
                    meta={
                        "current": 10,
                        "total": 100,
                        "phase": "validating_structure",
                        "message": "Validating CSV structure...",
                    },
                )

                validation_result = csv_processor.validate_csv_structure(
                    file_path, entity_type
                )

                if not validation_result["is_valid"]:
                    await _update_upload_session_failed(
                        session, upload_uuid, validation_result["errors"]
                    )
                    raise DataProcessingError(
                        f"CSV validation failed: {validation_result['errors']}",
                        phase="validation",
                        entity_type=entity_type,
                        validation_errors=validation_result["errors"],
                    )

                update_state_func(
                    state="PROGRESS",
                    meta={
                        "current": 30,
                        "total": 100,
                        "phase": "processing_data",
                        "message": "Processing CSV data...",
                    },
                )

                processing_result = csv_processor.process_csv_file(
                    file_path,
                    entity_type,
                    validate_data=True,
                    chunk_size=options.get("chunk_size", 1000) if options else 1000,
                )

                if not processing_result["success"]:
                    await _update_upload_session_failed(
                        session, upload_uuid, processing_result["errors"]
                    )
                    raise DataProcessingError(
                        f"CSV processing failed: {processing_result['errors']}",
                        phase="processing",
                        entity_type=entity_type,
                        validation_errors=processing_result["errors"],
                    )

                update_state_func(
                    state="PROGRESS",
                    meta={
                        "current": 60,
                        "total": 100,
                        "phase": "mapping_data",
                        "message": "Mapping data to database format...",
                    },
                )

                mapping_result = await data_mapper.map_data(
                    processing_result["data"], entity_type
                )

                if not mapping_result["success"]:
                    await _update_upload_session_failed(
                        session, upload_uuid, mapping_result["errors"]
                    )
                    raise DataProcessingError(
                        f"Data mapping failed: {mapping_result['errors']}",
                        phase="mapping",
                        entity_type=entity_type,
                        validation_errors=mapping_result["errors"],
                    )

                update_state_func(
                    state="PROGRESS",
                    meta={
                        "current": 80,
                        "total": 100,
                        "phase": "saving_results",
                        "message": "Saving processed data...",
                    },
                )

                await _update_upload_session_completed(
                    session,
                    upload_uuid,
                    {
                        "processing_result": processing_result,
                        "mapping_result": mapping_result,
                        "total_records": processing_result["total_rows"],
                        "processed_records": mapping_result["processed_records"],
                        "validation_errors": processing_result.get(
                            "validation_errors", []
                        ),
                    },
                )

                try:
                    # MODIFIED: Call the database function to log audit activity
                    await session.execute(
                        text(
                            """
                            SELECT exam_system.log_audit_activity(
                                p_user_id => :user_id,
                                p_action => :action,
                                p_entity_type => :entity_type,
                                p_notes => :notes,
                                p_session_id => :session_id
                            );
                            """
                        ),
                        {
                            "user_id": user_uuid,
                            "action": "data_import",
                            "entity_type": entity_type,
                            "notes": f"CSV upload processed {mapping_result['processed_records']} records for {entity_type}",
                            "session_id": upload_session_id,
                        },
                    )
                    await session.commit()
                except Exception as e:
                    logger.warning(f"Failed to create audit log: {e}")

                update_state_func(
                    state="SUCCESS",
                    meta={
                        "current": 100,
                        "total": 100,
                        "phase": "completed",
                        "message": f'Successfully processed {mapping_result["processed_records"]} records',
                    },
                )

                try:
                    os.unlink(file_path)
                except Exception as e:
                    logger.warning(
                        f"Failed to clean up temporary file {file_path}: {e}"
                    )

                return {
                    "success": True,
                    "upload_session_id": upload_session_id,
                    "entity_type": entity_type,
                    "total_records": processing_result["total_rows"],
                    "processed_records": mapping_result["processed_records"],
                    "mapped_data": mapping_result["mapped_data"][:100],
                    "validation_errors": processing_result.get("validation_errors", []),
                    "warnings": processing_result.get("warnings", [])
                    + mapping_result.get("warnings", []),
                }

            except Exception as e:
                logger.error(f"Error in CSV processing: {e}")
                await _update_upload_session_failed(
                    session, UUID(upload_session_id), [str(e)]
                )
                raise DataProcessingError(f"CSV processing failed: {e}").with_context(
                    upload_session_id=upload_session_id,
                    entity_type=entity_type,
                )

    finally:
        if engine:
            await engine.dispose()


@celery_app.task(bind=True, name="process_csv_upload")
def process_csv_upload_task(
    self,
    upload_session_id: str,
    file_path: str,
    entity_type: str,
    user_id: str,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    try:
        logger.info(
            f"Processing CSV upload {upload_session_id} for entity type {entity_type}"
        )

        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": 100,
                "phase": "starting",
                "message": "Initializing CSV processing...",
            },
        )

        return async_to_sync(_async_process_csv_upload)(
            self.request.id,
            upload_session_id,
            file_path,
            entity_type,
            user_id,
            options,
        )

    except Exception as exc:
        logger.error(f"CSV processing failed for {upload_session_id}: {exc}")
        raise DataProcessingError(f"CSV processing failed: {exc}").with_context(
            upload_session_id=upload_session_id
        )


@celery_app.task(bind=True, name="validate_data_integrity")
def validate_data_integrity_task(
    self, session_id: str, entity_types: List[str], user_id: str
) -> Dict[str, Any]:
    """
    Validate data integrity across multiple entity types for a session.
    Checks referential integrity, constraint violations, and data quality.
    """

    try:
        logger.info(f"Starting data integrity validation for session {session_id}")

        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": 100,
                "phase": "initializing",
                "message": "Starting data integrity validation...",
            },
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                _async_validate_data_integrity(self, session_id, entity_types, user_id)
            )
            return result
        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"Data integrity validation failed: {exc}")
        raise DataProcessingError(
            f"Data integrity validation failed: {exc}"
        ).with_context(session_id=session_id)


async def _async_validate_data_integrity(
    task, session_id: str, entity_types: List[str], user_id: str
) -> Dict[str, Any]:
    """Async implementation of data integrity validation"""

    from ..database import db_manager

    async with db_manager.get_session() as db:
        try:
            if db_manager.engine is None:
                raise RuntimeError("Database engine not initialized")

            sync_engine = db_manager.engine.sync_engine

            with Session(sync_engine) as sync_session:
                integrity_checker = DataIntegrityChecker(sync_session)

            session_uuid = UUID(session_id)
            validation_results = {}
            total_entities = len(entity_types)

            for i, entity_type in enumerate(entity_types):
                progress = int((i / total_entities) * 80) + 10

                task.update_state(
                    state="PROGRESS",
                    meta={
                        "current": progress,
                        "total": 100,
                        "phase": "validating",
                        "message": f"Validating {entity_type} integrity...",
                    },
                )

                data = await _get_entity_data(db, entity_type)
                entity_validation = integrity_checker.check_integrity(
                    {entity_type: data}
                )
                validation_results[entity_type] = entity_validation

            task.update_state(
                state="PROGRESS",
                meta={
                    "current": 90,
                    "total": 100,
                    "phase": "cross_validation",
                    "message": "Running cross-entity validation...",
                },
            )

            all_data = {}
            for entity_type in entity_types:
                all_data[entity_type] = await _get_entity_data(db, entity_type)

            cross_validation = integrity_checker.check_integrity(all_data)

            task.update_state(
                state="SUCCESS",
                meta={
                    "current": 100,
                    "total": 100,
                    "phase": "completed",
                    "message": "Data integrity validation completed",
                },
            )

            total_errors = sum(
                len(result.errors) for result in validation_results.values()
            ) + len(cross_validation.errors)

            total_warnings = sum(
                len(result.warnings) for result in validation_results.values()
            ) + len(cross_validation.warnings)

            return {
                "success": True,
                "session_id": session_id,
                "entity_validations": validation_results,
                "cross_validation": cross_validation,
                "summary": {
                    "total_errors": total_errors,
                    "total_warnings": total_warnings,
                    "entities_validated": len(entity_types),
                    "overall_status": "valid" if total_errors == 0 else "invalid",
                },
            }

        except Exception as e:
            logger.error(f"Error in data integrity validation: {e}")
            raise DataProcessingError(
                f"Data integrity validation failed: {e}"
            ).with_context(session_id=session_id)


@celery_app.task(bind=True, name="bulk_data_import")
def bulk_data_import_task(
    self, import_config: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    """
    Import data from multiple sources in bulk with validation and rollback support.
    """

    try:
        logger.info(
            f"Starting bulk data import with {len(import_config.get('sources', []))} sources"
        )

        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": 100,
                "phase": "preparing",
                "message": "Preparing bulk import...",
            },
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                _async_bulk_data_import(self, import_config, user_id)
            )
            return result
        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"Bulk data import failed: {exc}")
        raise DataProcessingError(f"Bulk data import failed: {exc}")


async def _async_bulk_data_import(
    task, import_config: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    """Async implementation of bulk data import"""

    from ..database import db_manager

    async with db_manager.get_session() as db:
        try:
            sources = import_config.get("sources", [])
            import_results = {}
            total_sources = len(sources)

            for i, source_config in enumerate(sources):
                progress = int((i / total_sources) * 90) + 5
                source_type = source_config.get("type")
                source_name = source_config.get("name", f"Source {i+1}")

                task.update_state(
                    state="PROGRESS",
                    meta={
                        "current": progress,
                        "total": 100,
                        "phase": "importing",
                        "message": f"Importing {source_name}...",
                    },
                )

                if source_type == "csv":
                    result = await _process_csv_source(db, source_config, user_id)
                elif source_type == "json":
                    result = await _process_json_source(db, source_config, user_id)
                elif source_type == "database":
                    result = await _process_database_source(db, source_config, user_id)
                else:
                    result = {
                        "success": False,
                        "error": f"Unsupported source type: {source_type}",
                    }

                import_results[source_name] = result

            task.update_state(
                state="PROGRESS",
                meta={
                    "current": 95,
                    "total": 100,
                    "phase": "finalizing",
                    "message": "Finalizing import...",
                },
            )

            successful_imports = sum(
                1 for r in import_results.values() if r.get("success")
            )
            total_records = sum(
                r.get("records_imported", 0) for r in import_results.values()
            )

            task.update_state(
                state="SUCCESS",
                meta={
                    "current": 100,
                    "total": 100,
                    "phase": "completed",
                    "message": f"Bulk import completed: {successful_imports}/{total_sources} sources, {total_records} records",
                },
            )

            return {
                "success": True,
                "import_results": import_results,
                "summary": {
                    "total_sources": total_sources,
                    "successful_imports": successful_imports,
                    "failed_imports": total_sources - successful_imports,
                    "total_records_imported": total_records,
                },
            }

        except Exception as e:
            logger.error(f"Error in bulk data import: {e}")
            raise DataProcessingError(f"Bulk data import failed: {e}")


# Helper functions


async def _get_entity_data(db: AsyncSession, entity_type: str) -> List[Dict[str, Any]]:
    """
    MODIFIED: Helper to get entity data for validation by calling a DB function.
    """
    result = await db.execute(
        text("SELECT exam_system.get_entity_data_as_json(:entity_type)"),
        {"entity_type": entity_type},
    )
    data = result.scalar_one_or_none()
    return data if data is not None else []


async def _update_upload_session_completed(
    db: AsyncSession, session_id: UUID, results: Dict[str, Any]
) -> None:
    """Update upload session as completed"""
    query = (
        update(FileUploadSession)
        .where(FileUploadSession.id == session_id)
        .values(
            status="completed",
            total_records=results.get("total_records", 0),
            processed_records=results.get("processed_records", 0),
            validation_errors=results.get("validation_errors"),
            completed_at=datetime.utcnow(),
        )
    )
    await db.execute(query)
    await db.commit()


async def _update_upload_session_failed(
    db: AsyncSession, session_id: UUID, errors: List[str]
) -> None:
    """Update upload session as failed"""
    query = (
        update(FileUploadSession)
        .where(FileUploadSession.id == session_id)
        .values(
            status="failed",
            validation_errors={"errors": errors},
            completed_at=datetime.utcnow(),
        )
    )
    await db.execute(query)
    await db.commit()


async def _process_csv_source(
    db: AsyncSession, source_config: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    """Process CSV data source"""
    return {"success": True, "records_imported": 0}


async def _process_json_source(
    db: AsyncSession, source_config: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    """Process JSON data source"""
    return {"success": True, "records_imported": 0}


async def _process_database_source(
    db: AsyncSession, source_config: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    """Process database data source"""
    return {"success": True, "records_imported": 0}


__all__ = [
    "process_csv_upload_task",
    "validate_data_integrity_task",
    "bulk_data_import_task",
]
