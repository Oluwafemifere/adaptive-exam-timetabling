# backend/app/api/v1/routes/profile.py
"""
API endpoints for managing user-specific profile data, such as filter presets.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.user_management.user_profile_service import UserProfileService
from ....services.data_retrieval import DataRetrievalService
from ....schemas.profile import FilterPresetCreate, FilterPresetRead
from ....schemas.system import GenericResponse

router = APIRouter()


@router.post(
    "/presets", response_model=GenericResponse, status_code=status.HTTP_201_CREATED
)
async def create_or_update_user_preset(
    preset_in: FilterPresetCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Create a new filter preset or update an existing one for the current user.
    Uniqueness is based on the combination of user, preset name, and preset type.
    """
    service = UserProfileService(db)
    result = await service.create_or_update_preset(
        user_id=user.id,
        preset_name=preset_in.preset_name,
        preset_type=preset_in.preset_type,
        filters=preset_in.filters,
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Failed to save preset.")
        )
    return GenericResponse(
        success=True, message="Preset saved successfully.", data=result.get("preset")
    )


@router.get("/presets", response_model=List[FilterPresetRead])
async def get_user_presets(
    preset_type: Optional[str] = Query(
        None, description="Filter presets by type, e.g., 'timetable_grid'"
    ),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Retrieve all filter presets for the currently authenticated user, optionally
    filtering by a specific preset type.
    """
    service = DataRetrievalService(db)
    presets = await service.get_user_presets(user_id=user.id, preset_type=preset_type)
    return presets if presets else []


@router.delete(
    "/presets/{preset_id}",
    response_model=GenericResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_user_preset(
    preset_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Delete a specific filter preset owned by the current user.
    """
    service = UserProfileService(db)
    result = await service.delete_preset(user_id=user.id, preset_id=preset_id)
    if not result.get("success"):
        raise HTTPException(
            status_code=404,
            detail=result.get("error", "Preset not found or deletion failed."),
        )
    return GenericResponse(success=True, message="Preset deleted successfully.")
