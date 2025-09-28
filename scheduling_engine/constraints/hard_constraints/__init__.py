# scheduling_engine/constraints/hard_constraints/__init__.py

"""
Hard Constraints Package

This package contains all hard constraint implementations for the exam timetabling system.
Hard constraints must be satisfied for a solution to be feasible.

Mathematical Foundation:
Each hard constraint Hi must be satisfied:
Hi = True ∀ i ∈ HardConstraints

Implemented Hard Constraints:
- H1: StartUniquenessConstraint - Each exam starts exactly once
- H2: OccupancyDefinitionConstraint - Occupancy linking (start → occupied slots)
- H3: RoomAssignmentConsistencyConstraint - Room assignment consistent with occupancy
- H5/H10: UnifiedStudentConflictConstraint - Prevents student temporal conflicts
- H6: MaxExamsPerStudentPerDayConstraint - Limits daily student exams
- H7: MinimumGapConstraint - Minimum gap between student exams
- H8: RoomCapacityHardConstraint - Room capacity for non-overbookable rooms
- H9: RoomContinuityConstraint - Multi-room exam room consistency
- H11: StartFeasibilityConstraint - Exam start feasibility within day boundaries
- H12: InvigilatorSinglePresenceConstraint - Invigilator single assignment per timeslot
- MinimumInvigilatorsConstraint - Minimum invigilators per exam-room assignment

Usage:
    from scheduling_engine.constraints.hard_constraints import (
        StartUniquenessConstraint,
        OccupancyDefinitionConstraint,
        RoomAssignmentConsistencyConstraint,
        UnifiedStudentConflictConstraint,
        MaxExamsPerStudentPerDayConstraint,
        MinimumGapConstraint,
        RoomCapacityHardConstraint,
        RoomContinuityConstraint,
        StartFeasibilityConstraint,
        InvigilatorSinglePresenceConstraint,
        MinimumInvigilatorsConstraint
    )
"""

from typing import Optional, Union, Dict, Any

# Import all hard constraint classes
from .start_uniqueness import StartUniquenessConstraint
from .occupancy_definition import OccupancyDefinitionConstraint
from .room_assignment_consistency import RoomAssignmentConsistencyConstraint
from .unified_student_conflict import UnifiedStudentConflictConstraint
from .max_exams_per_student_per_day import MaxExamsPerStudentPerDayConstraint
from .minimum_gap import MinimumGapConstraint
from .room_capacity_hard import RoomCapacityHardConstraint
from .room_continuity import RoomContinuityConstraint
from .start_feasibility import StartFeasibilityConstraint
from .invigilator_single_presence import InvigilatorSinglePresenceConstraint
from .minimum_invigilators import MinimumInvigilatorsConstraint

# Define package exports
__all__ = [
    "StartUniquenessConstraint",  # H1
    "OccupancyDefinitionConstraint",  # H2
    "RoomAssignmentConsistencyConstraint",  # H3
    "UnifiedStudentConflictConstraint",  # H5/H10
    "MaxExamsPerStudentPerDayConstraint",  # H6
    "MinimumGapConstraint",  # H7
    "RoomCapacityHardConstraint",  # H8
    "RoomContinuityConstraint",  # H9
    "StartFeasibilityConstraint",  # H11
    "InvigilatorSinglePresenceConstraint",  # H12
    "MinimumInvigilatorsConstraint",  # Additional invigilator constraint
]

# Hard constraint metadata for registration and management
HARD_CONSTRAINT_REGISTRY = {
    "StartUniquenessConstraint": {
        "class": StartUniquenessConstraint,
        "category": "CORE",
        "description": "Ensures each exam starts exactly once",
        "equation_ref": "H1",
        "dependencies": [],
        "is_critical": True,
    },
    "OccupancyDefinitionConstraint": {
        "class": OccupancyDefinitionConstraint,
        "category": "CORE",
        "description": "Links exam start to occupied slots using StartCovers logic",
        "equation_ref": "H2",
        "dependencies": ["StartUniquenessConstraint"],
        "is_critical": True,
    },
    "RoomAssignmentConsistencyConstraint": {
        "class": RoomAssignmentConsistencyConstraint,
        "category": "CORE",
        "description": "Ensures room assignments are consistent with occupancy",
        "equation_ref": "H3",
        "dependencies": ["OccupancyDefinitionConstraint"],
        "is_critical": True,
    },
    "UnifiedStudentConflictConstraint": {
        "class": UnifiedStudentConflictConstraint,
        "category": "STUDENT_CONSTRAINTS",
        "description": "Prevents students from having multiple exams in the same timeslot",
        "equation_ref": "H5/H10",
        "dependencies": ["OccupancyDefinitionConstraint"],
        "is_critical": True,
    },
    "MaxExamsPerStudentPerDayConstraint": {
        "class": MaxExamsPerStudentPerDayConstraint,
        "category": "STUDENT_CONSTRAINTS",
        "description": "Limits the number of exams a student can have on the same day",
        "equation_ref": "H6",
        "dependencies": ["StartUniquenessConstraint"],
        "is_critical": True,
    },
    "MinimumGapConstraint": {
        "class": MinimumGapConstraint,
        "category": "STUDENT_CONSTRAINTS",
        "description": "Ensures minimum gap between consecutive exams for students",
        "equation_ref": "H7",
        "dependencies": ["UnifiedStudentConflictConstraint"],
        "is_critical": True,
    },
    "RoomCapacityHardConstraint": {
        "class": RoomCapacityHardConstraint,
        "category": "RESOURCE_CONSTRAINTS",
        "description": "Enforces room capacity limits for non-overbookable rooms",
        "equation_ref": "H8",
        "dependencies": ["RoomAssignmentConsistencyConstraint"],
        "is_critical": True,
    },
    "RoomContinuityConstraint": {
        "class": RoomContinuityConstraint,
        "category": "RESOURCE_CONSTRAINTS",
        "description": "Ensures multi-slot exams use the same room throughout",
        "equation_ref": "H9",
        "dependencies": ["NoStudentConflictsSameRoomConstraint"],
        "is_critical": True,
    },
    "StartFeasibilityConstraint": {
        "class": StartFeasibilityConstraint,
        "category": "CORE",
        "description": "Ensures exams can only start at feasible slots within day boundaries",
        "equation_ref": "H11",
        "dependencies": [],
        "is_critical": True,
    },
    "InvigilatorSinglePresenceConstraint": {
        "class": InvigilatorSinglePresenceConstraint,
        "category": "INVIGILATOR_CONSTRAINTS",
        "description": "Ensures invigilators are assigned to at most one room per time slot",
        "equation_ref": "H12",
        "dependencies": ["MinimumInvigilatorsConstraint"],
        "is_critical": True,
    },
    "MinimumInvigilatorsConstraint": {
        "class": MinimumInvigilatorsConstraint,
        "category": "INVIGILATOR_CONSTRAINTS",
        "description": "Ensures sufficient invigilators are assigned to each exam",
        "equation_ref": "Additional",
        "dependencies": ["MaxExamsPerDayConstraint"],
        "is_critical": True,
    },
}


def get_all_hard_constraints():
    """Get all available hard constraint classes"""
    return [info["class"] for info in HARD_CONSTRAINT_REGISTRY.values()]


def get_hard_constraint_by_name(name: str):
    """Get a hard constraint class by name"""
    if name in HARD_CONSTRAINT_REGISTRY:
        return HARD_CONSTRAINT_REGISTRY[name]["class"]
    return None


def get_hard_constraint_metadata(
    name: Optional[str] = None,
) -> Union[Dict[str, Any], Dict[str, Dict[str, Any]], None]:
    """Get metadata for hard constraints"""
    if name is not None:
        return HARD_CONSTRAINT_REGISTRY.get(name)
    return HARD_CONSTRAINT_REGISTRY


def register_all_hard_constraints(constraint_manager):
    """Register all hard constraints with the constraint manager"""
    for name, info in HARD_CONSTRAINT_REGISTRY.items():
        category = str(info["category"])  # Ensure we're passing a string
        constraint_manager.register_module(info["class"], category)
    return len(HARD_CONSTRAINT_REGISTRY)


# Criticality flags for constraint validation
CRITICAL_CONSTRAINTS = {
    constraint_name: info["is_critical"]
    for constraint_name, info in HARD_CONSTRAINT_REGISTRY.items()
}


def is_constraint_critical(constraint_name: str) -> bool:
    """Check if a constraint is critical for feasibility"""
    return CRITICAL_CONSTRAINTS.get(constraint_name, False)
