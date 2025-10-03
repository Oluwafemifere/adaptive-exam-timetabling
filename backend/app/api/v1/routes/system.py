# backend/app/api/v1/routes/system.py
"""API endpoints for system configuration, auditing, and reports."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
import io
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.System.system_service import SystemService
from ....services.auditing.audit_service import AuditService
from ....services.export.reporting_service import ReportingService
from ....services.data_retrieval.data_retrieval_service import DataRetrievalService
from ....schemas.system import (
    SystemConfigCreate,
    SystemConfigRead,
    SystemConfigUpdate,
    SystemConfigConstraintsUpdate,
    ReportGenerateRequest,
    GenericResponse,
    PaginatedAuditLogResponse,
)

router = APIRouter()


# -- Configuration --
@router.post(
    "/configs", response_model=SystemConfigRead, status_code=status.HTTP_201_CREATED
)
async def create_system_configuration(
    config_in: SystemConfigCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Create a new system configuration."""
    service = SystemService(db)
    result = await service.save_system_configuration(
        user_id=user.id, **config_in.model_dump()
    )
    if not result or not result.get("id"):
        raise HTTPException(status_code=400, detail="Failed to save configuration.")
    return result


@router.put("/configs/{config_id}", response_model=SystemConfigRead)
async def update_system_configuration(
    config_id: UUID,
    config_in: SystemConfigUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Update an existing system configuration."""
    service = SystemService(db)
    result = await service.save_system_configuration(
        config_id=config_id, user_id=user.id, **config_in.model_dump(exclude_unset=True)
    )
    if not result or not result.get("id"):
        raise HTTPException(
            status_code=404, detail="Configuration not found or update failed."
        )
    return result


@router.put("/configs/{config_id}/constraints", response_model=GenericResponse)
async def update_configuration_constraints(
    config_id: UUID,
    constraints_in: SystemConfigConstraintsUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Update only the constraints for a specific system configuration."""
    service = SystemService(db)
    result = await service.update_system_configuration_constraints(
        config_id=config_id,
        user_id=user.id,
        constraints_payload=constraints_in.constraints,
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Failed to update constraints.")
        )
    return GenericResponse(
        success=True,
        message="Constraints updated successfully.",
        data=result.get("data"),
    )


@router.get("/configs", response_model=List[SystemConfigRead])
async def list_system_configurations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """List all system configurations."""
    service = DataRetrievalService(db)
    result = await service.get_paginated_entities(
        "system_configurations", page, page_size
    )
    return result.get("data", []) if result else []


@router.get("/configs/{config_id}", response_model=SystemConfigRead)
async def get_system_configuration_details(
    config_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Get details for a specific system configuration."""
    service = DataRetrievalService(db)
    config = await service.get_system_configuration_details(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found.")
    return config


# -- Auditing --
@router.get("/audit-history", response_model=PaginatedAuditLogResponse)
async def get_audit_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve paginated audit history."""
    service = DataRetrievalService(db)
    result = await service.get_audit_history(page, page_size, entity_type, entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Audit history not found.")
    return result


# -- Reports & Dashboard --
@router.post("/reports/{session_id}")
async def generate_system_report(
    session_id: UUID,
    report_in: ReportGenerateRequest,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Generate a system report and return as file download."""
    service = ReportingService(db)
    report_bytes = await service.generate_system_report(
        report_type=report_in.report_type,
        session_id=session_id,
        options=report_in.options,
    )

    if not report_bytes:
        raise HTTPException(status_code=404, detail="Report generation failed")

    filename = f"{report_in.report_type}_{session_id}.pdf"
    return StreamingResponse(
        io.BytesIO(report_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/dashboard/{session_id}", response_model=GenericResponse)
async def get_dashboard_kpis(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve Key Performance Indicators for the dashboard."""
    service = DataRetrievalService(db)
    result = await service.get_dashboard_kpis(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="KPIs not found for this session")
    return GenericResponse(success=True, data=result)


@router.get("/configs/default", response_model=GenericResponse)
async def get_default_config(
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve the ID of the default system configuration."""
    service = DataRetrievalService(db)
    config_id = await service.get_default_system_configuration()
    if not config_id:
        raise HTTPException(
            status_code=404, detail="No default system configuration found."
        )
    return GenericResponse(success=True, data={"config_id": config_id})
