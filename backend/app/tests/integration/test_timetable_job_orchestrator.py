import pytest
from uuid import UUID
from app.services.scheduling.timetable_job_orchestrator import (
    TimetableJobOrchestrator,
    OrchestratorOptions,
)


def dummy_solver(data):
    """Minimal solver for testing"""
    return {"status": "solved", "assignments": []}


@pytest.mark.asyncio
async def test_job_orchestration(test_session, complete_test_data):
    """Test complete job orchestration flow"""
    orchestrator = TimetableJobOrchestrator(test_session)
    session_id = complete_test_data["academic_session"].id
    config_id = complete_test_data["system_configuration"].id
    user_id = complete_test_data["user"].id

    options = OrchestratorOptions(
        run_room_planning=True, run_invigilator_planning=True, activate_version=False
    )

    job_id = await orchestrator.start_job(
        session_id=session_id,
        configuration_id=config_id,
        initiated_by=user_id,
        solver_callable=dummy_solver,
        options=options,
    )

    assert job_id is not None

    # Verify job was created in database
    from app.models.jobs import TimetableJob
    from sqlalchemy import select

    result = await test_session.execute(
        select(TimetableJob).where(TimetableJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    assert job is not None
    assert job.status in ["completed", "running", "queued"]
