# backend/app/api/v1/routes/academic_sessions.py
"""API endpoints for managing academic sessions."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_retrieval import DataRetrievalService
from ....services.System.system_service import SystemService
from ....schemas.academic import (
    AcademicSessionRead,
    AcademicSessionCreate,
    AcademicSessionUpdate,
)
from ....schemas.system import GenericResponse

router = APIRouter()


@router.post(
    "/", response_model=AcademicSessionRead, status_code=status.HTTP_201_CREATED
)
async def create_session(
    session_in: AcademicSessionCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Create a new academic session."""
    service = SystemService(db)
    result = await service.create_academic_session(
        p_name=session_in.name,
        p_start_date=session_in.start_date,
        p_end_date=session_in.end_date,
        p_timeslot_template_id=session_in.timeslot_template_id,
    )
    if not result or not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "Failed to create academic session."),
        )

    # Fetch the newly created session to return the full object
    retrieval_service = DataRetrievalService(db)
    new_session = await retrieval_service.get_entity_by_id(
        "academic_sessions", result["session_id"]
    )
    if not new_session:
        raise HTTPException(
            status_code=404, detail="Could not retrieve session after creation."
        )
    return new_session


@router.put("/{session_id}", response_model=AcademicSessionRead)
async def update_session(
    session_id: UUID,
    session_in: AcademicSessionUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Update an existing academic session."""
    service = SystemService(db)
    # --- START OF FIX ---
    # The user_id is now required by the service method to log the audit trail.
    result = await service.update_academic_session(
        session_id=session_id,
        update_data=session_in.model_dump(exclude_unset=True),
        user_id=user.id,
    )
    # --- END OF FIX ---
    if not result:
        raise HTTPException(
            status_code=404, detail="Academic session not found or update failed."
        )

    # After update, fetch the updated record to return it
    retrieval_service = DataRetrievalService(db)
    updated_session = await retrieval_service.get_entity_by_id(
        "academic_sessions", session_id
    )
    if not updated_session:
        raise HTTPException(
            status_code=404, detail="Academic session not found after update."
        )
    return updated_session


@router.delete(
    "/{session_id}",
    response_model=GenericResponse,
    status_code=status.HTTP_200_OK,
    summary="Archive an Academic Session",
)
async def archive_session(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Archive (soft-delete) an academic session.
    """
    service = SystemService(db)
    result = await service.archive_academic_session(
        session_id=session_id, user_id=user.id
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to archive session."),
        )
    return result


@router.get("/", response_model=List[AcademicSessionRead])
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve a paginated list of academic sessions."""
    service = DataRetrievalService(db)
    result = await service.get_paginated_entities(
        "academic_sessions", page=page, page_size=page_size
    )
    return result.get("data", []) if result else []


@router.get("/active", response_model=AcademicSessionRead)
async def get_active_session(
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve the currently active academic session."""
    service = DataRetrievalService(db)
    active_session = await service.get_active_academic_session()
    if not active_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active session found."
        )
    return active_session


@router.post(
    "/{session_id}/set-active",
    response_model=GenericResponse,
    status_code=status.HTTP_200_OK,
)
async def set_active_session(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Set a specific academic session as the active one."""
    service = SystemService(db)
    try:
        await service.set_active_academic_session(
            session_id=session_id, user_id=user.id
        )
        return GenericResponse(
            success=True, message="Active academic session updated successfully."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set active session: {e}",
        )
