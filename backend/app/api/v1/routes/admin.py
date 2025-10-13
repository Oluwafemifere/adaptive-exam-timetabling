# backend/app/api/v1/routes/admin.py
"""API endpoints for administrative tasks (email test, data retrieval)."""
from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...deps import db_session, current_user
from ....models.users import User
from ....services.notification.email_service import EmailService
from ....services.data_retrieval import DataRetrievalService
from ....schemas.system import GenericResponse
from ....services.session_setup_service import SessionSetupService

router = APIRouter()


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


@router.get("/data/{session_id}/{entity_type}", response_model=List[Dict[str, Any]])
async def get_all_entity_data(
    session_id: UUID,
    entity_type: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve all records for a given entity type within a specific session."""
    service = DataRetrievalService(db)
    result = await service.get_all_entities_as_json(
        entity_type=entity_type, session_id=session_id
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Entity type '{entity_type}' not found or no data available for the given session.",
        )
    return result


@router.post("/process-staged-data/{session_id}", response_model=GenericResponse)
async def process_all_staged_data(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Triggers the processing of all data in the staging tables for a given session.
    """
    service = SessionSetupService(db)
    result = await service.process_all_staged_data(session_id)
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "Failed to process staged data."),
        )
    return GenericResponse(success=True, message=result.get("message"))
