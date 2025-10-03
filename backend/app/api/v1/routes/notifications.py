# app/api/v1/routes/notifications.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_retrieval import DataRetrievalService
from ....services.System.system_service import SystemService
from ....schemas.notifications import NotificationRead, MarkNotificationsReadRequest
from ....schemas.system import GenericResponse

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
