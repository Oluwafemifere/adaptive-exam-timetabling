# scheduling_engine/core/constraint_types.py

"""
Common constraint types and definitions to break circular imports.
MODIFIED for a fully configurable, HITL-driven constraint system.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Type, Union
from uuid import UUID
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

if TYPE_CHECKING:
    from .problem_model import ExamSchedulingProblem
    from .solution import TimetableSolution


class ConstraintType(Enum):
    HARD = "hard"
    SOFT = "soft"


class ConstraintCategory(Enum):
    CORE = "core"
    STUDENT_CONSTRAINTS = "student_constraints"
    RESOURCE_CONSTRAINTS = "resource_constraints"
    INVIGILATOR_CONSTRAINTS = "invigilator_constraints"
    TEMPORAL_CONSTRAINTS = "temporal_constraints"
    ACADEMIC_POLICIES = "academic_policies"
    OPTIMIZATION_CONSTRAINTS = "optimization_constraints"
    CONVENIENCE_CONSTRAINTS = "convenience_constraints"
    WORKLOAD_BALANCE = "workload_balance"
    OTHER = "other"


class ConstraintSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ConstraintViolation:
    constraint_id: UUID
    violation_id: UUID
    severity: ConstraintSeverity
    affected_exams: List[UUID]
    affected_resources: List[UUID]
    description: str
    penalty: float
    suggestions: List[str] = field(default_factory=list)
    constraint_code: Optional[str] = None
    database_rule_id: Optional[UUID] = None
    constraint_config_id: Optional[UUID] = None  # For observability
    violation_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParameterDefinition:
    """Strongly-typed schema for a single constraint parameter."""

    key: str
    type: str  # e.g., 'int', 'float', 'enum', 'boolean'
    value: Any
    default: Any
    description: Optional[str] = None
    options: Optional[List[Any]] = None
    validation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConstraintDefinition:
    """
    Represents a fully configurable constraint, loaded dynamically from the database.
    This structure is the Python representation of the Constraint DSL.
    """

    id: str  # The unique code for the constraint, e.g., "student-minimum-gap"
    name: str
    description: str
    constraint_type: ConstraintType
    category: ConstraintCategory

    # HITL and Configurability Fields
    enabled: bool = True
    mutability: str = "editable"  # 'read-only', 'editable'
    parameters: List[ParameterDefinition] = field(default_factory=list)
    scope: List[Dict[str, Any]] = field(default_factory=list)

    # Soft Constraint Fields
    weight: float = 1.0

    # Observability and Linkage
    config_id: Optional[UUID] = None  # From constraint_configurations table
    version: Optional[int] = None
    database_rule_id: Optional[UUID] = None  # From constraint_rules table

    # Engine Internals
    constraint_class: Optional[Type] = (
        None  # The Python class that implements the logic
    )

    def get_parameter_value(self, key: str, default: Any = None) -> Any:
        """Helper to safely retrieve a parameter's value by its key."""
        for param in self.parameters:
            if param.key == key:
                return param.value
        return default
