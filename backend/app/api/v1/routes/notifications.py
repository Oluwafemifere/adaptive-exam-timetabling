# app/api/v1/routes/notifications.py
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_retrieval import DataRetrievalService
from ....services.System.system_service import SystemService
from ....schemas.notifications import NotificationRead, MarkNotificationsReadRequest
from ....schemas.system import GenericResponse
from ....schemas.reports import AllReportsResponse

router = APIRouter()


@router.get("/", response_model=List[NotificationRead])
async def get_admin_notifications(
    status: Optional[str] = Query(
        None, description="Filter by status (e.g., 'unread')"
    ),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve administrative notifications."""
    service = DataRetrievalService(db)
    notifications = await service.get_admin_notifications(status)
    return notifications if notifications else []


@router.post("/mark-as-read", response_model=GenericResponse)
async def mark_notifications_as_read(
    request: MarkNotificationsReadRequest,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Mark a list of notifications as read."""
    service = SystemService(db)
    result = await service.mark_notifications_as_read(request.notification_ids, user.id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return GenericResponse(success=True, message=result.get("message"))


@router.get(
    "/reports-and-requests",
    response_model=AllReportsResponse,
    summary="Get All Conflict Reports and Change Requests",
)
async def get_all_reports_and_requests(
    # Add the Request object to the dependencies
    request: Request,
    limit: Optional[int] = Query(
        None, ge=1, description="Limit the number of results for each category."
    ),
    # Remove 'statuses' from here as we'll parse it manually
    start_date: Optional[datetime] = Query(
        None, description="Filter for items submitted on or after this date."
    ),
    end_date: Optional[datetime] = Query(
        None, description="Filter for items submitted on or before this date."
    ),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Retrieves a comprehensive list of all student conflict reports and staff
    assignment change requests.

    This endpoint supports filtering and pagination options to manage the
    retrieved data.
    """
    # Manually parse the 'statuses' parameter from the raw query string.
    # This handles both 'statuses=pending' and 'statuses[]=pending' formats.
    statuses = request.query_params.getlist("statuses[]")
    if not statuses:
        statuses = request.query_params.getlist("statuses")

    service = DataRetrievalService(db)
    data = await service.get_all_reports_and_requests(
        limit=limit,
        statuses=statuses if statuses else None,
        start_date=start_date,
        end_date=end_date,
    )

    if data is None:
        raise HTTPException(
            status_code=404, detail="Could not retrieve reports and requests."
        )

    return data
