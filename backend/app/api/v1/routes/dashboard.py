# app/api/v1/routes/dashboard.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_retrieval import DataRetrievalService
from ....schemas.system import GenericResponse

router = APIRouter()


@router.get("/{session_id}/analytics", response_model=GenericResponse)
async def get_dashboard_analytics(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve detailed analytics for the dashboard."""
    service = DataRetrievalService(db)
    data = await service.get_dashboard_analytics(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Analytics data not found.")
    return GenericResponse(success=True, data=data)


@router.get("/{session_id}/overview", response_model=GenericResponse)
async def get_scheduling_overview(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve the scheduling overview data."""
    service = DataRetrievalService(db)
    data = await service.get_scheduling_overview(session_id)
    if data is None:
        raise HTTPException(
            status_code=404, detail="Scheduling overview data not found."
        )
    return GenericResponse(success=True, data=data)


@router.get("/{session_id}/summary", response_model=GenericResponse)
async def get_scheduling_data_summary(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve the scheduling data summary."""
    service = DataRetrievalService(db)
    data = await service.get_scheduling_data_summary(session_id)
    if data is None:
        raise HTTPException(
            status_code=404, detail="Scheduling data summary not found."
        )
    return GenericResponse(success=True, data=data)
