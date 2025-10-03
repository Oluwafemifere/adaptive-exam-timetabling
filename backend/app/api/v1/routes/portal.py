# backend/app/api/v1/routes/portal.py
"""API endpoints for user portal interactions."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_retrieval import DataRetrievalService
from ....services.portal.interaction_service import InteractionService
from ....schemas.portal import (
    ConflictReportCreate,
    RequestManage,
    ChangeRequestCreate,
    StaffAvailabilityUpdate,
)
from ....schemas.system import GenericResponse

router = APIRouter()


@router.get("/{user_id}", response_model=GenericResponse)
async def get_portal_data(
    user_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Retrieve all necessary data for a specific user's portal, based on the
    currently active academic session.
    """
    # Authorization: Admins can see anyone's portal, users can only see their own.
    if not user.is_superuser and user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this data.",
        )

    service = DataRetrievalService(db)
    portal_data = await service.get_portal_data(user_id)

    # Handle None response
    if portal_data is None:
        raise HTTPException(
            status_code=404, detail=f"Portal data not found for user {user_id}"
        )

    # Handle error case (portal_data is a dict with "error" key)
    if isinstance(portal_data, dict) and portal_data.get("error"):
        raise HTTPException(
            status_code=404,
            detail=portal_data.get(
                "error", f"Portal data not found for user {user_id}"
            ),
        )

    return GenericResponse(success=True, data=portal_data)


@router.post("/conflicts/student", response_model=GenericResponse)
async def submit_student_conflict_report(
    report_in: ConflictReportCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Endpoint for students to submit an exam conflict report."""
    service = InteractionService(db)
    result = await service.create_student_conflict_report(
        user.id, report_in.exam_id, report_in.description
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return GenericResponse(
        success=True, message="Conflict report submitted successfully.", data=result
    )


@router.put("/conflicts/{report_id}/manage", response_model=GenericResponse)
async def manage_student_conflict_report(
    report_id: UUID,
    manage_in: RequestManage,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Endpoint for admins to manage a student conflict report."""
    service = InteractionService(db)
    result = await service.manage_conflict_report(
        user.id, report_id, manage_in.new_status, manage_in.notes
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return GenericResponse(
        success=True, message="Conflict report updated.", data=result
    )


@router.post("/change-requests/staff", response_model=GenericResponse)
async def submit_staff_change_request(
    request_in: ChangeRequestCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Endpoint for staff to request a change to their invigilation assignment."""
    service = InteractionService(db)
    result = await service.create_staff_assignment_change_request(
        user.id, request_in.assignment_id, request_in.reason, request_in.description
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return GenericResponse(
        success=True, message="Change request submitted successfully.", data=result
    )


@router.put("/change-requests/{request_id}/manage", response_model=GenericResponse)
async def manage_staff_change_request(
    request_id: UUID,
    manage_in: RequestManage,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Endpoint for admins to manage a staff assignment change request."""
    service = InteractionService(db)
    result = await service.manage_assignment_change_request(
        user.id, request_id, manage_in.new_status, manage_in.notes
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return GenericResponse(success=True, message="Change request updated.", data=result)


@router.put("/staff/availability", response_model=GenericResponse)
async def update_staff_availability(
    update_in: StaffAvailabilityUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Endpoint for staff to update their availability preferences."""
    service = InteractionService(db)
    result = await service.update_staff_availability(
        user.id, update_in.availability_data
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return GenericResponse(
        success=True, message="Availability updated successfully.", data=result
    )
