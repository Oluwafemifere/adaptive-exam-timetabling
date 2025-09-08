# backend/app/tasks/notification_tasks.py

"""
Celery tasks for notification operations including email sending,
WebSocket broadcasts, and system-wide notifications.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from .celery_app import celery_app
from ..services.notification.email_service import EmailService
from ..services.notification.websocket_manager import (
    connection_manager,
    publish_job_update,
    notify_job_completed,
    notify_job_cancelled,
    notify_job_error,
)
from ..services.data_retrieval.user_data import UserData
from ..services.data_retrieval.audit_data import AuditData
from ..models.users import User
from ..models.jobs import TimetableJob
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from ..database import db_manager
from celery import Task

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="send_email_notification")
def send_email_notification_task(
    self: Task,
    recipient_email: str,
    subject: str,
    template_name: str,
    template_data: Dict[str, Any],
    sender_email: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send email notification using configured email service.
    Supports HTML templates and attachment handling.
    """

    try:
        logger.info(f"Sending email notification to {recipient_email}")

        self.update_state(
            state="PROGRESS",
            meta={
                "current": 10,
                "total": 100,
                "phase": "preparing",
                "message": "Preparing email content...",
            },
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                _async_send_email_notification(
                    self,
                    recipient_email,
                    subject,
                    template_name,
                    template_data,
                    sender_email,
                )
            )
            return result
        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"Email notification failed for {recipient_email}: {exc}")
        raise exc


async def _async_send_email_notification(
    task,
    recipient_email: str,
    subject: str,
    template_name: str,
    template_data: Dict[str, Any],
    sender_email: Optional[str] = None,
) -> Dict[str, Any]:
    """Async implementation of email notification"""

    async with db_manager.get_session() as db:  # Changed to use db_manager
        try:
            # Initialize email service
            email_service = EmailService()

            task.update_state(
                state="PROGRESS",
                meta={
                    "current": 30,
                    "total": 100,
                    "phase": "rendering",
                    "message": "Rendering email template...",
                },
            )

            # Render email content
            email_content = (
                await email_service._render_template(  # Changed to use private method
                    template_name, template_data
                )
            )

            task.update_state(
                state="PROGRESS",
                meta={
                    "current": 60,
                    "total": 100,
                    "phase": "sending",
                    "message": "Sending email...",
                },
            )

            # Send email - fixed parameters
            send_result = await email_service.send_email(
                subject=subject,
                recipients=[recipient_email],  # Fixed parameter
                template_name=template_name,  # Added template name
                context=template_data,  # Added context
                html_body=email_content,  # Fixed parameter name
            )

            task.update_state(
                state="SUCCESS",
                meta={
                    "current": 100,
                    "total": 100,
                    "phase": "completed",
                    "message": "Email sent successfully",
                },
            )

            return {
                "success": True,
                "recipient": recipient_email,
                "subject": subject,
                "template": template_name,
                "send_result": send_result,
            }

        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            raise e


@celery_app.task(bind=True, name="send_bulk_notifications")
def send_bulk_notifications_task(
    self: Task,
    notification_config: Dict[str, Any],
    user_filter: Dict[str, Any],
    notification_type: str = "email",
) -> Dict[str, Any]:
    """
    Send bulk notifications to multiple users based on filter criteria.
    Supports email and WebSocket notifications.
    """

    try:
        logger.info(f"Sending bulk {notification_type} notifications")

        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": 100,
                "phase": "preparing",
                "message": "Preparing bulk notifications...",
            },
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                _async_send_bulk_notifications(
                    self, notification_config, user_filter, notification_type
                )
            )
            return result
        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"Bulk notifications failed: {exc}")
        raise exc


async def _async_send_bulk_notifications(
    task,
    notification_config: Dict[str, Any],
    user_filter: Dict[str, Any],
    notification_type: str,
) -> Dict[str, Any]:
    """Async implementation of bulk notifications"""

    async with db_manager.get_session() as db:  # Changed to use db_manager
        try:
            # Get users based on filter
            user_data_service = UserData(db)

            task.update_state(
                state="PROGRESS",
                meta={
                    "current": 10,
                    "total": 100,
                    "phase": "filtering",
                    "message": "Finding target users...",
                },
            )

            # Apply user filters
            users = await _get_filtered_users(db, user_filter)
            total_users = len(users)

            if total_users == 0:
                return {
                    "success": True,
                    "message": "No users matched the filter criteria",
                    "users_notified": 0,
                }

            logger.info(f"Sending notifications to {total_users} users")

            # Send notifications
            successful_sends = 0
            failed_sends = 0

            for i, user in enumerate(users):
                progress = int(((i + 1) / total_users) * 80) + 15  # 15-95%

                task.update_state(
                    state="PROGRESS",
                    meta={
                        "current": progress,
                        "total": 100,
                        "phase": "sending",
                        "message": f"Sending to user {i+1}/{total_users}...",
                    },
                )

                try:
                    if notification_type == "email":
                        await _send_user_email_notification(user, notification_config)
                    elif notification_type == "websocket":
                        await _send_user_websocket_notification(
                            user, notification_config
                        )

                    successful_sends += 1

                except Exception as e:
                    logger.warning(
                        f"Failed to send notification to user {user['id']}: {e}"
                    )
                    failed_sends += 1

            task.update_state(
                state="SUCCESS",
                meta={
                    "current": 100,
                    "total": 100,
                    "phase": "completed",
                    "message": f"Bulk notifications completed: {successful_sends}/{total_users} successful",
                },
            )

            return {
                "success": True,
                "total_users": total_users,
                "successful_sends": successful_sends,
                "failed_sends": failed_sends,
                "notification_type": notification_type,
            }

        except Exception as e:
            logger.error(f"Error in bulk notifications: {e}")
            raise e


@celery_app.task(name="notify_job_status_change")
def notify_job_status_change_task(
    job_id: str,
    old_status: str,
    new_status: str,
    additional_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Notify relevant users about job status changes.
    Sends both WebSocket and email notifications based on status.
    """

    try:
        logger.info(
            f"Notifying job status change: {job_id} from {old_status} to {new_status}"
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                _async_notify_job_status_change(
                    job_id, old_status, new_status, additional_data
                )
            )
            return result
        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"Job status notification failed for {job_id}: {exc}")
        raise exc


async def _async_notify_job_status_change(
    job_id: str,
    old_status: str,
    new_status: str,
    additional_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Async implementation of job status change notification"""

    async with db_manager.get_session() as db:  # Changed to use db_manager
        try:
            # Get job details
            job_uuid = UUID(job_id)
            query = select(TimetableJob).where(TimetableJob.id == job_uuid)
            result = await db.execute(query)
            job = result.scalar_one_or_none()

            if not job:
                logger.warning(f"Job {job_id} not found for status notification")
                return {"success": False, "error": "Job not found"}

            # Prepare notification data
            notification_data = {
                "job_id": job_id,
                "old_status": old_status,
                "new_status": new_status,
                "session_id": str(job.session_id),
                "progress": job.progress_percentage,
                "timestamp": datetime.utcnow().isoformat(),
            }

            if additional_data:
                notification_data.update(additional_data)

            # Send WebSocket notification
            await publish_job_update(
                job_id,
                {
                    "status": new_status,
                    "progress": job.progress_percentage,
                    "phase": job.solver_phase or "",
                    "message": _get_status_message(new_status, additional_data),
                },
            )

            # Send email notification for important status changes
            if new_status in ["completed", "failed", "cancelled"]:
                await _send_job_completion_email(db, job, new_status, additional_data)

            return {
                "success": True,
                "job_id": job_id,
                "notifications_sent": (
                    ["websocket", "email"]
                    if new_status in ["completed", "failed", "cancelled"]
                    else ["websocket"]
                ),
            }

        except Exception as e:
            logger.error(f"Error in job status notification: {e}")
            raise e


@celery_app.task(name="send_system_maintenance_notification")
def send_system_maintenance_notification_task(
    maintenance_config: Dict[str, Any],
    notification_types: List[str] = ["email", "websocket"],
) -> Dict[str, Any]:
    """
    Send system-wide maintenance notifications to all active users.
    """

    try:
        logger.info("Sending system maintenance notifications")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                _async_send_maintenance_notification(
                    maintenance_config, notification_types
                )
            )
            return result
        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"System maintenance notification failed: {exc}")
        raise exc


async def _async_send_maintenance_notification(
    maintenance_config: Dict[str, Any], notification_types: List[str]
) -> Dict[str, Any]:
    """Async implementation of system maintenance notification"""

    async with db_manager.get_session() as db:  # Changed to use db_manager
        try:
            # Send WebSocket broadcast if requested
            if "websocket" in notification_types:
                await connection_manager.broadcast_system_message(
                    {
                        "type": "maintenance_notification",
                        "title": maintenance_config.get("title", "System Maintenance"),
                        "message": maintenance_config.get("message", ""),
                        "start_time": maintenance_config.get("start_time"),
                        "end_time": maintenance_config.get("end_time"),
                        "severity": maintenance_config.get("severity", "info"),
                    }
                )

            # Send email notifications if requested
            email_count = 0
            if "email" in notification_types:
                user_data_service = UserData(db)
                active_users = await user_data_service.get_active_users()

                for user in active_users:
                    try:
                        # Queue individual email tasks
                        send_email_notification_task.apply_async(  # type: ignore[attr-defined]
                            kwargs={
                                "recipient_email": user["email"],
                                "subject": maintenance_config.get(
                                    "title", "System Maintenance Notification"
                                ),
                                "template_name": "system_maintenance",
                                "template_data": {
                                    "user_name": user.get("username", "User"),
                                    **maintenance_config,
                                },
                            }
                        )
                        email_count += 1
                    except Exception as e:
                        logger.warning(
                            f"Failed to queue maintenance email for user {user['id']}: {e}"
                        )

            return {
                "success": True,
                "websocket_broadcast": "websocket" in notification_types,
                "email_notifications_queued": email_count,
                "notification_types": notification_types,
            }

        except Exception as e:
            logger.error(f"Error in system maintenance notification: {e}")
            raise e


@celery_app.task(name="cleanup_old_notifications")
def cleanup_old_notifications_task(days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old notification records and connection data.
    """

    try:
        logger.info(f"Cleaning up notifications older than {days_old} days")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(_async_cleanup_old_notifications(days_old))
            return result
        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"Notification cleanup failed: {exc}")
        raise exc


async def _async_cleanup_old_notifications(days_old: int) -> Dict[str, Any]:
    """Async implementation of notification cleanup"""

    async with db_manager.get_session() as db:  # Changed to use db_manager
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            # Clean up old user notifications
            from ..models.users import UserNotification

            stmt = delete(UserNotification).where(
                UserNotification.created_at < cutoff_date
            )
            result = await db.execute(stmt)
            cleanup_count = result.rowcount

            # Get connection statistics
            connection_stats = connection_manager.get_connection_stats()

            return {
                "success": True,
                "cleanup_date": cutoff_date.isoformat(),
                "records_cleaned": cleanup_count,
                "current_connections": connection_stats,
            }

        except Exception as e:
            logger.error(f"Error in notification cleanup: {e}")
            raise e


# Helper functions


async def _get_filtered_users(
    db: AsyncSession, user_filter: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Get users based on filter criteria"""

    user_data_service = UserData(db)

    # Apply different filters
    if user_filter.get("role"):
        return await user_data_service.get_users_by_role(user_filter["role"])
    elif user_filter.get("active_only", True):
        return await user_data_service.get_active_users()
    else:
        return await user_data_service.get_all_users()


async def _send_user_email_notification(
    user: Dict[str, Any], notification_config: Dict[str, Any]
) -> None:
    """Send email notification to a specific user"""

    # Queue email task
    send_email_notification_task.apply_async(  # type: ignore[attr-defined]
        kwargs={
            "recipient_email": user["email"],
            "subject": notification_config.get("subject", "Notification"),
            "template_name": notification_config.get(
                "template", "generic_notification"
            ),
            "template_data": {
                "user_name": user.get("username", "User"),
                **notification_config.get("template_data", {}),
            },
        }
    )


async def _send_user_websocket_notification(
    user: Dict[str, Any], notification_config: Dict[str, Any]
) -> None:
    """Send WebSocket notification to a specific user"""

    await connection_manager.send_user_notification(
        user_id=str(user["id"]),
        notification={
            "title": notification_config.get("title", "Notification"),
            "message": notification_config.get("message", ""),
            "type": notification_config.get("type", "info"),
            "data": notification_config.get("data", {}),
        },
    )


def _get_status_message(
    status: str, additional_data: Optional[Dict[str, Any]] = None
) -> str:
    """Get user-friendly status message"""

    status_messages = {
        "queued": "Job queued for processing",
        "running": "Job is currently running",
        "completed": "Job completed successfully",
        "failed": "Job failed to complete",
        "cancelled": "Job was cancelled",
    }

    base_message = status_messages.get(status, f"Job status: {status}")

    if additional_data and "error" in additional_data:
        base_message += f" - {additional_data['error']}"

    return base_message


async def _send_job_completion_email(
    db: AsyncSession,
    job: TimetableJob,
    status: str,
    additional_data: Optional[Dict[str, Any]] = None,
) -> None:
    """Send job completion email to job initiator"""

    try:
        # Get user details
        user_query = select(User).where(User.id == job.initiated_by)
        result = await db.execute(user_query)
        user = result.scalar_one_or_none()

        if not user or not user.email:
            logger.warning(
                f"Cannot send completion email for job {job.id} - user not found or no email"
            )
            return

        # Determine email template and subject
        if status == "completed":
            template = "job_completed"
            subject = "Timetable Generation Completed"
        elif status == "failed":
            template = "job_failed"
            subject = "Timetable Generation Failed"
        else:  # cancelled
            template = "job_cancelled"
            subject = "Timetable Generation Cancelled"

        # Queue email task
        send_email_notification_task.apply_async(  # type: ignore[attr-defined]
            kwargs={
                "recipient_email": user.email,
                "subject": subject,
                "template_name": template,
                "template_data": {
                    "user_name": user.username,
                    "job_id": str(job.id),
                    "session_id": str(job.session_id),
                    "status": status,
                    "completion_time": (
                        job.completed_at.isoformat() if job.completed_at else None  # type: ignore[attr-defined]
                    ),
                    "error_message": job.error_message,
                    "additional_data": additional_data or {},
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to send job completion email: {e}")


# Export task functions
__all__ = [
    "send_email_notification_task",
    "send_bulk_notifications_task",
    "notify_job_status_change_task",
    "send_system_maintenance_notification_task",
    "cleanup_old_notifications_task",
]
