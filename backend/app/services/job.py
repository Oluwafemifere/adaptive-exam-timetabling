# backend/app/services/job.py
import logging
from typing import Any, Dict, List, Optional, cast
from datetime import datetime, timedelta
from uuid import UUID
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func

from ..models.jobs import TimetableJob
from ..models.versioning import TimetableVersion
from ..models.users import User
from ..schemas.jobs import TimetableJobCreate as JobCreate, TimetableJobSummaryRead
from ..core.exceptions import JobNotFoundError, JobAccessDeniedError

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing background timetabling jobs via DB functions."""

    def __init__(self, db: AsyncSession, user: Optional[User] = None):
        self.db = db
        self.user = user

    async def create_job(self, job_data: JobCreate) -> TimetableJob:
        """Create a new timetabling job by calling the DB function."""
        try:
            query = text(
                "SELECT exam_system.create_timetable_job(:p_session_id, :p_initiated_by, :p_configuration_id)"
            )
            result = await self.db.execute(
                query,
                {
                    "p_session_id": job_data.session_id,
                    "p_initiated_by": self.user.id if self.user else None,
                    "p_configuration_id": job_data.configuration_id,
                },
            )
            job_id = result.scalar_one()
            await self.db.commit()

            # Retrieve the created job object to return it
            job = await self.db.get(TimetableJob, job_id)
            if not job:
                raise JobNotFoundError(f"Failed to retrieve created job {job_id}")

            logger.info(f"Created new job {job.id} for session {job_data.session_id}")
            return job

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create job: {e}", exc_info=True)
            raise

    async def list_jobs(
        self,
        session_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[TimetableJob]:
        """List jobs with optional filtering (direct read, no specific function available)."""
        try:
            query = select(TimetableJob)
            if session_id:
                query = query.where(TimetableJob.session_id == session_id)
            if status:
                query = query.where(TimetableJob.status == status)
            query = (
                query.order_by(TimetableJob.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await self.db.execute(query)
            jobs = cast(List[TimetableJob], result.scalars().all())
            logger.info(f"Retrieved {len(jobs)} jobs")
            return jobs
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}", exc_info=True)
            raise

    async def list_successful_jobs_for_session(
        self, session_id: UUID
    ) -> List[TimetableJobSummaryRead]:
        """List all successfully completed jobs for a given session."""
        try:
            # We need to join TimetableJob with TimetableVersion to get the is_published flag.
            # A job might not have a version yet if it's just completed.
            query = (
                select(
                    TimetableJob.id,
                    TimetableJob.created_at,
                    TimetableJob.status,
                    TimetableVersion.id.label("version_id"),
                    TimetableVersion.is_published,
                )
                .outerjoin(TimetableVersion, TimetableJob.id == TimetableVersion.job_id)
                .where(TimetableJob.session_id == session_id)
                .where(TimetableJob.status == "completed")
                .order_by(TimetableJob.created_at.desc())
            )

            result = await self.db.execute(query)
            job_rows = result.mappings().all()

            # Map the raw result to our Pydantic schema
            return [TimetableJobSummaryRead.model_validate(row) for row in job_rows]

        except Exception as e:
            logger.error(
                f"Failed to list successful jobs for session {session_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_job_status(self, job_id: UUID) -> Dict[str, Any]:
        """Get detailed job status by calling the DB function."""
        try:
            query = text("SELECT exam_system.get_job_status(:p_job_id)")
            result = await self.db.execute(query, {"p_job_id": job_id})
            job_status = result.scalar_one_or_none()

            if not job_status:
                raise JobNotFoundError(f"Job {job_id} not found")

            # Note: Access control logic is assumed to be handled within the DB function or API layer
            return job_status
        except JobNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}", exc_info=True)
            raise

    async def update_job_progress(
        self,
        job_id: UUID,
        progress: int,
        status: str,
        phase: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update job progress and status by calling the DB function."""
        try:
            query = text(
                "SELECT exam_system.update_job_status(:p_job_id, :p_status, :p_progress, :p_solver_phase, :p_metrics)"
            )
            await self.db.execute(
                query,
                {
                    "p_job_id": job_id,
                    "p_status": status,
                    "p_progress": progress,
                    "p_solver_phase": phase,
                    "p_metrics": json.dumps(metrics) if metrics else None,
                },
            )
            await self.db.commit()
            logger.info(
                f"Updated job {job_id} progress to {progress}% with status '{status}'"
            )
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to update job progress for {job_id}: {e}", exc_info=True
            )
            raise

    async def mark_job_failed(self, job_id: UUID, error_message: str) -> None:
        """Mark job as failed by calling the DB function."""
        try:
            query = text(
                "SELECT exam_system.update_job_failed(:p_job_id, :p_error_message)"
            )
            await self.db.execute(
                query, {"p_job_id": job_id, "p_error_message": error_message}
            )
            await self.db.commit()
            logger.error(f"Marked job {job_id} as failed: {error_message}")
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to mark job as failed for {job_id}: {e}", exc_info=True
            )
            raise

    async def get_active_jobs(self) -> List[TimetableJob]:
        """Get all currently active jobs (direct read, no specific function available)."""
        try:
            query = (
                select(TimetableJob)
                .where(TimetableJob.status.in_(["queued", "running"]))
                .order_by(TimetableJob.created_at)
            )
            result = await self.db.execute(query)
            return cast(List[TimetableJob], result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get active jobs: {e}", exc_info=True)
            raise

    async def cleanup_old_jobs(self, days_old: int = 30) -> int:
        """Clean up old completed jobs (direct read/update, no specific function available)."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            count_query = select(func.count(TimetableJob.id)).where(
                TimetableJob.completed_at < cutoff_date,
                TimetableJob.status.in_(["completed", "failed"]),
            )
            count_result = await self.db.execute(count_query)
            count = int(count_result.scalar_one())

            if count > 0:
                # This is an administrative task, direct update is acceptable if no function exists
                delete_query = text(
                    "UPDATE exam_system.timetable_jobs SET status = 'archived' WHERE completed_at < :cutoff AND status IN ('completed', 'failed')"
                )
                await self.db.execute(delete_query, {"cutoff": cutoff_date})
                await self.db.commit()
                logger.info(f"Cleaned up {count} old jobs")
            return count
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to cleanup old jobs: {e}", exc_info=True)
            raise

    async def cancel_job(self, job_id: UUID) -> None:
        """Cancel a running or queued job by calling the update_job_status function."""
        try:
            job_status_data = await self.get_job_status(job_id)
            if job_status_data.get("status") not in ["queued", "running"]:
                raise ValueError(
                    f"Cannot cancel job in status: {job_status_data.get('status')}"
                )

            await self.update_job_progress(
                job_id=job_id,
                status="cancelled",
                progress=job_status_data.get("progress_percentage", 0),
                phase="cancelled",
                metrics={"cancellation_reason": "Job cancelled by user"},
            )
            logger.info(f"Cancelled job {job_id}")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to cancel job {job_id}: {e}", exc_info=True)
            raise
