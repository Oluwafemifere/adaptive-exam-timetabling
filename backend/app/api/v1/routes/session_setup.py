# backend/app/api/v1/routes/session_setup.py
"""API endpoints for the multi-step exam session setup wizard."""

from typing import Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.session_setup_service import SessionSetupService
from ....services.seeding.data_seeding_service import DataSeedingService
from ....schemas.session_setup import SessionSetupCreate, SessionSetupSummary
from ....schemas.system import GenericResponse

router = APIRouter()


@router.post(
    "/session",
    response_model=GenericResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Step 1: Define Session and Schedule Structure",
)
async def create_exam_session_setup(
    setup_data: SessionSetupCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Creates a new academic exam session and its corresponding data seeding session.
    """
    service = SessionSetupService(db)
    result = await service.setup_new_exam_session(
        user_id=user.id,
        session_name=setup_data.session_name,
        start_date=setup_data.start_date,
        end_date=setup_data.end_date,
        slot_generation_mode=setup_data.slot_generation_mode,
        time_slots=[ts.model_dump() for ts in setup_data.time_slots],
    )

    if not result or not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to create the exam session."),
        )

    # The result from the service now contains both IDs
    return GenericResponse(
        success=True,
        message="Exam session created successfully. You can now upload data.",
        data={
            "academic_session_id": result.get("academic_session_id"),
            "data_seeding_session_id": result.get("data_seeding_session_id"),
        },
    )


@router.get(
    "/session/{session_id}/summary",
    response_model=SessionSetupSummary,
    summary="Step 4: Get Summary and Validation",
)
async def get_session_summary(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Retrieves a data summary and validation warnings for the specified session.
    This should be called after all required data files have been uploaded.
    """
    service = SessionSetupService(db)
    summary_data = await service.get_session_setup_summary_and_validate(session_id)

    if not summary_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not generate a summary for this session. Ensure data has been uploaded.",
        )

    return summary_data


@router.post(
    "/session/{session_id}/process-data",
    response_model=GenericResponse,
    summary="Step 5: Process All Uploaded Data",
)
async def process_staged_data(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Triggers the final, transactional processing of all staged data for the session.
    This should be the last step after uploading and validating all required files.
    """
    service = SessionSetupService(db)
    result = await service.process_all_staged_data(session_id)

    if not result or not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to process staged data."),
        )

    return GenericResponse(
        success=True,
        message=result.get(
            "message", "All staged data has been processed successfully."
        ),
        data={"academic_session_id": session_id},
    )


@router.get(
    "/staging-data/{session_id}/{entity_type}",
    response_model=GenericResponse,
    summary="Get Staged Data for Review",
)
async def get_staged_data_for_review(
    session_id: UUID,
    entity_type: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieves all data from a specified staging table for a given session."""
    service = DataSeedingService(db)
    result = await service.get_staged_data(session_id, entity_type)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return GenericResponse(success=True, data=result.get("data"))


@router.put(
    "/staging-data/{entity_type}/{record_pk}",
    response_model=GenericResponse,
    summary="Update a Staged Record",
)
async def update_staged_data_record(
    entity_type: str,
    record_pk: str,
    payload: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Updates a single record in a staging table before final processing."""
    service = DataSeedingService(db)
    result = await service.update_staged_record(entity_type, record_pk, payload)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("message")
        )
    return GenericResponse(success=True, data=result.get("data"))
