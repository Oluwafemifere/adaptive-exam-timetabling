# backend/app/api/v1/routes/timetables.py

from uuid import UUID
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Query
from fastapi.responses import Response

from ....services.export import TimetableExportService
from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_retrieval.data_retrieval_service import DataRetrievalService
from ....services.scheduling import TimetableManagementService
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
    timetable_data = await service.get_timetable_job_results(job_id=job_id)
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
    job_id = metadata.get("job_id")  # Assuming job_id is returned by the service
    assert job_id
    timetable_data = await service.get_timetable_job_results(job_id=job_id)
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
    job_id = metadata.get("job_id")  # Assuming job_id is returned by the service method
    assert job_id
    timetable_data = await service.get_timetable_job_results(job_id=job_id)
    return {
        "success": True,
        "message": "Latest session timetable retrieved successfully.",
        "data": timetable_data,
        "version_id": version_id,
        "last_modified": metadata["last_modified"],
    }


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


@router.get("/versions/{version_id}", response_model=GenericResponse)
async def get_timetable_version(
    version_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Get a fully structured timetable version by its ID."""
    service = DataRetrievalService(db)

    # --- START OF FIX ---
    # First, get the job_id associated with the given version_id.
    job_id = await service.get_job_id_from_version(version_id)
    if not job_id:
        raise HTTPException(
            status_code=404,
            detail=f"No job associated with timetable version ID '{version_id}' found.",
        )

    # Now, use the correct job_id to fetch the results.
    timetable_data = await service.get_timetable_job_results(job_id=job_id)
    # --- END OF FIX ---

    if not timetable_data:
        raise HTTPException(
            status_code=404,
            detail=f"Timetable version with ID '{version_id}' not found.",
        )
    return GenericResponse(success=True, data=timetable_data)


@router.post("/versions/{job_id}/publish", response_model=GenericResponse)
async def publish_version(
    job_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Publish a specific timetable version by its associated job ID."""
    service = TimetableManagementService(db)
    try:
        await service.publish_timetable_version(job_id=job_id, user_id=user.id)
        return GenericResponse(
            success=True, message="Timetable version published successfully."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/versions/{version_id}/unpublish",
    response_model=GenericResponse,
    summary="Unpublish a Timetable Version",
)
async def unpublish_version(
    version_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Unpublishes a specific timetable version, making it no longer the official version.
    """
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can unpublish timetables.",
        )
    service = TimetableManagementService(db)
    result = await service.unpublish_timetable_version(
        version_id=version_id, user_id=user.id
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to unpublish timetable version."),
        )
    return GenericResponse(success=True, message=result.get("message"))


@router.post("/versions/{version_id}/edit", response_model=GenericResponse)
async def create_manual_edit(
    version_id: UUID,
    edit_in: ManualTimetableEditCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Record a manual edit made to a timetable version."""
    service = TimetableManagementService(db)
    result = await service.create_manual_edit(
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
    response_model=GenericResponse,
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
    user_data = await service.get_users_for_timetable_notification(version_id)
    if user_data is None:
        raise HTTPException(
            status_code=404, detail="Could not retrieve users for notification."
        )
    return GenericResponse(success=True, data=user_data)


@router.get(
    "/versions/{version_id}/export",
    summary="Export Timetable Version",
    tags=["Timetables", "Export"],
)
async def export_timetable_version(
    version_id: UUID,
    format: str = Query(
        "pdf",
        description="The desired output format. Can be 'pdf' or 'csv'.",
        enum=["pdf", "csv"],
    ),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Exports a fully structured timetable version to a downloadable file (PDF or CSV).
    """
    service = TimetableExportService(db)
    file_bytes = await service.export_timetable(
        version_id=version_id, output_format=format
    )

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not generate export for timetable version '{version_id}'. The version may not exist or contains no data.",
        )

    # Determine file properties based on the requested format
    if format.lower() == "csv":
        media_type = "text/csv"
        filename = f"timetable_{version_id}.csv"
    else:
        media_type = "application/pdf"
        filename = f"timetable_{version_id}.pdf"

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}

    return Response(content=file_bytes, media_type=media_type, headers=headers)
