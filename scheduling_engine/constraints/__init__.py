# scheduling_engine/constraints/__init__.py

# Import all hard constraints

from .hard_constraints.invigilator_single_presence import (
    InvigilatorSinglePresenceConstraint,
)
from .hard_constraints.minimum_invigilators import MinimumInvigilatorsConstraint
from .hard_constraints.occupancy_definition import OccupancyDefinitionConstraint
from .hard_constraints.room_assignment_consistency import (
    RoomAssignmentConsistencyConstraint,
)

# from .hard_constraints.room_capacity_hard import RoomCapacityHardConstraint
from .hard_constraints.room_continuity import RoomContinuityConstraint
from .hard_constraints.start_uniqueness import StartUniquenessConstraint
from .hard_constraints.unified_student_conflict import UnifiedStudentConflictConstraint
from .hard_constraints.max_exams_per_student_per_day import (
    MaxExamsPerStudentPerDayConstraint,
)
from .hard_constraints.minimum_gap import MinimumGapConstraint
from .hard_constraints.start_feasibility import StartFeasibilityConstraint

# Register with the global registry so CPSATModelBuilder sees them
from ..core.constraint_registry import ConstraintRegistry
from ..core.constraint_types import (
    ConstraintDefinition,
    ConstraintType,
    ConstraintCategory,
)


# Create a global registry instance that will be shared
GLOBAL_CONSTRAINT_REGISTRY = ConstraintRegistry()

# Hard constraints with appropriate categories - only using imported constraints
hard_constraints = [
    (
        InvigilatorSinglePresenceConstraint,
        ConstraintCategory.INVIGILATOR_CONSTRAINTS,
        "Ensures each invigilator is only present in one location at a time",
    ),
    (
        MinimumInvigilatorsConstraint,
        ConstraintCategory.INVIGILATOR_CONSTRAINTS,
        "Ensures minimum number of invigilators are assigned when an exam is scheduled in a room",
    ),
    (
        OccupancyDefinitionConstraint,
        ConstraintCategory.CORE,
        "Defines occupancy rules for rooms",
    ),
    (
        RoomAssignmentConsistencyConstraint,
        ConstraintCategory.CORE,
        "Ensures room assignment constraints are met",
    ),
    # (
    #     RoomCapacityHardConstraint,
    #     ConstraintCategory.RESOURCE_CONSTRAINTS,
    #     "Ensures room capacity is not exceeded",
    # ),
    (
        RoomContinuityConstraint,
        ConstraintCategory.RESOURCE_CONSTRAINTS,
        "Ensures room continuity for exams",
    ),
    (
        StartUniquenessConstraint,
        ConstraintCategory.CORE,
        "Ensures each exam has a unique start time",
    ),
    (
        UnifiedStudentConflictConstraint,
        ConstraintCategory.STUDENT_CONSTRAINTS,
        "Ensures no student has overlapping exams at the same time slot",
    ),
    (
        MaxExamsPerStudentPerDayConstraint,
        ConstraintCategory.STUDENT_CONSTRAINTS,
        "Limits maximum exams per student per day",
    ),
    (
        MinimumGapConstraint,
        ConstraintCategory.STUDENT_CONSTRAINTS,
        "Ensures minimum gap between student exams",
    ),
    (
        StartFeasibilityConstraint,
        ConstraintCategory.CORE,
        "Ensures exams start in feasible time slots",
    ),
]
# Register all hard constraints in the global registry
for cls, category, description in hard_constraints:
    cat_key = category.name if hasattr(category, "name") else str(category)
    definition = ConstraintDefinition(
        constraint_id=cls.__name__,
        name=cls.__name__.replace("Constraint", "").replace("_", " ").title(),
        description=description
        or f"{cls.__name__.replace('Constraint', '')} constraint",
        constraint_type=ConstraintType.HARD,
        category=category,
        parameters={"category": cat_key, "required": (cat_key == "CORE")},
    )
    GLOBAL_CONSTRAINT_REGISTRY.register_definition(definition)


def get_global_constraint_registry():
    """Get the global constraint registry with all pre-registered constraints."""
    return GLOBAL_CONSTRAINT_REGISTRY


def initialize_problem_registry(problem_registry):
    """
    Initialize a problem's constraint registry with all global constraint definitions.
    This should be called when creating a new ExamSchedulingProblem.
    """
    global_definitions = GLOBAL_CONSTRAINT_REGISTRY.list_definitions()
    for definition in global_definitions:
        problem_registry.register_definition(definition)
    return len(global_definitions)
