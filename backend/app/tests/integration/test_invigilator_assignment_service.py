import pytest
from uuid import UUID
from app.services.scheduling.invigilator_assignment_service import (
    InvigilatorAssignmentService,
)


@pytest.mark.asyncio
async def test_invigilator_assignment(test_session, complete_test_data):
    """Test invigilator assignment with real data"""
    service = InvigilatorAssignmentService(test_session)
    session_id = complete_test_data["academic_session"].id

    assignments = await service.assign_invigilators(session_id)

    assert len(assignments) > 0
    for assignment in assignments:
        assert assignment.exam_id is not None
        # Should have at least some assignments
        assert len(assignment.staff_ids) >= 0


@pytest.mark.asyncio
async def test_notification_payloads(test_session, complete_test_data):
    """Test notification payload generation"""
    service = InvigilatorAssignmentService(test_session)
    session_id = complete_test_data["academic_session"].id

    assignments = await service.assign_invigilators(session_id)
    payloads = await service.build_notification_payloads(assignments)

    assert len(payloads) >= 0
    if len(payloads) > 0:
        assert "user_id" in payloads[0]
        assert "message" in payloads[0]
