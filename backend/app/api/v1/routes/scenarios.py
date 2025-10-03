# app/api/v1/routes/scenarios.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.scheduling import TimetableManagementService
from ....services.data_retrieval import DataRetrievalService
from ....schemas.system import GenericResponse
from ....schemas.versioning import (
    ScenarioCreate,
    ScenarioRead,
    ScenarioComparisonRequest,
)

router = APIRouter()


@router.post("/", response_model=ScenarioRead, status_code=status.HTTP_201_CREATED)
async def create_scenario(
    scenario_in: ScenarioCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Create a new scenario from an existing timetable version."""
    service = TimetableManagementService(db)
    scenario_id = await service.create_scenario_from_version(
        parent_version_id=scenario_in.parent_version_id,
        scenario_name=scenario_in.name,
        scenario_description=scenario_in.description,
        user_id=user.id,
    )
    if not scenario_id:
        raise HTTPException(status_code=400, detail="Failed to create scenario.")

    # Fetch the created scenario to return the full object
    retrieval_service = DataRetrievalService(db)
    new_scenario = await retrieval_service.get_entity_by_id("scenario", scenario_id)
    return new_scenario


@router.get("/", response_model=List[ScenarioRead])
async def list_scenarios(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve a paginated list of all scenarios."""
    service = DataRetrievalService(db)
    result = await service.get_all_scenarios(page, page_size)
    return result.get("items", []) if result else []


@router.delete("/{scenario_id}", response_model=GenericResponse)
async def delete_scenario(
    scenario_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete a scenario."""
    service = TimetableManagementService(db)
    result = await service.delete_scenario(scenario_id, user.id)
    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Failed to delete scenario.")
        )
    return GenericResponse(success=True, message="Scenario deleted successfully.")


@router.post("/compare", response_model=GenericResponse)
async def compare_scenarios(
    request: ScenarioComparisonRequest,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Compare two or more scenarios."""
    service = DataRetrievalService(db)  # compare_scenarios is a retrieval function
    comparison_data = await service.get_scenario_comparison_details(
        request.scenario_ids
    )
    if not comparison_data:
        raise HTTPException(
            status_code=404,
            detail="Could not retrieve comparison data for the given scenarios.",
        )
    return GenericResponse(success=True, data=comparison_data)
