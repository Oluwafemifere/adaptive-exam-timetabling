from collections import defaultdict
import logging
import time
import traceback
from typing import Optional, Dict, Any, Tuple, TYPE_CHECKING
from uuid import UUID
from ortools.sat.python import cp_model

from scheduling_engine.data_flow_tracker import track_data_flow

# TITLE: FIXED MODEL BUILDER - Enhanced with GA Integration Support

if TYPE_CHECKING:
    from .constraint_encoder import SharedVariables, ConstraintEncoder
    from scheduling_engine.core.problem_model import ExamSchedulingProblem

logger = logging.getLogger(__name__)


class CPSATModelBuilder:
    """FIXED: Enhanced CP-SAT model builder with GA integration support"""

    def __init__(
        self,
        problem: "ExamSchedulingProblem",  # Use string annotation to avoid circular import
        enable_ga_integration: bool = True,
        ga_parameters: Optional[Dict] = None,
    ):
        self.problem = problem
        self.model = cp_model.CpModel()
        self.shared_variables: Optional["SharedVariables"] = None
        self.build_start_time = 0.0
        self.build_duration = 0.0

        # TITLE: Use TYPE_CHECKING to avoid circular imports
        self.enable_ga_integration = enable_ga_integration
        self.ga_parameters = ga_parameters or {
            "population_size": 50,
            "max_generations": 20,
            "pruning_aggressiveness": 0.2,
        }
        self.ga_search_hints = []

        logger.info(
            f"Initialized GA-integrated CPSATModelBuilder for problem {problem.id}"
        )

    def configure(self, configuration: str) -> None:
        """Configure the model builder with specific constraint sets"""
        logger.info(f"Configuring model builder with {configuration}")

        if configuration == "COMPLETE":
            self.problem.constraint_registry.configure_complete_with_soft()
        elif configuration == "MINIMAL":
            self.problem.constraint_registry.configure_minimal()
        elif configuration == "BASIC":
            self.problem.constraint_registry.configure_basic()
        elif configuration == "WITH_RESOURCES":
            self.problem.constraint_registry.configure_with_resources()
        else:
            logger.warning(f"Unknown configuration: {configuration}")

    @track_data_flow("build_cp_sat_model", include_stats=True)
    def build(self) -> Tuple[cp_model.CpModel, "SharedVariables"]:
        """FIXED: Enhanced build process with GA integration support"""
        self.build_start_time = time.time()

        try:
            logger.info("Starting GA-integrated CP-SAT model build process...")

            # TITLE: FIXED GA integration parameters
            logger.info("Performing comprehensive pre-build validation...")
            self._validate_problem_data_enhanced()
            logger.info("Pre-build validation complete")

            # TITLE: STEP 1: Comprehensive pre-build validation
            logger.info("Creating GA-integrated constraint encoder...")
            shared_variables = self._create_shared_variables_with_ga()
            logger.info("GA-integrated variable creation completed successfully")

            # TITLE: STEP 2: Create GA-integrated constraint encoder
            logger.info("Registering and applying constraints...")
            self._register_constraints(shared_variables)
            logger.info("Constraint registration completed")

            # TITLE: STEP 3: Register and apply constraints
            logger.info("Performing final model validation...")
            self._validate_final_model()
            logger.info("Final model validation completed")

            self.build_duration = time.time() - self.build_start_time
            logger.info(
                f"GA-integrated model build SUCCESS after {self.build_duration:.2f}s"
            )

            self.shared_variables = shared_variables
            return self.model, shared_variables

        except Exception as e:
            self.build_duration = time.time() - self.build_start_time
            error_msg = (
                f"GA-integrated model building failed - cannot proceed with encoding"
            )
            logger.error(
                f"GA-integrated model build FAILED after {self.build_duration:.2f}s: {error_msg}"
            )
            logger.error("Traceback:")
            logger.error(traceback.format_exc())

            # TITLE: STEP 4: Final model validation
            raise RuntimeError(f"GA-integrated model building failed: {str(e)}") from e

    def _create_shared_variables_with_ga(self) -> "SharedVariables":
        """Enhanced variable creation with detailed logging"""
        logger.info("=== VARIABLE CREATION PHASE START ===")

        # Log problem dimensions
        problem_stats = {
            "exams": len(self.problem.exams),
            "timeslots": len(self.problem.timeslots),
            "rooms": len(self.problem.rooms),
            "students": len(self.problem.students),
            "invigilators": len(self.problem.invigilators),
        }

        logger.info(f"📐 PROBLEM DIMENSIONS: {problem_stats}")

        # Calculate expected variable counts
        expected_vars = {
            "x_vars": problem_stats["exams"] * problem_stats["timeslots"],
            "y_vars": problem_stats["exams"]
            * problem_stats["rooms"]
            * problem_stats["timeslots"],
            "u_vars": problem_stats["invigilators"]
            * problem_stats["exams"]
            * problem_stats["timeslots"],
            "z_vars": problem_stats["exams"] * problem_stats["timeslots"],
        }

        total_expected = sum(expected_vars.values())
        logger.info(f"📊 EXPECTED VARIABLES: {expected_vars}")
        logger.info(f"📊 TOTAL EXPECTED: {total_expected:,} variables")

        # Check if variable space is reasonable
        if total_expected > 500000:  # 500K threshold
            logger.warning(
                f"⚠️ LARGE VARIABLE SPACE: {total_expected:,} variables may cause performance issues"
            )

            # Suggest optimizations
            optimization_suggestions = []
            if problem_stats["rooms"] > 30:
                optimization_suggestions.append(
                    f"Consider reducing rooms from {problem_stats['rooms']} to ~30"
                )
            if problem_stats["timeslots"] > 30:
                optimization_suggestions.append(
                    f"Consider reducing timeslots from {problem_stats['timeslots']} to ~30"
                )

            if optimization_suggestions:
                logger.info("💡 OPTIMIZATION SUGGESTIONS:")
                for suggestion in optimization_suggestions:
                    logger.info(f"  • {suggestion}")

        # Create variables with timing
        start_time = time.time()
        try:
            from .constraint_encoder import ConstraintEncoder

            encoder = ConstraintEncoder(problem=self.problem, model=self.model)
            shared_variables = encoder.encode()

            creation_time = time.time() - start_time

            # Log actual variable counts
            actual_vars = {
                "x_vars": len(shared_variables.x_vars),
                "y_vars": len(shared_variables.y_vars),
                "u_vars": len(shared_variables.u_vars),
                "z_vars": len(shared_variables.z_vars),
            }

            total_actual = sum(actual_vars.values())

            logger.info(f"✅ ACTUAL VARIABLES CREATED: {actual_vars}")
            logger.info(
                f"✅ TOTAL ACTUAL: {total_actual:,} variables in {creation_time:.2f}s"
            )

            # Compare expected vs actual
            for var_type in expected_vars:
                expected = expected_vars[var_type]
                actual = actual_vars[var_type]
                if expected != actual:
                    logger.warning(
                        f"📊 {var_type.upper()} MISMATCH: expected {expected:,}, got {actual:,}"
                    )

            return shared_variables

        except Exception as e:
            logger.error(
                f"❌ Variable creation failed after {time.time() - start_time:.2f}s: {e}"
            )
            raise

    def _register_constraints(self, shared_variables: "SharedVariables") -> None:
        """Enhanced constraint registration with detailed logging"""
        logger.info("=== CONSTRAINT REGISTRATION PHASE START ===")

        active_constraints = (
            self.problem.constraint_registry.get_active_constraint_classes()
        )
        logger.info(
            f"📋 ACTIVE CONSTRAINTS: {len(active_constraints)} constraints to apply"
        )

        # Group constraints by category for better logging
        constraints_by_category = defaultdict(list)
        for constraint_id, constraint_info in active_constraints.items():
            category = constraint_info.get("category", "UNKNOWN")
            constraints_by_category[category].append(constraint_id)

        logger.info("📊 CONSTRAINTS BY CATEGORY:")
        for category, constraints in constraints_by_category.items():
            logger.info(f"  🏷️ {category}: {len(constraints)} constraints")

        # Apply constraints with detailed timing and error tracking
        constraint_stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "timing": {},
            "constraint_counts": {},
        }

        for constraint_id in active_constraints.keys():
            constraint_info = active_constraints[constraint_id]
            constraint_stats["total"] += 1

            start_time = time.time()
            try:
                logger.info(f"🔧 APPLYING: {constraint_id}")

                # Create and apply constraint
                constraint_class = constraint_info["class"]
                constraint_instance = constraint_class(
                    constraint_id=constraint_id,
                    problem=self.problem,
                    shared_vars=shared_variables,
                    model=self.model,
                )

                constraint_instance.add_constraints()

                # Track timing and counts
                elapsed = time.time() - start_time
                constraint_stats["timing"][constraint_id] = elapsed
                constraint_stats["successful"] += 1

                # Get constraint count if available
                constraint_count = getattr(
                    constraint_instance, "constraint_count", "unknown"
                )
                constraint_stats["constraint_counts"][constraint_id] = constraint_count

                logger.info(
                    f"✅ {constraint_id}: {constraint_count} constraints in {elapsed:.3f}s"
                )

            except Exception as e:
                elapsed = time.time() - start_time
                constraint_stats["failed"] += 1
                constraint_stats["timing"][constraint_id] = elapsed

                logger.error(f"❌ {constraint_id} FAILED in {elapsed:.3f}s: {e}")

                # Determine if this is critical
                is_critical = (
                    getattr(constraint_instance, "is_critical", False)  # type: ignore
                    if "constraint_instance" in locals()
                    else False
                )
                if is_critical:
                    logger.error(f"🔴 CRITICAL CONSTRAINT FAILED: {constraint_id}")
                    raise RuntimeError(
                        f"Critical constraint {constraint_id} failed: {e}"
                    ) from e
                else:
                    logger.warning(
                        f"⚠️ Non-critical constraint {constraint_id} failed, continuing..."
                    )

        # Log summary statistics
        total_time = sum(constraint_stats["timing"].values())
        total_constraints = sum(
            count
            for count in constraint_stats["constraint_counts"].values()
            if isinstance(count, int)
        )

        logger.info("=== CONSTRAINT REGISTRATION SUMMARY ===")
        logger.info(f"📊 Processed: {constraint_stats['total']} constraints")
        logger.info(f"✅ Successful: {constraint_stats['successful']}")
        logger.info(f"❌ Failed: {constraint_stats['failed']}")
        logger.info(f"⏱️ Total time: {total_time:.2f}s")
        logger.info(f"🔢 Total constraints added: {total_constraints}")

        # Log slowest constraints
        if constraint_stats["timing"]:
            slowest = sorted(
                constraint_stats["timing"].items(), key=lambda x: x[1], reverse=True
            )[:3]
            logger.info("🐌 SLOWEST CONSTRAINTS:")
            for constraint_id, elapsed in slowest:
                logger.info(f"  • {constraint_id}: {elapsed:.3f}s")

    def validate_problem_data_enhanced(self) -> None:
        """FIXED - Enhanced validation with proper timeslot counting"""
        logger.info("Validating problem data with Day consistency checks...")

        # Count timeslots through days (the correct way)
        total_timeslots = 0
        for day in self.problem.days.values():
            total_timeslots += len(day.timeslots)

        logger.info(f"Problem size analysis:")
        logger.info(f"- Exams: {len(self.problem.exams)}")
        logger.info(f"- Time slots: {total_timeslots}")  # FIXED: Use correct count
        logger.info(f"- Rooms: {len(self.problem.rooms)}")
        logger.info(f"- Days: {len(self.problem.days)}")

        # Validate expected timeslot count
        expected_timeslots = len(self.problem.days) * 3  # 3 timeslots per day
        if total_timeslots != expected_timeslots:
            error_msg = f"Timeslot count error: {total_timeslots} found, expected {expected_timeslots}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Validate day-timeslot relationships
        for day_id, day in self.problem.days.items():
            for timeslot in day.timeslots:
                if timeslot.parent_day_id != day_id:
                    error_msg = f"Timeslot {timeslot.id} has wrong parent_day_id"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

    def _validate_problem_data_enhanced(self) -> None:
        """FIXED: Enhanced problem data validation with Day consistency checks"""
        logger.info("Validating problem data with Day consistency checks...")

        # TITLE: Validate variable key consistency
        self.validate_problem_data_enhanced()  # Use the global validation function

        logger.info("Problem size analysis:")
        logger.info(f"  Exams: {len(self.problem.exams)}")
        logger.info(f"  Time slots: {len(self.problem.timeslots)}")
        logger.info(f"  Rooms: {len(self.problem.rooms)}")
        logger.info(f"  Days: {len(self.problem.days)}")

        # TITLE: Basic entity validation
        if not self.problem.exams:
            raise ValueError("No exams defined - cannot build model")
        if not self.problem.timeslots:
            raise ValueError("No time slots defined - cannot build model")
        if not self.problem.rooms:
            raise ValueError("No rooms defined - cannot build model")
        if not self.problem.days:
            raise ValueError("No days defined - cannot build model")

        # TITLE: Validate basic entities exist
        self._validate_uuid_consistency()  # FIXED: Enhanced UUID consistency validation

        student_registrations = 0
        student_courses = getattr(self.problem, "student_courses", {})
        if student_courses:
            student_registrations = sum(
                len(courses) for courses in student_courses.values()
            )

        if student_registrations > 0:
            logger.info(
                f"Student data validation passed: {student_registrations} registrations found"
            )
        else:
            logger.warning(
                "Configuration warning: No student course data - student conflict constraints will be skipped"
            )

        # TITLE: Student data validation with UUID consistency
        student_mappings = 0
        for exam in self.problem.exams.values():
            students = getattr(exam, "students", set())
            student_mappings += len(students)

        if student_mappings == 0:
            logger.warning(
                "No student-exam mappings found - limited conflicts possible!"
            )
        else:
            logger.info(f"Student-exam mappings validated: {student_mappings} total")

    def _validate_uuid_consistency(self) -> None:
        """FIXED: Enhanced UUID consistency validation across all problem entities"""
        logger.info("Validating UUID consistency...")

        # TITLE: Validate student-exam mappings
        exams = self.problem.exams
        rooms = self.problem.rooms
        timeslots = self.problem.timeslots
        days = self.problem.days

        # TITLE: Pre-store entity collections for faster access
        invalid_exam_ids = []
        for exam_id, exam in exams.items():
            if not isinstance(exam_id, UUID):
                invalid_exam_ids.append(f"{exam_id} ({type(exam_id)})")
            if not isinstance(getattr(exam, "id", None), UUID):
                invalid_exam_ids.append(
                    f"exam.id {exam.id} ({type(getattr(exam, 'id', None))})"
                )
            if not isinstance(getattr(exam, "course_id", None), UUID):
                invalid_exam_ids.append(
                    f"exam.course_id {exam.course_id} ({type(getattr(exam, 'course_id', None))})"
                )

        if invalid_exam_ids:
            raise ValueError(f"Non-UUID exam identifiers found: {invalid_exam_ids[:3]}")
            self._fix_uuid_consistency()

        # TITLE: Check exam UUIDs
        invalid_room_ids = []
        for room_id, room in rooms.items():
            if not isinstance(room_id, UUID):
                invalid_room_ids.append(f"{room_id} ({type(room_id)})")
            if not isinstance(getattr(room, "id", None), UUID):
                invalid_room_ids.append(
                    f"room.id {room.id} ({type(getattr(room, 'id', None))})"
                )

        if invalid_room_ids:
            raise ValueError(f"Non-UUID room identifiers found: {invalid_room_ids[:3]}")
            self._fix_uuid_consistency()

        # TITLE: Check room UUIDs
        invalid_slot_ids = []
        for slot_id, slot in timeslots.items():
            if not isinstance(slot_id, UUID):
                invalid_slot_ids.append(f"{slot_id} ({type(slot_id)})")
            if not isinstance(getattr(slot, "id", None), UUID):
                invalid_slot_ids.append(
                    f"slot.id {slot.id} ({type(getattr(slot, 'id', None))})"
                )

        if invalid_slot_ids:
            raise ValueError(f"Non-UUID slot identifiers found: {invalid_slot_ids[:3]}")
            self._fix_uuid_consistency()

        # TITLE: Check time slot UUIDs via property
        invalid_day_ids = []
        for day_id, day in days.items():
            if not isinstance(day_id, UUID):
                invalid_day_ids.append(f"{day_id} ({type(day_id)})")
            if not isinstance(getattr(day, "id", None), UUID):
                invalid_day_ids.append(
                    f"day.id {day.id} ({type(getattr(day, 'id', None))})"
                )

        if invalid_day_ids:
            raise ValueError(f"Non-UUID day identifiers found: {invalid_day_ids[:3]}")
            self._fix_uuid_consistency()

        # TITLE: Check day UUIDs
        student_courses = getattr(self.problem, "student_courses", {})
        if student_courses:
            invalid_student_data = []
            for student_id, course_ids in student_courses.items():
                if not isinstance(student_id, UUID):
                    invalid_student_data.append(
                        f"student_id {student_id} ({type(student_id)})"
                    )
                for course_id in course_ids:
                    if not isinstance(course_id, UUID):
                        invalid_student_data.append(
                            f"course_id {course_id} ({type(course_id)})"
                        )

            if invalid_student_data:
                raise ValueError(
                    f"Non-UUID student/course identifiers found: {invalid_student_data[:3]}"
                )
                self._fix_uuid_consistency()

        logger.info("UUID consistency validation passed")

    def _fix_uuid_consistency(self) -> None:
        """Fix UUID consistency by converting string UUIDs to UUID objects"""
        logger.info("Fixing UUID consistency...")

        # Fix student_courses dictionary
        if hasattr(self.problem, "student_courses"):
            fixed_student_courses = {}
            for student_id, course_ids in self.problem._student_courses.items():
                # Convert student_id to UUID if it's a string
                fixed_student_id = student_id
                if isinstance(student_id, str):
                    try:
                        fixed_student_id = UUID(student_id)
                    except ValueError:
                        logger.warning(f"Invalid student UUID string: {student_id}")
                        continue

                # Convert course_ids to UUID objects
                fixed_course_ids = set()
                for course_id in course_ids:
                    if isinstance(course_id, str):
                        try:
                            fixed_course_ids.add(UUID(course_id))
                        except ValueError:
                            logger.warning(f"Invalid course UUID string: {course_id}")
                    else:
                        fixed_course_ids.add(course_id)

                fixed_student_courses[fixed_student_id] = fixed_course_ids

            self.problem._student_courses = fixed_student_courses

        # Fix course_students dictionary
        if hasattr(self.problem, "course_students"):
            fixed_course_students = {}
            for course_id, student_ids in self.problem.course_students.items():
                # Convert course_id to UUID if it's a string
                fixed_course_id = course_id
                if isinstance(course_id, str):
                    try:
                        fixed_course_id = UUID(course_id)
                    except ValueError:
                        logger.warning(f"Invalid course UUID string: {course_id}")
                        continue

                # Convert student_ids to UUID objects
                fixed_student_ids = set()
                for student_id in student_ids:
                    if isinstance(student_id, str):
                        try:
                            fixed_student_ids.add(UUID(student_id))
                        except ValueError:
                            logger.warning(f"Invalid student UUID string: {student_id}")
                    else:
                        fixed_student_ids.add(student_id)

                fixed_course_students[fixed_course_id] = fixed_student_ids

            self.problem.course_students = fixed_course_students

        logger.info("UUID consistency fix completed")

    def _validate_variable_keys(self, shared_variables: "SharedVariables") -> None:
        """FIXED: Enhanced variable key consistency validation"""
        logger.info("Validating variable key consistency...")

        def _is_valid_uuid(value):
            if isinstance(value, UUID):
                return True
            if isinstance(value, str):
                try:
                    UUID(value)
                    return True
                except ValueError:
                    return False
            return False

        # TITLE: Check student course registrations
        x_vars_keys = list(shared_variables.x_vars.keys())
        for i in range(min(3, len(x_vars_keys))):
            key = x_vars_keys[i]
            if not isinstance(key, tuple) or len(key) != 2:
                raise ValueError(f"Invalid x variable key format: {key}")
            exam_id, slot_id = key
            if not _is_valid_uuid(exam_id) or not _is_valid_uuid(slot_id):
                raise ValueError(
                    f"Non-UUID keys in x variables: {type(exam_id)}, {type(slot_id)}"
                )

        # TITLE: Sample x variables (exam_id, slot_id)
        y_vars_keys = list(shared_variables.y_vars.keys())
        for i in range(min(3, len(y_vars_keys))):
            key = y_vars_keys[i]
            if not isinstance(key, tuple) or len(key) != 3:
                raise ValueError(f"Invalid y variable key format: {key}")
            exam_id, room_id, slot_id = key
            if not all(_is_valid_uuid(k) for k in [exam_id, room_id, slot_id]):
                raise ValueError(
                    f"Non-UUID keys in y variables: {[type(k) for k in key]}"
                )

        # TITLE: Sample y variables (exam_id, room_id, slot_id)
        conflict_pairs = shared_variables.precomputed_data.get("conflict_pairs", set())
        conflict_pairs_list = list(conflict_pairs)
        for i in range(min(3, len(conflict_pairs_list))):
            pair = conflict_pairs_list[i]
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise ValueError(f"Invalid conflict pair format: {pair}")
            exam1, exam2 = pair
            if not _is_valid_uuid(exam1) or not _is_valid_uuid(exam2):
                raise ValueError(
                    f"Non-UUID conflict pair: {type(exam1)}, {type(exam2)}"
                )

        logger.info("Variable key consistency validation passed")

    def _validate_final_model(self) -> None:
        """Enhanced final model validation with GA integration awareness"""
        logger.info("Performing final GA-integrated model validation...")

        # TITLE: Log constraint application summary
        if not hasattr(self.model, "Proto"):
            raise RuntimeError("Invalid CP-SAT model - missing Proto method")

        # TITLE: Basic model validation
        try:
            proto = self.model.Proto()
            num_variables = len(proto.variables)
            num_constraints = len(proto.constraints)

            logger.info(f"Final model statistics:")
            logger.info(f"  Variables: {num_variables}")
            logger.info(f"  Constraints: {num_constraints}")

            if num_variables == 0:
                raise RuntimeError("Model has no variables!")
            if num_constraints == 0:
                logger.warning(
                    "Model has no constraints - this may be intentional for testing"
                )

        except Exception as e:
            logger.warning(f"Could not extract model statistics: {e}")

        # TITLE: Get model statistics
        if self.shared_variables:
            total_shared_vars = (
                len(self.shared_variables.x_vars)
                + len(self.shared_variables.z_vars)
                + len(self.shared_variables.y_vars)
                + len(self.shared_variables.u_vars)
            )
            logger.info(f"Shared variables: {total_shared_vars}")

            if total_shared_vars == 0:
                raise RuntimeError("No shared variables created!")

        logger.info("Final GA-integrated model validation passed")

    def get_build_statistics(self) -> Dict[str, Any]:
        """Get comprehensive build statistics including GA integration metrics"""
        stats = {
            "build_duration": self.build_duration,
            "model_valid": self.model is not None,
            "shared_variables_created": self.shared_variables is not None,
            "ga_integration_enabled": self.enable_ga_integration,
            "problem_entities": {
                "exams": len(self.problem.exams),
                "timeslots": len(self.problem.timeslots),
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
