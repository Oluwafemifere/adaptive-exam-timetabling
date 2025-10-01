# backend/app/api/v1/routes/rooms.py
"""API endpoints for managing rooms and venues."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_management.core_data_service import CoreDataService
from ....services.data_retrieval import DataRetrievalService
from sqlalchemy.ext.asyncio import AsyncSession

# Import the new, complete schemas from the correct location
from ....schemas.infrastructure import RoomCreate, RoomRead, RoomUpdate


router = APIRouter()


@router.post("/", response_model=RoomRead, status_code=status.HTTP_201_CREATED)
async def create_room(
    room_in: RoomCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Create a new room/venue."""
    service = CoreDataService(db)
    result = await service.create_room(room_in.model_dump(), user.id)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to create room."),
        )
    data_service = DataRetrievalService(db)
    created_room = await data_service.get_entity_by_id("room", result["id"])
    return created_room


@router.get("/", response_model=List[RoomRead])
async def list_rooms(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve a paginated list of rooms."""
    service = DataRetrievalService(db)
    result = await service.get_paginated_entities(
        "rooms", page=page, page_size=page_size
    )
    assert result
    return result.get("data", [])


@router.get("/{room_id}", response_model=RoomRead)
async def get_room(
    room_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve a single room by its ID."""
    service = DataRetrievalService(db)
    room = await service.get_entity_by_id("room", room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    return room


@router.put("/{room_id}", response_model=RoomRead)
async def update_room(
    room_id: UUID,
    room_in: RoomUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Update an existing room."""
    service = CoreDataService(db)
    result = await service.update_room(
        room_id, room_in.model_dump(exclude_unset=True), user.id
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to update room."),
        )
    data_service = DataRetrievalService(db)
    updated_room = await data_service.get_entity_by_id("room", room_id)
    return updated_room


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete a room."""
    service = CoreDataService(db)
    result = await service.delete_room(room_id, user.id)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to delete room."),
        )
    return None
