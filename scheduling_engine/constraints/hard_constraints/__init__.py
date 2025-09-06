# scheduling_engine/constraints/hard_constraints/__init__.py

"""
Hard Constraints Module

This module contains all hard constraint implementations for the exam scheduling system.
Hard constraints are mandatory requirements that must be satisfied for a solution
to be considered feasible.

All constraints inherit from EnhancedBaseConstraint and support database integration.
"""

from .no_student_conflict import NoStudentConflictConstraint
from .room_capacity import RoomCapacityConstraint
from .time_availability import TimeAvailabilityConstraint
from .carryover_priority import CarryoverPriorityConstraint
from typing import List, Dict, Any

# Export all hard constraint classes
__all__ = [
    "NoStudentConflictConstraint",
    "RoomCapacityConstraint",
    "TimeAvailabilityConstraint",
    "CarryoverPriorityConstraint",
]

# Constraint registry for dynamic loading
HARD_CONSTRAINT_REGISTRY = {
    "NO_STUDENT_CONFLICT": NoStudentConflictConstraint,
    "ROOM_CAPACITY": RoomCapacityConstraint,
    "TIME_AVAILABILITY": TimeAvailabilityConstraint,
    "CARRYOVER_PRIORITY": CarryoverPriorityConstraint,
}


def get_hard_constraint_class(constraint_id: str):
    """
    Get hard constraint class by identifier

    Args:
        constraint_id: Constraint identifier string

    Returns:
        Constraint class or None if not found
    """
    return HARD_CONSTRAINT_REGISTRY.get(constraint_id.upper())


def get_all_hard_constraint_classes():
    """
    Get all available hard constraint classes

    Returns:
        Dictionary mapping constraint IDs to classes
    """
    return HARD_CONSTRAINT_REGISTRY.copy()


def create_hard_constraint_instance(constraint_id: str, **kwargs):
    """
    Create instance of hard constraint by identifier

    Args:
        constraint_id: Constraint identifier string
        **kwargs: Additional arguments for constraint initialization

    Returns:
        Constraint instance or None if not found
    """
    constraint_class = get_hard_constraint_class(constraint_id)
    if constraint_class:
        return constraint_class(**kwargs)
    return None


def get_essential_hard_constraints():
    """
    Get list of essential hard constraint codes that should always be present

    Returns:
        List of essential constraint codes
    """
    return [
        "NO_STUDENT_CONFLICT",
        "ROOM_CAPACITY",
        "TIME_AVAILABILITY",
    ]


def validate_hard_constraint_set(constraint_codes: List[str]) -> Dict[str, Any]:
    """
    Validate that a set of hard constraints is complete

    Args:
        constraint_codes: List of constraint codes to validate

    Returns:
        Validation result dictionary
    """
    essential = set(get_essential_hard_constraints())
    provided = set(code.upper() for code in constraint_codes)

    missing = essential - provided
    unknown = provided - set(HARD_CONSTRAINT_REGISTRY.keys())

    return {
        "valid": len(missing) == 0 and len(unknown) == 0,
        "missing_essential": list(missing),
        "unknown_constraints": list(unknown),
        "all_constraints_valid": len(unknown) == 0,
        "has_essential_constraints": len(missing) == 0,
    }
