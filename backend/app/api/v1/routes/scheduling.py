# backend/app/api/v1/routes/scheduling.py
"""
API endpoints for scheduling-related operations including data retrieval,
timetable generation, and scheduling configuration management.
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.users import User
from app.services.data_retrieval import (
    SchedulingData as SchedulingDataService,
    ConflictAnalysis as ConflictAnalysisService,
)
from app.services.scheduling.integrated_engine_manager import (
    IntegratedSchedulingEngineManager as SchedulingEngineManager,
)
from app.services.job import JobService, JobCreate
from app.schemas.scheduling import (
    SchedulingDataResponse,
    TimetableGenerationRequest,
    TimetableGenerationResponse,
    ConflictAnalysisResponse,
    SchedulingJobResponse,
)
from app.schemas.jobs import TimetableJobRead as JobRead

router = APIRouter()


@router.get(
    "/data/{session_id}",
    response_model=SchedulingDataResponse,
    summary="Get scheduling data for session",
    description="Retrieves all data needed for scheduling a specific academic session",
)
async def get_scheduling_data(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get comprehensive scheduling data for an academic session including:
    - All exams with course details
    - Available time slots
    - Room information
    - Available staff and constraints
    - Student course registrations
    """
    try:
        service = SchedulingDataService(db)
        data = await service.get_scheduling_data_for_session(session_id)

        return SchedulingDataResponse(
            success=True, message="Scheduling data retrieved successfully", data=data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scheduling data: {str(e)}",
        )


@router.get(
    "/courses/{session_id}",
    summary="Get courses with registration counts",
    description="Retrieves courses with their student registration counts for a session",
)
async def get_courses_with_registrations(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all courses for a session with registration counts"""
    try:
        service = SchedulingDataService(db)
        courses = await service.get_courses_with_registrations(session_id)

        return {
            "success": True,
            "message": f"Found {len(courses)} courses for session",
            "data": courses,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve courses: {str(e)}",
        )


@router.get(
    "/students/{session_id}",
    summary="Get students for session",
    description="Retrieves all students registered for courses in the session",
)
async def get_students_for_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all students registered for courses in the session"""
    try:
        service = SchedulingDataService(db)
        students = await service.get_students_for_session(session_id)

        return {
            "success": True,
            "message": f"Found {len(students)} students for session",
            "data": students,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve students: {str(e)}",
        )


@router.get(
    "/conflicts/{session_id}",
    response_model=ConflictAnalysisResponse,
    summary="Analyze scheduling conflicts",
    description="Analyzes potential scheduling conflicts and room utilization",
)
async def analyze_scheduling_conflicts(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze potential scheduling conflicts including:
    - Student registration conflicts
    - Room utilization statistics
    """
    try:
        service = ConflictAnalysisService(db)

        student_conflicts = await service.get_student_conflicts(str(session_id))
        room_utilization = await service.get_room_utilization()

        return ConflictAnalysisResponse(
            success=True,
            message="Conflict analysis completed successfully",
            data={
                "student_conflicts": student_conflicts,
                "room_utilization": room_utilization,
                "conflict_summary": {
                    "total_student_conflicts": len(student_conflicts),
                    "total_buildings": len(room_utilization),
                },
            },
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
    description="Initiates timetable generation using the hybrid CP-SAT + GA engine",
)
async def generate_timetable(
    request: TimetableGenerationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate an exam timetable for the specified session using the hybrid optimization engine.
    This creates a background job that can be monitored for progress.
    """
    try:
        # Initialize services
        job_service = JobService(db, current_user)
        engine_manager = SchedulingEngineManager(db)

        # Create a new timetable job. Provide required fields.
        job_payload = JobCreate(
            session_id=request.session_id,
            configuration_id=request.configuration_id,
            initiated_by=current_user.id,
        )
        job = await job_service.create_job(job_payload)

        # Start the background scheduling process
        await engine_manager.start_timetable_job(
            str(request.session_id), str(request.configuration_id)
        )

        return TimetableGenerationResponse(
            success=True,
            message="Timetable generation initiated successfully",
            job_id=job.id,
            status=job.status,
            estimated_completion_minutes=(
                request.options.get("estimated_time", 15) if request.options else 15
            ),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate timetable generation: {str(e)}",
        )


@router.get(
    "/jobs/{job_id}",
    response_model=SchedulingJobResponse,
    summary="Get scheduling job status",
    description="Retrieves the current status and progress of a scheduling job",
)
async def get_scheduling_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed status information for a scheduling job"""
    try:
        job_service = JobService(db, current_user)
        job = await job_service.get_job_status(job_id)

        return SchedulingJobResponse(success=True, job=JobRead.from_orm(job))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve job status: {str(e)}",
        )


@router.post(
    "/jobs/{job_id}/cancel",
    summary="Cancel scheduling job",
    description="Cancels a running or queued scheduling job",
)
async def cancel_scheduling_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a scheduling job if it's still running or queued"""
    try:
        job_service = JobService(db, current_user)
        engine_manager = SchedulingEngineManager(db)

        # Get the job
        job = await job_service.get_job_status(job_id)

        # Check if job can be cancelled
        if job.status not in ["queued", "running"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel job with status: {job.status}",
            )

        # Cancel the job via engine manager and mark it cancelled in DB
        # Use cancel_job which is the common naming convention for engine managers
        if hasattr(engine_manager, "cancel_scheduling_job"):
            await engine_manager.cancel_timetable_job(job_id)
        elif hasattr(engine_manager, "cancel_job"):
            await engine_manager.cancel_job(job_id)
        else:
            # If engine manager lacks a cancel method, raise explicit error
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Scheduling engine does not support job cancellation",
            )

        await job_service.cancel_job(job_id)

        return {
            "success": True,
            "message": "Scheduling job cancelled successfully",
            "job_id": str(job_id),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel scheduling job: {str(e)}",
        )


@router.get(
    "/jobs",
    summary="List scheduling jobs",
    description="Retrieves a list of scheduling jobs with optional filtering",
)
async def list_scheduling_jobs(
    session_id: Optional[UUID] = Query(None, description="Filter by session ID"),
    job_status: Optional[str] = Query(
        None, description="Filter by job status", alias="status"
    ),
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of jobs to return"
    ),
    offset: int = Query(0, ge=0, description="Number of jobs to skip"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List scheduling jobs with optional filtering and pagination"""
    try:
        job_service = JobService(db, current_user)

        jobs = await job_service.list_jobs(
            session_id=session_id, status=job_status, limit=limit, offset=offset
        )

        return {
            "success": True,
            "message": f"Retrieved {len(jobs)} scheduling jobs",
            "data": [JobRead.from_orm(job) for job in jobs],
            "pagination": {"limit": limit, "offset": offset, "count": len(jobs)},
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scheduling jobs: {str(e)}",
        )


@router.get(
    "/configurations",
    summary="List scheduling configurations",
    description="Retrieves available scheduling configurations",
)
async def list_scheduling_configurations(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """List available scheduling configurations"""
    try:
        # TODO: Implement configuration service
        # For now, return a mock response
        configurations = [
            {
                "id": "default",
                "name": "Standard Configuration",
                "description": "Default scheduling configuration with balanced constraints",
                "is_default": True,
            },
            {
                "id": "exam_week",
                "name": "Exam Week Configuration",
                "description": "Optimized for intensive exam periods",
                "is_default": False,
            },
            {
                "id": "emergency",
                "name": "Emergency Configuration",
                "description": "Minimal constraints for emergency scheduling",
                "is_default": False,
            },
        ]

        return {
            "success": True,
            "message": f"Retrieved {len(configurations)} configurations",
            "data": configurations,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configurations: {str(e)}",
        )


@router.get(
    "/summary/{session_id}",
    summary="Get scheduling summary",
    description="Provides a high-level summary of scheduling status for a session",
)
async def get_scheduling_summary(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get high-level scheduling summary for a session"""
    try:
        data_service = SchedulingDataService(db)
        conflict_service = ConflictAnalysisService(db)
        job_service = JobService(db, current_user)

        # Get basic data counts
        data = await data_service.get_scheduling_data_for_session(session_id)
        metadata = data.get("metadata", {})

        # Get conflict analysis
        student_conflicts = await conflict_service.get_student_conflicts(
            str(session_id)
        )

        # Get recent jobs for this session
        recent_jobs = await job_service.list_jobs(
            session_id=session_id, limit=5, offset=0
        )

        # Calculate summary statistics
        summary = {
            "session_id": str(session_id),
            "data_summary": {
                "total_exams": metadata.get("total_exams", 0),
                "total_rooms": metadata.get("total_rooms", 0),
                "total_staff": metadata.get("total_staff", 0),
                "total_students": metadata.get("total_students", 0),
            },
            "conflict_summary": {
                "student_conflicts": len(student_conflicts),
                "has_conflicts": len(student_conflicts) > 0,
            },
            "scheduling_status": {
                "recent_jobs": len(recent_jobs),
                "latest_job_status": recent_jobs[0].status if recent_jobs else None,
                "has_active_job": any(
                    job.status in ["queued", "running"] for job in recent_jobs
                ),
            },
        }

        return {
            "success": True,
            "message": "Scheduling summary retrieved successfully",
            "data": summary,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scheduling summary: {str(e)}",
        )
