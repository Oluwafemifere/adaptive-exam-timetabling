# FIXED MODEL BUILDER - Enhanced CP-SAT model building with Day data class support

# MODIFIED: Day data class implementation with validation

# Critical Issues Fixed:
# 1. Updated to work with Day data class and timeslots property
# 2. Enhanced error message propagation with UUID keys
# 3. Better validation using Day structure
# 4. Added validate_problem_data_enhanced function
# 5. Comprehensive logging with Day tracking

from typing import Optional, Dict, Any, Tuple, List
from uuid import UUID
import logging
import time
import traceback
from ortools.sat.python import cp_model
from scheduling_engine.core.problem_model import ExamSchedulingProblem
from .constraint_encoder import ConstraintEncoder, SharedVariables
from .solver_manager import CPSATSolverManager

logger = logging.getLogger(__name__)


def validate_problem_data_enhanced(problem):
    """Enhanced problem data validation for Day data class architecture"""
    if not problem.days:
        raise ValueError("No days defined")

    for day_id, day in problem.days.items():
        if len(day.timeslots) != 3:
            raise ValueError(
                f"Day {day_id} has {len(day.timeslots)} timeslots; expected 3"
            )

    total_timeslots = sum(len(d.timeslots) for d in problem.days.values())
    if total_timeslots != len(problem.timeslots):
        raise ValueError("Timeslot count mismatch between days and property")


class CPSATModelBuilder:
    """FIXED: Enhanced CP-SAT model builder with Day data class support"""

    def __init__(self, problem: ExamSchedulingProblem):
        self.problem = problem
        self.model = cp_model.CpModel()
        self.shared_variables: Optional[SharedVariables] = None
        self.build_start_time = 0.0
        self.build_duration = 0.0

        logger.info(
            f"🏗️ Initialized Day-aware CPSATModelBuilder for problem: {problem.id}"
        )

    def configure(self, configuration: str) -> None:
        """Configure the model builder with specific constraint sets"""
        logger.info(f"🔧 Configuring model builder with: {configuration}")

        if configuration == "COMPLETE":
            self.problem.constraint_registry.configure_complete()
        elif configuration == "MINIMAL":
            self.problem.constraint_registry.configure_minimal()
        elif configuration == "BASIC":
            self.problem.constraint_registry.configure_basic()
        elif configuration == "WITH_RESOURCES":
            self.problem.constraint_registry.configure_with_resources()
        else:
            logger.warning(f"⚠️ Unknown configuration: {configuration}")

    def build(self) -> Tuple[cp_model.CpModel, SharedVariables]:
        """FIXED: Enhanced build process with Day data class support"""
        self.build_start_time = time.time()

        try:
            logger.info("🚀 Starting Day-aware CP-SAT model build process...")

            # STEP 1: Comprehensive pre-build validation
            logger.info("🔍 Performing comprehensive pre-build validation...")
            self._validate_problem_data_enhanced()
            logger.info("✅ Pre-build validation complete")

            # STEP 2: Create optimized variables with UUID keys
            logger.info("🔧 Creating optimized variables with UUID keys...")
            shared_variables = self._create_shared_variables()
            logger.info("✅ Variable creation completed successfully")

            # STEP 3: Register and apply constraints
            logger.info("🔗 Registering and applying constraints...")
            self._register_constraints(shared_variables)
            logger.info("✅ Constraint registration completed")

            # STEP 4: Final model validation
            logger.info("🔍 Performing final model validation...")
            self._validate_final_model()
            logger.info("✅ Final model validation completed")

            self.build_duration = time.time() - self.build_start_time

            logger.info(
                f"✅ Day-aware model build SUCCESS after {self.build_duration:.2f}s"
            )

            self.shared_variables = shared_variables
            return self.model, shared_variables

        except Exception as e:
            self.build_duration = time.time() - self.build_start_time
            error_msg = (
                f"Day-aware model building failed - cannot proceed with encoding"
            )

            logger.error(
                f"❌ Day-aware model build FAILED after {self.build_duration:.2f}s: {error_msg}"
            )
            logger.error("🐛 Traceback:")
            logger.error(traceback.format_exc())

            # Re-raise with more descriptive error for test framework
            raise RuntimeError(f"Day-aware model building failed: {str(e)}") from e

    def _validate_problem_data_enhanced(self) -> None:
        """FIXED: Enhanced problem data validation with Day consistency checks"""
        logger.info("🔍 Validating problem data with Day consistency checks...")

        # Use the global validation function
        validate_problem_data_enhanced(self.problem)

        # Basic entity validation
        logger.info("📊 Problem size analysis:")
        logger.info(f" • Exams: {len(self.problem.exams)}")
        logger.info(f" • Time slots: {len(self.problem.timeslots)}")
        logger.info(f" • Rooms: {len(self.problem.rooms)}")
        logger.info(f" • Days: {len(self.problem.days)}")

        # Validate basic entities exist
        if not self.problem.exams:
            raise ValueError("No exams defined - cannot build model")

        if not self.problem.timeslots:
            raise ValueError("No time slots defined - cannot build model")

        if not self.problem.rooms:
            raise ValueError("No rooms defined - cannot build model")

        if not self.problem.days:
            raise ValueError("No days defined - cannot build model")

        # UUID consistency validation
        self._validate_uuid_consistency()

        # Student data validation with UUID consistency
        student_registrations = 0
        student_courses = getattr(self.problem, "_student_courses", {})
        if student_courses:
            student_registrations = sum(
                len(courses) for courses in student_courses.values()
            )

        if student_registrations > 0:
            logger.info(
                f"✅ Student data validation passed: {student_registrations} registrations found"
            )
        else:
            logger.warning(
                "⚠️ Configuration warning: No student course data - student conflict constraints will be skipped"
            )

        # Validate student-exam mappings
        student_mappings = 0
        for exam in self.problem.exams.values():
            students = getattr(exam, "students", [])
            student_mappings += len(students)

        if student_mappings == 0:
            logger.warning(
                "⚠️ No student-exam mappings found - limited conflicts possible!"
            )
        else:
            logger.info(f"✅ Student-exam mappings validated: {student_mappings} total")

    def _perform_capacity_feasibility_check(self) -> None:
        """CRITICAL: Check basic capacity feasibility before constraint creation"""
        logger.info("🔍 Performing capacity feasibility check...")

        total_exam_enrollment = sum(
            getattr(exam, "expected_students", 0)
            for exam in self.problem.exams.values()
        )

        total_room_capacity = 0
        for room in self.problem.rooms.values():
            total_room_capacity += getattr(
                room, "exam_capacity", getattr(room, "capacity", 0)
            )

        total_timeslots = len(self.problem.timeslots)

        # Calculate required vs available seat-time
        required_seat_time = total_exam_enrollment * 3  # Assume 3-hour exams
        available_seat_time = total_room_capacity * total_timeslots

        utilization = (
            required_seat_time / available_seat_time
            if available_seat_time > 0
            else float("inf")
        )

        logger.info(f"📊 Capacity Analysis:")
        logger.info(f"  • Required seat-time: {required_seat_time}")
        logger.info(f"  • Available seat-time: {available_seat_time}")
        logger.info(f"  • Utilization: {utilization:.2%}")

        if utilization > 0.8:
            logger.warning(
                f"⚠️  High utilization ({utilization:.2%}) - may cause infeasibility"
            )

        if utilization > 1.0:
            raise RuntimeError(
                f"INFEASIBLE: Required seat-time exceeds capacity by {(utilization-1)*100:.1f}%"
            )

    def _validate_uuid_consistency(self) -> None:
        """Validate UUID consistency across all problem entities"""
        logger.info("🔍 Validating UUID consistency...")

        # Pre-store entity collections for faster access
        exams = self.problem.exams
        rooms = self.problem.rooms
        timeslots = self.problem.timeslots
        days = self.problem.days

        # Check exam UUIDs
        invalid_exam_ids = []
        for exam_id, exam in exams.items():
            if not isinstance(exam_id, UUID):
                invalid_exam_ids.append(exam_id)
            if not isinstance(getattr(exam, "id", None), UUID):
                invalid_exam_ids.append(f"exam.id: {exam.id}")
            if not isinstance(getattr(exam, "course_id", None), UUID):
                invalid_exam_ids.append(f"exam.course_id: {exam.course_id}")

        if invalid_exam_ids:
            raise ValueError(f"Non-UUID exam identifiers found: {invalid_exam_ids[:3]}")

        # Check room UUIDs
        invalid_room_ids = []
        for room_id, room in rooms.items():
            if not isinstance(room_id, UUID):
                invalid_room_ids.append(room_id)
            if not isinstance(getattr(room, "id", None), UUID):
                invalid_room_ids.append(f"room.id: {room.id}")

        if invalid_room_ids:
            raise ValueError(f"Non-UUID room identifiers found: {invalid_room_ids[:3]}")

        # Check time slot UUIDs via property
        invalid_slot_ids = []
        for slot_id, slot in timeslots.items():
            if not isinstance(slot_id, UUID):
                invalid_slot_ids.append(slot_id)
            if not isinstance(getattr(slot, "id", None), UUID):
                invalid_slot_ids.append(f"slot.id: {slot.id}")

        if invalid_slot_ids:
            raise ValueError(f"Non-UUID slot identifiers found: {invalid_slot_ids[:3]}")

        # Check day UUIDs
        invalid_day_ids = []
        for day_id, day in days.items():
            if not isinstance(day_id, UUID):
                invalid_day_ids.append(day_id)
            if not isinstance(getattr(day, "id", None), UUID):
                invalid_day_ids.append(f"day.id: {day.id}")

        if invalid_day_ids:
            raise ValueError(f"Non-UUID day identifiers found: {invalid_day_ids[:3]}")

        # Check student course registrations
        student_courses = getattr(self.problem, "_student_courses", {})
        if student_courses:
            invalid_student_data = []
            for student_id, course_ids in student_courses.items():
                if not isinstance(student_id, UUID):
                    invalid_student_data.append(f"student_id: {student_id}")
                for course_id in course_ids:
                    if not isinstance(course_id, UUID):
                        invalid_student_data.append(f"course_id: {course_id}")

            if invalid_student_data:
                raise ValueError(
                    f"Non-UUID student/course identifiers found: {invalid_student_data[:3]}"
                )

        logger.info("✅ UUID consistency validation passed")

    def _create_shared_variables(self) -> SharedVariables:
        """Create shared variables using Day-aware constraint encoder"""
        logger.info("🔧 Creating shared variables with Day-aware encoder...")

        encoder = ConstraintEncoder(self.problem, self.model)
        shared_variables = encoder.encode()

        # Log variable creation statistics
        variable_stats = {
            "x_vars": len(shared_variables.x_vars),
            "z_vars": len(shared_variables.z_vars),
            "y_vars": len(shared_variables.y_vars),
            "u_vars": len(shared_variables.u_vars),
        }

        total_vars = sum(variable_stats.values())

        logger.info(f"📊 Day-aware variable creation statistics:")
        for var_type, count in variable_stats.items():
            logger.info(f" • {var_type}: {count}")
        logger.info(f" • Total variables: {total_vars}")

        # Validate variable key consistency
        self._validate_variable_keys(shared_variables)

        return shared_variables

    def _validate_variable_keys(self, shared_variables: SharedVariables) -> None:
        """Validate that all variable keys are proper UUIDs"""
        logger.info("🔍 Validating variable key consistency...")

        # Sample x variables (exam_id, slot_id)
        x_vars_keys = list(shared_variables.x_vars.keys())
        for i in range(min(3, len(x_vars_keys))):
            key = x_vars_keys[i]
            if not isinstance(key, tuple) or len(key) != 2:
                raise ValueError(f"Invalid x variable key format: {key}")

            exam_id, slot_id = key
            if not isinstance(exam_id, UUID) or not isinstance(slot_id, UUID):
                raise ValueError(
                    f"Non-UUID keys in x variables: {type(exam_id)}, {type(slot_id)}"
                )

        # Sample y variables (exam_id, room_id, slot_id)
        y_vars_keys = list(shared_variables.y_vars.keys())
        for i in range(min(3, len(y_vars_keys))):
            key = y_vars_keys[i]
            if not isinstance(key, tuple) or len(key) != 3:
                raise ValueError(f"Invalid y variable key format: {key}")

            exam_id, room_id, slot_id = key
            if not all(isinstance(k, UUID) for k in [exam_id, room_id, slot_id]):
                raise ValueError(
                    f"Non-UUID keys in y variables: {[type(k) for k in key]}"
                )

        # Check conflict pairs in precomputed data
        conflict_pairs = shared_variables.precomputed_data.get("conflict_pairs", set())
        conflict_pairs_list = list(conflict_pairs)
        for i in range(min(3, len(conflict_pairs_list))):
            pair = conflict_pairs_list[i]
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise ValueError(f"Invalid conflict pair format: {pair}")

            exam1, exam2 = pair
            if not isinstance(exam1, UUID) or not isinstance(exam2, UUID):
                raise ValueError(
                    f"Non-UUID conflict pair: {type(exam1)}, {type(exam2)}"
                )

        logger.info("✅ Variable key consistency validation passed")

    def _register_constraints(self, shared_variables: SharedVariables) -> None:
        """FIXED: Enforce category filtering and prevent all constraints from loading"""
        logger.info("🔗 Registering constraints with ENFORCED category filtering...")

        # CRITICAL FIX: Get ONLY requested categories from constraint registry
        active_constraints = (
            self.problem.constraint_registry.get_active_constraint_classes()
        )
        constraint_stats = {"total": 0, "successful": 0, "failed": 0}

        # CRITICAL: Log what categories were actually requested vs activated
        requested_categories = set()
        for info in active_constraints.values():
            requested_categories.add(info.get("category", "UNKNOWN"))

        logger.info(
            f"ENFORCED category filter - Requested: {list(requested_categories)}"
        )
        logger.info(f"ENFORCED constraint count: {len(active_constraints)}")

        # CRITICAL: Validate category filtering worked
        if len(active_constraints) == 0:
            logger.error("❌ No constraints loaded after filtering!")
            # Only fallback if truly no constraints were loaded
            logger.info("Attempting CORE-only fallback...")
            self.problem.constraint_registry.active_constraints.clear()
            self.problem.constraint_registry._activate_category("CORE")
            active_constraints = (
                self.problem.constraint_registry.get_active_constraint_classes()
            )

        if not active_constraints:
            logger.error("❌ No constraints to apply after category filtering!")
            return

        # Apply only the filtered constraints
        constraint_ids = list(active_constraints.keys())
        for constraint_id in constraint_ids:
            constraint_info = active_constraints[constraint_id]
            try:
                logger.info(f"🔧 Applying constraint: {constraint_id}")
                constraint_class = constraint_info["class"]
                category = constraint_info.get("category", "UNKNOWN")

                # Create and apply constraint with Day-aware shared variables
                constraint_instance = constraint_class(
                    constraint_id=constraint_id,
                    problem=self.problem,
                    shared_vars=shared_variables,
                    model=self.model,
                    factory=None,  # Use constraint encoder's factory if needed
                )

                # Initialize variables first if needed
                if hasattr(constraint_instance, "initialize_variables"):
                    constraint_instance.initialize_variables()

                # Apply the constraint
                constraint_instance.add_constraints()
                constraint_stats["successful"] += 1

                constraint_count = getattr(
                    constraint_instance, "constraint_count", "unknown"
                )
                logger.debug(
                    f"✅ Successfully applied {constraint_id} "
                    f"({constraint_count} constraints, category: {category})"
                )

            except Exception as e:
                constraint_stats["failed"] += 1
                logger.error(f"❌ Failed to apply constraint {constraint_id}: {e}")

                # Get full traceback for debugging
                logger.error(f"Full traceback: {traceback.format_exc()}")

                # Decide whether to continue or fail based on constraint criticality
                is_critical = getattr(constraint_instance, "is_critical", False)  # type: ignore

                if is_critical:
                    raise RuntimeError(
                        f"Critical constraint {constraint_id} failed: {e}"
                    ) from e
                else:
                    logger.warning(
                        f"Non-critical constraint {constraint_id} failed, continuing..."
                    )

            constraint_stats["total"] += 1

        # Log constraint application summary
        logger.info("🔗 Constraint application summary:")
        logger.info(f"  • Total constraints processed: {constraint_stats['total']}")
        logger.info(f"  • Successfully applied: {constraint_stats['successful']}")
        logger.info(f"  • Failed: {constraint_stats['failed']}")

        if constraint_stats["successful"] == 0:
            logger.error("❌ No constraints were successfully applied!")
            raise RuntimeError("No constraints were successfully applied!")
        else:
            logger.info(
                f"✅ Successfully applied {constraint_stats['successful']} constraints"
            )

        logger.info("✅ Constraint registration completed")

    def _validate_variable_domains(self, shared_variables: SharedVariables):
        """Validate that all exams have feasible assignments"""
        for exam_id in self.problem.exams:
            # Check start slots
            start_vars = [
                v for k, v in shared_variables.x_vars.items() if k[0] == exam_id
            ]
            if not start_vars:
                raise ValueError(f"Exam {exam_id} has no start variables!")

            # Check room assignments
            room_vars = [
                v for k, v in shared_variables.y_vars.items() if k[0] == exam_id
            ]
            if not room_vars:
                raise ValueError(f"Exam {exam_id} has no room assignment variables!")

    def _validate_final_model(self) -> None:
        """Validate the final CP-SAT model"""
        logger.info("🔍 Performing final Day-aware model validation...")

        # Basic model validation
        if not hasattr(self.model, "Proto"):
            raise RuntimeError("Invalid CP-SAT model - missing Proto method")

        # Get model statistics
        try:
            proto = self.model.Proto()
            num_variables = len(proto.variables)
            num_constraints = len(proto.constraints)

            logger.info(f"📊 Final model statistics:")
            logger.info(f" • Variables: {num_variables}")
            logger.info(f" • Constraints: {num_constraints}")

            if num_variables == 0:
                raise RuntimeError("Model has no variables!")

            if num_constraints == 0:
                logger.warning(
                    "⚠️ Model has no constraints - this may be intentional for testing"
                )

        except Exception as e:
            logger.warning(f"⚠️ Could not extract model statistics: {e}")

        # Validate shared variables consistency
        if self.shared_variables:
            total_shared_vars = (
                len(self.shared_variables.x_vars)
                + len(self.shared_variables.z_vars)
                + len(self.shared_variables.y_vars)
                + len(self.shared_variables.u_vars)
            )

            logger.info(f" • Shared variables: {total_shared_vars}")

            if total_shared_vars == 0:
                raise RuntimeError("No shared variables created!")

        logger.info("✅ Final Day-aware model validation passed")

    def get_build_statistics(self) -> Dict[str, Any]:
        """Get comprehensive build statistics"""
        stats = {
            "build_duration": self.build_duration,
            "model_valid": self.model is not None,
            "shared_variables_created": self.shared_variables is not None,
            "problem_entities": {
                "exams": len(self.problem.exams),
                "time_slots": len(self.problem.timeslots),
                "rooms": len(self.problem.rooms),
                "days": len(self.problem.days),
                "students": len(getattr(self.problem, "students", {})),
            },
            "active_constraints": len(
                self.problem.constraint_registry.get_active_constraints()
            ),
        }

        if self.shared_variables:
            stats["variable_counts"] = {
                "x_vars": len(self.shared_variables.x_vars),
                "z_vars": len(self.shared_variables.z_vars),
                "y_vars": len(self.shared_variables.y_vars),
                "u_vars": len(self.shared_variables.u_vars),
            }

            stats["total_variables"] = sum(stats["variable_counts"].values())

        return stats
