# backend/app/api/v1/routes/scheduling.py
"""
API endpoints for scheduling-related operations including data retrieval,
timetable generation, and scheduling configuration management.
"""
from typing import Optional, Union, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import date

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_retrieval import DataRetrievalService
from ....services.scheduling import (
    SchedulingService,
)
from ....schemas.scheduling import (
    SchedulingDataResponse,
    TimetableGenerationRequest,
    TimetableGenerationResponse,
    ConflictAnalysisResponse,
    TimetableValidationRequest,
)
from ....schemas.system import GenericResponse
from ....schemas.jobs import TimetableJobRead

router = APIRouter()


@router.get(
    "/data/{session_id}",
    response_model=SchedulingDataResponse,
    summary="Get scheduling data for session",
)
async def get_scheduling_data(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Get comprehensive scheduling data for an academic session.
    """
    service = DataRetrievalService(db)
    data = await service.get_scheduling_dataset(session_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scheduling data",
        )
    return SchedulingDataResponse(
        success=True, message="Scheduling data retrieved successfully", data=data
    )


@router.get(
    "/conflicts/{version_id}",
    response_model=ConflictAnalysisResponse,
    summary="Analyze scheduling conflicts",
)
async def analyze_scheduling_conflicts(
    version_id: Union[UUID, str],
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    data_service = DataRetrievalService(db)

    # Handle "latest" special case
    if isinstance(version_id, str) and version_id == "latest":
        metadata = await data_service.get_latest_version_metadata()
        if not metadata or "id" not in metadata:
            raise HTTPException(
                status_code=404, detail="No completed timetable versions found."
            )
        try:
            version_uuid = UUID(metadata["id"])
        except ValueError:
            raise HTTPException(
                status_code=500, detail="Invalid version ID in metadata."
            )
    else:
        # Ensure input can be coerced to UUID
        try:
            version_uuid = UUID(str(version_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid version_id format.")

    # Run conflict analysis
    conflict_data = await data_service.get_timetable_conflicts(version_uuid)
    if not conflict_data:
        return ConflictAnalysisResponse(
            success=True,
            message="Conflict analysis completed. No conflicts found.",
            data={"conflicts": []},
        )

    return ConflictAnalysisResponse(
        success=True,
        message="Conflict analysis completed successfully",
        data=conflict_data,
    )


@router.post(
    "/generate",
    response_model=TimetableGenerationResponse,
    summary="Generate exam timetable",
)
async def generate_timetable(
    request: TimetableGenerationRequest,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    service = SchedulingService(db)
    options = request.options or {}
    options["start_date"] = request.start_date.isoformat()
    options["end_date"] = request.end_date.isoformat()
    result = await service.start_new_scheduling_job(
        session_id=request.session_id, user_id=user.id, options=options
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to start job"),
        )
    job_status_result = await service.get_job_status(result["job_id"])
    job_status = TimetableJobRead.model_validate(job_status_result)
    return TimetableGenerationResponse(
        success=True,
        message="Timetable generation initiated successfully",
        job_id=result["job_id"],
        status=job_status.status,
        estimated_completion_minutes=15,
    )


# --- NEWLY ADDED ROUTE ---


# Define a new schema for the request body, specific to this route,
# to avoid requiring a session_id from the client.
class ActiveSessionTimetableRequest(BaseModel):
    start_date: date
    end_date: date
    options: Optional[Dict[str, Any]] = None


@router.post(
    "/generate/active-session",
    response_model=TimetableGenerationResponse,
    summary="Generate Timetable for Active Session",
    description="Automatically finds the active academic session and starts a new timetable generation job for it.",
)
async def generate_timetable_for_active_session(
    request: ActiveSessionTimetableRequest,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Automatically retrieves the active academic session and initiates
    a new timetable generation job for it.
    """
    data_service = DataRetrievalService(db)

    # 1. Fetch the active academic session ID
    active_session = await data_service.get_active_academic_session()
    if not active_session or not active_session.get("id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active academic session found. An administrator must set an active session.",
        )
    session_id = active_session["id"]

    # 2. Start the scheduling job using the retrieved session ID
    scheduling_service = SchedulingService(db)
    options = request.options or {}
    options["start_date"] = request.start_date.isoformat()
    options["end_date"] = request.end_date.isoformat()

    result = await scheduling_service.start_new_scheduling_job(
        session_id=session_id, user_id=user.id, options=options
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to start the scheduling job."),
        )

    # 3. Fetch and return the initial status of the created job
    job_id = result["job_id"]
    job_status_result = await scheduling_service.get_job_status(job_id)
    job_status = TimetableJobRead.model_validate(job_status_result)

    return TimetableGenerationResponse(
        success=True,
        message="Timetable generation for active session initiated successfully.",
        job_id=job_id,
        status=job_status.status,
        estimated_completion_minutes=15,
    )


@router.post("/validate", response_model=GenericResponse)
async def validate_timetable_assignments(
    request: TimetableValidationRequest,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Validate a proposed set of timetable assignments against constraints.
    Uses the `validate_timetable` service method.
    """
    service = DataRetrievalService(db)
    try:
        validation_result = await service.validate_timetable(
            assignments=request.assignments, version_id=request.version_id
        )
        return GenericResponse(
            success=True,
            message="Timetable validation completed.",
            data=validation_result,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to validate timetable: {e}"
        )
