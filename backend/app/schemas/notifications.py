# app/schemas/notifications.py
from uuid import UUID
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class NotificationRead(BaseModel):
    id: UUID
    title: str
    message: str
    event_type: str
    priority: str
    created_at: datetime
    is_read: bool
    details: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class MarkNotificationsReadRequest(BaseModel):
    notification_ids: List[UUID]
