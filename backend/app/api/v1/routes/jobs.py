# backend/app/api/v1/routes/jobs.py
"""
API endpoints for monitoring and retrieving results from background jobs.
"""
from uuid import UUID
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.scheduling.scheduling_management_service import (
    SchedulingManagementService,
)
from ....schemas.jobs import TimetableJobRead

router = APIRouter()


@router.get(
    "/{job_id}",
    response_model=TimetableJobRead,
    summary="Get Job Status and Result",
    description="Retrieves the current status and, if completed, the final results of a timetable generation job.",
)
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Fetches the details of a specific timetable job from the database.
    """
    service = SchedulingManagementService(db)
    job_status = await service.get_job_status(job_id)

    if not job_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found.",
        )

    # The DB function returns a dict, which we can unpack into our Pydantic model
    return TimetableJobRead(**job_status)
