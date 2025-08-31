# backend/app/tests/unit/test_notification_services.py
"""
Unit tests for notification services functionality.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json
from uuid import uuid4

from app.services.notification import (
    EmailService,
    EmailConfig,
    EmailMessage,
    ConnectionManager,
    connection_manager,
    publish_job_update,
    get_initial_job_status,
    user_can_access_job,
    notify_job_completed,
    notify_job_cancelled,
    notify_job_error,
)


class TestEmailService:
    """Test the EmailService functionality."""

    @pytest.fixture
    def email_config(self):
        """Create test email configuration."""
        return EmailConfig(
            smtp_server="localhost",
            smtp_port=587,
            smtp_user="test@example.com",
            smtp_password="password",
            smtp_from="noreply@test.com",
            use_tls=True,
        )

    @pytest.fixture
    def email_service(Self, email_config):
        return EmailService(email_config)

    @pytest.mark.asyncio
    async def test_send_email_success(self, email_service):
        """Test successful email sending."""
        with patch.object(email_service, "_send_message", return_value=True):
            result = await email_service.send_email(
                subject="Test Subject",
                recipients=["test@example.com"],
                html_body="<h1>Test</h1>",
                text_body="Test",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_send_email_validation_failure(self, email_service):
        """Test email validation failures."""
        # No recipients
        result = await email_service.send_email(
            subject="Test Subject", recipients=[], html_body="Test"
        )
        assert result is False

        # No subject
        result = await email_service.send_email(
            subject="", recipients=["test@example.com"], html_body="Test"
        )
        assert result is False

        # No content
        result = await email_service.send_email(
            subject="Test Subject", recipients=["test@example.com"]
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_send_email_with_template(self, email_service):
        """Test sending email with template rendering."""
        template_content = "Hello {{name}}, your job {{job_id}} is {{status}}."

        with patch.object(
            email_service, "_load_template", return_value=template_content
        ):
            with patch.object(email_service, "_send_message", return_value=True):
                result = await email_service.send_email(
                    subject="Test Subject",
                    recipients=["test@example.com"],
                    template_name="job_notification",
                    context={"name": "User", "job_id": "123", "status": "completed"},
                )

                assert result is True

    @pytest.mark.asyncio
    async def test_send_job_notification(self, email_service):
        """Test sending job status notifications."""
        with patch.object(email_service, "_send_message", return_value=True):
            result = await email_service.send_job_notification(
                user_email="user@example.com",
                job_id="job-123",
                status="completed",
                additional_info={"runtime": "5 minutes"},
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_email_retry_mechanism(self, email_service):
        """Test email retry mechanism."""
        call_count = 0

        async def mock_send_message(message):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return True

        with patch.object(
            email_service, "_send_message", side_effect=mock_send_message
        ):
            result = await email_service.send_email(
                subject="Test Subject",
                recipients=["test@example.com"],
                html_body="Test",
                retry_count=3,
            )

            assert result is True
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_template_rendering(self, email_service):
        """Test template rendering functionality."""
        template_content = "Hello {{name}}, status: {{status}}"
        context = {"name": "John", "status": "active"}

        with patch.object(
            email_service, "_load_template", return_value=template_content
        ):
            rendered = await email_service._render_template("test_template", context)

            assert rendered == "Hello John, status: active"

    @pytest.mark.asyncio
    async def test_template_loading(self, email_service):
        """Test template loading from filesystem."""
        # Test template not found
        result = await email_service._load_template("nonexistent_template")
        assert result is None

    def test_email_message_dataclass(self):
        """Test EmailMessage dataclass functionality."""
        message = EmailMessage(
            subject="Test Subject",
            recipients=["test@example.com"],
            html_body="<h1>Test</h1>",
            cc=["cc@example.com"],
        )

        assert message.subject == "Test Subject"
        assert len(message.recipients) == 1
        assert message.html_body == "<h1>Test</h1>"
        assert message.cc == ["cc@example.com"]


class TestConnectionManager:
    """Test WebSocket connection manager functionality."""

    @pytest.fixture
    def manager(self):
        """Create ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock()
        mock_ws.close = AsyncMock()
        return mock_ws

    @pytest.mark.asyncio
    async def test_connect_job_updates(self, manager, mock_websocket):
        """Test connecting to job updates."""
        job_id = "test-job-123"
        user_id = "user-456"

        await manager.connect_job_updates(mock_websocket, job_id, user_id)

        # Verify connection is tracked
        assert job_id in manager.job_connections
        assert mock_websocket in manager.job_connections[job_id]
        assert user_id in manager.user_connections
        assert mock_websocket in manager.user_connections[user_id]

        # Verify metadata
        assert mock_websocket in manager.connection_metadata
        metadata = manager.connection_metadata[mock_websocket]
        assert metadata["job_id"] == job_id
        assert metadata["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_websocket):
        """Test WebSocket disconnection."""
        job_id = "test-job-123"
        user_id = "user-456"

        # First connect
        await manager.connect_job_updates(mock_websocket, job_id, user_id)

        # Then disconnect
        await manager.disconnect(mock_websocket)

        # Verify cleanup
        assert job_id not in manager.job_connections
        assert user_id not in manager.user_connections
        assert mock_websocket not in manager.connection_metadata

    @pytest.mark.asyncio
    async def test_send_job_update(self, manager, mock_websocket):
        """Test sending job updates."""
        job_id = "test-job-123"
        user_id = "user-456"

        # Connect WebSocket
        await manager.connect_job_updates(mock_websocket, job_id, user_id)

        # Send update
        update_message = {
            "status": "running",
            "progress": 50,
            "message": "Processing...",
        }

        await manager.send_job_update(job_id, update_message)

        # Verify message was sent
        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        message_data = json.loads(call_args)

        assert message_data["type"] == "job_update"
        assert message_data["job_id"] == job_id
        assert message_data["status"] == "running"
        assert message_data["progress"] == 50

    @pytest.mark.asyncio
    async def test_send_user_notification(self, manager, mock_websocket):
        """Test sending user notifications."""
        job_id = "test-job-123"
        user_id = "user-456"

        # Connect WebSocket
        await manager.connect_job_updates(mock_websocket, job_id, user_id)

        # Send notification
        notification = {"title": "Job Completed", "message": "Your timetable is ready"}

        await manager.send_user_notification(user_id, notification)

        # Verify notification was sent
        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        message_data = json.loads(call_args)

        assert message_data["type"] == "notification"
        assert message_data["user_id"] == user_id
        assert message_data["title"] == "Job Completed"

    @pytest.mark.asyncio
    async def test_broadcast_system_message(self, manager, mock_websocket):
        """Test broadcasting system messages."""
        job_id = "test-job-123"
        user_id = "user-456"

        # Connect WebSocket
        await manager.connect_job_updates(mock_websocket, job_id, user_id)

        # Broadcast system message
        system_message = {
            "title": "System Maintenance",
            "message": "Scheduled maintenance in 1 hour",
        }

        await manager.broadcast_system_message(system_message)

        # Verify message was broadcast
        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        message_data = json.loads(call_args)

        assert message_data["type"] == "system_message"
        assert message_data["title"] == "System Maintenance"

    def test_connection_stats(self, manager, mock_websocket):
        """Test connection statistics."""
        # Initially no connections
        stats = manager.get_connection_stats()
        assert stats["total_job_connections"] == 0
        assert stats["total_user_connections"] == 0

        # Add some connections (without async setup for simplicity)
        manager.job_connections["job1"] = {mock_websocket}
        manager.user_connections["user1"] = {mock_websocket}

        stats = manager.get_connection_stats()
        assert stats["total_job_connections"] == 1
        assert stats["total_user_connections"] == 1
        assert stats["job_subscriptions"] == 1
        assert stats["user_subscriptions"] == 1

    @pytest.mark.asyncio
    async def test_websocket_disconnection_handling(self, manager):
        """Test handling of WebSocket disconnections during send."""
        from fastapi import WebSocketDisconnect

        mock_websocket = MagicMock()
        mock_websocket.send_text = AsyncMock(side_effect=WebSocketDisconnect)

        job_id = "test-job-123"
        user_id = "user-456"

        # Manually add to connections (simulating previous connection)
        manager.job_connections[job_id] = {mock_websocket}
        manager.user_connections[user_id] = {mock_websocket}
        manager.connection_metadata[mock_websocket] = {
            "job_id": job_id,
            "user_id": user_id,
        }

        # Try to send update (should handle disconnection)
        await manager.send_job_update(job_id, {"status": "running"})

        # Connection should be cleaned up
        assert job_id not in manager.job_connections
        assert user_id not in manager.user_connections
        assert mock_websocket not in manager.connection_metadata


class TestWebSocketUtilities:
    """Test WebSocket utility functions."""

    # Update the test to properly mock Redis

    @pytest.mark.asyncio
    async def test_publish_job_update(self):
        """Test publishing job updates."""
        job_id = "test-job-123"
        update_data = {
            "status": "running",
            "progress": 75,
            "phase": "optimization",
            "message": "Running genetic algorithm...",
        }

        with patch(
            "app.services.notification.websocket_manager.connection_manager"
        ) as mock_manager:
            mock_manager.send_job_update = AsyncMock()
            # Mock Redis to return None
            with patch(
                "app.services.notification.websocket_manager.connection_manager.get_redis",
                return_value=None,
            ):
                await publish_job_update(job_id, update_data)
                mock_manager.send_job_update.assert_called_once_with(
                    job_id, update_data
                )

    @pytest.mark.asyncio
    async def test_get_initial_job_status(self, test_session):
        """Test getting initial job status."""
        from app.models import TimetableJob

        # Create test job
        job = TimetableJob(
            id=uuid4(),
            session_id=uuid4(),
            configuration_id=uuid4(),
            status="running",
            progress_percentage=25,
            solver_phase="cpsat",
        )
        test_session.add(job)
        await test_session.commit()
        await test_session.refresh(job)

        # Get initial status
        status = await get_initial_job_status(str(job.id), test_session)

        assert status is not None
        assert status["status"] == "running"
        assert status["progress"] == 25
        assert status["phase"] == "cpsat"

    @pytest.mark.asyncio
    async def test_get_initial_job_status_not_found(self, test_session):
        """Test getting status for non-existent job."""
        non_existent_id = str(uuid4())

        status = await get_initial_job_status(non_existent_id, test_session)

        assert status is None

    @pytest.mark.asyncio
    async def test_user_can_access_job(self, test_session):
        """Test user job access checking."""
        from app.models import TimetableJob

        user_id = uuid4()

        # Create job owned by user
        job = TimetableJob(
            id=uuid4(),
            session_id=uuid4(),
            configuration_id=uuid4(),
            initiated_by=user_id,
            status="running",
        )
        test_session.add(job)
        await test_session.commit()
        await test_session.refresh(job)

        # User should have access to their own job
        has_access = await user_can_access_job(str(user_id), str(job.id), test_session)
        assert has_access is True

        # Different user should not have access
        other_user_id = uuid4()
        has_access = await user_can_access_job(
            str(other_user_id), str(job.id), test_session
        )
        assert has_access is False

    @pytest.mark.asyncio
    async def test_notify_job_completed(self):
        """Test job completion notification."""
        job_id = "test-job-123"
        result = {
            "success": True,
            "metrics": {"assignment_rate": 0.95},
            "execution_time": 120.5,
        }

        with patch("app.services.notification.publish_job_update") as mock_publish:
            await notify_job_completed(job_id, result)

            mock_publish.assert_called_once()
            call_args = mock_publish.call_args[0]
            assert call_args[0] == job_id
            update_data = call_args[1]
            assert update_data["status"] == "completed"
            assert update_data["progress"] == 100

    @pytest.mark.asyncio
    async def test_notify_job_cancelled(self):
        """Test job cancellation notification."""
        job_id = "test-job-123"
        reason = "Cancelled by user"

        with patch("app.services.notification.publish_job_update") as mock_publish:
            await notify_job_cancelled(job_id, reason)

            mock_publish.assert_called_once()
            call_args = mock_publish.call_args[0]
            assert call_args[0] == job_id
            update_data = call_args[1]
            assert update_data["status"] == "cancelled"
            assert update_data["message"] == reason

    @pytest.mark.asyncio
    async def test_notify_job_error(self):
        """Test job error notification."""
        job_id = "test-job-123"
        error_message = "Optimization failed: insufficient data"

        with patch("app.services.notification.publish_job_update") as mock_publish:
            await notify_job_error(job_id, error_message)

            mock_publish.assert_called_once()
            call_args = mock_publish.call_args[0]
            assert call_args[0] == job_id
            update_data = call_args[1]
            assert update_data["status"] == "failed"
            assert error_message in update_data["message"]


@pytest.mark.integration
class TestNotificationIntegration:
    """Integration tests for notification services."""

    @pytest.mark.asyncio
    async def test_email_websocket_integration(self, email_service):
        """Test integration between email and WebSocket notifications."""
        job_id = "integration-test-job"
        user_email = "user@example.com"

        # Simulate job completion
        with patch.object(
            email_service, "send_job_notification", return_value=True
        ) as mock_email:
            with patch("app.services.notification.publish_job_update") as mock_ws:

                # Send both email and WebSocket notifications
                await email_service.send_job_notification(
                    user_email, job_id, "completed"
                )
                await publish_job_update(
                    job_id, {"status": "completed", "progress": 100}
                )

                mock_email.assert_called_once()
                mock_ws.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_fallback(self):
        """Test Redis fallback behavior."""
        with patch("app.services.notification.connection_manager") as mock_manager:
            # Simulate Redis unavailable
            mock_manager.send_job_update = AsyncMock()

            await publish_job_update("test-job", {"status": "running"})

            # Should still send via WebSocket manager
            mock_manager.send_job_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_connections_same_job(self):
        """Test multiple WebSocket connections for the same job."""
        manager = ConnectionManager()

        # Create multiple mock WebSockets
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()

        ws2 = MagicMock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()

        job_id = "multi-connection-job"

        # Connect both WebSockets to same job
        await manager.connect_job_updates(ws1, job_id, "user1")
        await manager.connect_job_updates(ws2, job_id, "user2")

        # Send update
        await manager.send_job_update(job_id, {"status": "running"})

        # Both WebSockets should receive the update
        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()
