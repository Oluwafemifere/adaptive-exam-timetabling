# scheduling_engine/cp_sat/constraint_encoder.py
# UPDATED: constraint_encoder.py with filtering and pruning removed
# Constraint encoder with simplified variable creation (no filtering)
# scheduling_engine\cp_sat\constraint_encoder.py
from collections import defaultdict
from typing import TYPE_CHECKING
from datetime import date, timedelta
from types import MappingProxyType
from ortools.sat.python import cp_model
from dataclasses import dataclass
from typing import Dict, Set, Any, List, Optional, Union, Tuple
import logging
import math
import uuid
from uuid import UUID
import random
import time
import psutil
import os
import sys
import platform

from scheduling_engine.data_flow_tracker import track_data_flow

# Add GA imports for pre-filtering
from scheduling_engine.genetic_algorithm import GAProcessor, GAInput, GAResult


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..core.problem_model import ExamSchedulingProblem, Invigilator


@dataclass
class VariableCreationStats:
    """Basic statistics for variable creation"""

    x_vars_created: int = 0
    y_vars_created: int = 0
    z_vars_created: int = 0
    u_vars_created: int = 0
    # --- START OF FIX for Soft Constraints ---
    unused_seats_vars_created: int = 0
    daily_exam_count_vars_created: int = 0
    # --- END OF FIX for Soft Constraints ---
    creation_time: float = 0.0


class VariableFactory:
    """
    MODIFIED: Variable factory that now supports optional pre-filtering based on GA results.
    """

    def __init__(
        self,
        model,
        problem,
        viable_y_vars: Optional[Set] = None,
        viable_u_vars: Optional[Set] = None,
    ):
        self.model = model
        self.problem = problem
        self.variable_cache = {}
        self.stats = VariableCreationStats()
        self.creation_start_time = time.time()

        self.viable_y_vars = viable_y_vars
        self.viable_u_vars = viable_u_vars
        self.filtering_enabled = viable_y_vars is not None and viable_u_vars is not None

        if self.filtering_enabled:
            # Add type assertions to help the type checker
            assert viable_y_vars is not None
            assert viable_u_vars is not None
            logger.info(
                f"VariableFactory initialized in FILTERING mode. Viable Y: {len(viable_y_vars)}, Viable U: {len(viable_u_vars)}"
            )
        else:
            logger.info("VariableFactory initialized in SIMPLE mode (no filtering).")

    def get_x_var(self, exam_id: UUID, slot_id: UUID):
        """Create X variable (exam start) without filtering"""
        key = f"x_{exam_id}_{slot_id}"
        if key not in self.variable_cache:
            self.variable_cache[key] = self.model.NewBoolVar(key)
            self.stats.x_vars_created += 1
        return self.variable_cache[key]

    def get_y_var(self, exam_id: UUID, room_id: UUID, slot_id: UUID):
        """MODIFIED: Create Y variable (room assignment) only if it's in the viable set."""
        key = f"y_{exam_id}_{room_id}_{slot_id}"
        # If filtering is on, only create variables present in the viable set.
        if self.filtering_enabled:
            # Add type assertion to help the type checker
            assert self.viable_y_vars is not None
            if (exam_id, room_id, slot_id) not in self.viable_y_vars:
                return None

        if key not in self.variable_cache:
            self.variable_cache[key] = self.model.NewBoolVar(key)
            self.stats.y_vars_created += 1
        return self.variable_cache[key]

    def get_u_var(
        self, invigilator_id: UUID, exam_id: UUID, room_id: UUID, slot_id: UUID
    ):
        """MODIFIED: Create U variable (invigilator assignment) only if it's in the viable set."""
        key = f"u_{invigilator_id}_{exam_id}_{room_id}_{slot_id}"

        # If filtering is on, only create variables present in the viable set.
        if self.filtering_enabled:
            # Add type assertion to help the type checker
            assert self.viable_u_vars is not None
            if (invigilator_id, exam_id, room_id, slot_id) not in self.viable_u_vars:
                return None

        if key not in self.variable_cache:
            self.variable_cache[key] = self.model.NewBoolVar(key)
            self.stats.u_vars_created += 1
        return self.variable_cache[key]

    def get_z_var(self, exam_id: UUID, slot_id: UUID):
        """Create Z variable (occupancy) without filtering"""
        key = f"z_{exam_id}_{slot_id}"
        if key not in self.variable_cache:
            self.variable_cache[key] = self.model.NewBoolVar(key)
            self.stats.z_vars_created += 1
        return self.variable_cache[key]

    # --- START OF FIX for Soft Constraints ---
    def get_unused_seats_var(self, room_id: UUID, slot_id: UUID, room_capacity: int):
        """Create IntVar for unused seats in a room during a timeslot."""
        key = f"unused_seats_{room_id}_{slot_id}"
        if key not in self.variable_cache:
            # The number of unused seats can range from 0 to the room's total capacity.
            self.variable_cache[key] = self.model.NewIntVar(0, room_capacity, key)
            self.stats.unused_seats_vars_created += 1
        return self.variable_cache[key]

    def get_daily_exam_count_var(self, invigilator_id: UUID, day_id: UUID):
        """Create IntVar for the number of exams an invigilator works on a given day."""
        key = f"daily_exams_{invigilator_id}_{day_id}"
        if key not in self.variable_cache:
            # Assuming max 3 slots per day, an invigilator can't have more than 3 assignments.
            self.variable_cache[key] = self.model.NewIntVar(0, 3, key)
            self.stats.daily_exam_count_vars_created += 1
        return self.variable_cache[key]

    # --- END OF FIX for Soft Constraints ---

    def get_creation_stats(self) -> VariableCreationStats:
        """Get basic variable creation statistics"""
        self.stats.creation_time = time.time() - self.creation_start_time
        return self.stats

    def log_statistics(self):
        """Log basic statistics"""
        stats = self.get_creation_stats()
        total_vars = (
            stats.x_vars_created
            + stats.y_vars_created
            + stats.u_vars_created
            + stats.z_vars_created
            + stats.unused_seats_vars_created
            + stats.daily_exam_count_vars_created
        )

        logger.info("=== VARIABLE FACTORY STATISTICS ===")
        logger.info(f"X Variables: {stats.x_vars_created}")
        logger.info(f"Y Variables: {stats.y_vars_created}")
        logger.info(f"U Variables: {stats.u_vars_created}")
        logger.info(f"Z Variables: {stats.z_vars_created}")
        logger.info(f"Unused Seats Variables: {stats.unused_seats_vars_created}")
        logger.info(
            f"Daily Exam Count Variables: {stats.daily_exam_count_vars_created}"
        )
        logger.info(f"Total creation time: {stats.creation_time:.2f}s")
        logger.info(f"Total variables created: {total_vars}")


@dataclass(frozen=True)
class SharedVariables:
    """Shared variables with UUID key types"""

    x_vars: MappingProxyType  # (exam_id: UUID, slot_id: UUID) -> BoolVar
    z_vars: MappingProxyType  # (exam_id: UUID, slot_id: UUID) -> BoolVar
    y_vars: MappingProxyType  # (exam_id: UUID, room_id: UUID, slot_id: UUID) -> BoolVar
    u_vars: MappingProxyType  # (invigilator_id: UUID, exam_id: UUID, room_id: UUID, slot_id: UUID) -> BoolVar
    # --- START OF FIX for Soft Constraints ---
    unused_seats_vars: MappingProxyType  # (room_id: UUID, slot_id: UUID) -> IntVar
    daily_exam_count_vars: (
        MappingProxyType  # (invigilator_id: UUID, day_id: UUID) -> IntVar
    )
    # --- END OF FIX for Soft Constraints ---
    precomputed_data: MappingProxyType  # All precomputed data
    variable_creation_stats: VariableCreationStats  # Variable creation statistics


class ConstraintEncoder:
    """
    MODIFIED: This class now orchestrates the hybrid GA + CP-SAT approach,
    using the GA to pre-filter the variable space before building the CP-SAT model.
    """

    def __init__(self, problem, model, use_ga_filter: bool = False):
        self.problem = problem
        self.model = model
        self.factory: Optional[VariableFactory] = None
        self.use_ga_filter = use_ga_filter
        # Performance tracking
        self.encoding_stats = {
            "total_time": 0.0,
            "variable_creation_time": 0.0,
            "constraint_creation_time": 0.0,
            "ga_filtering_time": 0.0,
        }

    @track_data_flow("encode_constraints", include_stats=True)
    def encode(self) -> SharedVariables:
        """MODIFIED: Encoding process now includes an optional GA pre-filtering stage."""
        encoding_start_time = time.time()
        logger.info("Starting constraint encoding...")

        try:

            ga_results = None
            if self.use_ga_filter:
                ga_start_time = time.time()
                ga_results = self._run_ga_pre_filter()
                self.encoding_stats["ga_filtering_time"] = time.time() - ga_start_time

                # If the GA's best fitness is effectively zero, its results are unreliable.
                # Discard the pruned sets to fall back to the full variable space.
                # A small epsilon is used to handle floating point inaccuracies.
                best_fitness = ga_results.get("stats", {}).get("best_fitness", 0.0)
                FITNESS_THRESHOLD = 1e-6
                if best_fitness < FITNESS_THRESHOLD:
                    logger.warning(
                        f"GA performance is poor (Best Fitness: {best_fitness:.4f}). "
                        f"Discarding GA results and falling back to a full CP-SAT search. "
                        f"This may be slow."
                    )
                    ga_results["viable_y_vars"] = None
                    ga_results["viable_u_vars"] = None
                    # We can still keep the search hints, as they guide but don't restrict.

            viable_y_vars = ga_results.get("viable_y_vars") if ga_results else None
            viable_u_vars = ga_results.get("viable_u_vars") if ga_results else None
            search_hints = ga_results.get("search_hints", []) if ga_results else {}

            self.initialize_factory(
                viable_y_vars=viable_y_vars, viable_u_vars=viable_u_vars
            )

            # Create variables (now filtered if GA was used)
            creation_start_time = time.time()
            variables = self.create_all_variables()
            self.encoding_stats["variable_creation_time"] = (
                time.time() - creation_start_time
            )

            # Create basic constraints
            constraint_start_time = time.time()
            self._add_basic_constraints(variables)
            self.encoding_stats["constraint_creation_time"] = (
                time.time() - constraint_start_time
            )

            # Add search hints from GA if available
            if search_hints:
                for exam_id, slot_id in search_hints.items():
                    x_var_key = (exam_id, slot_id)
                    if x_var_key in variables["x"]:
                        self.model.AddHint(variables["x"][x_var_key], 1)
                logger.info(f"Added {len(search_hints)} search hints to the model.")

            # Build precomputed data, now including search hints from GA
            day_slot_groupings = self.build_day_slot_groupings()
            precomputed_data = {
                "day_slot_groupings": day_slot_groupings,
                "search_hints": search_hints,
            }

            factory_stats = (
                self.factory.get_creation_stats()
                if self.factory
                else VariableCreationStats()
            )

            shared_variables = SharedVariables(
                x_vars=MappingProxyType(variables["x"]),
                y_vars=MappingProxyType(variables["y"]),
                z_vars=MappingProxyType(variables["z"]),
                u_vars=MappingProxyType(variables["u"]),
                unused_seats_vars=MappingProxyType(variables["unused_seats"]),
                daily_exam_count_vars=MappingProxyType(variables["daily_exam_counts"]),
                precomputed_data=MappingProxyType(precomputed_data),
                variable_creation_stats=factory_stats,
            )

            self.encoding_stats["total_time"] = time.time() - encoding_start_time

            logger.info(
                f"Encoding completed in {self.encoding_stats['total_time']:.2f}s"
            )
            self._log_performance_breakdown()

            return shared_variables

        except Exception as e:
            logger.error(f"Encoding failed: {e}")
            raise

    def initialize_factory(
        self, viable_y_vars: Optional[Set] = None, viable_u_vars: Optional[Set] = None
    ):
        """MODIFIED: Initialize variable factory with optional filtering sets."""
        logger.info("Initializing VariableFactory...")
        self.factory = VariableFactory(
            model=self.model,
            problem=self.problem,
            viable_y_vars=viable_y_vars,
            viable_u_vars=viable_u_vars,
        )
        logger.info("VariableFactory initialized.")

    def _run_ga_pre_filter(self) -> Dict[str, Any]:
        """
        MODIFIED: Runs the GA pre-filter to get viable variables and search hints.
        """
        logger.info("Running GA pre-filter to prune variable space...")
        start_time = time.time()

        try:
            # 1. Prepare GAInput from the problem model
            exam_info = {
                eid: {
                    "id": eid,
                    "size": exam.expected_students,
                    "required_features": [],
                }
                for eid, exam in self.problem.exams.items()
            }
            room_info = {
                rid: {"id": rid, "capacity": room.exam_capacity, "features": []}
                for rid, room in self.problem.rooms.items()
            }

            # --- START OF FIX ---
            # Create slot_to_day_map for the GA to be aware of daily constraints
            slot_to_day_map = {}
            for day_id, day in self.problem.days.items():
                for timeslot in day.timeslots:
                    slot_to_day_map[timeslot.id] = day_id

            # Define GA-specific penalty weights, can be tuned
            ga_penalty_weights = {
                "student_conflict": 1000.0,
                "room_over_capacity": 100.0,
                "invigilator_shortage": 500.0,  # New penalty
                "max_exams_per_day": 750.0,  # New penalty
            }

            # Extract student-exam mapping from the problem model
            student_exam_map = defaultdict(list)
            course_to_exam_map = {
                exam.course_id: exam_id for exam_id, exam in self.problem.exams.items()
            }
            for student_id, course_ids in self.problem._student_courses.items():
                for course_id in course_ids:
                    if course_id in course_to_exam_map:
                        student_exam_map[student_id].append(
                            course_to_exam_map[course_id]
                        )
            # --- END OF FIX ---

            # This is a simplified availability map for the GA.
            all_slot_ids = list(self.problem.timeslots.keys())
            invigilator_info = {
                inv_id: {"id": inv_id, "availability_by_slot": all_slot_ids}
                for inv_id in getattr(self.problem, "invigilators", {})
            }

            ga_input = GAInput(
                exam_ids=list(self.problem.exams.keys()),
                timeslot_ids=all_slot_ids,
                exam_info=exam_info,
                room_info=room_info,
                invigilator_info=invigilator_info,
                student_exam_map=student_exam_map,
                # --- START OF FIX ---
                # Pass the new context and parameters to the GA
                ga_params={
                    "pop_size": 200,
                    "generations": 150,
                    "cx_prob": 0.6,
                    "mut_prob": 0.2,
                    "mut_indpb": 0.02,
                    "hint_threshold": 0.9,
                    "top_n_pct": 0.1,
                    "seed": 42,
                    "slot_to_day_map": slot_to_day_map,  # Pass day context
                    "max_exams_per_day": getattr(self.problem, "max_exams_per_day", 2),
                    "penalty_weights": ga_penalty_weights,  # Pass penalty weights
                },
                # --- END OF FIX ---
            )

            # 2. Instantiate and run the GAProcessor
            processor = GAProcessor(ga_input)
            ga_result = processor.run()

            # 3. Log results and return the required dictionary
            stats = ga_result.stats
            logger.info(f"GA pre-filter completed in {stats['runtime_seconds']:.2f}s.")
            logger.info(f"  - Viable Y-vars found: {stats['viable_y_vars_count']}")
            logger.info(f"  - Viable U-vars found: {stats['viable_u_vars_count']}")
            logger.info(f"  - High-confidence hints: {stats['search_hints_count']}")

            # If GA produces no viable variables, return empty sets to trigger fallback.
            if not ga_result.viable_y_vars:
                logger.warning(
                    "GA did not produce any viable Y variables. The CP-SAT model will use the full variable space."
                )
                return {
                    "viable_y_vars": set(),
                    "viable_u_vars": set(),
                    "search_hints": [],
                    "stats": ga_result.stats,  # --- FIX: Also return stats on empty result ---
                }

            # The search hints in the encoder are expected as a list of tuples (var, value)
            # but here we just pass the dict and let the main `encode` method handle it.
            return {
                "viable_y_vars": ga_result.viable_y_vars,
                "viable_u_vars": ga_result.viable_u_vars,
                "search_hints": ga_result.search_hints,
                "stats": ga_result.stats,  # --- FIX: Pass the full stats dictionary back ---
            }

        except Exception as e:
            logger.error(f"GA pre-filtering failed: {e}", exc_info=True)
            # On failure, return empty sets to allow the encoder to fall back
            # to creating all variables, ensuring the process doesn't halt.
            return {
                "viable_y_vars": None,
                "viable_u_vars": None,
                "search_hints": [],
                "stats": {},  # --- FIX: Return empty stats on failure ---
            }

    def _log_performance_breakdown(self):
        """MODIFIED: Log performance breakdown including GA stage."""
        total_time = self.encoding_stats["total_time"]
        if total_time == 0:
            total_time = 1e-6  # Avoid division by zero
        logger.info("=== ENCODING PERFORMANCE BREAKDOWN ===")

        if self.use_ga_filter:
            logger.info(
                f"GA pre-filtering: {self.encoding_stats['ga_filtering_time']:.2f}s "
                f"({100 * self.encoding_stats['ga_filtering_time'] / total_time:.1f}%)"
            )

        logger.info(
            f"Variable creation: {self.encoding_stats['variable_creation_time']:.2f}s "
            f"({100 * self.encoding_stats['variable_creation_time'] / total_time:.1f}%)"
        )
        logger.info(
            f"Constraint creation: {self.encoding_stats['constraint_creation_time']:.2f}s "
            f"({100 * self.encoding_stats['constraint_creation_time'] / total_time:.1f}%)"
        )
        logger.info(f"Total encoding time: {total_time:.2f}s")

        if self.factory:
            self.factory.log_statistics()

    # --- START OF OPTIMIZATION: RESTRUCTURED VARIABLE CREATION ---
    def create_all_variables(self) -> Dict[str, Dict]:
        """
        MODIFIED: Creates variables much more efficiently.
        If GA filtering is enabled, it iterates directly over the small sets of
        viable variables instead of all possible combinations.
        """
        if not self.factory:
            raise RuntimeError("Factory not initialized")

        variables = {
            "x": {},
            "y": {},
            "u": {},
            "z": {},
            "unused_seats": {},
            "daily_exam_counts": {},
        }
        invigilators = getattr(self.problem, "invigilators", {})
        logger.info(f"Found {len(invigilators)} potential invigilators.")

        # Always create all X and Z variables as they are fundamental.
        for exam_id in self.problem.exams:
            for slot_id in self.problem.timeslots:
                variables["x"][(exam_id, slot_id)] = self.factory.get_x_var(
                    exam_id, slot_id
                )
                variables["z"][(exam_id, slot_id)] = self.factory.get_z_var(
                    exam_id, slot_id
                )

        # Create soft-constraint variables
        for room_id, room in self.problem.rooms.items():
            for slot_id in self.problem.timeslots:
                variables["unused_seats"][(room_id, slot_id)] = (
                    self.factory.get_unused_seats_var(
                        room_id, slot_id, room.exam_capacity
                    )
                )
        if invigilators:
            for inv_id in invigilators:
                for day_id in self.problem.days:
                    variables["daily_exam_counts"][(inv_id, day_id)] = (
                        self.factory.get_daily_exam_count_var(inv_id, day_id)
                    )

        # OPTIMIZED: Create Y and U variables based on filtering mode
        if self.factory.filtering_enabled:
            logger.info("Creating Y and U variables from GA-pruned sets...")
            assert self.factory.viable_y_vars is not None
            assert self.factory.viable_u_vars is not None

            # Efficiently create Y variables by iterating over the viable set
            for exam_id, room_id, slot_id in self.factory.viable_y_vars:
                # The factory's get_y_var will handle caching and stats
                y_var = self.factory.get_y_var(exam_id, room_id, slot_id)
                if y_var is not None:
                    variables["y"][(exam_id, room_id, slot_id)] = y_var

            # Efficiently create U variables by iterating over the viable set
            if invigilators:
                for inv_id, exam_id, room_id, slot_id in self.factory.viable_u_vars:
                    u_var = self.factory.get_u_var(inv_id, exam_id, room_id, slot_id)
                    if u_var is not None:
                        variables["u"][(inv_id, exam_id, room_id, slot_id)] = u_var

        else:
            # Fallback: Create all possible Y and U variables if filtering is off
            logger.warning(
                "GA filtering disabled. Creating full set of Y and U variables. This will be slow."
            )
            for exam_id in self.problem.exams:
                for room_id in self.problem.rooms:
                    for slot_id in self.problem.timeslots:
                        y_var = self.factory.get_y_var(exam_id, room_id, slot_id)
                        if y_var is not None:
                            variables["y"][(exam_id, room_id, slot_id)] = y_var

            if invigilators:
                for inv_id in invigilators:
                    for exam_id in self.problem.exams:
                        for room_id in self.problem.rooms:
                            for slot_id in self.problem.timeslots:
                                u_var = self.factory.get_u_var(
                                    inv_id, exam_id, room_id, slot_id
                                )
                                if u_var is not None:
                                    variables["u"][
                                        (inv_id, exam_id, room_id, slot_id)
                                    ] = u_var
        # --- END OF OPTIMIZATION ---

        logger.info(
            f"Created all variables: X={len(variables['x'])}, Y={len(variables['y'])}, U={len(variables['u'])}, Z={len(variables['z'])}, "
            f"unused_seats={len(variables['unused_seats'])}, daily_exam_counts={len(variables['daily_exam_counts'])}"
        )
        return variables

    def initialize_simple_factory(self):
        """Initialize simple variable factory without filtering"""
        logger.info("Initializing simple factory (no filtering)...")
        self.factory = VariableFactory(model=self.model, problem=self.problem)
        logger.info("Simple factory initialized")

    def build_day_slot_groupings(self) -> Dict[str, List[UUID]]:
        """Build day-slot groupings from problem.days for constraint use."""
        day_slot_groupings = {}

        for day_id, day in self.problem.days.items():
            slot_ids = [timeslot.id for timeslot in day.timeslots]
            day_slot_groupings[str(day_id)] = slot_ids

        logger.info(f"Built day-slot groupings for {len(day_slot_groupings)} days")
        return day_slot_groupings

    # --- START OF OPTIMIZATION: MORE EFFICIENT CONSTRAINT CREATION ---

    def _add_basic_constraints(self, variables: Dict[str, Dict]):
        """
        MODIFIED: Adds basic binding constraints more efficiently by iterating
        over created variables instead of all possible combinations.
        """
        logger.info("Adding basic constraints...")
        constraints_added = 0

        # Group created Y variables by (exam_id, slot_id)
        y_vars_by_exam_slot = defaultdict(list)
        for (exam_id, room_id, slot_id), y_var in variables["y"].items():
            y_vars_by_exam_slot[(exam_id, slot_id)].append(y_var)

        # Create the binding constraint: sum(Y_ers) == X_es
        for (exam_id, slot_id), y_vars_list in y_vars_by_exam_slot.items():
            x_var = variables["x"].get((exam_id, slot_id))

            # --- START OF FIX ---
            # Changed from "if x_var:" to "if x_var is not None:" to avoid evaluating the symbolic literal.
            if x_var is not None:
                # --- END OF FIX ---
                self.model.Add(sum(y_vars_list) == x_var)
                constraints_added += 1

        logger.info(f"Added {constraints_added} basic binding constraints.")

    # --- END OF OPTIMIZATION ---
