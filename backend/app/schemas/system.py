# backend/app/schemas/system.py
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime


class SystemConfigBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_default: bool = False
    solver_parameters: Dict[str, Any] = Field(default_factory=dict)
    constraints: List[Dict[str, Any]] = Field(default_factory=list)


class SystemConfigCreate(SystemConfigBase):
    pass


class SystemConfigUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
    solver_parameters: Optional[Dict[str, Any]] = None
    constraints: Optional[List[Dict[str, Any]]] = None


class SystemConfigConstraintsUpdate(BaseModel):
    constraints: List[Dict[str, Any]]


class SystemConfigRead(SystemConfigBase):
    id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class ReportGenerateRequest(BaseModel):
    report_type: str
    options: Dict[str, Any]


class AuditLogRead(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    action: str
    entity_type: str
    entity_id: Optional[UUID] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    created_at: datetime
    user_email: Optional[str] = None  # Enriched by DB function

    class Config:
        from_attributes = True


class PaginatedAuditLogResponse(BaseModel):
    total_items: int
    total_pages: int
    page: int
    page_size: int
    items: List[AuditLogRead]


class GenericResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any] | List[Any]] = None
    error: Optional[str] = None
