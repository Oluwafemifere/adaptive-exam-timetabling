# backend/app/api/v1/routes/seeding.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.seeding.data_seeding_service import DataSeedingService
from ....schemas.system import GenericResponse

router = APIRouter()


@router.get(
    "/{academic_session_id}/status",
    response_model=GenericResponse,
    summary="Get Overall Data Seeding Status",
)
async def get_data_seeding_status(
    academic_session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Retrieves the status of the overall data seeding session for an academic session,
    including the status of all individual file uploads.
    """
    service = DataSeedingService(db)
    session_data = await service.get_seeding_session_by_academic_session(
        academic_session_id
    )

    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data seeding session has been initiated for this academic session.",
        )

    # Get the detailed view including file statuses
    seeding_session_id = session_data["id"]
    detailed_status = await service.get_seeding_session_with_files(seeding_session_id)

    if not detailed_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not retrieve status details for seeding session {seeding_session_id}.",
        )

    return GenericResponse(success=True, data=detailed_status)
