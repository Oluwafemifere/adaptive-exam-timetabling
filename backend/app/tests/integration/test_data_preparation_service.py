import pytest
from uuid import UUID
from app.services.scheduling.data_preparation_service import DataPreparationService


@pytest.mark.asyncio
async def test_build_dataset(test_session, complete_test_data):
    """Test building a dataset"""
    service = DataPreparationService(test_session)
    session_id = complete_test_data["academic_session"].id

    dataset = await service.build_dataset(session_id)
    assert dataset.session_id == session_id
    assert isinstance(dataset.exams, list)
    assert isinstance(dataset.rooms, list)
    assert isinstance(dataset.time_slots, list)
    assert isinstance(dataset.staff, list)
    assert isinstance(dataset.course_registrations, list)
    assert isinstance(dataset.indices, dict)
    assert isinstance(dataset.validations, dict)


# backend.app.tests.integration.test_data_preparation_service
