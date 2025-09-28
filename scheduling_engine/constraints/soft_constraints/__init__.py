# scheduling_engine/constraints/soft_constraints/__init__.py

"""
Soft Constraints Package

This package contains all soft constraint implementations for the exam timetabling system.
Soft constraints allow penalty-based optimization rather than hard feasibility requirements.

Mathematical Foundation:
Each soft constraint Si contributes penalty terms to the objective function:
Minimize: ∑(Wi × penalty_termsi) where Wi is the penalty weight for constraint Si

Implemented Soft Constraints:
- S1: OverbookingPenaltyConstraint (W=1000) - Room overbooking penalties
- S2: PreferenceSlotsConstraint (W=500) - Exam preference violations
- S3: StudentGapPenaltyConstraint (W=2000) - Student gap violations
- S4: InvigilatorLoadBalanceConstraint (W=300) - Invigilator workload imbalance
- S5: RoomContinuityConstraint (W=800) - Multi-room exam penalties
- S6: InvigilatorAvailabilityConstraint (W=1500) - Unavailable invigilator assignments
- S7: DailyWorkloadBalanceConstraint (W=200) - Daily exam distribution imbalance
- S8: UnusedSeatsConstraint (W=50) - Room underutilization penalties

Usage:
    from scheduling_engine.constraints.soft_constraints import (
        OverbookingPenaltyConstraint,
        PreferenceSlotsConstraint,
        StudentGapPenaltyConstraint,
        InvigilatorLoadBalanceConstraint,
        RoomContinuityConstraint,
        InvigilatorAvailabilityConstraint,
        DailyWorkloadBalanceConstraint,
        UnusedSeatsConstraint
    )
"""
from typing import Optional, Union, Dict, Any

# Import all soft constraint classes
from .overbooking_penalty import OverbookingPenaltyConstraint
from .preference_slots import PreferenceSlotsConstraint
from .student_gap_penalty import StudentGapPenaltyConstraint
from .invigilator_load_balance import InvigilatorLoadBalanceConstraint
from .invigilator_availability import InvigilatorAvailabilityConstraint
from .daily_workload_balance import DailyWorkloadBalanceConstraint
from .unused_seats import UnusedSeatsConstraint

# Define package exports
__all__ = [
    "OverbookingPenaltyConstraint",  # S1 - W=1000
    "PreferenceSlotsConstraint",  # S2 - W=500
    "StudentGapPenaltyConstraint",  # S3 - W=2000
    "InvigilatorLoadBalanceConstraint",  # S4 - W=300
    "InvigilatorAvailabilityConstraint",  # S6 - W=1500
    "DailyWorkloadBalanceConstraint",  # S7 - W=200
    "UnusedSeatsConstraint",  # S8 - W=50
]

# Soft constraint metadata for registration and management
SOFT_CONSTRAINT_REGISTRY = {
    "OverbookingPenaltyConstraint": {
        "class": OverbookingPenaltyConstraint,
        "weight": 1000,
        "category": "SOFT_CONSTRAINTS",
        "description": "Penalizes room overbooking beyond allowed limits",
        "equation_ref": "S1",
        "dependencies": [],
    },
    "PreferenceSlotsConstraint": {
        "class": PreferenceSlotsConstraint,
        "weight": 500,
        "category": "SOFT_CONSTRAINTS",
        "description": "Penalizes scheduling exams outside preferred time slots",
        "equation_ref": "S2",
        "dependencies": [],
    },
    "StudentGapPenaltyConstraint": {
        "class": StudentGapPenaltyConstraint,
        "weight": 2000,
        "category": "SOFT_CONSTRAINTS",
        "description": "Penalizes undesired gaps between student exams on same day",
        "equation_ref": "S3",
        "dependencies": ["UnifiedStudentConflictConstraint"],
    },
    "InvigilatorLoadBalanceConstraint": {
        "class": InvigilatorLoadBalanceConstraint,
        "weight": 300,
        "category": "SOFT_CONSTRAINTS",
        "description": "Penalizes imbalanced workload distribution among invigilators",
        "equation_ref": "S4",
        "dependencies": ["InvigilatorSingleAssignmentConstraint"],
    },
    "InvigilatorAvailabilityConstraint": {
        "class": InvigilatorAvailabilityConstraint,
        "weight": 1500,
        "category": "SOFT_CONSTRAINTS",
        "description": "Penalizes assigning invigilators when they are unavailable",
        "equation_ref": "S6",
        "dependencies": ["InvigilatorSingleAssignmentConstraint"],
    },
    "DailyWorkloadBalanceConstraint": {
        "class": DailyWorkloadBalanceConstraint,
        "weight": 200,
        "category": "SOFT_CONSTRAINTS",
        "description": "Penalizes deviations from ideal daily exam distribution",
        "equation_ref": "S7",
        "dependencies": ["StartUniquenessConstraint"],
    },
    "UnusedSeatsConstraint": {
        "class": UnusedSeatsConstraint,
        "weight": 50,
        "category": "SOFT_CONSTRAINTS",
        "description": "Penalizes underutilization of room capacity",
        "equation_ref": "S8",
        "dependencies": ["RoomAssignmentBasicConstraint"],
    },
}


def get_all_soft_constraints():
    """Get all available soft constraint classes"""
    return [info["class"] for info in SOFT_CONSTRAINT_REGISTRY.values()]


def get_soft_constraint_by_name(name: str):
    """Get a soft constraint class by name"""
    if name in SOFT_CONSTRAINT_REGISTRY:
        return SOFT_CONSTRAINT_REGISTRY[name]["class"]
    return None


def get_soft_constraint_metadata(
    name: Optional[str] = None,
) -> Union[Dict[str, Any], Dict[str, Dict[str, Any]], None]:
    """Get metadata for soft constraints"""
    if name is not None:
        return SOFT_CONSTRAINT_REGISTRY.get(name)
    return SOFT_CONSTRAINT_REGISTRY


def register_all_soft_constraints(constraint_manager):
    """Register all soft constraints with the constraint manager"""
    for name, info in SOFT_CONSTRAINT_REGISTRY.items():
        category = str(info["category"])  # Ensure we're passing a string
        constraint_manager.register_module(info["class"], category)
    return len(SOFT_CONSTRAINT_REGISTRY)


# Priority weights for objective function (highest to lowest priority)
PENALTY_WEIGHTS = {
    "StudentGapPenaltyConstraint": 2000,  # Highest - student experience
    "InvigilatorAvailabilityConstraint": 1500,  # High - staff constraints
    "OverbookingPenaltyConstraint": 1000,  # High - capacity limits
    "RoomContinuityConstraint": 800,  # Medium-high - exam integrity
    "PreferenceSlotsConstraint": 500,  # Medium - preferences
    "InvigilatorLoadBalanceConstraint": 300,  # Medium - workload fairness
    "DailyWorkloadBalanceConstraint": 200,  # Low-medium - distribution
    "UnusedSeatsConstraint": 50,  # Low - optimization
}


def get_penalty_weight(constraint_name: str) -> int:
    """Get the penalty weight for a constraint"""
    return PENALTY_WEIGHTS.get(constraint_name, 0)
