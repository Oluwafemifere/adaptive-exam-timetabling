# backend/app/services/notification/__init__.py

"""
Consolidated notification service for real-time updates and email notifications.
"""

from .email_service import EmailService, EmailConfig, EmailMessage
from .websocket_manager import (
    ConnectionManager,
    connection_manager,
    subscribe_job,
    publish_job_update,
    get_initial_job_status,
    user_can_access_job,
    notify_job_cancelled,
    notify_job_completed,
    notify_job_error,
)
from .notification_orchestration_service import NotificationOrchestrationService

__all__ = [
    # Email service
    "EmailService",
    "EmailConfig",
    "EmailMessage",
    # WebSocket manager
    "ConnectionManager",
    "connection_manager",
    "subscribe_job",
    "publish_job_update",
    "get_initial_job_status",
    "user_can_access_job",
    "notify_job_cancelled",
    "notify_job_completed",
    "notify_job_error",
    # Orchestration service
    "NotificationOrchestrationService",
]
