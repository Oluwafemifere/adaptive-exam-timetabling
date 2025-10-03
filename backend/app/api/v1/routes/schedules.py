# backend/app/api/v1/routes/schedules.py
"""API endpoints for retrieving individual schedules."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_retrieval.data_retrieval_service import DataRetrievalService
from ....schemas.system import GenericResponse

router = APIRouter()


@router.get("/student/{student_id}", response_model=GenericResponse)
async def get_student_schedule(
    student_id: UUID,
    job_id: UUID = Query(...),  # UPDATED: Changed from session_id to job_id
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Get the exam schedule for a specific student for a given job ID."""
    service = DataRetrievalService(db)
    # UPDATED: Passing job_id to the service layer
    schedule = await service.get_student_schedule(student_id, job_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return GenericResponse(success=True, data=schedule)


@router.get("/room/{room_id}", response_model=GenericResponse)
async def get_room_schedule(
    room_id: UUID,
    job_id: UUID = Query(...),  # UPDATED: Changed from session_id to job_id
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Get the exam schedule for a specific room for a given job ID."""
    service = DataRetrievalService(db)
    # UPDATED: Passing job_id to the service layer
    schedule = await service.get_room_schedule(room_id, job_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return GenericResponse(success=True, data=schedule)


@router.get("/invigilator/{staff_id}", response_model=GenericResponse)
async def get_invigilator_schedule(
    staff_id: UUID,
    job_id: UUID = Query(...),  # UPDATED: Changed from session_id to job_id
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Get the invigilation schedule for a staff member for a given job ID."""
    service = DataRetrievalService(db)
    # UPDATED: Passing job_id to the service layer
    schedule = await service.get_invigilator_schedule(staff_id, job_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return GenericResponse(success=True, data=schedule)


# --- NEWLY ADDED ENDPOINT ---
@router.get("/instructor/{staff_id}", response_model=GenericResponse)
async def get_instructor_schedule(
    staff_id: UUID,
    job_id: UUID = Query(...),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Get the teaching/instructor schedule for a staff member for a given job ID."""
    service = DataRetrievalService(db)
    schedule = await service.get_instructor_schedule(staff_id, job_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return GenericResponse(success=True, data=schedule)
