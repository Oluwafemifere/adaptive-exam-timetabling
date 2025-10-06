# backend/app/tasks/notification_tasks.py

"""
Celery tasks for notification operations including email sending,
WebSocket broadcasts, and system-wide notifications.
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from .celery_app import celery_app, _run_coro_in_new_loop
from ..services.notification.email_service import EmailService
from ..services.notification.websocket_manager import (
    connection_manager,
    publish_job_update,
)
from ..models.users import (
    User,
)  # Keep for email sending logic if user details are needed
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy import event, select, delete, text
from ..core.config import settings
from sqlalchemy.pool import NullPool
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
    """
    try:
        logger.info(f"Sending email notification to {recipient_email}")
        self.update_state(
            state="PROGRESS",
            meta={"current": 10, "total": 100, "phase": "preparing"},
        )
        return _run_coro_in_new_loop(
            _async_send_email_notification(
                self,
                recipient_email,
                subject,
                template_name,
                template_data,
                sender_email,
            )
        )
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
    try:
        email_service = EmailService()
        task.update_state(
            state="PROGRESS",
            meta={"current": 30, "total": 100, "phase": "rendering"},
        )
        email_content = await email_service._render_template(
            template_name, template_data
        )
        task.update_state(
            state="PROGRESS", meta={"current": 60, "total": 100, "phase": "sending"}
        )
        send_result = await email_service.send_email(
            subject=subject,
            recipients=[recipient_email],
            template_name=template_name,
            context=template_data,
            html_body=email_content,
        )
        task.update_state(
            state="SUCCESS",
            meta={"current": 100, "total": 100, "phase": "completed"},
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
    """
    try:
        logger.info(f"Sending bulk {notification_type} notifications")
        self.update_state(
            state="PROGRESS", meta={"current": 0, "total": 100, "phase": "preparing"}
        )
        return _run_coro_in_new_loop(
            _async_send_bulk_notifications(
                self, notification_config, user_filter, notification_type
            )
        )
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
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    schema_search_path = "staging, exam_system, public"

    @event.listens_for(engine.sync_engine, "connect")
    def set_search_path(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET search_path TO {schema_search_path};")
        cursor.close()

    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session_factory() as db:
        try:
            task.update_state(
                state="PROGRESS",
                meta={"current": 10, "total": 100, "phase": "filtering"},
            )
            users = await _get_filtered_users(db, user_filter)
            total_users = len(users)

            if total_users == 0:
                return {
                    "success": True,
                    "message": "No users matched the filter criteria",
                    "users_notified": 0,
                }

            logger.info(f"Sending notifications to {total_users} users")
            successful_sends = 0
            failed_sends = 0

            for i, user in enumerate(users):
                progress = int(((i + 1) / total_users) * 80) + 15
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
                meta={"current": 100, "total": 100, "phase": "completed"},
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
        finally:
            if engine:
                await engine.dispose()


@celery_app.task(name="notify_job_status_change")
def notify_job_status_change_task(
    job_id: str,
    old_status: str,
    new_status: str,
    additional_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Notify relevant users about job status changes.
    """
    try:
        logger.info(
            f"Notifying job status change: {job_id} from {old_status} to {new_status}"
        )
        return _run_coro_in_new_loop(
            _async_notify_job_status_change(
                job_id, old_status, new_status, additional_data
            )
        )
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
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    schema_search_path = "staging, exam_system, public"

    @event.listens_for(engine.sync_engine, "connect")
    def set_search_path(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET search_path TO {schema_search_path};")
        cursor.close()

    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session_factory() as db:
        try:
            job_uuid = UUID(job_id)
            # Use the get_job_status DB function
            result = await db.execute(
                text("SELECT exam_system.get_job_status(:p_job_id)"),
                {"p_job_id": job_uuid},
            )
            job_details = result.scalar_one_or_none()

            if not job_details:
                logger.warning(f"Job {job_id} not found for status notification")
                return {"success": False, "error": "Job not found"}

            await publish_job_update(
                job_id,
                {
                    "status": new_status,
                    "progress": job_details.get("progress_percentage", 0),
                    "phase": job_details.get("solver_phase", ""),
                    "message": _get_status_message(new_status, additional_data),
                },
            )

            if new_status in ["completed", "failed", "cancelled"]:
                await _send_job_completion_email(
                    db, job_details, new_status, additional_data
                )

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
        finally:
            if engine:
                await engine.dispose()


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
        return _run_coro_in_new_loop(
            _async_send_maintenance_notification(maintenance_config, notification_types)
        )
    except Exception as exc:
        logger.error(f"System maintenance notification failed: {exc}")
        raise exc


async def _async_send_maintenance_notification(
    maintenance_config: Dict[str, Any], notification_types: List[str]
) -> Dict[str, Any]:
    """Async implementation of system maintenance notification"""
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    schema_search_path = "staging, exam_system, public"

    @event.listens_for(engine.sync_engine, "connect")
    def set_search_path(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET search_path TO {schema_search_path};")
        cursor.close()

    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session_factory() as db:
        try:
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
            email_count = 0
            if "email" in notification_types:
                active_users = await _get_filtered_users(db, {"active_only": True})
                for user in active_users:
                    try:
                        send_email_notification_task.apply_async(
                            kwargs={
                                "recipient_email": user["email"],
                                "subject": maintenance_config.get(
                                    "title", "System Maintenance Notification"
                                ),
                                "template_name": "system_maintenance",
                                "template_data": {
                                    "user_name": user.get("first_name", "User"),
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
        finally:
            if engine:
                await engine.dispose()


@celery_app.task(name="cleanup_old_notifications")
def cleanup_old_notifications_task(days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old notification records and connection data.
    Note: This task uses a direct ORM delete as a dedicated DB function
    for this maintenance task is not available.
    """
    try:
        logger.info(f"Cleaning up notifications older than {days_old} days")
        return _run_coro_in_new_loop(_async_cleanup_old_notifications(days_old))
    except Exception as exc:
        logger.error(f"Notification cleanup failed: {exc}")
        raise exc


async def _async_cleanup_old_notifications(days_old: int) -> Dict[str, Any]:
    """Async implementation of notification cleanup"""
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    schema_search_path = "staging, exam_system, public"

    @event.listens_for(engine.sync_engine, "connect")
    def set_search_path(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET search_path TO {schema_search_path};")
        cursor.close()

    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session_factory() as db:
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            from ..models.users import UserNotification

            stmt = delete(UserNotification).where(
                UserNotification.created_at < cutoff_date
            )
            result = await db.execute(stmt)
            await db.commit()
            cleanup_count = result.rowcount
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
        finally:
            if engine:
                await engine.dispose()


# Helper functions
async def _get_filtered_users(
    db: AsyncSession, user_filter: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Get users based on filter criteria by calling the appropriate DB function.
    """
    role = user_filter.get("role")
    if role:
        result = await db.execute(
            text("SELECT exam_system.get_users_by_role_json(:p_role_name)"),
            {"p_role_name": role},
        )
    elif user_filter.get("active_only", True):
        result = await db.execute(text("SELECT exam_system.get_active_users_json()"))
    else:
        result = await db.execute(text("SELECT exam_system.get_all_users_json()"))

    users = result.scalar_one_or_none()
    return users if users is not None else []


async def _send_user_email_notification(
    user: Dict[str, Any], notification_config: Dict[str, Any]
) -> None:
    """Send email notification to a specific user"""
    send_email_notification_task.apply_async(
        kwargs={
            "recipient_email": user["email"],
            "subject": notification_config.get("subject", "Notification"),
            "template_name": notification_config.get(
                "template", "generic_notification"
            ),
            "template_data": {
                "user_name": user.get("first_name", "User"),
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
    job_details: Dict[str, Any],
    status: str,
    additional_data: Optional[Dict[str, Any]] = None,
) -> None:
    """Send job completion email to job initiator"""
    try:
        # Note: A get_user_by_id function would be ideal here.
        # Using a simple ORM query as a fallback.
        user_id = job_details.get("initiated_by")
        if not user_id:
            logger.warning(f"Cannot get initiator for job {job_details.get('id')}")
            return

        user_query = select(User).where(User.id == UUID(user_id))
        result = await db.execute(user_query)
        user = result.scalar_one_or_none()

        if not user or not user.email:
            logger.warning(
                f"Cannot send completion email for job {job_details.get('id')} - user not found"
            )
            return

        if status == "completed":
            template, subject = "job_completed", "Timetable Generation Completed"
        elif status == "failed":
            template, subject = "job_failed", "Timetable Generation Failed"
        else:
            template, subject = "job_cancelled", "Timetable Generation Cancelled"

        send_email_notification_task.apply_async(
            kwargs={
                "recipient_email": user.email,
                "subject": subject,
                "template_name": template,
                "template_data": {
                    "user_name": user.first_name,
                    "job_id": str(job_details.get("id")),
                    "session_id": str(job_details.get("session_id")),
                    "status": status,
                    "completion_time": job_details.get("completed_at"),
                    "error_message": job_details.get("error_message"),
                    "additional_data": additional_data or {},
                },
            }
        )
    except Exception as e:
        logger.error(f"Failed to send job completion email: {e}")


__all__ = [
    "send_email_notification_task",
    "send_bulk_notifications_task",
    "notify_job_status_change_task",
    "send_system_maintenance_notification_task",
    "cleanup_old_notifications_task",
]
