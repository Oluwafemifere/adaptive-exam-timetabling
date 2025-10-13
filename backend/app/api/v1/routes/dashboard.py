# app/api/v1/routes/dashboard.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_retrieval import DataRetrievalService
from ....schemas.dashboard import (
    DashboardAnalytics,
    ConflictHotspot,
    TopBottleneck,
    DashboardKpis,
)

router = APIRouter()


@router.get("/{session_id}/analytics", response_model=DashboardAnalytics)
async def get_dashboard_analytics(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve all dashboard analytics data in a single call."""
    service = DataRetrievalService(db)
    analytics_data = await service.get_dashboard_analytics(session_id)
    if not analytics_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard analytics not found. A timetable may not be generated or published yet.",
        )
    return analytics_data


@router.get("/{session_id}/kpis", response_model=DashboardKpis)
async def get_dashboard_kpis(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve Key Performance Indicators for the dashboard."""
    service = DataRetrievalService(db)
    kpis = await service.get_dashboard_kpis(session_id)
    if not kpis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KPIs not found for this session. A timetable version may not be published yet.",
        )
    return kpis


@router.get("/{session_id}/conflict-hotspots", response_model=List[ConflictHotspot])
async def get_conflict_hotspots(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve the top 5 time slots with the highest conflict density."""
    service = DataRetrievalService(db)
    hotspots = await service.get_conflict_hotspots(session_id)
    if hotspots is None:
        # Return an empty list if no hotspots are found, which is a valid state
        return []
    return hotspots


@router.get("/{session_id}/top-bottlenecks", response_model=List[TopBottleneck])
async def get_top_bottlenecks(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve the top 5 items causing the most scheduling issues."""
    service = DataRetrievalService(db)
    bottlenecks = await service.get_top_bottlenecks(session_id)
    if bottlenecks is None:
        # Return an empty list if no bottlenecks are identified
        return []
    return bottlenecks
