# backend/app/services/scheduling/scheduling_management_service.py
"""
Service for managing the lifecycle of timetable scheduling jobs.
Handles job creation, task dispatching, and status retrieval.
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession


from ...models import TimetableJob  # Import the model for querying
from ...tasks import generate_timetable_task

logger = logging.getLogger(__name__)


class SchedulingManagementService:
    """Manages timetable generation jobs."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def start_new_scheduling_job(
        self,
        session_id: UUID,
        user_id: UUID,
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Creates a new timetable job record and dispatches a Celery task to run the solver.

        Args:
            session_id: The academic session to generate a timetable for.
            user_id: The ID of the user initiating the job.
            options: A dictionary of solver and configuration options,
                     e.g., {"solver_time_limit": 300, "exam_days": 10}.

        Returns:
            A dictionary containing the new job_id and task_id, or an error message.
        """
        try:
            # Step 1: Create the job record in the database using the PG function.
            # This ensures a job ID is created transactionally before the task is dispatched.
            logger.info(
                f"Creating timetable job for session {session_id} by user {user_id}"
            )
            create_job_query = text(
                "SELECT exam_system.create_timetable_job(:session_id, :user_id)"
            )
            result = await self.session.execute(
                create_job_query, {"session_id": session_id, "user_id": user_id}
            )
            job_id = result.scalar_one()
            logger.info(f"Database job record created with ID: {job_id}")

            # Step 2: Retrieve the configuration_id from the newly created job.
            # This ensures the Celery task uses the same configuration as the DB record.
            get_config_query = select(TimetableJob.configuration_id).where(
                TimetableJob.id == job_id
            )
            config_result = await self.session.execute(get_config_query)
            configuration_id = config_result.scalar_one_or_none()

            if not configuration_id:
                raise Exception(
                    f"Could not retrieve configuration_id for new job {job_id}"
                )

            logger.info(
                f"Retrieved configuration_id {configuration_id} for job {job_id}"
            )
            await self.session.commit()

            # Step 3: Dispatch the Celery task with the correct configuration_id.
            task_signature = generate_timetable_task.s(
                job_id=str(job_id),
                session_id=str(session_id),
                configuration_id=str(configuration_id),
                user_id=str(user_id),
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
            return {
                "success": False,
                "error": "An internal error occurred while starting the scheduling job.",
            }

    async def get_job_status(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieves the status of a specific job from the database.

        Args:
            job_id: The ID of the job to check.

        Returns:
            A dictionary with the job's status and details, or None if not found.
        """
        try:
            logger.debug(f"Retrieving status for job {job_id}")
            query = text("SELECT exam_system.get_job_status(:p_job_id)")
            result = await self.session.execute(query, {"p_job_id": job_id})
            status = result.scalar_one_or_none()
            return status
        except Exception as e:
            logger.error(
                f"Error retrieving status for job {job_id}: {e}", exc_info=True
            )
            return None
