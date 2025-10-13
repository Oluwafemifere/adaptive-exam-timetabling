# backend/app/api/v1/routes/scheduling.py
"""
API endpoints for scheduling-related operations including data retrieval,
timetable generation, and scheduling configuration management.
"""
from typing import Optional, Union, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_retrieval import DataRetrievalService
from ....services.scheduling import (
    SchedulingService,
    TimetableManagementService,
)
from ....schemas.scheduling import (
    SchedulingDataResponse,
    TimetableGenerationResponse,
    ConflictAnalysisResponse,
    TimetableValidationRequest,
)
from ....schemas.system import GenericResponse
from ....schemas.jobs import TimetableJobRead

router = APIRouter()


# Define the new, simplified request body for generating a timetable.
class TimetableGenerationRequest(BaseModel):
    """Specifies optional parameters for initiating a timetable generation job."""

    configuration_id: Optional[UUID] = None
    options: Optional[Dict[str, Any]] = None


@router.post("/generate", response_model=TimetableGenerationResponse)
async def generate_timetable(
    request: TimetableGenerationRequest,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Generate a new exam timetable for the currently active academic session.

    This endpoint initiates a background job to solve the scheduling problem.
    The date range and timeslot structure are automatically derived from the
    active session's configuration.
    """
    data_service = DataRetrievalService(db)
    scheduling_service = SchedulingService(db)

    # 1. Fetch the active academic session to get its ID.
    active_session = await data_service.get_active_academic_session()
    if not active_session or not active_session.get("id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active academic session found. Please set an active session.",
        )
    session_id = active_session["id"]

    # 2. Determine the configuration ID. Use the one from the request,
    # or fetch the system's default configuration if not provided.
    config_id = (
        request.configuration_id
        or await data_service.get_default_system_configuration()
    )
    if not config_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No configuration ID provided and no default system configuration was found.",
        )

    # 3. Start the scheduling job.
    # The 'options' dictionary is passed for future flexibility but no longer
    # contains dates or timeslot templates.
    result = await scheduling_service.start_new_scheduling_job(
        session_id=session_id,
        user_id=user.id,
        configuration_id=config_id,
        options=request.options or {},
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to start the timetabling job."),
        )

    # 4. Fetch and return the initial status of the created job.
    job_status_result = await scheduling_service.get_job_status(result["job_id"])
    job_status = TimetableJobRead.model_validate(job_status_result)

    return TimetableGenerationResponse(
        success=True,
        message="Timetable generation for active session initiated successfully.",
        job_id=job_status.id,
        status=job_status.status,
    )


@router.get(
    "/data/{job_id}",
    response_model=SchedulingDataResponse,
    summary="Get scheduling data for a specific job",
)
async def get_scheduling_data(
    job_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Get the comprehensive, tailored scheduling dataset for a specific job ID.
    This dataset is the exact input used by the scheduling solver.
    """
    service = DataRetrievalService(db)
    data = await service.get_scheduling_dataset(job_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failed to retrieve scheduling dataset for job ID {job_id}.",
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
    """
    Analyzes a generated timetable version for any conflicts.
    Accepts a specific version UUID or the string "latest".
    """
    data_service = DataRetrievalService(db)

    version_uuid: UUID
    if isinstance(version_id, str) and version_id.lower() == "latest":
        metadata = await data_service.get_latest_version_metadata()
        if not metadata or "id" not in metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No completed timetable versions found.",
            )
        version_uuid = metadata["id"]
    else:
        try:
            version_uuid = UUID(str(version_id))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid version_id format.",
            )

    conflict_data = await data_service.get_timetable_conflicts(version_uuid)
    if not conflict_data:
        return ConflictAnalysisResponse(
            success=True,
            message="Conflict analysis completed. No conflicts found.",
            data={"conflicts": []},
        )

    return ConflictAnalysisResponse(
        success=True,
        message="Conflict analysis completed successfully.",
        data=conflict_data,
    )


@router.post("/validate", response_model=GenericResponse)
async def validate_timetable_assignments(
    request: TimetableValidationRequest,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Validate a proposed set of timetable assignments against constraints."""
    service = TimetableManagementService(db)
    try:
        validation_result = await service.validate_assignments(
            assignments=request.assignments,
            version_id=request.version_id,
        )
        return GenericResponse(
            success=True,
            message="Timetable validation completed.",
            data=validation_result,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate timetable: {e}",
        )
