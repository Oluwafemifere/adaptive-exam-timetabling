# scheduling_engine/constraints/soft_constraints/__init__.py

"""
Soft Constraints Module

This module contains all soft constraint implementations for the exam scheduling system.
Soft constraints contribute to the optimization objective but are not strictly required
for solution feasibility.

All constraints inherit from EnhancedBaseConstraint and support database integration.
"""

from .exam_distribution import ExamDistributionConstraint
from .room_utilization import RoomUtilizationConstraint
from .invigilator_balance import InvigilatorBalanceConstraint
from .student_travel import StudentTravelConstraint
from typing import List, Dict, Any

# Export all soft constraint classes
__all__ = [
    "ExamDistributionConstraint",
    "RoomUtilizationConstraint",
    "InvigilatorBalanceConstraint",
    "StudentTravelConstraint",
]

# Constraint registry for dynamic loading
SOFT_CONSTRAINT_REGISTRY = {
    "EXAM_DISTRIBUTION": ExamDistributionConstraint,
    "ROOM_UTILIZATION": RoomUtilizationConstraint,
    "INVIGILATOR_BALANCE": InvigilatorBalanceConstraint,
    "STUDENT_TRAVEL": StudentTravelConstraint,
}


def get_soft_constraint_class(constraint_id: str):
    """
    Get soft constraint class by identifier

    Args:
        constraint_id: Constraint identifier string

    Returns:
        Constraint class or None if not found
    """
    return SOFT_CONSTRAINT_REGISTRY.get(constraint_id.upper())


def get_all_soft_constraint_classes():
    """
    Get all available soft constraint classes

    Returns:
        Dictionary mapping constraint IDs to classes
    """
    return SOFT_CONSTRAINT_REGISTRY.copy()


def create_soft_constraint_instance(constraint_id: str, **kwargs):
    """
    Create instance of soft constraint by identifier

    Args:
        constraint_id: Constraint identifier string
        **kwargs: Additional arguments for constraint initialization

    Returns:
        Constraint instance or None if not found
    """
    constraint_class = get_soft_constraint_class(constraint_id)
    if constraint_class:
        return constraint_class(**kwargs)
    return None


def get_optimization_focused_constraints():
    """
    Get list of constraint codes that are most important for optimization

    Returns:
        List of optimization-focused constraint codes with their priorities
    """
    return [
        ("EXAM_DISTRIBUTION", 1),  # Highest priority - temporal distribution
        ("ROOM_UTILIZATION", 2),  # High priority - resource efficiency
        ("INVIGILATOR_BALANCE", 3),  # Medium priority - workload fairness
        ("STUDENT_TRAVEL", 4),  # Lower priority - convenience
    ]


def validate_soft_constraint_set(constraint_codes: List[str]) -> Dict[str, Any]:
    """
    Validate that a set of soft constraints makes sense for optimization

    Args:
        constraint_codes: List of constraint codes to validate

    Returns:
        Validation result dictionary
    """
    provided = set(code.upper() for code in constraint_codes)
    available = set(SOFT_CONSTRAINT_REGISTRY.keys())

    unknown = provided - available
    missing_important = []

    # Check for important constraints
    important_constraints = ["EXAM_DISTRIBUTION", "ROOM_UTILIZATION"]
    for important in important_constraints:
        if important not in provided:
            missing_important.append(important)

    return {
        "valid": len(unknown) == 0,
        "unknown_constraints": list(unknown),
        "missing_important": missing_important,
        "has_core_optimization": len(missing_important) == 0,
        "constraint_count": len(provided),
        "coverage_score": len(provided) / len(available),
    }


def create_balanced_soft_constraint_set(**weight_overrides) -> List:
    """
    Create a balanced set of soft constraints with appropriate weights

    Args:
        **weight_overrides: Optional weight overrides for specific constraints

    Returns:
        List of constraint instances with balanced weights
    """
    # Default balanced weights
    default_weights = {
        "EXAM_DISTRIBUTION": 0.7,
        "ROOM_UTILIZATION": 0.6,
        "INVIGILATOR_BALANCE": 0.5,
        "STUDENT_TRAVEL": 0.4,
    }

    constraints = []
    for constraint_code, default_weight in default_weights.items():
        weight = weight_overrides.get(constraint_code, default_weight)
        constraint = create_soft_constraint_instance(constraint_code, weight=weight)
        if constraint:
            constraints.append(constraint)

    return constraints
