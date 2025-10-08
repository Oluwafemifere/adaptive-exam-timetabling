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


# --- FIX START ---
# Added a more specific schema for the constraint configuration details endpoint.
# This model accurately reflects the data returned by the current database function,
# which includes a 'rules' field (not 'constraints') and lacks the audit timestamps.
class Rule(BaseModel):
    """Defines the structure of a single rule within a constraint configuration."""

    code: str
    name: str
    type: str
    weight: float
    rule_id: UUID
    category: str
    is_enabled: bool
    parameters: Dict[str, Any]
    description: str


class ConstraintConfigDetailRead(BaseModel):
    """
    Detailed schema for a single constraint configuration profile, matching the
    data structure returned from `get_constraint_configuration_details`.
    """

    id: UUID
    name: str
    description: Optional[str] = None
    is_default: bool
    rules: List[Rule]


# --- FIX END ---


class ReportGenerateRequest(BaseModel):
    report_type: str
    options: Dict[str, Any]


class AuditLogRead(BaseModel):
    id: UUID
    action: str
    entity_type: str
    entity_id: Optional[UUID] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    created_at: datetime
    user: Optional[str] = None  # Renamed from user_email to match SQL function

    class Config:
        from_attributes = True


class PaginatedAuditLogResponse(BaseModel):
    total_count: int  # Renamed from total_items to match SQL function
    page: int
    page_size: int
    logs: List[AuditLogRead]  # Renamed from items to match SQL function


class GenericResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any] | List[Any]] = None
    error: Optional[str] = None
