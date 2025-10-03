# backend/app/tests/tasks/test_scheduling_tasks.py

import pytest
import pytest_asyncio
import uuid
from datetime import date, datetime, timezone
from unittest.mock import patch, AsyncMock
import asyncio

from backend.app.tasks.scheduling_tasks import generate_timetable_task
from backend.app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
import json

# --- Test Constants ---
TEST_SESSION_ID = "a2ec1e3b-e903-41b6-910f-67b817255b30"  # <-- must exist in DB already
TEST_USER_ID = "d0574de6-ad28-4610-95e0-9293d43d03d4"
TEST_CONFIGURATION_ID = "fc65db3b-10a1-4078-b4b5-7052326f9ccd"
TEST_START_DATE = date(2025, 11, 3)
TEST_END_DATE = date(2025, 11, 21)


@pytest.fixture(scope="function")
def celery_app(celery_app):
    """Configure Celery for synchronous testing."""
    celery_app.conf.update(task_always_eager=True)
    return celery_app


@pytest_asyncio.fixture(scope="module")
async def db_session_factory():
    """Provide async DB session factory for the test."""
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def setup_test_dependencies_in_db(db_factory, job_id: uuid.UUID):
    """
    Insert only user, system configuration, and timetable job records.
    The academic session is assumed to already exist.
    """
    async with db_factory() as session:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # 1. User
        await session.execute(
            text(
                """
                INSERT INTO exam_system.users
                (id, email, first_name, last_name, is_active, is_superuser, created_at, updated_at)
                VALUES
                (:id, :email, 'Test', 'User', true, false, :now, :now)
                ON CONFLICT (id) DO NOTHING;
                """
            ),
            {
                "id": uuid.UUID(TEST_USER_ID),
                "email": "test.user@example.com",
                "now": now,
            },
        )

        # 2. System Configuration
        await session.execute(
            text(
                """
                INSERT INTO exam_system.system_configurations
                (id, name, created_by, is_default, created_at, updated_at)
                VALUES
                (:id, 'Test Config', :user_id, false, :now, :now)
                ON CONFLICT (id) DO NOTHING;
                """
            ),
            {
                "id": uuid.UUID(TEST_CONFIGURATION_ID),
                "user_id": uuid.UUID(TEST_USER_ID),
                "now": now,
            },
        )

        # 3. Timetable Job
        await session.execute(
            text(
                """
                INSERT INTO exam_system.timetable_jobs
                (id, session_id, configuration_id, status, initiated_by, progress_percentage,
                 hard_constraint_violations, created_at, updated_at, can_pause, can_resume, can_cancel)
                VALUES
                (:id, :session_id, :config_id, 'pending', :user_id, 0, 0, :now, :now, false, false, true)
                """
            ),
            {
                "id": job_id,
                "session_id": uuid.UUID(TEST_SESSION_ID),  # existing session
                "config_id": uuid.UUID(TEST_CONFIGURATION_ID),
                "user_id": uuid.UUID(TEST_USER_ID),
                "now": now,
            },
        )
        await session.commit()
    print(f"\nSetup complete for job {job_id} with existing session {TEST_SESSION_ID}.")


async def _verify_db_state(db_factory, job_id: uuid.UUID):
    """Check final job state in DB."""
    async with db_factory() as session:
        db_result = await session.execute(
            text(
                "SELECT status, result_data, completed_at FROM exam_system.timetable_jobs WHERE id = :job_id"
            ),
            {"job_id": job_id},
        )
        job_record = db_result.one()

        assert job_record.status == "running"
        assert job_record.result_data is not None

        results_payload = json.loads(job_record.result_data)
        assert isinstance(results_payload, dict)
        assert "solution" in results_payload
        assert "lookup_metadata" in results_payload
        assert "exams" in results_payload["lookup_metadata"]


def test_generate_timetable_end_to_end(celery_app, db_session_factory):
    """End-to-end test using existing academic session."""
    job_id = uuid.uuid4()
    asyncio.run(setup_test_dependencies_in_db(db_session_factory, job_id))

    task_options = {
        "start_date": TEST_START_DATE.isoformat(),
        "end_date": TEST_END_DATE.isoformat(),
    }

    with patch(
        "backend.app.tasks.scheduling_tasks.publish_job_update",
        new_callable=AsyncMock,
    ) as mock_publish_update, patch(
        "backend.app.tasks.scheduling_tasks.enrich_timetable_result_task.delay"
    ) as mock_enrich_task:
        result = generate_timetable_task.apply(
            kwargs={
                "job_id": str(job_id),
                "session_id": TEST_SESSION_ID,
                "configuration_id": TEST_CONFIGURATION_ID,
                "user_id": TEST_USER_ID,
                "options": task_options,
            }
        )

        assert result.successful(), f"Task failed: {result.traceback}"
        task_output = result.get()
        assert task_output["success"] is True
        assert task_output["job_id"] == str(job_id)

        mock_enrich_task.assert_called_once_with(job_id=str(job_id))
        assert mock_publish_update.call_count > 0

        final_update_call = mock_publish_update.call_args_list[-1]
        assert final_update_call[0][1]["status"] == "post_processing"

        asyncio.run(_verify_db_state(db_session_factory, job_id))

    print(f"\n✅ Test finished for job {job_id} with session {TEST_SESSION_ID}")
