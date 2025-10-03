# backend/app/services/scheduling/scheduling_service.py
"""
Service for managing the lifecycle of timetable scheduling jobs.
Handles job creation, task dispatching, and status retrieval.
"""

import json
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import TimetableJob, SystemConfiguration
from ...tasks import generate_timetable_task

logger = logging.getLogger(__name__)


class SchedulingService:
    """Manages timetable generation jobs by calling dedicated DB functions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def start_new_scheduling_job(
        self,
        session_id: UUID,
        user_id: UUID,
        configuration_id: UUID,
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Creates a new timetable job record and dispatches a Celery task.
        The dispatched task only needs the job_id to retrieve all necessary data.
        """
        try:
            logger.info(
                f"Creating timetable job for session {session_id} by user {user_id}"
            )

            # --- START OF FIX ---
            # Corrected the function call to match the database signature.
            # The p_start_date and p_end_date parameters are removed as they are not
            # part of the DB function for creating the job record. They are passed
            # in the 'options' to the Celery task instead.
            create_job_query = text(
                "SELECT exam_system.create_timetable_job(:p_session_id, :p_initiated_by, :p_configuration_id)"
            )
            result = await self.session.execute(
                create_job_query,
                {
                    "p_session_id": session_id,
                    "p_initiated_by": user_id,
                    "p_configuration_id": configuration_id,
                },
            )
            # --- END OF FIX ---

            job_id = result.scalar_one()
            await self.session.commit()
            logger.info(f"Database job record created with ID: {job_id}")

            # Dispatch the Celery task with only the job_id and options.
            # The task can now fetch the complete, tailored dataset using this ID.
            task_signature = generate_timetable_task.s(
                job_id=str(job_id),
                options=options,
            )

            async_result = task_signature.apply_async()
            logger.info(f"Dispatched Celery task {async_result.id} for job {job_id}")

            return {
                "success": True,
                "job_id": job_id,
                "task_id": async_result.id,
                "message": "Timetable generation has been initiated.",
            }

        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Failed to start scheduling job for session {session_id}: {e}",
                exc_info=True,
            )
            return {"success": False, "error": "Failed to start scheduling job."}

    async def get_job_status(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieves job status by calling the `get_job_status` DB function.
        """
        try:
            logger.debug(f"Retrieving status for job {job_id}")
            query = text("SELECT exam_system.get_job_status(:p_job_id)")
            result = await self.session.execute(query, {"p_job_id": job_id})
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                f"Error retrieving status for job {job_id}: {e}", exc_info=True
            )
            return None

    async def update_job_status_progress(
        self,
        job_id: UUID,
        status: str,
        progress: int,
        phase: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Updates job status, progress, and other metrics by calling the `update_job_status` DB function.
        """
        logger.info(f"Updating job {job_id}: status={status}, progress={progress}%")
        try:
            query = text(
                "SELECT exam_system.update_job_status(:p_job_id, :p_status, :p_progress, :p_solver_phase, :p_metrics)"
            )
            await self.session.execute(
                query,
                {
                    "p_job_id": job_id,
                    "p_status": status,
                    "p_progress": progress,
                    "p_solver_phase": phase,
                    "p_metrics": json.dumps(metrics) if metrics else None,
                },
            )
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Failed to update job status for {job_id}: {e}", exc_info=True
            )

    async def mark_job_as_failed(self, job_id: UUID, error_message: str) -> None:
        """
        Marks a job as failed by calling the `update_job_failed` DB function.
        """
        logger.error(f"Marking job {job_id} as failed: {error_message}")
        try:
            query = text(
                "SELECT exam_system.update_job_failed(:p_job_id, :p_error_message)"
            )
            await self.session.execute(
                query, {"p_job_id": job_id, "p_error_message": error_message}
            )
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Failed to mark job as failed for {job_id}: {e}", exc_info=True
            )

    async def save_job_results(
        self, job_id: UUID, results_data: Dict[str, Any]
    ) -> None:
        """
        Saves the final results of a job by calling `update_job_results`.
        """
        logger.info(f"Saving results for completed job {job_id}")
        try:
            query = text(
                "SELECT exam_system.update_job_results(:p_job_id, :p_results_data)"
            )
            await self.session.execute(
                query,
                {
                    "p_job_id": job_id,
                    "p_results_data": json.dumps(results_data, default=str),
                },
            )
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to save job results for {job_id}: {e}", exc_info=True)
