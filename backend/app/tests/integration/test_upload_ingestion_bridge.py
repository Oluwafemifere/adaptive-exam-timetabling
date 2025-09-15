import pytest
from uuid import UUID
from app.services.scheduling.upload_ingestion_bridge import UploadIngestionBridge


@pytest.mark.asyncio
async def test_list_recent_uploads(test_session):
    """Test listing recent uploads"""
    service = UploadIngestionBridge(test_session)
    uploads = await service.list_recent_uploads(limit=10)

    # We don't have any uploads in the test database, so we expect an empty list
    assert isinstance(uploads, list)


@pytest.mark.asyncio
async def test_ready_for_ingestion(test_session):
    """Test checking if an upload is ready for ingestion"""
    service = UploadIngestionBridge(test_session)
    # Create a fake UUID to test
    fake_upload_id = UUID("12345678-1234-5678-1234-567812345678")
    is_ready = await service.ready_for_ingestion(fake_upload_id)

    assert isinstance(is_ready, bool)
    assert is_ready is False  # Because the upload doesn't exist
