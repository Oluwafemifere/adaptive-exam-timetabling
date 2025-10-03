# scheduling_engine/constraints/hard_constraints/__init__.py

"""
This package contains all hard constraint implementations for the exam timetabling system.
Hard constraints are rules that must be satisfied for a solution to be considered feasible.
"""

from .start_uniqueness import StartUniquenessConstraint
from .occupancy_definition import OccupancyDefinitionConstraint
from .room_assignment_consistency import RoomAssignmentConsistencyConstraint
from .unified_student_conflict import UnifiedStudentConflictConstraint
from .max_exams_per_student_per_day import MaxExamsPerStudentPerDayConstraint


from .room_capacity_hard import RoomCapacityHardConstraint
from .room_continuity import RoomContinuityConstraint
from .start_feasibility import StartFeasibilityConstraint
from .invigilator_single_presence import InvigilatorSinglePresenceConstraint
from .minimum_invigilators import MinimumInvigilatorsConstraint
from .room_sequential_use import RoomSequentialUseConstraint
from .instructor_conflict import InstructorConflictConstraint


__all__ = [
    "StartUniquenessConstraint",
    "OccupancyDefinitionConstraint",
    "RoomAssignmentConsistencyConstraint",
    "UnifiedStudentConflictConstraint",
    "MaxExamsPerStudentPerDayConstraint",
    "RoomCapacityHardConstraint",
    "RoomContinuityConstraint",
    "StartFeasibilityConstraint",
    "InvigilatorSinglePresenceConstraint",
    "MinimumInvigilatorsConstraint",
    "RoomSequentialUseConstraint",
    "InstructorConflictConstraint",
]
