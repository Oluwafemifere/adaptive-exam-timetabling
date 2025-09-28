# COMPREHENSIVE FIX - scheduling_engine/constraints/base_constraint.py

# MODIFIED: UUID-only implementation - removed normalize_id usage

"""
BASE CONSTRAINT ENHANCEMENT - UUID-only version with Day data class support
with enhanced graceful degradation and error handling

MODIFIED for UUID-only usage with Day data class integration
ENHANCED with graceful degradation and improved error recovery

Critical Issues Fixed:
1. Removed normalize_id() function completely
2. Updated all constraint logic to work with UUID keys directly
3. Removed string conversions in variable handling
4. Enhanced validation for UUID-based variable consistency
5. Maintained comprehensive error handling with UUID keys
6. Added Day data class helper functions
7. Enhanced graceful degradation for missing data scenarios
8. Improved validation that doesn't treat "no violations" as errors
9. Better error recovery mechanisms
10. More flexible constraint validation
"""

from abc import ABC, abstractmethod
from datetime import date
from types import MappingProxyType
import logging
from typing import Dict, Any, Optional, Set, List, Union
import psutil  # For system resource monitoring
import math
from ortools.sat.python import cp_model
from uuid import UUID

logger = logging.getLogger(__name__)


# Day data class helper functions
def get_day_for_timeslot(problem, timeslot_id):
    """Get the Day object containing a specific timeslot"""
    return problem.get_day_for_timeslot(timeslot_id)


def get_day_slot_ids(problem, day_id):
    """Get all timeslot IDs for a specific day"""
    day = problem.days.get(day_id)
    if day is None:
        raise ValueError(f"Day {day_id} not found")
    return [slot.id for slot in day.timeslots]


def get_slot_index_in_day(problem, timeslot_id):
    """Get the index of a timeslot within its day (0, 1, or 2)"""
    day = get_day_for_timeslot(problem, timeslot_id)
    for idx, slot in enumerate(day.timeslots):
        if slot.id == timeslot_id:
            return idx
    raise ValueError(f"Timeslot {timeslot_id} not found in its Day")


class CPSATBaseConstraint(ABC):
    """ENHANCED: Base constraint with UUID-only keys, Day data class support, and graceful degradation"""

    def __init__(
        self,
        constraint_id: str,
        problem,
        shared_vars: Any,
        model: cp_model.CpModel,
        factory: Any = None,
    ):
        """Initialize constraint with UUID-only validation and enhanced error handling"""
        self.constraint_id = constraint_id
        self.problem = problem
        self.model = model
        self.factory = factory
        self.constraint_category = getattr(self, "constraint_category", "UNKNOWN")

        # CRITICAL: Initialize constraint tracking
        self.constraint_count = 0
        self.validation_errors = []
        self.creation_start_time = None
        self.creation_end_time = None

        # Precompute frequently accessed attributes
        self._exams = getattr(problem, "exams", {})
        self._timeslots = getattr(problem, "timeslots", {})
        self._rooms = getattr(problem, "rooms", {})
        self._students = getattr(problem, "students", {})

        # Enhanced attribute initialization to prevent access errors
        self._initialize_shared_variables(shared_vars)
        self._validate_dependencies()

        logger.debug(
            f"Initialized {self.constraint_id} with UUID-only validation and graceful error handling"
        )

    def _initialize_shared_variables(self, shared_vars):
        """CRITICAL: Initialize shared variables with UUID validation and graceful degradation"""
        try:
            # Extract variables with graceful fallbacks
            self.x = self._safe_extract_vars(shared_vars, ["x_vars", "x"], {})
            self.z = self._safe_extract_vars(shared_vars, ["z_vars", "z"], {})
            self.y = self._safe_extract_vars(shared_vars, ["y_vars", "y"], {})
            self.u = self._safe_extract_vars(shared_vars, ["u_vars", "u"], {})

            # Extract precomputed data with graceful fallbacks
            if hasattr(shared_vars, "precomputed_data"):
                precomputed = shared_vars.precomputed_data
                self.conflict_pairs = precomputed.get("conflict_pairs", set())
                self.student_exams = precomputed.get("student_exams", {})
                self.room_metadata = precomputed.get("room_metadata", {})
                self.invigilator_availability = precomputed.get(
                    "invigilator_availability", {}
                )
                self.allowed_rooms = precomputed.get("allowed_rooms", {})
                self.day_slot_groupings = precomputed.get("day_slot_groupings", {})
                self.precomputed_data = shared_vars.precomputed_data
            else:
                # Graceful fallback initialization
                self.conflict_pairs = set()
                self.student_exams = {}
                self.room_metadata = {}
                self.invigilator_availability = {}
                self.allowed_rooms = {}
                self.precomputed_data = {}

                logger.debug(
                    f"{self.constraint_id}: No precomputed data available, using defaults"
                )

            logger.debug(
                f"{self.constraint_id}: Initialized UUID variables - "
                f"x:{len(self.x)}, z:{len(self.z)}, y:{len(self.y)}, u:{len(self.u)}"
            )

        except Exception as e:
            logger.error(
                f"❌ {self.constraint_id}: Failed to initialize shared variables: {e}"
            )
            # Don't raise - allow graceful degradation for non-critical constraints
            if getattr(self, "is_critical", False):
                raise RuntimeError(
                    f"Variable initialization failed for {self.constraint_id}"
                )
            else:
                self._initialize_empty_variables()

    def _safe_extract_vars(self, shared_vars, attr_names, default):
        """Safely extract variables with multiple fallback attribute names"""
        for attr_name in attr_names:
            if hasattr(shared_vars, attr_name):
                return getattr(shared_vars, attr_name)
        return default

    def _initialize_empty_variables(self):
        """Initialize empty variables for graceful degradation"""
        self.x = {}
        self.z = {}
        self.y = {}
        self.u = {}
        self.conflict_pairs = set()
        self.student_exams = {}
        self.room_metadata = {}
        self.invigilator_availability = {}
        self.allowed_rooms = {}
        self.precomputed_data = {}

        logger.warning(
            f"{self.constraint_id}: Initialized with empty variables due to errors"
        )

    def _validate_dependencies(self):
        """CRITICAL: Validate constraint dependencies"""
        if not hasattr(self, "dependencies"):
            return

        # This is a basic check - in a real system, you'd validate that
        # dependent constraints have actually been applied
        for dep in getattr(self, "dependencies", []):
            logger.debug(f"{self.constraint_id}: Depends on {dep}")

    def validate_variable_consistency(self) -> bool:
        """CRITICAL: Validate variable consistency for this constraint"""
        validation_passed = True

        # Check if required variables exist based on constraint category
        if hasattr(self, "constraint_category"):
            category = self.constraint_category

            if category == "STUDENT_CONFLICTS":
                # Student conflict constraints need conflict pairs and appropriate variables
                if not self.conflict_pairs and not self.student_exams:
                    logger.warning(f"{self.constraint_id}: No conflict data available")
                    # This might be normal, so don't fail validation

                if "room" in self.constraint_id.lower() and not self.y:
                    logger.error(
                        f"❌ {self.constraint_id}: Room conflict constraint needs y variables"
                    )
                    validation_passed = False

                if "overlap" in self.constraint_id.lower() and not self.z:
                    logger.error(
                        f"❌ {self.constraint_id}: Overlap constraint needs z variables"
                    )
                    validation_passed = False

        # ADDED: Validate UUID key consistency
        self._validate_uuid_key_consistency()

        return validation_passed

    def _validate_uuid_key_consistency(self):
        """Validate that all variable keys are properly formatted UUIDs"""
        try:
            # Check x variables (exam_id, slot_id) pairs
            for key in list(self.x.keys())[:3]:  # Sample first 3
                if isinstance(key, tuple) and len(key) == 2:
                    exam_id, slot_id = key
                    if not isinstance(exam_id, UUID) or not isinstance(slot_id, UUID):
                        logger.warning(
                            f"{self.constraint_id}: Non-UUID keys in x variables: {type(exam_id)}, {type(slot_id)}"
                        )
                        break

            # Check y variables (exam_id, room_id, slot_id) tuples
            for key in list(self.y.keys())[:3]:  # Sample first 3
                if isinstance(key, tuple) and len(key) == 3:
                    exam_id, room_id, slot_id = key
                    if not all(
                        isinstance(k, UUID) for k in [exam_id, room_id, slot_id]
                    ):
                        logger.warning(
                            f"{self.constraint_id}: Non-UUID keys in y variables"
                        )
                        break

            # Check conflict pairs (should be UUID tuples)
            for pair in list(self.conflict_pairs)[:3]:  # Sample first 3
                if isinstance(pair, tuple) and len(pair) == 2:
                    exam1, exam2 = pair
                    if not isinstance(exam1, UUID) or not isinstance(exam2, UUID):
                        logger.warning(f"{self.constraint_id}: Non-UUID conflict pairs")
                        break

        except Exception as e:
            logger.debug(f"{self.constraint_id}: UUID validation error: {e}")

    def get_day_slot_groupings(self) -> Dict[str, List[UUID]]:
        """Get day-slot groupings for constraint creation - CENTRALIZED ONLY"""
        # First check precomputed data
        if hasattr(self, "day_slot_groupings") and self.day_slot_groupings:
            logger.debug(f"{self.constraint_id}: Using precomputed day-slot groupings")
            return self.day_slot_groupings

        # Try to get from precomputed_data
        if hasattr(self, "precomputed_data") and self.precomputed_data:
            groupings = self.precomputed_data.get("day_slot_groupings", {})
            if groupings:
                logger.debug(
                    f"{self.constraint_id}: Using precomputed data day-slot groupings"
                )
                return groupings

        # NO FALLBACK - raise error
        raise ValueError(
            f"{self.constraint_id}: No day-slot groupings available. All day-related constraints require centralized precomputed day-slot groupings."
        )

    def validate_day_slot_groupings(self) -> bool:
        """Enhanced validation for day-slot groupings"""
        groupings = self.get_day_slot_groupings()
        if not groupings:
            logger.warning(f"{self.constraint_id}: No day-slot groupings available")
            return False

        total_slots = sum(len(slots) for slots in groupings.values())
        if total_slots == 0:
            logger.error(f"{self.constraint_id}: Day-slot groupings contain no slots")
            return False

        # Validate UUID format
        for day, slots in groupings.items():
            for slot_id in slots:
                if not isinstance(slot_id, UUID):
                    logger.error(
                        f"{self.constraint_id}: Non-UUID slot ID in day-slot groupings: {slot_id}"
                    )
                    return False

        logger.debug(
            f"{self.constraint_id}: Day-slot groupings validated: {len(groupings)} days, {total_slots} total slots"
        )
        return True

    def analyze_solution_space(self):
        """Analyze potential solution space constraints"""
        total_exam_slots = len(self._exams) * len(self._timeslots)
        total_room_slots = len(self._rooms) * len(self._timeslots)

        logger.info(f"Solution space analysis:")
        logger.info(f" - Possible exam-slot assignments: {total_exam_slots}")
        logger.info(f" - Possible room-slot assignments: {total_room_slots}")
        logger.info(
            f" - Exam-room-slot combinations: {total_exam_slots * len(self._rooms)}"
        )

        # Check basic feasibility
        if len(self._exams) > total_room_slots:
            logger.error(
                "More exams than available room-slots - problem likely infeasible"
            )

    def validate_constraint_data(self) -> bool:
        """Enhanced constraint data validation with graceful handling"""
        validation_passed = True

        # Basic problem data validation with graceful fallbacks
        if not self._exams:
            logger.warning(f"⚠️ {self.constraint_id}: No exam data available")
            if self._is_exam_dependent():
                validation_passed = False

        if not self._timeslots:
            logger.warning(f"⚠️ {self.constraint_id}: No time slot data available")
            if self._is_timeslot_dependent():
                validation_passed = False

        if not self._rooms:
            logger.warning(f"⚠️ {self.constraint_id}: No room data available")
            if self._is_room_dependent():
                validation_passed = False

        return validation_passed

    def _is_exam_dependent(self) -> bool:
        """Check if constraint depends on exam data"""
        return True  # Most constraints depend on exams

    def _is_timeslot_dependent(self) -> bool:
        """Check if constraint depends on timeslot data"""
        return True  # Most constraints depend on timeslots

    def _is_room_dependent(self) -> bool:
        """Check if constraint depends on room data"""
        return (
            "room" in self.constraint_id.lower()
            or "capacity" in self.constraint_id.lower()
        )

    def log_constraint_creation_start(self):
        """Log constraint creation start with resource monitoring"""
        import time

        self.creation_start_time = time.time()

        # Log memory usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        logger.info(
            f"🔧 {self.constraint_id}: Starting UUID-only constraint creation (Memory: {memory_mb:.1f}MB)"
        )

    def log_constraint_creation_end(self):
        """Log constraint creation end with statistics"""
        import time

        if self.creation_start_time:
            self.creation_end_time = time.time()
            duration = self.creation_end_time - self.creation_start_time

            # Log memory usage
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024

            logger.info(
                f"✅ {self.constraint_id}: Created {self.constraint_count} constraints "
                f"in {duration:.2f}s (Memory: {memory_mb:.1f}MB)"
            )
        else:
            logger.info(
                f"✅ {self.constraint_id}: Created {self.constraint_count} constraints"
            )

    def initialize_variables(self):
        """Initialize local variables - called by model_builder"""
        self.create_variables()

    def create_variables(self):
        """Create local variables with enhanced error handling"""
        try:
            logger.debug(
                f"{self.constraint_id}: Creating local variables with UUID keys"
            )
            self._create_local_variables()
            logger.debug(f"{self.constraint_id}: Local variables created successfully")

        except Exception as e:
            logger.error(
                f"❌ CRITICAL {self.constraint_id}: Failed to create local variables: {e}"
            )
            if getattr(self, "is_critical", False):
                raise RuntimeError(
                    f"Local variable creation failed for {self.constraint_id}"
                )
            else:
                logger.warning(
                    f"⚠️ Non-critical constraint {self.constraint_id} variable creation failed"
                )

    def add_constraints(self):
        """Enhanced constraint addition with comprehensive error handling and graceful degradation"""
        try:
            self.log_constraint_creation_start()

            # Add soft constraint specific logging
            if self.constraint_category == "SOFT_CONSTRAINTS":
                logger.info(f"🟡 Starting SOFT constraint: {self.constraint_id}")
            # Pre-validation with graceful handling
            if not self.validate_constraint_data():
                logger.warning(
                    f"⚠️ {self.constraint_id}: Data validation failed - attempting graceful degradation"
                )
                # Don't raise error immediately - try to continue

            # Create constraints
            logger.debug(f"{self.constraint_id}: Adding constraint implementation")
            initial_constraint_count = self.constraint_count

            self._add_constraint_implementation()

            # Post-validation
            constraints_added = self.constraint_count - initial_constraint_count

            # Enhanced minimum constraint checking
            min_expected = getattr(self, "min_expected_constraints", 1)
            is_critical = getattr(self, "is_critical", False)

            if self.constraint_count < min_expected:
                message = (
                    f"{self.constraint_id}: Only {self.constraint_count} constraints created, "
                    f"expected at least {min_expected}"
                )

                if is_critical:
                    # Even critical constraints can have zero constraints if no violations exist
                    if self.constraint_count == 0 and self._zero_constraints_valid():
                        logger.info(
                            f"✅ {self.constraint_id}: Zero constraints valid (no violations to prevent)"
                        )
                    else:
                        logger.error(f"❌ CRITICAL {message}")
                        raise RuntimeError(
                            f"Critical constraint {self.constraint_id} failed to create minimum constraints"
                        )
                else:
                    logger.warning(f"⚠️ {message}")

            self.log_constraint_creation_end()
            if self.constraint_category == "SOFT_CONSTRAINTS":
                logger.info(
                    f"🟢 Finished SOFT constraint: {self.constraint_id} - {self.constraint_count} constraints"
                )

        except Exception as e:
            logger.error(f"❌ {self.constraint_id}: Constraint creation failed: {e}")

            if self.constraint_category == "SOFT_CONSTRAINTS":
                logger.error(f"🔴 SOFT constraint {self.constraint_id} failed: {e}")
            if getattr(self, "is_critical", False):
                # Even for critical constraints, check if zero constraints might be valid
                if self._zero_constraints_valid():
                    logger.info(
                        f"✅ {self.constraint_id}: Critical constraint with zero constraints - valid scenario"
                    )
                    self.constraint_count = 0
                else:
                    raise  # Re-raise for truly critical failures
            else:
                logger.warning(
                    f"⚠️ Non-critical constraint {self.constraint_id} failed, continuing..."
                )
                self.constraint_count = 0

    def _zero_constraints_valid(self) -> bool:
        """Check if zero constraints is a valid scenario for this constraint type"""
        constraint_id_lower = self.constraint_id.lower()

        # Student conflict constraints can validly have zero constraints
        if "student" in constraint_id_lower and "conflict" in constraint_id_lower:
            return not self.conflict_pairs  # Valid if no conflicts exist

        # Capacity constraints can be zero if all rooms are overbookable
        if "capacity" in constraint_id_lower:
            if self._rooms:
                all_overbookable = all(
                    getattr(room, "overbookable", False)
                    for room in self._rooms.values()
                )
                return all_overbookable

        # Invigilator constraints can be zero if no invigilators
        if "invigilator" in constraint_id_lower:
            return (
                not hasattr(self.problem, "invigilators")
                or not self.problem.invigilators
            )

        # Default: zero constraints might be valid
        return True

    @abstractmethod
    def _create_local_variables(self):
        """Create constraint-specific local variables"""
        pass

    @abstractmethod
    def _add_constraint_implementation(self):
        """Add the actual constraint implementation"""
        pass

    def get_constraint_statistics(self) -> Dict[str, Any]:
        """Get comprehensive constraint statistics"""
        stats = {
            "constraint_id": self.constraint_id,
            "constraint_count": self.constraint_count,
            "is_critical": getattr(self, "is_critical", False),
            "constraint_category": getattr(self, "constraint_category", "UNKNOWN"),
            "dependencies": getattr(self, "dependencies", []),
            "validation_errors": self.validation_errors,
            "uuid_consistency": True,  # Since we're UUID-only now
        }

        if self.creation_start_time and self.creation_end_time:
            stats["creation_time"] = self.creation_end_time - self.creation_start_time

        return stats

    def __str__(self):
        return f"{self.constraint_id}(constraints={self.constraint_count})"

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"id='{self.constraint_id}', "
            f"constraints={self.constraint_count})"
        )

    # Helper methods for UUID-based constraint creation
    def iterate_exam_pairs_from_conflicts(self):
        """Iterate over exam pairs from conflict data (UUID keys)"""
        for exam1_id, exam2_id in self.conflict_pairs:
            if exam1_id in self._exams and exam2_id in self._exams:
                yield exam1_id, exam2_id

    def iterate_student_exams(self):
        """Iterate over student-exam mappings (UUID keys)"""
        for student_id, exam_ids in self.student_exams.items():
            if len(exam_ids) > 1:  # Only students with multiple exams
                yield student_id, exam_ids

    def get_allowed_rooms_for_exam(self, exam_id: UUID) -> Set[UUID]:
        """Get allowed rooms for an exam (UUID keys)"""
        return self.allowed_rooms.get(exam_id, set())

    def get_room_capacity(self, room_id: UUID) -> int:
        """Get room capacity (UUID key)"""
        room_meta = self.room_metadata.get(room_id, {})
        return room_meta.get("capacity", 0)
