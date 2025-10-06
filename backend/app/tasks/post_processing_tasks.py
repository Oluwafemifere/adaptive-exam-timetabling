# backend/app/tasks/post_processing_tasks.py

"""
Celery tasks for post-processing operations, such as enriching timetable results.
"""

import logging
from typing import Dict, Any
from uuid import UUID
from .celery_app import celery_app, _run_coro_in_new_loop
from ..services.data_retrieval.data_retrieval_service import DataRetrievalService
from ..services.scheduling.enrichment_service import EnrichmentService
from ..services.notification.websocket_manager import publish_job_update
from ..core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import event
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)


async def _async_enrich_timetable_result(job_id: str):
    """Async implementation for enriching timetable results."""
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    schema_search_path = "staging, exam_system, public"

    @event.listens_for(engine.sync_engine, "connect")
    def set_search_path(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET search_path TO {schema_search_path};")
        cursor.close()

    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    job_uuid = UUID(job_id)

    async with async_session_factory() as session:
        try:
            await publish_job_update(
                job_id,
                {
                    "status": "post_processing",
                    "phase": "enriching_results",
                    "message": "Adding human-readable details to timetable.",
                },
            )

            # 1. Instantiate services
            data_retrieval_service = DataRetrievalService(session)
            enrichment_service = EnrichmentService()

            # 2. Fetch the raw job results (which include lookup metadata)
            raw_results = await data_retrieval_service.get_timetable_job_results(
                job_uuid
            )
            if not raw_results or raw_results.get("is_enriched"):
                logger.warning(
                    f"Skipping enrichment for job {job_id}: No data or already enriched."
                )
                return {"success": True, "message": "Enrichment skipped."}

            # 3. Perform enrichment
            enriched_results = await enrichment_service.enrich_solution_data(
                raw_results
            )

            # 4. Save the enriched data back to the database
            await data_retrieval_service.update_timetable_job_results(
                job_uuid, enriched_results
            )
            await session.commit()

            # 5. Notify frontend of completion
            await publish_job_update(
                job_id,
                {
                    "status": "completed",
                    "phase": "completed",
                    "message": "Timetable generation and enrichment complete.",
                    "result": enriched_results,
                },
            )
            logger.info(f"Successfully enriched and updated results for job {job_id}")
            return {"success": True, "job_id": job_id}

        except Exception as e:
            logger.error(
                f"Failed to enrich timetable for job {job_id}: {e}", exc_info=True
            )
            await publish_job_update(
                job_id,
                {
                    "status": "completed",
                    "phase": "enrichment_failed",
                    "message": f"Enrichment failed: {e}",
                },
            )
            raise
        finally:
            if engine:
                await engine.dispose()


@celery_app.task(bind=True, name="enrich_timetable_result")
def enrich_timetable_result_task(self, job_id: str) -> Dict[str, Any]:
    """
    Celery task to enrich a raw timetable solution with human-readable data.
    """
    logger.info(f"Received enrichment task for job {job_id}")
    return _run_coro_in_new_loop(_async_enrich_timetable_result(job_id))
