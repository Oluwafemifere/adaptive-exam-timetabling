# backend/app/api/v1/routes/jobs.py
"""
API endpoints for monitoring and managing background jobs.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.job import JobService
from ....services.data_retrieval import DataRetrievalService
from ....schemas.jobs import (
    TimetableJobRead,
)
from ....schemas.system import GenericResponse

router = APIRouter()


@router.get("/", response_model=List[TimetableJobRead])
async def list_jobs(
    session_id: Optional[UUID] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """List all timetabling jobs with optional filtering."""
    service = JobService(db, user)
    return await service.list_jobs(
        session_id=session_id, status=status, limit=limit, offset=offset
    )


@router.get("/active", response_model=List[TimetableJobRead])
async def list_active_jobs(
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """List all currently queued or running jobs."""
    service = JobService(db, user)
    return await service.get_active_jobs()


@router.get("/{job_id}", response_model=TimetableJobRead)
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Fetches the details of a specific timetable job."""
    service = JobService(db, user)
    return await service.get_job_status(job_id)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_job(
    job_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Cancel a running or queued job."""
    service = JobService(db, user)
    await service.cancel_job(job_id)
    return None


@router.post("/cleanup", response_model=dict)
async def cleanup_old_jobs(
    days_old: int = Query(30, ge=1),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete old completed or failed jobs."""
    service = JobService(db, user)
    count = await service.cleanup_old_jobs(days_old=days_old)
    return {"detail": f"Cleaned up {count} old jobs"}


# --- NEWLY ADDED ROUTE ---


@router.get("/sessions/{session_id}/latest-successful", response_model=GenericResponse)
async def get_latest_successful_job_for_session(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Retrieve the ID of the latest successfully completed timetable job for a session.
    Uses the `get_latest_successful_timetable_job` service method.
    """
    service = DataRetrievalService(db)
    job_id = await service.get_latest_successful_timetable_job(session_id)
    if not job_id:
        raise HTTPException(
            status_code=404,
            detail="No successful timetable job found for this session.",
        )
    return GenericResponse(success=True, data={"job_id": job_id})


@router.get("/{job_id}/result", response_model=GenericResponse)
async def get_job_result(
    job_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Fetches the result_data of a specific completed timetable job."""
    service = DataRetrievalService(db)
    result_data = await service.get_timetable_job_results(job_id=job_id)
    if not result_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found for this job. It may be pending, failed, or have no result data.",
        )
    return GenericResponse(success=True, data=result_data)
