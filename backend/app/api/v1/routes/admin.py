# backend/app/api/v1/routes/admin.py
"""API endpoints for administrative tasks (seeding, uploads, email test)."""
from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...deps import db_session, current_user
from ....models.users import User
from ....services.data_management.database_seeder import DatabaseSeeder
from ....services.uploads.data_upload_service import DataUploadService
from ....services.notification.email_service import EmailService
from ....services.data_retrieval import DataRetrievalService
from ....schemas.admin import SeedingRequest, UploadSessionCreate, JsonSeedingRequest
from ....schemas.system import GenericResponse

router = APIRouter()


@router.post("/seed/{session_id}", response_model=GenericResponse)
async def seed_database(
    session_id: UUID,
    seed_in: SeedingRequest,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Trigger database seeding for a specific session."""
    seeder = DatabaseSeeder(db)
    try:
        result = await seeder.seed_for_scheduling_engine(
            session_id=session_id, validation_mode=seed_in.validation_mode
        )
        return GenericResponse(success=result["success"], data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/session", response_model=GenericResponse)
async def create_upload_session(
    upload_in: UploadSessionCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Create a new metadata session for a bulk upload."""
    service = DataUploadService(db)
    result = await service.create_upload_session(
        user_id=user.id,
        session_id=upload_in.session_id,
        upload_type=upload_in.upload_type,
        file_metadata=upload_in.file_metadata,
    )
    if not result.get("success", True):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Failed to create upload session"),
        )
    return GenericResponse(success=True, data=result)


@router.get("/email/test")
async def test_email_connection(
    user: User = Depends(current_user),
):
    """Test the SMTP connection configuration."""
    service = EmailService()
    success = await service.test_connection()
    if not success:
        raise HTTPException(status_code=500, detail="SMTP connection test failed")
    return {"detail": "SMTP connection successful"}


@router.post("/seed/json", response_model=GenericResponse)
async def seed_from_json(
    seed_request: JsonSeedingRequest,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Seed data for a specific entity from a JSON object."""
    # Corrected: This function is on DataUploadService
    service = DataUploadService(db)
    try:
        result = await service.seed_entity_data(
            entity_type=seed_request.entity_type,
            data=seed_request.data,
        )
        return GenericResponse(
            success=True, message="Data seeding successful.", data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to seed data: {e}")


@router.get("/data/{entity_type}", response_model=List[Dict[str, Any]])
async def get_all_entity_data(
    entity_type: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve all records for a given entity type."""
    service = DataRetrievalService(db)
    # Corrected: The method is named get_all_entities_as_json
    result = await service.get_all_entities_as_json(entity_type)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Entity type '{entity_type}' not found or no data available.",
        )
    return result
