# backend/app/tasks/__init__.py
"""Tasks package for Celery - exports all task functions."""

from .celery_app import celery_app, task_with_db_session, TaskMonitor

# Import and re-export notification tasks
from .notification_tasks import (
    send_email_notification_task,
    send_bulk_notifications_task,
    notify_job_status_change_task,
    send_system_maintenance_notification_task,
    cleanup_old_notifications_task,
)

# Import and re-export scheduling tasks
from .scheduling_tasks import (
    generate_timetable_task,
)

# Import and re-export data processing tasks
from .data_processing_tasks import (
    process_csv_upload_task,
    validate_data_integrity_task,
    bulk_data_import_task,
)

__all__ = [
    # Core celery components
    "celery_app",
    "task_with_db_session",
    "TaskMonitor",
    # Notification tasks
    "send_email_notification_task",
    "send_bulk_notifications_task",
    "notify_job_status_change_task",
    "send_system_maintenance_notification_task",
    "cleanup_old_notifications_task",
    # Scheduling tasks
    "generate_timetable_task",
    # Data processing tasks
    "process_csv_upload_task",
    "validate_data_integrity_task",
    "bulk_data_import_task",
]
