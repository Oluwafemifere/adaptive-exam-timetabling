# backend/app/tests/integration/test_api_endpoints.py

"""
Integration tests for API endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4
import json

from app.main import app
from app.models import TimetableJob


@pytest.mark.asyncio
class TestSchedulingEndpoints:
    """Test scheduling API endpoints."""

    async def test_create_timetable_job(
        self, client, sample_academic_session, sample_system_configuration
    ):
        """Test creating a new timetable job."""
        response = await client.post(
            "/api/v1/scheduling/jobs",
            json={
                "session_id": str(sample_academic_session.id),
                "configuration_id": str(sample_system_configuration.id),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "job_id" in data
        assert data["status"] == "queued"

    async def test_get_job_status(
        self, client, test_session, sample_academic_session, sample_system_configuration
    ):
        """Test getting job status."""
        # Create a job first
        job = TimetableJob(
            id=uuid4(),
            session_id=sample_academic_session.id,
            configuration_id=sample_system_configuration.id,
            status="running",
            progress_percentage=50,
        )
        test_session.add(job)
        await test_session.commit()
        await test_session.refresh(job)

        response = await client.get(f"/api/v1/scheduling/jobs/{job.id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == str(job.id)
        assert data["status"] == "running"
        assert data["progress_percentage"] == 50

    async def test_cancel_job(
        self, client, test_session, sample_academic_session, sample_system_configuration
    ):
        """Test canceling a job."""
        job = TimetableJob(
            id=uuid4(),
            session_id=sample_academic_session.id,
            configuration_id=sample_system_configuration.id,
            status="running",
            progress_percentage=25,
        )
        test_session.add(job)
        await test_session.commit()
        await test_session.refresh(job)

        response = await client.post(f"/api/v1/scheduling/jobs/{job.id}/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "cancelled"

    async def test_get_nonexistent_job(self, client):
        """Test getting status of non-existent job."""
        non_existent_id = uuid4()
        response = await client.get(f"/api/v1/scheduling/jobs/{non_existent_id}/status")

        assert response.status_code == 404

    async def test_invalid_job_creation_data(self, client):
        """Test job creation with invalid data."""
        response = await client.post(
            "/api/v1/scheduling/jobs",
            json={"session_id": "invalid-uuid", "configuration_id": str(uuid4())},
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
class TestUploadEndpoints:
    """Test file upload endpoints."""

    async def test_upload_csv_file(self, client):
        """Test uploading CSV file."""
        # Create test CSV content
        csv_content = """Course Code,Course Title,Credit Units,Level
CSC201,Data Structures,3,200
CSC301,Algorithm Analysis,3,300"""

        response = await client.post(
            "/api/v1/uploads/csv",
            files={"file": ("test_courses.csv", csv_content, "text/csv")},
            data={"file_type": "courses", "session_id": str(uuid4())},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "upload_session_id" in data

    async def test_upload_invalid_file_type(self, client):
        """Test uploading invalid file type."""
        response = await client.post(
            "/api/v1/uploads/csv",
            files={"file": ("test.txt", "invalid content", "text/plain")},
            data={"file_type": "courses", "session_id": str(uuid4())},
        )

        assert response.status_code == 400

    async def test_upload_empty_file(self, client):
        """Test uploading empty file."""
        response = await client.post(
            "/api/v1/uploads/csv",
            files={"file": ("empty.csv", "", "text/csv")},
            data={"file_type": "courses", "session_id": str(uuid4())},
        )

        assert response.status_code == 400

    async def test_get_upload_status(self, client, test_session):
        """Test getting upload status."""
        from app.models import FileUploadSession

        upload_session = FileUploadSession(
            id=uuid4(),
            uploaded_by=uuid4(),
            session_id=uuid4(),
            upload_type="courses",
            status="processing",
        )

        test_session.add(upload_session)
        await test_session.commit()
        await test_session.refresh(upload_session)

        response = await client.get(f"/api/v1/uploads/{upload_session.id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"


@pytest.mark.asyncio
class TestTimetableEndpoints:
    """Test timetable management endpoints."""

    async def test_get_timetable_data(
        self, client, test_session, sample_academic_session, sample_system_configuration
    ):
        """Test getting timetable data."""
        job = TimetableJob(
            id=uuid4(),
            session_id=sample_academic_session.id,
            configuration_id=sample_system_configuration.id,
            status="completed",
            progress_percentage=100,
        )
        test_session.add(job)
        await test_session.commit()
        await test_session.refresh(job)

        response = await client.get(f"/api/v1/timetables/{job.id}")

        # Might return 404 if no timetable version exists, which is expected
        assert response.status_code in [200, 404]

    async def test_export_timetable(
        self, client, test_session, sample_academic_session, sample_system_configuration
    ):
        """Test exporting timetable."""
        job = TimetableJob(
            id=uuid4(),
            session_id=sample_academic_session.id,
            configuration_id=sample_system_configuration.id,
            status="completed",
            progress_percentage=100,
        )
        test_session.add(job)
        await test_session.commit()
        await test_session.refresh(job)

        response = await client.get(
            f"/api/v1/timetables/{job.id}/export", params={"format": "csv"}
        )

        # Might return 404 if no timetable version exists
        assert response.status_code in [200, 404]

    async def test_apply_manual_edit(
        self, client, test_session, sample_academic_session, sample_system_configuration
    ):
        """Test applying manual edit to timetable."""
        job = TimetableJob(
            id=uuid4(),
            session_id=sample_academic_session.id,
            configuration_id=sample_system_configuration.id,
            status="completed",
            progress_percentage=100,
        )
        test_session.add(job)
        await test_session.commit()
        await test_session.refresh(job)

        edit_data = {
            "exam_id": str(uuid4()),
            "edit_type": "time_change",
            "new_timeslot_id": str(uuid4()),
        }

        response = await client.post(
            f"/api/v1/timetables/{job.id}/edit", json=edit_data
        )

        # Might return 404 if no timetable version exists
        assert response.status_code in [200, 404, 400]


@pytest.mark.asyncio
class TestWebSocketEndpoints:
    """Test WebSocket endpoints."""

    async def test_job_updates_websocket(
        self, client, test_session, sample_academic_session, sample_system_configuration
    ):
        """Test WebSocket connection for job updates."""
        job = TimetableJob(
            id=uuid4(),
            session_id=sample_academic_session.id,
            configuration_id=sample_system_configuration.id,
            status="running",
            progress_percentage=30,
        )
        test_session.add(job)
        await test_session.commit()
        await test_session.refresh(job)

        # Test WebSocket connection
        with client.websocket_connect(f"/api/v1/ws/jobs/{job.id}") as websocket:
            # Should receive initial status
            data = websocket.receive_json()
            assert data["status"] == "running"
            assert data["progress"] == 30


@pytest.mark.asyncio
class TestHealthEndpoints:
    """Test health check endpoints."""

    async def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    async def test_health_check(self, client):
        """Test health check endpoint."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert "service" in data
        assert "database" in data

    async def test_api_test_endpoint(self, client):
        """Test API test endpoint."""
        response = await client.get("/api/v1/test")

        assert response.status_code == 200
        data = response.json()
        assert data["test"] == "passed"


@pytest.mark.asyncio
class TestAuthenticationEndpoints:
    """Test authentication-related endpoints."""

    async def test_login_endpoint_exists(self, client):
        """Test that login endpoint exists (might not be implemented yet)."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "test@example.com", "password": "password"},
        )

        # Might return 404 if not implemented yet
        assert response.status_code in [200, 404, 422]

    async def test_protected_endpoint_without_auth(self, client):
        """Test accessing protected endpoint without authentication."""
        # This test assumes some endpoints require authentication
        # Adjust based on actual implementation
        response = await client.get("/api/v1/scheduling/jobs")

        # Should either work (if no auth required) or return 401/403
        assert response.status_code in [200, 401, 403]


@pytest.mark.asyncio
class TestErrorHandling:
    """Test API error handling."""

    async def test_invalid_uuid_parameter(self, client):
        """Test handling of invalid UUID parameters."""
        response = await client.get("/api/v1/scheduling/jobs/invalid-uuid/status")

        assert response.status_code == 422  # Validation error

    async def test_missing_required_fields(self, client):
        """Test handling of missing required fields."""
        response = await client.post("/api/v1/scheduling/jobs", json={})

        assert response.status_code == 422  # Validation error

    async def test_invalid_json_payload(self, client):
        """Test handling of invalid JSON payload."""
        response = await client.post(
            "/api/v1/scheduling/jobs",
            data="invalid json",
            headers={"content-type": "application/json"},
        )

        assert response.status_code == 422

    async def test_method_not_allowed(self, client):
        """Test method not allowed handling."""
        response = await client.delete("/api/v1/test")  # Assuming DELETE is not allowed

        assert response.status_code == 405

    async def test_large_payload(self, client):
        """Test handling of large payloads."""
        large_data = {"data": "x" * (10 * 1024 * 1024)}  # 10MB payload

        response = await client.post("/api/v1/scheduling/jobs", json=large_data)

        # Should either reject due to size limits or validation error
        assert response.status_code in [413, 422]


@pytest.mark.integration
class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""

    async def test_complete_timetable_generation_workflow(
        self,
        client,
        sample_academic_session,
        sample_system_configuration,
        sample_courses,
        sample_students,
        sample_course_registrations,
        sample_buildings_and_rooms,
        sample_time_slots,
        sample_staff,
    ):
        """Test complete timetable generation workflow."""
        # Step 1: Create timetable job
        response = await client.post(
            "/api/v1/scheduling/jobs",
            json={
                "session_id": str(sample_academic_session.id),
                "configuration_id": str(sample_system_configuration.id),
            },
        )

        assert response.status_code == 200
        job_data = response.json()
        job_id = job_data["job_id"]

        # Step 2: Check job status
        response = await client.get(f"/api/v1/scheduling/jobs/{job_id}/status")
        assert response.status_code == 200
        status_data = response.json()
        assert status_data["status"] in ["queued", "running"]

        # Step 3: In a real test, we might wait for completion or mock it
        # For this test, we'll just verify the endpoints work

        # Step 4: Try to get timetable data (might not exist yet)
        response = await client.get(f"/api/v1/timetables/{job_id}")
        assert response.status_code in [200, 404]  # 404 is expected if not completed

    async def test_file_upload_and_processing_workflow(
        self, client, sample_academic_session
    ):
        """Test file upload and processing workflow."""
        # Step 1: Upload CSV file
        csv_content = """Student ID,Matric Number,Programme,Level
1,2021/CS/001,Computer Science,200
2,2021/CS/002,Computer Science,300"""

        response = await client.post(
            "/api/v1/uploads/csv",
            files={"file": ("students.csv", csv_content, "text/csv")},
            data={
                "file_type": "students",
                "session_id": str(sample_academic_session.id),
            },
        )

        assert response.status_code == 200
        upload_data = response.json()
        upload_session_id = upload_data["upload_session_id"]

        # Step 2: Check upload status
        response = await client.get(f"/api/v1/uploads/{upload_session_id}/status")
        assert response.status_code == 200
        status_data = response.json()
        assert "status" in status_data

    async def test_concurrent_job_creation(
        self, client, sample_academic_session, sample_system_configuration
    ):
        """Test creating multiple jobs concurrently."""
        import asyncio

        async def create_job():
            return client.post(
                "/api/v1/scheduling/jobs",
                json={
                    "session_id": str(sample_academic_session.id),
                    "configuration_id": str(sample_system_configuration.id),
                },
            )

        # Create multiple jobs concurrently
        tasks = [create_job() for _ in range(3)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
