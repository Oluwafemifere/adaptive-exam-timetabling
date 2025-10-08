# backend/app/api/v1/routes/system.py
"""API endpoints for system configuration, auditing, and reports."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from pydantic import BaseModel, Field

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.System.system_service import SystemService
from ....services.data_retrieval.data_retrieval_service import DataRetrievalService
from ....schemas.system import (
    GenericResponse,
    PaginatedAuditLogResponse,
    # --- FIX START ---
    # Replaced SystemConfigRead with the more accurate ConstraintConfigDetailRead schema
    # for the details endpoint to prevent response validation errors.
    ConstraintConfigDetailRead,
    # --- FIX END ---
)

router = APIRouter()

# --- Schemas specific to this route file for clarity ---


class ConstraintConfigRead(BaseModel):
    """Lean schema for listing constraint configuration profiles."""

    id: UUID
    name: str
    description: Optional[str] = None
    is_default: bool


class SystemConfigReadList(BaseModel):
    """Lean schema for listing system configurations."""

    id: UUID
    name: str
    description: Optional[str] = None
    is_default: bool


class ConfigCloneRequest(BaseModel):
    """Schema for cloning a CONSTRAINT configuration."""

    name: str = Field(..., min_length=3)
    description: Optional[str] = None
    source_config_id: UUID


class ConfigRulesUpdate(BaseModel):
    """Schema for updating the rules of a CONSTRAINT configuration."""

    constraints: List[dict]


# --- 1. Endpoints for SYSTEM Configurations (for Scheduling Page) ---


@router.get(
    "/system-configs",
    response_model=List[SystemConfigReadList],
    summary="List All System Configurations",
)
async def list_system_configurations(
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Retrieve a list of all available system configurations. These are the top-level
    profiles used to start a scheduling job (e.g., 'Default System Setup', 'Fast Draft').
    """
    service = SystemService(db)
    configs = await service.get_all_system_configurations()
    return configs or []


# --- 2. Endpoints for CONSTRAINT Configurations (for Constraints Page) ---


@router.get(
    "/constraint-configs",
    response_model=List[ConstraintConfigRead],
    summary="List All Constraint Configuration Profiles",
)
async def list_constraint_configurations(
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Retrieve a list of all available constraint configuration profiles, which contain
    the detailed rule settings (e.g., 'Default', 'Fast Solve', 'High Quality').
    """
    service = SystemService(db)
    configs = await service.get_all_constraint_configurations()
    return configs or []


@router.get(
    "/constraint-configs/{config_id}",
    # --- FIX START ---
    # Changed response_model from SystemConfigRead to ConstraintConfigDetailRead
    # to match the actual data returned by the service layer.
    response_model=ConstraintConfigDetailRead,
    # --- FIX END ---
    summary="Get Constraint Configuration Details",
)
async def get_constraint_configuration_details(
    config_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Get the detailed settings for a single constraint profile, including all its
    rules, parameters, weights, and enabled/disabled status.
    """
    service = SystemService(db)
    config_details = await service.get_constraint_configuration_details(config_id)
    if not config_details:
        raise HTTPException(
            status_code=404, detail="Constraint configuration profile not found."
        )
    return config_details


@router.post(
    "/constraint-configs/clone",
    response_model=ConstraintConfigRead,
    status_code=status.HTTP_201_CREATED,
    summary="Clone a Constraint Configuration Profile",
)
async def clone_constraint_configuration(
    config_in: ConfigCloneRequest,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Create a new constraint profile by cloning an existing one.
    """
    service = SystemService(db)
    result = await service.clone_configuration(
        source_config_id=config_in.source_config_id,
        new_name=config_in.name,
        new_description=config_in.description or "",
        user_id=user.id,
    )
    if not result or not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Failed to clone configuration."),
        )

    # Fetch the newly created config to return its full data
    new_config_id = result["id"]
    # --- FIX START ---
    # Corrected method call from get_configuration_details to get_constraint_configuration_details
    new_config_details = await service.get_constraint_configuration_details(
        new_config_id
    )
    # --- FIX END ---
    if not new_config_details:
        raise HTTPException(
            status_code=404, detail="Could not retrieve newly created configuration."
        )
    return new_config_details


@router.put(
    "/constraint-configs/{config_id}/rules",
    response_model=GenericResponse,
    summary="Update Rules for a Constraint Configuration",
)
async def update_configuration_rules(
    config_id: UUID,
    rules_in: ConfigRulesUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Update multiple rule settings for a constraint profile in a single transaction.
    """
    service = SystemService(db)
    result = await service.update_configuration_rules(
        config_id=config_id,
        rules_payload=rules_in.constraints,
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Failed to update rules.")
        )
    return GenericResponse(
        success=True, message="Configuration rules updated successfully."
    )


@router.post(
    "/constraint-configs/{config_id}/set-default",
    response_model=GenericResponse,
    summary="Set a Constraint Profile as Default",
)
async def set_default_constraint_configuration(
    config_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    service = SystemService(db)
    result = await service.set_default_configuration(config_id=config_id)
    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Failed to set default.")
        )
    return GenericResponse(success=True, message="Default constraint profile updated.")


@router.delete(
    "/constraint-configs/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Constraint Profile",
)
async def delete_constraint_configuration(
    config_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    service = SystemService(db)
    result = await service.delete_configuration(config_id=config_id, user_id=user.id)
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Failed to delete configuration."),
        )
    return None


# --- 3. General System Endpoints ---


@router.get(
    "/audit-history",
    response_model=PaginatedAuditLogResponse,
    summary="Get Audit History",
)
async def get_audit_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    service = DataRetrievalService(db)
    result = await service.get_audit_history(page, page_size, entity_type, entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Audit history not found.")
    return result
