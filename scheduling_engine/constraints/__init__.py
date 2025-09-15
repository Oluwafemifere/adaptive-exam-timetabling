# scheduling_engine/constraints/__init__.py

# Import all hard constraints
from .hard_constraints.back_to_back_prohibition import BackToBackProhibitionConstraint
from .hard_constraints.invigilator_availability import InvigilatorAvailabilityConstraint
from .hard_constraints.invigilator_single_assignment import (
    InvigilatorSingleAssignmentConstraint,
)
from .hard_constraints.max_exams_per_day_per_student import (
    MaxExamsPerDayPerStudentConstraint,
)
from .hard_constraints.minimum_gap_between_exams import MinimumGapBetweenExamsConstraint
from .hard_constraints.minimum_invigilators_assignment import (
    MinimumInvigilatorsAssignmentConstraint,
)
from .hard_constraints.multi_exam_room_capacity import MultiExamRoomCapacityConstraint
from .hard_constraints.no_student_conflicts_same_room import (
    NoStudentConflictsSameRoomConstraint,
)
from .hard_constraints.no_student_temporal_overlap import (
    NoStudentTemporalOverlapConstraint,
)

# Register with the global registry so CPSATModelBuilder sees them
from .constraint_manager import CPSATConstraintManager
from ..core.constraint_registry import ConstraintRegistry
from ..core.constraint_types import (
    ConstraintDefinition,
    ConstraintType,
    ConstraintCategory,
)


# Helper function to create constraint definitions
def create_constraint_definition(cls, constraint_type, category, description=None):
    # Ensure 'parameters' carries the registry category key expected by core registry
    cat_key = category.name if hasattr(category, "name") else str(category)
    return ConstraintDefinition(
        constraint_id=cls.__name__,
        name=cls.__name__.replace("Constraint", "").replace("_", " ").title(),
        description=description
        or f"{cls.__name__.replace('Constraint', '')} constraint",
        constraint_type=constraint_type,
        category=category,
        parameters={"category": cat_key, "required": (cat_key == "CORE")},
    )


# Create a global registry instance that will be shared
GLOBAL_CONSTRAINT_REGISTRY = ConstraintRegistry()

# Hard constraints with appropriate categories
hard_constraints = [
    (
        BackToBackProhibitionConstraint,
        ConstraintCategory.INVIGILATOR_CONSTRAINTS,
        "Prevents invigilators from being responsible for exams in consecutive time slots",
    ),
    (
        InvigilatorAvailabilityConstraint,
        ConstraintCategory.INVIGILATOR_CONSTRAINTS,
        "Ensures invigilators cannot be responsible for an exam and simultaneously assigned to invigilate another exam",
    ),
    (
        InvigilatorSingleAssignmentConstraint,
        ConstraintCategory.INVIGILATOR_CONSTRAINTS,
        "Ensures each invigilator is assigned to at most one exam-room combination at any given time slot",
    ),
    (
        MaxExamsPerDayPerStudentConstraint,
        ConstraintCategory.STUDENT_CONSTRAINTS,
        "Limits the number of exams a student can have in one day",
    ),
    (
        MinimumGapBetweenExamsConstraint,
        ConstraintCategory.TEMPORAL_CONSTRAINTS,
        "Ensures minimum gap between exams for students",
    ),
    (
        MinimumInvigilatorsAssignmentConstraint,
        ConstraintCategory.INVIGILATOR_CONSTRAINTS,
        "Ensures minimum number of invigilators are assigned when an exam is scheduled in a room",
    ),
    (
        MultiExamRoomCapacityConstraint,
        ConstraintCategory.RESOURCE_CONSTRAINTS,
        "Ensures total enrollment of exams assigned to a room doesn't exceed effective capacity",
    ),
    (
        NoStudentConflictsSameRoomConstraint,
        ConstraintCategory.STUDENT_CONSTRAINTS,
        "Prevents student conflicts when multiple exams share the same room",
    ),
    (
        NoStudentTemporalOverlapConstraint,
        ConstraintCategory.STUDENT_CONSTRAINTS,
        "Ensures no student has overlapping exams at the same time slot",
    ),
]

# Register all hard constraints in the global registry
for cls, category, description in hard_constraints:
    definition = create_constraint_definition(
        cls, ConstraintType.HARD, category, description
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
