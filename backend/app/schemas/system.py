# backend/app/schemas/system.py
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel


class SystemConfigCreate(BaseModel):
    config_name: str
    description: str
    is_default: bool
    solver_parameters: Dict[str, Any]
    constraints: List[Dict[str, Any]]
    config_id: Optional[UUID] = None


class ReportGenerateRequest(BaseModel):
    report_type: str
    options: Dict[str, Any]


class AuditLogCreate(BaseModel):
    action: str
    entity_type: str
    entity_id: Optional[UUID] = None
    notes: Optional[str] = None


class GenericResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
