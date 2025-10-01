"""API endpoints for managing academic sessions."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_retrieval import DataRetrievalService

# Assuming a Pydantic schema exists or is created in ....schemas.academic
from ....schemas.academic import AcademicSessionRead
from ....schemas.system import GenericResponse

router = APIRouter()


@router.get("/", response_model=List[AcademicSessionRead])
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Retrieve a paginated list of academic sessions.
    The frontend will use this to find the active session.
    """
    service = DataRetrievalService(db)
    # The get_paginated_entities function is generic and can fetch any entity type
    result = await service.get_paginated_entities(
        "academic_sessions", page=page, page_size=page_size
    )
    return result.get("data", []) if result else []


# --- NEWLY ADDED ROUTES ---


@router.get("/active", response_model=AcademicSessionRead)
async def get_active_session(
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Retrieve the currently active academic session.
    Uses the `get_active_academic_session` service method.
    """
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
    """
    Set a specific academic session as the active one.
    Uses the `set_active_academic_session` service method.
    """
    service = DataRetrievalService(db)
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
