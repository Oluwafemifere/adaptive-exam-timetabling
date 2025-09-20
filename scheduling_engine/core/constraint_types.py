# scheduling_engine/core/constraint_types.py

"""
Common constraint types and definitions to break circular imports.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Type
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
    violation_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConstraintDefinition:
    constraint_id: str
    name: str
    description: str
    constraint_type: ConstraintType
    category: ConstraintCategory
    parameters: Dict[str, Any] = field(default_factory=dict)
    validation_rules: List[str] = field(default_factory=list)
    constraint_class: Optional[Type] = None
    database_rule_id: Optional[UUID] = None
    is_database_loaded: bool = False
    default_weight: float = 1.0
    is_configurable: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
