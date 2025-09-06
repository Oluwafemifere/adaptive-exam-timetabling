# backend/app/services/job.py
import logging
from typing import List, Optional, cast
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from ..models.jobs import TimetableJob
from ..models.users import User
from ..schemas.jobs import TimetableJobCreate as JobCreate
from ..core.exceptions import JobNotFoundError, JobAccessDeniedError

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing background timetabling jobs."""

    def __init__(self, db: AsyncSession, user: Optional[User] = None):
        self.db = db
        self.user = user

    async def create_job(self, job_data: JobCreate) -> TimetableJob:
        """Create a new timetabling job."""
        try:
            job = TimetableJob(
                id=uuid4(),
                session_id=job_data.session_id,
                configuration_id=job_data.configuration_id,
                initiated_by=self.user.id if self.user else None,
                status="queued",
                progress_percentage=0,
                created_at=datetime.utcnow(),
            )

            self.db.add(job)
            await self.db.commit()
            await self.db.refresh(job)

            logger.info(f"Created new job {job.id} for session {job_data.session_id}")
            return job

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create job: {e}")
            raise

    async def list_jobs(
        self,
        session_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[TimetableJob]:
        """List jobs with optional filtering."""
        try:
            query = select(TimetableJob)

            if session_id:
                query = query.where(TimetableJob.session_id == session_id)
            if status:
                query = query.where(TimetableJob.status == status)

            query = query.order_by(TimetableJob.created_at.desc())
            query = query.offset(offset).limit(limit)

            result = await self.db.execute(query)
            jobs = cast(List[TimetableJob], result.scalars().all())

            logger.info(f"Retrieved {len(jobs)} jobs")
            return jobs

        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            raise

    async def get_job_status(self, job_id: UUID) -> TimetableJob:
        """Get detailed job status. Raises if not found or access denied."""
        try:
            query = select(TimetableJob).where(TimetableJob.id == job_id)
            result = await self.db.execute(query)
            job = result.scalar_one_or_none()

            if not job:
                raise JobNotFoundError(f"Job {job_id} not found")

            if self.user and not self._can_access_job(job):
                raise JobAccessDeniedError(f"Access denied to job {job_id}")

            return job

        except (JobNotFoundError, JobAccessDeniedError):
            raise
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            raise

    async def update_job_progress(
        self,
        job_id: UUID,
        progress: int,
        phase: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        """Update job progress and status."""
        try:
            update_data = {
                "progress_percentage": progress,
                "updated_at": datetime.utcnow(),
            }

            if phase:
                update_data["solver_phase"] = phase
            if message:
                update_data["status_message"] = message

            if progress >= 100:
                update_data["status"] = "completed"
                update_data["completed_at"] = datetime.utcnow()

            query = (
                update(TimetableJob)
                .where(TimetableJob.id == job_id)
                .values(**update_data)
            )

            await self.db.execute(query)
            await self.db.commit()

            logger.info(f"Updated job {job_id} progress to {progress}%")

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update job progress for {job_id}: {e}")
            raise

    async def mark_job_failed(self, job_id: UUID, error_message: str) -> None:
        """Mark job as failed with error message."""
        try:
            query = (
                update(TimetableJob)
                .where(TimetableJob.id == job_id)
                .values(
                    status="failed",
                    error_message=error_message,
                    completed_at=datetime.utcnow(),
                )
            )

            await self.db.execute(query)
            await self.db.commit()

            logger.error(f"Marked job {job_id} as failed: {error_message}")

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to mark job as failed for {job_id}: {e}")
            raise

    async def get_active_jobs(self) -> List[TimetableJob]:
        """Get all currently active jobs."""
        try:
            query = (
                select(TimetableJob)
                .where(TimetableJob.status.in_(["queued", "running"]))
                .order_by(TimetableJob.created_at)
            )

            result = await self.db.execute(query)
            jobs = cast(List[TimetableJob], result.scalars().all())

            return jobs

        except Exception as e:
            logger.error(f"Failed to get active jobs: {e}")
            raise

    async def cleanup_old_jobs(self, days_old: int = 30) -> int:
        """Clean up old completed jobs."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            count_query = select(func.count(TimetableJob.id)).where(
                TimetableJob.completed_at < cutoff_date,
                TimetableJob.status.in_(["completed", "failed"]),
            )

            count_result = await self.db.execute(count_query)
            count = int(count_result.scalar_one())

            if count > 0:
                delete_query = (
                    update(TimetableJob)
                    .where(
                        TimetableJob.completed_at < cutoff_date,
                        TimetableJob.status.in_(["completed", "failed"]),
                    )
                    .values(deleted=True, deleted_at=datetime.utcnow())
                )

                await self.db.execute(delete_query)
                await self.db.commit()

                logger.info(f"Cleaned up {count} old jobs")

            return count

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to cleanup old jobs: {e}")
            raise

    def _can_access_job(self, job: TimetableJob) -> bool:
        """Check if user can access job."""
        if not self.user:
            return False

        # system admin can access all jobs
        if getattr(self.user, "is_superuser", False):
            return True

        # users can access their own jobs
        if getattr(job, "initiated_by", None) == getattr(self.user, "id", None):
            return True

        # department/faculty level access can be added here
        return False

    async def cancel_job(self, job_id: UUID) -> None:
        """Cancel a running or queued job."""
        try:
            job = await self.get_job_status(job_id)

            if job.status not in ["queued", "running"]:
                raise ValueError(f"Cannot cancel job in status: {job.status}")

            query = (
                update(TimetableJob)
                .where(TimetableJob.id == job_id)
                .values(
                    status="cancelled",
                    completed_at=datetime.utcnow(),
                    error_message="Job cancelled by user",
                )
            )

            await self.db.execute(query)
            await self.db.commit()

            logger.info(f"Cancelled job {job_id}")

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to cancel job {job_id}: {e}")
            raise
