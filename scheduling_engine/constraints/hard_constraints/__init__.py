# scheduling_engine/constraints/hard_constraints/__init__.py

"""
This package contains all hard constraint implementations for the exam timetabling system.
Hard constraints are rules that must be satisfied for a solution to be considered feasible.
"""

from .start_uniqueness import StartUniquenessConstraint
from .occupancy_definition import OccupancyDefinitionConstraint
from .room_assignment_consistency import RoomAssignmentConsistencyConstraint
from .unified_student_conflict import UnifiedStudentConflictConstraint


from .room_capacity_hard import RoomCapacityHardConstraint, AggregateCapacityConstraint
from .room_continuity import RoomContinuityConstraint
from .start_feasibility import StartFeasibilityConstraint

# --- MODIFICATION START ---
from .invigilator_single_presence import InvigilatorSinglePresenceConstraint
from .invigilator_requirement import InvigilatorRequirementConstraint
from .invigilator_continuity import InvigilatorContinuityConstraint

# --- MODIFICATION END ---
from .room_sequential_use import RoomSequentialUseConstraint


__all__ = [
    "StartUniquenessConstraint",
    "OccupancyDefinitionConstraint",
    "RoomAssignmentConsistencyConstraint",
    "UnifiedStudentConflictConstraint",
    "RoomCapacityHardConstraint",
    "AggregateCapacityConstraint",
    "RoomContinuityConstraint",
    "StartFeasibilityConstraint",
    "InvigilatorRequirementConstraint",
    "InvigilatorSinglePresenceConstraint",
    "InvigilatorContinuityConstraint",
    "RoomSequentialUseConstraint",
]
