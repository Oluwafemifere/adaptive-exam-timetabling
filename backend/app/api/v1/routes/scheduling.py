# backend/app/api/v1/routes/scheduling.py
"""
API endpoints for scheduling-related operations including data retrieval,
timetable generation, and scheduling configuration management.
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_retrieval.unified_data_retrieval import UnifiedDataService
from ....services.scheduling.conflict_detection_service import ConflictDetectionService
from ....services.scheduling.scheduling_management_service import (
    SchedulingManagementService,
)
from ....schemas.scheduling import (
    SchedulingDataResponse,
    TimetableGenerationRequest,
    TimetableGenerationResponse,
    ConflictAnalysisResponse,
    SchedulingJobResponse,
)
from ....schemas.jobs import TimetableJobRead

router = APIRouter()


@router.get(
    "/data/{session_id}",
    response_model=SchedulingDataResponse,
    summary="Get scheduling data for session",
    description="Retrieves all data needed for scheduling a specific academic session",
)
async def get_scheduling_data(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Get comprehensive scheduling data for an academic session.
    """
    try:
        service = UnifiedDataService(db)
        data = await service.get_scheduling_dataset(session_id)
        return SchedulingDataResponse(
            success=True, message="Scheduling data retrieved successfully", data=data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scheduling data: {str(e)}",
        )


@router.get(
    "/conflicts/{version_id}",
    response_model=ConflictAnalysisResponse,
    summary="Analyze scheduling conflicts",
    description="Analyzes potential scheduling conflicts for a timetable version",
)
async def analyze_scheduling_conflicts(
    version_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Analyze potential scheduling conflicts for a given set of timetable assignments.
    """
    try:
        data_service = UnifiedDataService(db)
        timetable_data = await data_service.get_full_timetable(version_id)

        if not timetable_data or "assignments" not in timetable_data:
            raise HTTPException(
                status_code=404,
                detail="Timetable version not found or has no assignments.",
            )

        conflict_service = ConflictDetectionService(db)
        conflict_result = await conflict_service.check_for_conflicts(
            timetable_data["assignments"], version_id
        )

        return ConflictAnalysisResponse(
            success=conflict_result.get("success", False),
            message="Conflict analysis completed successfully",
            data=conflict_result,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze conflicts: {str(e)}",
        )


@router.post(
    "/generate",
    response_model=TimetableGenerationResponse,
    summary="Generate exam timetable",
    description="Initiates timetable generation using the backend solver engine",
)
async def generate_timetable(
    request: TimetableGenerationRequest,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Generate an exam timetable for the specified session.
    This creates a background job that can be monitored for progress.
    """
    try:
        service = SchedulingManagementService(db)

        # MODIFIED: Extract start_date and end_date from request and add to options
        options = request.options or {}
        options["start_date"] = request.start_date.isoformat()
        options["end_date"] = request.end_date.isoformat()

        result = await service.start_new_scheduling_job(
            session_id=request.session_id,
            user_id=user.id,
            options=options,  # Use the prepared options dict
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to start job"),
            )

        job_status = await service.get_job_status(result["job_id"])
        assert job_status
        return TimetableGenerationResponse(
            success=True,
            message="Timetable generation initiated successfully",
            job_id=result["job_id"],
            status=job_status.get("status", "queued"),
            estimated_completion_minutes=15,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate timetable generation: {str(e)}",
        )
