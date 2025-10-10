# backend/app/api/v1/routes/system.py
"""API endpoints for system-level tasks like auditing and reports."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_retrieval.data_retrieval_service import DataRetrievalService
from ....schemas.system import (
    PaginatedAuditLogResponse,
)

router = APIRouter()


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
    """
    Retrieves a paginated and filterable history of all audit log entries.
    """
    service = DataRetrievalService(db)
    result = await service.get_audit_history(page, page_size, entity_type, entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Audit history not found.")
    return result
