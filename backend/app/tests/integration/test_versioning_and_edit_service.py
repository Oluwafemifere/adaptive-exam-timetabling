import pytest
from uuid import UUID
from app.services.scheduling.versioning_and_edit_service import (
    VersioningAndEditService,
    ProposedEdit,
)


@pytest.mark.asyncio
async def test_propose_edit(test_session, complete_test_data):
    """Test proposing an edit"""
    service = VersioningAndEditService(test_session)
    user_id = complete_test_data["user"].id
    version_id = complete_test_data["timetable_version"].id
    exam_id = complete_test_data["exam"].id

    edit = ProposedEdit(
        version_id=version_id,
        exam_id=exam_id,
        edit_type="time_slot_change",
        old_values={"time_slot_id": "old_value"},
        new_values={"time_slot_id": "new_value"},
        reason="Test reason",
    )

    edit_id = await service.propose_edit(user_id, edit)
    assert edit_id is not None


@pytest.mark.asyncio
async def test_validate_edit(test_session, complete_test_data):
    """Test validating an edit"""
    service = VersioningAndEditService(test_session)
    # We need to create an edit first
    user_id = complete_test_data["user"].id
    version_id = complete_test_data["timetable_version"].id
    exam_id = complete_test_data["exam"].id

    edit = ProposedEdit(
        version_id=version_id,
        exam_id=exam_id,
        edit_type="time_slot_change",
        old_values={"time_slot_id": "old_value"},
        new_values={"time_slot_id": "new_value"},
        reason="Test reason",
    )

    edit_id = await service.propose_edit(user_id, edit)

    validation_result = await service.validate_edit(edit_id)
    assert "valid" in validation_result
