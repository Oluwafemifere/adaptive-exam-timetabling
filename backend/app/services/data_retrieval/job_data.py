# backend/app/services/data_retrieval/job_data.py

"""
Service for retrieving job and timetable data from the database
"""

from typing import Dict, List, cast
from uuid import UUID
from datetime import datetime as ddatetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.jobs import (
    TimetableJob,
    TimetableVersion,
)


class JobData:
    """Service for retrieving job and timetable-related data"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_job(
        self,
        session_id: UUID,
        configuration_id: UUID,
        initiated_by: UUID,
        status: str = "queued",
        progress_percentage: float = 0.0,
    ) -> UUID:
        """Create a new timetable job"""
        job = TimetableJob(
            session_id=session_id,
            configuration_id=configuration_id,
            initiated_by=initiated_by,
            status=status,
            progress_percentage=progress_percentage,
        )
        self.session.add(job)
        await self.session.flush()
        return job.id

    # Timetable Jobs
    async def get_all_timetable_jobs(self) -> List[Dict]:
        """Get all timetable jobs with session and configuration information"""
        stmt = (
            select(TimetableJob)
            .options(
                selectinload(TimetableJob.session),
                selectinload(TimetableJob.configuration),
                selectinload(TimetableJob.initiated_by_user),
                selectinload(TimetableJob.version),
            )
            .order_by(TimetableJob.created_at.desc())
        )
        result = await self.session.execute(stmt)
        jobs = result.scalars().all()

        return [
            {
                "id": str(job.id),
                "session_id": str(job.session_id),
                "session_name": job.session.name if job.session else None,
                "configuration_id": str(job.configuration_id),
                "configuration_name": (
                    job.configuration.name if job.configuration else None
                ),
                "initiated_by": str(job.initiated_by),
                "initiated_by_email": (
                    job.initiated_by_user.email if job.initiated_by_user else None
                ),
                "initiated_by_name": (
                    f"{job.initiated_by_user.first_name} {job.initiated_by_user.last_name}"
                    if job.initiated_by_user
                    else None
                ),
                "status": job.status,
                "progress_percentage": job.progress_percentage,
                "cp_sat_runtime_seconds": job.cp_sat_runtime_seconds,
                "ga_runtime_seconds": job.ga_runtime_seconds,
                "total_runtime_seconds": job.total_runtime_seconds,
                "hard_constraint_violations": job.hard_constraint_violations,
                "soft_constraint_score": (
                    float(str(job.soft_constraint_score))
                    if job.soft_constraint_score is not None
                    else None
                ),
                "room_utilization_percentage": (
                    float(str(job.room_utilization_percentage))
                    if job.room_utilization_percentage is not None
                    else None
                ),
                "solver_phase": job.solver_phase,
                "error_message": job.error_message,
                "has_version": job.version is not None,
                "version_number": job.version.version_number if job.version else None,
                "is_active_version": job.version.is_active if job.version else False,
                "started_at": (
                    cast(ddatetime, job.started_at).isoformat()
                    if job.started_at
                    else None
                ),
                "completed_at": (
                    cast(ddatetime, job.completed_at).isoformat()
                    if job.completed_at
                    else None
                ),
                "created_at": (
                    cast(ddatetime, job.created_at).isoformat()
                    if job.created_at
                    else None
                ),
                "updated_at": (
                    cast(ddatetime, job.updated_at).isoformat()
                    if job.updated_at
                    else None
                ),
            }
            for job in jobs
        ]

    async def get_jobs_by_session(self, session_id: UUID) -> List[Dict]:
        """Get timetable jobs for a specific session"""
        stmt = (
            select(TimetableJob)
            .options(
                selectinload(TimetableJob.configuration),
                selectinload(TimetableJob.initiated_by_user),
                selectinload(TimetableJob.version),
            )
            .where(TimetableJob.session_id == session_id)
            .order_by(TimetableJob.created_at.desc())
        )
        result = await self.session.execute(stmt)
        jobs = result.scalars().all()

        return [
            {
                "id": str(job.id),
                "configuration_id": str(job.configuration_id),
                "configuration_name": (
                    job.configuration.name if job.configuration else None
                ),
                "initiated_by": str(job.initiated_by),
                "initiated_by_email": (
                    job.initiated_by_user.email if job.initiated_by_user else None
                ),
                "status": job.status,
                "progress_percentage": job.progress_percentage,
                "total_runtime_seconds": job.total_runtime_seconds,
                "hard_constraint_violations": job.hard_constraint_violations,
                "soft_constraint_score": (
                    float(str(job.soft_constraint_score))
                    if job.soft_constraint_score is not None
                    else None
                ),
                "room_utilization_percentage": (
                    float(str(job.room_utilization_percentage))
                    if job.room_utilization_percentage is not None
                    else None
                ),
                "solver_phase": job.solver_phase,
                "has_version": job.version is not None,
                "version_number": job.version.version_number if job.version else None,
                "is_active_version": job.version.is_active if job.version else False,
                "started_at": (
                    cast(ddatetime, job.started_at).isoformat()
                    if job.started_at
                    else None
                ),
                "completed_at": (
                    cast(ddatetime, job.completed_at).isoformat()
                    if job.completed_at
                    else None
                ),
                "created_at": (
                    cast(ddatetime, job.created_at).isoformat()
                    if job.created_at
                    else None
                ),
            }
            for job in jobs
        ]

    async def get_job_by_id(self, job_id: UUID) -> Dict | None:
        """Get detailed information about a specific job"""
        stmt = (
            select(TimetableJob)
            .options(
                selectinload(TimetableJob.session),
                selectinload(TimetableJob.configuration),
                selectinload(TimetableJob.initiated_by_user),
                selectinload(TimetableJob.version).selectinload(
                    TimetableVersion.approver
                ),
            )
            .where(TimetableJob.id == job_id)
        )
        result = await self.session.execute(stmt)
        job = result.scalar_one_or_none()

        if not job:
            return None

        return {
            "id": str(job.id),
            "session_id": str(job.session_id),
            "session_name": job.session.name if job.session else None,
            "configuration_id": str(job.configuration_id),
            "configuration_name": job.configuration.name if job.configuration else None,
            "configuration_description": (
                job.configuration.description if job.configuration else None
            ),
            "initiated_by": str(job.initiated_by),
            "initiated_by_email": (
                job.initiated_by_user.email if job.initiated_by_user else None
            ),
            "initiated_by_name": (
                f"{job.initiated_by_user.first_name} {job.initiated_by_user.last_name}"
                if job.initiated_by_user
                else None
            ),
            "status": job.status,
            "progress_percentage": job.progress_percentage,
            "cp_sat_runtime_seconds": job.cp_sat_runtime_seconds,
            "ga_runtime_seconds": job.ga_runtime_seconds,
            "total_runtime_seconds": job.total_runtime_seconds,
            "hard_constraint_violations": job.hard_constraint_violations,
            "soft_constraint_score": (
                float(str(job.soft_constraint_score))
                if job.soft_constraint_score is not None
                else None
            ),
            "room_utilization_percentage": (
                float(str(job.room_utilization_percentage))
                if job.room_utilization_percentage is not None
                else None
            ),
            "solver_phase": job.solver_phase,
            "error_message": job.error_message,
            "result_data": job.result_data,
            "version": (
                {
                    "id": str(job.version.id),
                    "version_number": job.version.version_number,
                    "is_active": job.version.is_active,
                    "approval_level": job.version.approval_level,
                    "approved_by": (
                        str(job.version.approved_by)
                        if job.version.approved_by
                        else None
                    ),
                    "approver_email": (
                        job.version.approver.email if job.version.approver else None
                    ),
                    "approved_at": (
                        cast(ddatetime, job.version.approved_at).isoformat()
                        if job.version.approved_at
                        else None
                    ),
                    "created_at": (
                        cast(ddatetime, job.version.created_at).isoformat()
                        if job.version.created_at
                        else None
                    ),
                }
                if job.version
                else None
            ),
            "started_at": (
                cast(ddatetime, job.started_at).isoformat() if job.started_at else None
            ),
            "completed_at": (
                cast(ddatetime, job.completed_at).isoformat()
                if job.completed_at
                else None
            ),
            "created_at": (
                cast(ddatetime, job.created_at).isoformat() if job.created_at else None
            ),
            "updated_at": (
                cast(ddatetime, job.updated_at).isoformat() if job.updated_at else None
            ),
        }

    async def get_jobs_by_status(self, status: str) -> List[Dict]:
        """Get jobs by status"""
        stmt = (
            select(TimetableJob)
            .options(
                selectinload(TimetableJob.session),
                selectinload(TimetableJob.configuration),
                selectinload(TimetableJob.initiated_by_user),
            )
            .where(TimetableJob.status == status)
            .order_by(TimetableJob.created_at.desc())
        )
        result = await self.session.execute(stmt)
        jobs = result.scalars().all()

        return [
            {
                "id": str(job.id),
                "session_name": job.session.name if job.session else None,
                "configuration_name": (
                    job.configuration.name if job.configuration else None
                ),
                "initiated_by_email": (
                    job.initiated_by_user.email if job.initiated_by_user else None
                ),
                "progress_percentage": job.progress_percentage,
                "solver_phase": job.solver_phase,
                "error_message": job.error_message,
                "started_at": (
                    cast(ddatetime, job.started_at).isoformat()
                    if job.started_at
                    else None
                ),
                "created_at": (
                    cast(ddatetime, job.created_at).isoformat()
                    if job.created_at
                    else None
                ),
            }
            for job in jobs
        ]

    async def get_running_jobs(self) -> List[Dict]:
        """Get currently running jobs"""
        stmt = (
            select(TimetableJob)
            .options(
                selectinload(TimetableJob.session),
                selectinload(TimetableJob.configuration),
                selectinload(TimetableJob.initiated_by_user),
            )
            .where(TimetableJob.status.in_(["queued", "running"]))
            .order_by(TimetableJob.created_at.asc())
        )
        result = await self.session.execute(stmt)
        jobs = result.scalars().all()

        return [
            {
                "id": str(job.id),
                "session_name": job.session.name if job.session else None,
                "configuration_name": (
                    job.configuration.name if job.configuration else None
                ),
                "initiated_by_email": (
                    job.initiated_by_user.email if job.initiated_by_user else None
                ),
                "status": job.status,
                "progress_percentage": job.progress_percentage,
                "solver_phase": job.solver_phase,
                "started_at": (
                    cast(ddatetime, job.started_at).isoformat()
                    if job.started_at
                    else None
                ),
                "created_at": (
                    cast(ddatetime, job.created_at).isoformat()
                    if job.created_at
                    else None
                ),
            }
            for job in jobs
        ]

    # Timetable Versions
    async def get_all_timetable_versions(self) -> List[Dict]:
        """Get all timetable versions"""
        stmt = (
            select(TimetableVersion)
            .options(
                selectinload(TimetableVersion.job).selectinload(TimetableJob.session),
                selectinload(TimetableVersion.approver),
            )
            .order_by(TimetableVersion.version_number.desc())
        )
        result = await self.session.execute(stmt)
        versions = result.scalars().all()

        return [
            {
                "id": str(version.id),
                "job_id": str(version.job_id),
                "session_name": (
                    version.job.session.name
                    if version.job and version.job.session
                    else None
                ),
                "version_number": version.version_number,
                "is_active": version.is_active,
                "approval_level": version.approval_level,
                "approved_by": (
                    str(version.approved_by) if version.approved_by else None
                ),
                "approver_email": version.approver.email if version.approver else None,
                "approver_name": (
                    f"{version.approver.first_name} {version.approver.last_name}"
                    if version.approver
                    else None
                ),
                "approved_at": (
                    cast(ddatetime, version.approved_at).isoformat()
                    if version.approved_at
                    else None
                ),
                "created_at": (
                    cast(ddatetime, version.created_at).isoformat()
                    if version.created_at
                    else None
                ),
                "updated_at": (
                    cast(ddatetime, version.updated_at).isoformat()
                    if version.updated_at
                    else None
                ),
            }
            for version in versions
        ]

    async def get_active_timetable_versions(self) -> List[Dict]:
        """Get active timetable versions"""
        stmt = (
            select(TimetableVersion)
            .options(
                selectinload(TimetableVersion.job).selectinload(TimetableJob.session),
                selectinload(TimetableVersion.approver),
            )
            .where(TimetableVersion.is_active)
            .order_by(TimetableVersion.version_number.desc())
        )
        result = await self.session.execute(stmt)
        versions = result.scalars().all()

        return [
            {
                "id": str(version.id),
                "job_id": str(version.job_id),
                "session_name": (
                    version.job.session.name
                    if version.job and version.job.session
                    else None
                ),
                "version_number": version.version_number,
                "approval_level": version.approval_level,
                "approved_by": (
                    str(version.approved_by) if version.approved_by else None
                ),
                "approver_email": version.approver.email if version.approver else None,
                "approved_at": (
                    cast(ddatetime, version.approved_at).isoformat()
                    if version.approved_at
                    else None
                ),
                "created_at": (
                    cast(ddatetime, version.created_at).isoformat()
                    if version.created_at
                    else None
                ),
            }
            for version in versions
        ]

    async def get_version_by_id(self, version_id: UUID) -> Dict | None:
        """Get timetable version by ID"""
        stmt = (
            select(TimetableVersion)
            .options(
                selectinload(TimetableVersion.job).selectinload(TimetableJob.session),
                selectinload(TimetableVersion.job).selectinload(
                    TimetableJob.configuration
                ),
                selectinload(TimetableVersion.job).selectinload(
                    TimetableJob.initiated_by_user
                ),
                selectinload(TimetableVersion.approver),
            )
            .where(TimetableVersion.id == version_id)
        )
        result = await self.session.execute(stmt)
        version = result.scalar_one_or_none()

        if not version:
            return None

        return {
            "id": str(version.id),
            "job_id": str(version.job_id),
            "version_number": version.version_number,
            "is_active": version.is_active,
            "approval_level": version.approval_level,
            "approved_by": str(version.approved_by) if version.approved_by else None,
            "approver_email": version.approver.email if version.approver else None,
            "approver_name": (
                f"{version.approver.first_name} {version.approver.last_name}"
                if version.approver
                else None
            ),
            "approved_at": (
                cast(ddatetime, version.approved_at).isoformat()
                if version.approved_at
                else None
            ),
            "job": {
                "id": str(version.job.id),
                "session_name": (
                    version.job.session.name if version.job.session else None
                ),
                "configuration_name": (
                    version.job.configuration.name
                    if version.job.configuration
                    else None
                ),
                "initiated_by_email": (
                    version.job.initiated_by_user.email
                    if version.job.initiated_by_user
                    else None
                ),
                "status": version.job.status,
                "total_runtime_seconds": version.job.total_runtime_seconds,
                "hard_constraint_violations": version.job.hard_constraint_violations,
                "soft_constraint_score": (
                    float(str(version.job.soft_constraint_score))
                    if version.job.soft_constraint_score is not None
                    else None
                ),
                "room_utilization_percentage": (
                    float(str(version.job.room_utilization_percentage))
                    if version.job.room_utilization_percentage is not None
                    else None
                ),
                "completed_at": (
                    cast(ddatetime, version.job.completed_at).isoformat()
                    if version.job.completed_at
                    else None
                ),
            },
            "created_at": (
                cast(ddatetime, version.created_at).isoformat()
                if version.created_at
                else None
            ),
            "updated_at": (
                cast(ddatetime, version.updated_at).isoformat()
                if version.updated_at
                else None
            ),
        }

    async def get_latest_version_number(self) -> int:
        """Get the latest version number"""
        stmt = select(func.max(TimetableVersion.version_number))
        result = await self.session.execute(stmt)
        max_version = result.scalar()
        return max_version or 0

    # Statistics and analysis
    async def get_job_statistics(self) -> Dict:
        """Get job statistics"""
        # Total jobs
        total_stmt = select(func.count(TimetableJob.id))
        total_result = await self.session.execute(total_stmt)
        total_jobs = total_result.scalar() or 0

        # Jobs by status
        status_stmt = select(
            TimetableJob.status, func.count(TimetableJob.id).label("count")
        ).group_by(TimetableJob.status)
        status_result = await self.session.execute(status_stmt)
        status_counts = {row.status: row.count for row in status_result}

        # Average runtime
        runtime_stmt = select(
            func.avg(TimetableJob.total_runtime_seconds).label("avg_runtime"),
            func.min(TimetableJob.total_runtime_seconds).label("min_runtime"),
            func.max(TimetableJob.total_runtime_seconds).label("max_runtime"),
        ).where(TimetableJob.total_runtime_seconds.isnot(None))
        runtime_result = await self.session.execute(runtime_stmt)
        runtime_stats = runtime_result.first()

        # Success rate (completed without errors)
        success_stmt = select(func.count(TimetableJob.id)).where(
            and_(
                TimetableJob.status == "completed", TimetableJob.error_message.is_(None)
            )
        )
        success_result = await self.session.execute(success_stmt)
        successful_jobs = success_result.scalar() or 0

        # Calculate success rate safely
        success_rate = 0.0
        if total_jobs and total_jobs > 0:
            success_rate = (successful_jobs / total_jobs) * 100

        # Extract runtime stats safely
        avg_runtime = None
        min_runtime = None
        max_runtime = None

        if runtime_stats:
            avg_runtime = (
                float(str(runtime_stats.avg_runtime))
                if runtime_stats.avg_runtime
                else None
            )
            min_runtime = runtime_stats.min_runtime
            max_runtime = runtime_stats.max_runtime

        return {
            "total_jobs": total_jobs,
            "status_breakdown": status_counts,
            "successful_jobs": successful_jobs,
            "success_rate": success_rate,
            "average_runtime_seconds": avg_runtime,
            "min_runtime_seconds": min_runtime,
            "max_runtime_seconds": max_runtime,
        }

    async def get_performance_metrics(self) -> List[Dict]:
        """Get performance metrics for completed jobs"""
        stmt = (
            select(TimetableJob)
            .options(
                selectinload(TimetableJob.session),
                selectinload(TimetableJob.configuration),
            )
            .where(
                and_(
                    TimetableJob.status == "completed",
                    TimetableJob.total_runtime_seconds.isnot(None),
                )
            )
            .order_by(TimetableJob.completed_at.desc())
        )
        result = await self.session.execute(stmt)
        jobs = result.scalars().all()

        return [
            {
                "job_id": str(job.id),
                "session_name": job.session.name if job.session else None,
                "configuration_name": (
                    job.configuration.name if job.configuration else None
                ),
                "total_runtime_seconds": job.total_runtime_seconds,
                "cp_sat_runtime_seconds": job.cp_sat_runtime_seconds,
                "ga_runtime_seconds": job.ga_runtime_seconds,
                "hard_constraint_violations": job.hard_constraint_violations,
                "soft_constraint_score": (
                    float(str(job.soft_constraint_score))
                    if job.soft_constraint_score is not None
                    else None
                ),
                "room_utilization_percentage": (
                    float(str(job.room_utilization_percentage))
                    if job.room_utilization_percentage is not None
                    else None
                ),
                "completed_at": (
                    cast(ddatetime, job.completed_at).isoformat()
                    if job.completed_at
                    else None
                ),
            }
            for job in jobs
        ]

    async def get_jobs_by_user(self, user_id: UUID) -> List[Dict]:
        """Get jobs initiated by a specific user"""
        stmt = (
            select(TimetableJob)
            .options(
                selectinload(TimetableJob.session),
                selectinload(TimetableJob.configuration),
                selectinload(TimetableJob.version),
            )
            .where(TimetableJob.initiated_by == user_id)
            .order_by(TimetableJob.created_at.desc())
        )
        result = await self.session.execute(stmt)
        jobs = result.scalars().all()

        return [
            {
                "id": str(job.id),
                "session_name": job.session.name if job.session else None,
                "configuration_name": (
                    job.configuration.name if job.configuration else None
                ),
                "status": job.status,
                "progress_percentage": job.progress_percentage,
                "total_runtime_seconds": job.total_runtime_seconds,
                "hard_constraint_violations": job.hard_constraint_violations,
                "has_version": job.version is not None,
                "is_active_version": job.version.is_active if job.version else False,
                "started_at": (
                    cast(ddatetime, job.started_at).isoformat()
                    if job.started_at
                    else None
                ),
                "completed_at": (
                    cast(ddatetime, job.completed_at).isoformat()
                    if job.completed_at
                    else None
                ),
                "created_at": (
                    cast(ddatetime, job.created_at).isoformat()
                    if job.created_at
                    else None
                ),
            }
            for job in jobs
        ]
