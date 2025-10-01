# backend/app/api/v1/routes/system.py
"""API endpoints for system configuration, auditing, and reports."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.System.system_service import SystemService
from ....services.auditing.audit_service import AuditService
from ....services.data_retrieval.data_retrieval_service import DataRetrievalService
from ....schemas.system import (
    SystemConfigCreate,
    ReportGenerateRequest,
    AuditLogCreate,
    GenericResponse,
)

router = APIRouter()


@router.post("/configs", response_model=GenericResponse)
async def save_system_configuration(
    config_in: SystemConfigCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Create or update a system configuration."""
    service = SystemService(db)
    result = await service.save_system_configuration(
        user_id=user.id, **config_in.model_dump()
    )
    if not result.get("success", True):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Failed to save configuration")
        )
    return GenericResponse(success=True, data=result)


@router.post("/reports/{session_id}", response_model=GenericResponse)
async def generate_system_report(
    session_id: UUID,
    report_in: ReportGenerateRequest,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Generate a system report."""
    service = SystemService(db)
    result = await service.generate_report(
        report_type=report_in.report_type,
        session_id=session_id,
        options=report_in.options,
    )
    return GenericResponse(success=True, data=result)


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


@router.post("/audit", status_code=status.HTTP_201_CREATED)
async def log_audit_event(
    audit_in: AuditLogCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Manually log an audit event (e.g., from the frontend)."""
    service = AuditService(db)
    success = await service.log(
        user_id=user.id,
        action=audit_in.action,
        entity_type=audit_in.entity_type,
        entity_id=audit_in.entity_id,
        notes=audit_in.notes,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to log audit event")
    return {"detail": "Audit event logged successfully"}


# --- NEWLY ADDED ROUTE ---


@router.get("/configs/default", response_model=GenericResponse)
async def get_default_config(
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Retrieve the ID of the default system configuration.
    Uses the `get_default_system_configuration` service method.
    """
    service = DataRetrievalService(db)
    config_id = await service.get_default_system_configuration()
    if not config_id:
        raise HTTPException(
            status_code=404, detail="No default system configuration found."
        )
    return GenericResponse(success=True, data={"config_id": config_id})
