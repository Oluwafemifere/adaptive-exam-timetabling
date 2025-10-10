# backend/app/api/v1/routes/configurations.py
"""
API endpoints for managing System Configurations and their underlying
Constraint Configuration profiles.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.configuration_service import ConfigurationService
from ....schemas.system import GenericResponse
from ....schemas.configuration import (
    SystemConfigListItem,
    SystemConfigDetails,
    SystemConfigSave,
)

router = APIRouter()


@router.get(
    "/",
    response_model=List[SystemConfigListItem],
    summary="List All System Configurations",
)
async def list_system_configurations(
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Retrieve a list of all available system configurations. These are the top-level
    profiles used to start a scheduling job (e.g., 'Standard University Policy Profile').
    """
    service = ConfigurationService(db)
    configs = await service.get_system_configuration_list()
    return configs or []


@router.get(
    "/{config_id}",
    response_model=SystemConfigDetails,
    summary="Get System Configuration Details",
)
async def get_system_configuration_details(
    config_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Get the detailed settings for a single system configuration, including all its
    rules, parameters, weights, and enabled/disabled status.
    """
    service = ConfigurationService(db)
    config_details = await service.get_system_configuration_details(config_id)
    if not config_details:
        raise HTTPException(status_code=404, detail="System configuration not found.")
    return config_details


@router.post(
    "/",
    response_model=GenericResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a New System Configuration",
)
async def create_system_configuration(
    config_in: SystemConfigSave,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Create a new system configuration profile from a full JSON payload.
    """
    service = ConfigurationService(db)
    result = await service.save_system_configuration(config_in.model_dump(), user.id)
    return GenericResponse(
        success=True, message="System configuration created successfully.", data=result
    )


@router.put(
    "/{config_id}",
    response_model=GenericResponse,
    summary="Update a System Configuration",
)
async def update_system_configuration(
    config_id: UUID,
    config_in: SystemConfigSave,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Update an existing system configuration profile from a full JSON payload.
    """
    # Ensure the ID in the path matches the ID in the payload
    config_in.id = config_id
    service = ConfigurationService(db)
    result = await service.save_system_configuration(config_in.model_dump(), user.id)
    return GenericResponse(
        success=True, message="System configuration updated successfully.", data=result
    )


@router.post(
    "/{config_id}/set-default",
    response_model=GenericResponse,
    summary="Set a System Configuration as Default",
)
async def set_default_system_configuration(
    config_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    service = ConfigurationService(db)
    await service.set_default_system_configuration(config_id=config_id)
    return GenericResponse(
        success=True, message="Default system configuration updated."
    )


@router.delete(
    "/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a System Configuration",
)
async def delete_system_configuration(
    config_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    service = ConfigurationService(db)
    try:
        await service.delete_system_configuration(config_id=config_id)
    except Exception as e:
        # Catch exceptions raised from the service (e.g., trying to delete the default)
        raise HTTPException(status_code=400, detail=str(e))
    return None
