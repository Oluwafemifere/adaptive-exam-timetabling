# scheduling_engine/core/constraint_registry.py

"""
FIXED Constraint Registry - Enhanced Logging and Proper Category Activation

Key Fixes:
- Load definitions exactly once into GLOBAL_CONSTRAINT_DEFINITIONS
- Share category‐to‐IDs mapping in GLOBAL_CATEGORY_CONSTRAINTS
- Simplify __init__ to reuse globals
"""

import logging
from typing import Dict, List, Set, Optional, Any, TYPE_CHECKING
from .constraint_types import ConstraintDefinition, ConstraintType, ConstraintCategory

if TYPE_CHECKING:
    from .problem_model import ExamSchedulingProblem

logger = logging.getLogger(__name__)


def _load_all_definitions() -> (
    tuple[Dict[str, ConstraintDefinition], Dict[str, List[str]]]
):
    """Collect all constraint definitions and category mappings once."""
    definitions: Dict[str, ConstraintDefinition] = {}
    category_map: Dict[str, List[str]] = {}

    def register_group(cat_key: str, items: List[tuple], cat_enum: ConstraintCategory):
        ids = []
        for cid, name, desc in items:
            definition = ConstraintDefinition(
                constraint_id=cid,
                name=name,
                description=desc,
                constraint_type=ConstraintType.HARD,
                category=cat_enum,
                parameters={"category": cat_key, "required": (cat_key == "CORE")},
            )
            definitions[cid] = definition
            ids.append(cid)
        category_map[cat_key] = ids

    # CORE C1–C3
    register_group(
        "CORE",
        [
            (
                "StartUniquenessConstraint",
                "C1: Start Uniqueness",
                "Ensures each exam starts exactly once",
            ),
            (
                "OccupancyDefinitionConstraint",
                "C2: Occupancy Definition",
                "Links occupancy to start variables",
            ),
            (
                "RoomAssignmentBasicConstraint",
                "C3: Room Assignment Basic",
                "Enforces room sum equals occupancy",
            ),
        ],
        ConstraintCategory.RESOURCE_CONSTRAINTS,
    )

    # MULTI_EXAM_CAPACITY C4–C5
    register_group(
        "MULTI_EXAM_CAPACITY",
        [
            (
                "MultiExamRoomCapacityConstraint",
                "C4: Multi-Exam Room Capacity",
                "Total enrollment ≤ effective capacity",
            ),
            (
                "NoStudentConflictsSameRoomConstraint",
                "C5: No Student Conflicts Same Room",
                "Prevents students in same room at same time",
            ),
        ],
        ConstraintCategory.RESOURCE_CONSTRAINTS,
    )

    # STUDENT_CONFLICT C7–C9
    register_group(
        "STUDENT_CONFLICT",
        [
            (
                "NoStudentTemporalOverlapConstraint",
                "C7: No Temporal Overlap",
                "Prevents simultaneous exams",
            ),
            (
                "MinimumGapBetweenExamsConstraint",
                "C8: Minimum Gap",
                "Enforces gap between exams",
            ),
            (
                "MaxExamsPerDayPerStudentConstraint",
                "C9: Max Exams Per Day",
                "Limits exams per day",
            ),
        ],
        ConstraintCategory.STUDENT_CONSTRAINTS,
    )

    # INVIGILATOR C10–C13
    register_group(
        "INVIGILATOR",
        [
            (
                "MinimumInvigilatorsAssignmentConstraint",
                "C10: Minimum Invigilators",
                "Min invigilators per exam-room",
            ),
            (
                "InvigilatorSingleAssignmentConstraint",
                "C11: Single Assignment",
                "AtMostOne per invigilator/time",
            ),
            (
                "InvigilatorAvailabilityConstraint",
                "C12: Availability",
                "Invigilator responsibility + assignments ≤1",
            ),
            (
                "BackToBackProhibitionConstraint",
                "C13: Back-to-Back Prohibition",
                "No consecutive responsibilities",
            ),
        ],
        ConstraintCategory.INVIGILATOR_CONSTRAINTS,
    )

    logger.info(f"Loaded {len(definitions)} constraint definitions")
    return definitions, category_map


# Initialize globals once
GLOBAL_CONSTRAINT_DEFINITIONS, GLOBAL_CATEGORY_CONSTRAINTS = _load_all_definitions()


class ConstraintRegistry:
    """
    FIXED Registry for constraint definitions with enhanced logging and validation.
    """

    def __init__(self):
        # Copy the preloaded definitions and categories
        self._definitions: Dict[str, ConstraintDefinition] = (
            GLOBAL_CONSTRAINT_DEFINITIONS.copy()
        )
        self._active_constraints: Set[str] = set()
        self._category_constraints: Dict[str, List[str]] = GLOBAL_CATEGORY_CONSTRAINTS

    def register_definition(self, definition: ConstraintDefinition):
        """Register a constraint definition (not normally used)."""
        self._definitions[definition.constraint_id] = definition
        logger.debug(f"Registered constraint definition: {definition.constraint_id}")

    def activate(self, constraint_id: str):
        """Activate a constraint by its ID with detailed logging."""
        if constraint_id in self._definitions:
            self._active_constraints.add(constraint_id)
            logger.info(f"✓ ACTIVATED constraint: {constraint_id}")
        else:
            logger.warning(f"✗ Cannot activate unknown constraint: {constraint_id}")

    def deactivate(self, constraint_id: str):
        """Deactivate a constraint by its ID."""
        if constraint_id in self._active_constraints:
            self._active_constraints.remove(constraint_id)
            logger.info(f"✗ DEACTIVATED constraint: {constraint_id}")

    def get_active_constraints(self) -> Set[str]:
        """Get set of active constraint IDs."""
        return set(self._active_constraints)

    def _activate_category(self, category: str):
        """Activate all constraints in a category."""
        if category not in self._category_constraints:
            logger.error(f"❌ Unknown category: {category}")
            return
        for cid in self._category_constraints[category]:
            self.activate(cid)
        logger.info(f"✅ Category '{category}' activation complete")

    def configure_minimal(self):
        """CORE only."""
        logger.info("🚀 Starting MINIMAL configuration...")
        self._active_constraints.clear()
        self._activate_category("CORE")
        logger.info("✅ MINIMAL setup complete")

    def configure_standard(self):
        """CORE + MULTI_EXAM_CAPACITY."""
        logger.info("🚀 Starting STANDARD configuration...")
        self._active_constraints.clear()
        self._activate_category("CORE")
        self._activate_category("MULTI_EXAM_CAPACITY")
        logger.info("✅ STANDARD setup complete")

    def configure_with_student_conflicts(self):
        """STANDARD + STUDENT_CONFLICT."""
        logger.info("🚀 Starting STUDENT_CONFLICTS configuration...")
        self.configure_standard()
        self._activate_category("STUDENT_CONFLICT")
        logger.info("✅ STUDENT_CONFLICTS setup complete")

    def configure_complete(self):
        """All constraints."""
        logger.info("🚀 Starting COMPLETE configuration...")
        self.configure_with_student_conflicts()
        self._activate_category("INVIGILATOR")
        logger.info("✅ COMPLETE setup complete")

    def list_definitions(self) -> List[ConstraintDefinition]:
        """List all registered constraint definitions."""
        return list(self._definitions.values())

    def get_active_constraint_classes(self) -> Dict[str, Dict[str, Any]]:
        """
        Dynamically import and return active constraint classes and their categories.
        """
        import importlib

        active = {}
        module_map = {
            "StartUniquenessConstraint": "scheduling_engine.constraints.hard_constraints.start_uniqueness",
            "OccupancyDefinitionConstraint": "scheduling_engine.constraints.hard_constraints.occupancy_definition",
            "RoomAssignmentBasicConstraint": "scheduling_engine.constraints.hard_constraints.room_assignment_basic",
            "MultiExamRoomCapacityConstraint": "scheduling_engine.constraints.hard_constraints.multi_exam_room_capacity",
            "NoStudentConflictsSameRoomConstraint": "scheduling_engine.constraints.hard_constraints.no_student_conflicts_same_room",
            "NoStudentTemporalOverlapConstraint": "scheduling_engine.constraints.hard_constraints.no_student_temporal_overlap",
            "MinimumGapBetweenExamsConstraint": "scheduling_engine.constraints.hard_constraints.minimum_gap_between_exams",
            "MaxExamsPerDayPerStudentConstraint": "scheduling_engine.constraints.hard_constraints.max_exams_per_day_per_student",
            "MinimumInvigilatorsAssignmentConstraint": "scheduling_engine.constraints.hard_constraints.minimum_invigilators_assignment",
            "InvigilatorSingleAssignmentConstraint": "scheduling_engine.constraints.hard_constraints.invigilator_single_assignment",
            "InvigilatorAvailabilityConstraint": "scheduling_engine.constraints.hard_constraints.invigilator_availability",
            "BackToBackProhibitionConstraint": "scheduling_engine.constraints.hard_constraints.back_to_back_prohibition",
        }
        for cid in self._active_constraints:
            definition = self._definitions[cid]
            module_path = module_map.get(cid)
            if not module_path:
                logger.error(f"No module mapping for {cid}")
                continue
            try:
                mod = importlib.import_module(module_path)
                cls = getattr(mod, cid)
                # Fallback to Enum category if parameters["category"] is missing
                cat_key = None
                params = getattr(definition, "parameters", None)
                if isinstance(params, dict):
                    cat_key = params.get("category")
                if (
                    not cat_key
                    and hasattr(definition, "category")
                    and definition.category
                ):
                    # Map Enum to expected key
                    cat_key = (
                        definition.category.name
                    )  # e.g., "CORE", "STUDENT_CONFLICT"
                if not cat_key:
                    cat_key = "UNKNOWN"
                active[cid] = {"class": cls, "category": cat_key}
            except Exception as e:
                logger.error(f"Failed to load {cid}: {e}")
        return active

    def get_definition(self, constraint_id: str) -> Optional[ConstraintDefinition]:
        """
        Get a specific constraint definition by ID.
        Added for completeness and consistency.
        """
        return self._definitions.get(constraint_id)

    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get summary of current configuration with constraint mapping."""
        active_constraints = self.get_active_constraints()

        # Group by category
        active_by_category = {}
        constraint_mapping = {}

        for constraint_id in active_constraints:
            definition = self._definitions.get(constraint_id)
            if definition:
                category = definition.parameters.get("category", "UNKNOWN")
                if category not in active_by_category:
                    active_by_category[category] = []
                active_by_category[category].append(constraint_id)

                # Map to mathematical constraints
                mapping = {
                    "StartUniquenessConstraint": "C1",
                    "OccupancyDefinitionConstraint": "C2",
                    "RoomAssignmentBasicConstraint": "C3",
                    "MultiExamRoomCapacityConstraint": "C4",
                    "NoStudentConflictsSameRoomConstraint": "C5",
                    "NoStudentTemporalOverlapConstraint": "C7",
                    "MinimumGapBetweenExamsConstraint": "C8",
                    "MaxExamsPerDayPerStudentConstraint": "C9",
                    "MinimumInvigilatorsAssignmentConstraint": "C10",
                    "InvigilatorSingleAssignmentConstraint": "C11",
                    "InvigilatorAvailabilityConstraint": "C12",
                    "BackToBackProhibitionConstraint": "C13",
                }

                constraint_mapping[constraint_id] = mapping.get(
                    constraint_id, "Unknown"
                )

        return {
            "total_registered": len(self._definitions),
            "total_active": len(active_constraints),
            "active_categories": list(active_by_category.keys()),
            "active_by_category": active_by_category,
            "constraint_mapping": constraint_mapping,
            "available_categories": list(self._category_constraints.keys()),
            "note": "C6 (Allowed Rooms) handled as domain restriction during variable creation",
        }


def create_optimized_constraint_system(
    configuration: str = "standard",
) -> ConstraintRegistry:
    """Factory function to create a configured constraint system."""
    registry = ConstraintRegistry()

    if configuration == "minimal":
        registry.configure_minimal()
    elif configuration == "standard":
        registry.configure_standard()
    elif configuration == "with_conflicts":
        registry.configure_with_student_conflicts()
    elif configuration == "complete":
        registry.configure_complete()
        registry._activate_category("STUDENT_CONFLICT")
    else:
        raise ValueError(
            f"Unknown configuration: {configuration}. "
            f"Valid options: minimal, standard, with_conflicts, complete"
        )

    logger.info(
        f"Created optimized constraint system with '{configuration}' configuration - "
        f"12 constraint definitions (C6 handled as domain restriction)"
    )

    return registry
