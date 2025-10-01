# backend/app/api/v1/routes/timetables.py

from uuid import UUID
from typing import Union, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_retrieval.data_retrieval_service import DataRetrievalService
from ....schemas.system import GenericResponse
from ....schemas.scheduling import ManualTimetableEditCreate

router = APIRouter()


@router.get(
    "/active/latest",
    summary="Get Latest Timetable for Active Session",
    response_model=GenericResponse,
)
async def get_latest_timetable_for_active_session(
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Retrieves the latest successful timetable for the currently active academic session.
    This endpoint chains three operations:
    1. Fetches the active academic session.
    2. Finds the latest successfully completed timetable job for that session.
    3. Retrieves the detailed results for that job.
    """
    service = DataRetrievalService(db)

    # 1. Get active academic session
    active_session = await service.get_active_academic_session()
    if not active_session or not active_session.get("id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active academic session found.",
        )
    session_id = active_session["id"]

    # 2. Get latest successful job for the session
    job_id = await service.get_latest_successful_timetable_job(session_id)
    if not job_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No successful timetable job found for active session '{session_id}'.",
        )

    # 3. Get the results for that job
    timetable_data = await service.get_timetable_results(job_id=job_id)
    if not timetable_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timetable data for job '{job_id}' could not be retrieved.",
        )

    return GenericResponse(
        success=True,
        message="Latest timetable for active session retrieved successfully.",
        data={
            "timetable": timetable_data,
            "session_id": session_id,
            "job_id": job_id,
        },
    )


@router.get(
    "/versions/latest",
    summary="Get latest timetable version",
)
async def get_latest_timetable_version(
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Get the latest completed timetable version."""
    service = DataRetrievalService(db)
    metadata = await service.get_latest_version_metadata()
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed timetable versions found.",
        )
    version_id = metadata["id"]
    timetable_data = await service.get_timetable_results(job_id=version_id)
    if not timetable_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timetable data for the latest version could not be retrieved.",
        )
    return {
        "success": True,
        "message": "Latest timetable data retrieved successfully.",
        "data": timetable_data,
        "version_id": version_id,
        "last_modified": metadata["last_modified"],
    }


@router.get(
    "/versions/{version_id}",
    summary="Get a specific timetable version",
)
async def get_timetable_version(
    version_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Get a fully structured timetable version by its ID."""
    service = DataRetrievalService(db)
    timetable_data = await service.get_timetable_results(job_id=version_id)
    if not timetable_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timetable version with ID '{version_id}' not found.",
        )
    return {
        "success": True,
        "message": "Timetable data retrieved successfully.",
        "data": timetable_data,
        "version_id": version_id,
    }


@router.get(
    "/sessions/{session_id}/latest",
    summary="Get latest timetable for a session",
)
async def get_latest_timetable_for_session(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Get the latest completed timetable for a specific session."""
    service = DataRetrievalService(db)
    metadata = await service.get_latest_version_metadata(session_id=session_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No completed timetables found for session '{session_id}'.",
        )
    version_id = metadata["id"]
    timetable_data = await service.get_timetable_results(job_id=version_id)
    return {
        "success": True,
        "message": "Latest session timetable retrieved successfully.",
        "data": timetable_data,
        "version_id": version_id,
        "last_modified": metadata["last_modified"],
    }


router.get(
    "/{job_id}/result",
    summary="Get timetable result for a job",
    include_in_schema=False,
)(get_timetable_version)


# --- NEWLY ADDED ROUTES ---


@router.get(
    "/sessions/{session_id}/published",
    response_model=GenericResponse,
    summary="Get Published Timetable Version ID",
)
async def get_published_version(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Retrieve the ID of the published timetable version for a session.
    Uses `get_published_timetable_version` service method.
    """
    service = DataRetrievalService(db)
    version_id = await service.get_published_timetable_version(session_id)
    if not version_id:
        raise HTTPException(
            status_code=404, detail="No published timetable found for this session."
        )
    return GenericResponse(success=True, data={"version_id": version_id})


@router.post(
    "/versions/{version_id}/publish",
    response_model=GenericResponse,
    status_code=status.HTTP_200_OK,
)
async def publish_version(
    version_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Publish a specific timetable version, making it the official schedule.
    Uses `publish_timetable_version` service method.
    """
    service = DataRetrievalService(db)
    await service.publish_timetable_version(version_id=version_id, user_id=user.id)
    return GenericResponse(
        success=True, message="Timetable version published successfully."
    )


@router.post(
    "/versions/{version_id}/edit",
    response_model=GenericResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_manual_edit(
    version_id: UUID,
    edit_in: ManualTimetableEditCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Record a manual edit made to a timetable version.
    Uses the `create_manual_timetable_edit` service method.
    """
    service = DataRetrievalService(db)
    result = await service.create_manual_timetable_edit(
        version_id=version_id,
        edited_by=user.id,
        exam_id=edit_in.exam_id,
        new_values=edit_in.new_values,
        old_values=edit_in.old_values,
        reason=edit_in.reason,
    )
    return GenericResponse(
        success=True, message="Manual edit recorded successfully.", data=result
    )


@router.get(
    "/versions/{version_id}/notifications/users",
    response_model=List[Dict[str, Any]],
    summary="Get Users for Notification",
)
async def get_notification_users(
    version_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Get a list of users who should be notified about a timetable update.
    Uses `get_users_for_notification` service method.
    """
    service = DataRetrievalService(db)
    users = await service.get_users_for_notification(version_id)
    if users is None:
        raise HTTPException(
            status_code=404, detail="Could not retrieve users for notification."
        )
    return users
