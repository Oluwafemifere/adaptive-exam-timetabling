# scheduling_engine/cp_sat/constraint_encoder.py
# UPDATED: constraint_encoder.py with filtering and pruning removed
# Constraint encoder with simplified variable creation (no filtering)
# scheduling_engine\cp_sat\constraint_encoder.py
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
    Simplified variable factory without any filtering or pruning.
    Creates all variables unconditionally.
    """

    def __init__(self, model, problem):
        self.model = model
        self.problem = problem
        self.variable_cache = {}
        self.stats = VariableCreationStats()
        self.creation_start_time = time.time()
        logger.info("SimpleVariableFactory initialized (no filtering)")

    def get_x_var(self, exam_id: UUID, slot_id: UUID):
        """Create X variable (exam start) without filtering"""
        key = f"x_{exam_id}_{slot_id}"
        if key not in self.variable_cache:
            self.variable_cache[key] = self.model.NewBoolVar(key)
            self.stats.x_vars_created += 1
        return self.variable_cache[key]

    def get_y_var(self, exam_id: UUID, room_id: UUID, slot_id: UUID):
        """Create Y variable (room assignment) without filtering"""
        key = f"y_{exam_id}_{room_id}_{slot_id}"
        if key not in self.variable_cache:
            self.variable_cache[key] = self.model.NewBoolVar(key)
            self.stats.y_vars_created += 1
        return self.variable_cache[key]

    def get_u_var(
        self, invigilator_id: UUID, exam_id: UUID, room_id: UUID, slot_id: UUID
    ):
        """Create U variable (invigilator assignment) without filtering"""
        key = f"u_{invigilator_id}_{exam_id}_{room_id}_{slot_id}"
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

        logger.info("=== SIMPLE VARIABLE FACTORY STATISTICS ===")
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
    Constraint encoder without any filtering or pruning functionality.
    Creates all variables unconditionally and relies on the solver to handle infeasibilities.
    """

    def __init__(self, problem, model):
        self.problem = problem
        self.model = model
        self.factory: Optional[VariableFactory] = None

        # Performance tracking
        self.encoding_stats = {
            "total_time": 0.0,
            "variable_creation_time": 0.0,
            "constraint_creation_time": 0.0,
        }

    @track_data_flow("encode_constraints", include_stats=True)
    def encode(self) -> SharedVariables:
        """Simple encoding without filtering"""
        encoding_start_time = time.time()
        logger.info("Starting simple constraint encoding (no filtering)...")

        try:
            # Step 1: Initialize simple factory
            self.initialize_simple_factory()

            # Step 2: Create all variables without filtering
            creation_start_time = time.time()
            variables = self.create_all_variables()
            self.encoding_stats["variable_creation_time"] = (
                time.time() - creation_start_time
            )

            # Step 3: Create basic constraints
            constraint_start_time = time.time()
            self._add_basic_constraints(variables)
            self.encoding_stats["constraint_creation_time"] = (
                time.time() - constraint_start_time
            )

            # Step 4: Build precomputed data
            day_slot_groupings = self.build_day_slot_groupings()
            precomputed_data = {"day_slot_groupings": day_slot_groupings}

            # Step 5: Create final shared variables structure
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
                # --- START OF FIX for Soft Constraints ---
                unused_seats_vars=MappingProxyType(variables["unused_seats"]),
                daily_exam_count_vars=MappingProxyType(variables["daily_exam_counts"]),
                # --- END OF FIX for Soft Constraints ---
                precomputed_data=MappingProxyType(precomputed_data),
                variable_creation_stats=factory_stats,
            )

            self.encoding_stats["total_time"] = time.time() - encoding_start_time

            logger.info(
                f"Simple encoding completed in {self.encoding_stats['total_time']:.2f}s"
            )
            self._log_performance_breakdown()

            return shared_variables

        except Exception as e:
            logger.error(f"Simple encoding failed: {e}")
            raise

    def create_all_variables(self) -> Dict[str, Dict]:
        """Create all variables with enhanced logging"""
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

        # Log available entities
        logger.info(f"Available entities for variable creation:")
        logger.info(f"  - Exams: {len(self.problem.exams)}")
        logger.info(f"  - Timeslots: {len(self.problem.timeslots)}")
        logger.info(f"  - Rooms: {len(self.problem.rooms)}")
        logger.info(f"  - Days: {len(self.problem.days)}")

        # Check for invigilators - FIXED: Use proper attribute access
        invigilators = getattr(self.problem, "invigilators", {})
        if not invigilators:
            # Also check for instructors and staff that can be used as invigilators
            if hasattr(self.problem, "instructors"):
                invigilators.update(getattr(self.problem, "instructors", {}))
            if hasattr(self.problem, "staff"):
                invigilators.update(getattr(self.problem, "staff", {}))

        logger.info(f"  - Invigilators: {len(invigilators)}")

        if not invigilators:
            logger.warning("NO INVIGILATORS FOUND - U variables will not be created!")
        else:
            logger.info(f"Found {len(invigilators)} potential invigilators")

        # Create all X and Z variables
        for exam_id in self.problem.exams:
            for slot_id in self.problem.timeslots:
                variables["x"][(exam_id, slot_id)] = self.factory.get_x_var(
                    exam_id, slot_id
                )
                variables["z"][(exam_id, slot_id)] = self.factory.get_z_var(
                    exam_id, slot_id
                )

        # Create all Y variables
        for exam_id in self.problem.exams:
            for room_id in self.problem.rooms:
                for slot_id in self.problem.timeslots:
                    variables["y"][(exam_id, room_id, slot_id)] = (
                        self.factory.get_y_var(exam_id, room_id, slot_id)
                    )

        # Create all U variables (only if invigilators exist) - FIXED
        if invigilators:
            for inv_id in invigilators:
                for exam_id in self.problem.exams:
                    for room_id in self.problem.rooms:
                        for slot_id in self.problem.timeslots:
                            variables["u"][(inv_id, exam_id, room_id, slot_id)] = (
                                self.factory.get_u_var(
                                    inv_id, exam_id, room_id, slot_id
                                )
                            )
            logger.info(f"Created U variables for {len(invigilators)} invigilators")
        else:
            logger.warning("No invigilators found - U variables will be missing!")

        # --- START OF FIX for Soft Constraints ---
        # Create unused_seats_vars
        for room_id, room in self.problem.rooms.items():
            for slot_id in self.problem.timeslots:
                variables["unused_seats"][(room_id, slot_id)] = (
                    self.factory.get_unused_seats_var(
                        room_id, slot_id, room.exam_capacity
                    )
                )

        # Create daily_exam_count_vars
        if invigilators:
            for inv_id in invigilators:
                for day_id in self.problem.days:
                    variables["daily_exam_counts"][(inv_id, day_id)] = (
                        self.factory.get_daily_exam_count_var(inv_id, day_id)
                    )
        # --- END OF FIX for Soft Constraints ---

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

    def _add_basic_constraints(self, variables):
        """Add basic constraints without filtering awareness"""
        logger.info("Adding basic constraints...")
        constraints_added = 0

        # Basic binding constraints: sum(Y_vars) = X_var for each exam-slot
        for exam_id in self.problem.exams:
            for slot_id in self.problem.timeslots:
                # Get all room variables for this exam-slot
                room_vars = []
                for room_id in self.problem.rooms:
                    y_key = (exam_id, room_id, slot_id)
                    if y_key in variables["y"]:
                        room_vars.append(variables["y"][y_key])

                # Add binding constraint if we have room variables
                if room_vars:
                    x_key = (exam_id, slot_id)
                    if x_key in variables["x"]:
                        x_var = variables["x"][x_key]
                        self.model.Add(sum(room_vars) == x_var)
                        constraints_added += 1

        logger.info(f"Added {constraints_added} basic constraints")

    def _log_performance_breakdown(self):
        """Log basic performance breakdown"""
        total_time = self.encoding_stats["total_time"]
        if total_time == 0:
            total_time = 1e-6  # Avoid division by zero
        logger.info("=== ENCODING PERFORMANCE BREAKDOWN ===")
        logger.info(
            f"Variable creation: {self.encoding_stats['variable_creation_time']:.2f}s "
            f"({100 * self.encoding_stats['variable_creation_time'] / total_time:.1f}%)"
        )
        logger.info(
            f"Constraint creation: {self.encoding_stats['constraint_creation_time']:.2f}s "
            f"({100 * self.encoding_stats['constraint_creation_time'] / total_time:.1f}%)"
        )
        logger.info(f"Total encoding time: {total_time:.2f}s")

        # Log factory statistics
        if self.factory:
            self.factory.log_statistics()
