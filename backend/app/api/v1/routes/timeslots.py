# backend/app/api/v1/routes/timeslots.py
"""API endpoints for managing time slots."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_management.core_data_service import CoreDataService
from ....services.data_retrieval.unified_data_retrieval import UnifiedDataService

from sqlalchemy.ext.asyncio import AsyncSession

# Placeholder schemas, these should be defined in a proper schema file
from pydantic import BaseModel
from datetime import time


class TimeSlotBase(BaseModel):
    name: str
    start_time: time
    end_time: time
    is_active: bool = True


class TimeSlotCreate(TimeSlotBase):
    pass


class TimeSlotUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    is_active: Optional[bool] = None


class TimeSlotRead(TimeSlotBase):
    id: UUID


router = APIRouter()


@router.post("/", response_model=TimeSlotRead, status_code=status.HTTP_201_CREATED)
async def create_time_slot(
    timeslot_in: TimeSlotCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Create a new time slot."""
    service = CoreDataService(db)
    result = await service.create_time_slot(timeslot_in.model_dump(), user.id)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to create time slot."),
        )
    data_service = UnifiedDataService(db)
    created_ts = await data_service.get_entity_by_id("time_slot", result["id"])
    return created_ts


@router.get("/", response_model=List[TimeSlotRead])
async def list_time_slots(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve a paginated list of time slots."""
    service = UnifiedDataService(db)
    result = await service.get_paginated_entities(
        "time_slots", page=page, page_size=page_size
    )
    assert result
    return result.get("data", [])


@router.get("/{timeslot_id}", response_model=TimeSlotRead)
async def get_time_slot(
    timeslot_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve a single time slot by its ID."""
    service = UnifiedDataService(db)
    ts = await service.get_entity_by_id("time_slot", timeslot_id)
    if not ts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Time slot not found"
        )
    return ts


@router.put("/{timeslot_id}", response_model=TimeSlotRead)
async def update_time_slot(
    timeslot_id: UUID,
    timeslot_in: TimeSlotUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Update an existing time slot."""
    service = CoreDataService(db)
    result = await service.update_time_slot(
        timeslot_id, timeslot_in.model_dump(exclude_unset=True), user.id
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to update time slot."),
        )
    data_service = UnifiedDataService(db)
    updated_ts = await data_service.get_entity_by_id("time_slot", timeslot_id)
    return updated_ts


@router.delete("/{timeslot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_time_slot(
    timeslot_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete a time slot."""
    service = CoreDataService(db)
    result = await service.delete_time_slot(timeslot_id, user.id)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to delete time slot."),
        )
    return None
