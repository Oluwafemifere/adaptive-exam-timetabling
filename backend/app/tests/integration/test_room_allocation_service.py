import pytest
from uuid import UUID
from app.services.scheduling.room_allocation_service import RoomAllocationService


@pytest.mark.asyncio
async def test_room_allocation(test_session, complete_test_data):
    """Test room allocation with real data"""
    service = RoomAllocationService(test_session)
    session_id = complete_test_data["academic_session"].id

    proposals = await service.plan_room_allocations(session_id)

    assert len(proposals) > 0
    for proposal in proposals:
        assert proposal.exam_id is not None


@pytest.mark.asyncio
async def test_room_plan_validation(test_session, complete_test_data):
    """Test room plan validation"""
    service = RoomAllocationService(test_session)
    session_id = complete_test_data["academic_session"].id

    proposals = await service.plan_room_allocations(session_id)
    validation = await service.validate_room_plan(proposals, session_id)

    assert "errors" in validation
    assert "warnings" in validation
    # Should not have critical errors with test data
    assert len(validation["errors"]) == 0
