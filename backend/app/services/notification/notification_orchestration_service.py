# backend/app/services/notification/notification_orchestration_service.py
"""
High-level service for orchestrating notifications.
This service centralizes the business logic for when and how to notify users,
using lower-level services like EmailService and WebSocketManager to perform the delivery.
"""

import logging
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from .email_service import EmailService
from .websocket_manager import connection_manager

logger = logging.getLogger(__name__)


class NotificationOrchestrationService:
    """Orchestrates sending notifications for key system events."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.email_service = EmailService()

    async def notify_timetable_published(
        self, version_id: UUID, publisher_id: UUID
    ) -> Dict[str, Any]:
        """
        Notifies all relevant users that a new timetable has been published.
        This includes students and staff associated with the academic session.

        Args:
            version_id: The ID of the published timetable version.
            publisher_id: The ID of the user who published the timetable.

        Returns:
            A summary of the notification actions taken.
        """
        try:
            logger.info(
                f"Initiating notification for published timetable version {version_id}"
            )

            # 1. Get user list and timetable details from a PG function
            query = text(
                "SELECT exam_system.get_users_for_timetable_notification(:p_version_id)"
            )
            result = await self.session.execute(query, {"p_version_id": version_id})
            notification_data = result.scalar_one_or_none()

            if not notification_data or not notification_data.get("users"):
                logger.warning(
                    f"No users found to notify for timetable version {version_id}"
                )
                return {
                    "success": True,
                    "message": "No users to notify.",
                    "sent_count": 0,
                }

            users_to_notify = notification_data["users"]
            session_name = notification_data.get("session_name", "the current session")

            # 2. Broadcast a system-wide message via WebSocket
            await connection_manager.broadcast_system_message(
                {
                    "type": "timetable_published",
                    "title": "Timetable Published",
                    "message": f"The official exam timetable for {session_name} is now available.",
                    "version_id": str(version_id),
                }
            )

            # 3. Queue individual email notifications
            email_subject = (
                f"Official Exam Timetable for {session_name} is Now Available"
            )
            sent_count = 0
            for user in users_to_notify:
                try:
                    # In a real system, this would be `apply_async` to a Celery task
                    await self.email_service.send_email(
                        subject=email_subject,
                        recipients=[user["email"]],
                        template_name="timetable_published",
                        context={
                            "user_name": user.get("first_name", "Valued User"),
                            "session_name": session_name,
                            "version_id": str(version_id),
                            # A direct link to the user's schedule would be ideal
                            "schedule_link": f"https://yourapp.com/schedule/{user['id']}",
                        },
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to send publication email to {user['email']}: {e}"
                    )

            logger.info(
                f"Sent {sent_count}/{len(users_to_notify)} publication notifications."
            )
            return {"success": True, "sent_count": sent_count}

        except Exception as e:
            logger.error(
                f"Error orchestrating timetable publication notification: {e}",
                exc_info=True,
            )
            return {"success": False, "error": "An internal error occurred."}
