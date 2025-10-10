# backend/app/schemas/configuration.py
"""Pydantic schemas for System and Constraint Configuration management."""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from uuid import UUID

# --- Schemas for Listing Configurations ---


class SystemConfigListItem(BaseModel):
    """Lean schema for listing system configurations."""

    id: UUID
    name: str
    description: Optional[str] = None
    is_default: bool


class ConstraintConfigListItem(BaseModel):
    """Lean schema for listing constraint configuration profiles."""

    id: UUID
    name: str
    description: Optional[str] = None
    is_default: bool


# --- Schemas for Detailed View and Saving ---


class RuleSetting(BaseModel):
    """Defines the structure of a single configurable rule for saving."""

    rule_id: UUID
    is_enabled: bool
    weight: float = Field(..., ge=0)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class RuleSettingRead(RuleSetting):
    """Detailed rule structure for reading, including descriptive fields."""

    code: str
    name: str
    type: str
    category: str
    description: Optional[str] = None


class SystemConfigDetails(BaseModel):
    """
    Comprehensive schema for viewing and editing a single system configuration.
    This is the primary model for the configuration management UI.
    """

    id: UUID
    name: str
    description: Optional[str] = None
    is_default: bool
    solver_parameters: Dict[str, Any]
    constraint_config_id: UUID
    rules: List[RuleSettingRead]


class SystemConfigSave(BaseModel):
    """
    Schema for creating or updating a system configuration. The frontend sends this
    entire object to the `save_system_configuration` endpoint.
    """

    id: Optional[UUID] = None  # Null when creating, provided when updating
    name: str = Field(..., min_length=3)
    description: Optional[str] = None
    is_default: bool = False
    solver_parameters: Dict[str, Any] = Field(default_factory=dict)
    rules: List[RuleSetting] = Field(default_factory=list)
