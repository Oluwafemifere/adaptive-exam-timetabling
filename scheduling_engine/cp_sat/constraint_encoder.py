# scheduling_engine/cp_sat/constraint_encoder.py

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
    unused_seats_vars_created: int = 0
    daily_exam_count_vars_created: int = 0
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
        if self.filtering_enabled:
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

        if self.filtering_enabled:
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

    def get_unused_seats_var(self, room_id: UUID, slot_id: UUID, room_capacity: int):
        """Create IntVar for unused seats in a room during a timeslot."""
        key = f"unused_seats_{room_id}_{slot_id}"
        if key not in self.variable_cache:
            self.variable_cache[key] = self.model.NewIntVar(0, room_capacity, key)
            self.stats.unused_seats_vars_created += 1
        return self.variable_cache[key]

    def get_daily_exam_count_var(self, invigilator_id: UUID, day_id: UUID):
        """Create IntVar for the number of exams an invigilator works on a given day."""
        key = f"daily_exams_{invigilator_id}_{day_id}"
        if key not in self.variable_cache:
            self.variable_cache[key] = self.model.NewIntVar(
                0, 3, key
            )  # Assuming max 3 slots
            self.stats.daily_exam_count_vars_created += 1
        return self.variable_cache[key]

    def get_creation_stats(self) -> VariableCreationStats:
        self.stats.creation_time = time.time() - self.creation_start_time
        return self.stats

    def log_statistics(self):
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
        logger.info(
            f"Total variables created: {total_vars} in {stats.creation_time:.2f}s"
        )


@dataclass(frozen=True)
class SharedVariables:
    x_vars: MappingProxyType
    z_vars: MappingProxyType
    y_vars: MappingProxyType
    u_vars: MappingProxyType
    unused_seats_vars: MappingProxyType
    daily_exam_count_vars: MappingProxyType
    variable_creation_stats: VariableCreationStats
    precomputed_data: Dict[str, Any]


class ConstraintEncoder:
    """
    Orchestrates the creation of solver variables and constraints,
    now with HITL lock enforcement as a primary step.
    """

    def __init__(self, problem, model, use_ga_filter: bool = False):
        self.problem = problem
        self.model = model
        self.factory: Optional[VariableFactory] = None
        self.use_ga_filter = use_ga_filter
        self.encoding_stats = defaultdict(float)

    @track_data_flow("encode_constraints", include_stats=True)
    def encode(self) -> SharedVariables:
        """Encoding process with lock enforcement."""
        encoding_start_time = time.time()
        logger.info("Starting constraint encoding...")

        # For simplicity, this example will not run the GA filter
        self.initialize_factory()

        # Create all potential variables
        creation_start_time = time.time()
        variables = self.create_all_variables()
        self.encoding_stats["variable_creation_time"] = (
            time.time() - creation_start_time
        )

        # Create basic structural constraints
        constraint_start_time = time.time()
        self._add_basic_constraints(variables)
        self.encoding_stats["constraint_creation_time"] = (
            time.time() - constraint_start_time
        )

        day_slot_groupings = self.build_day_slot_groupings()
        precomputed_data = {"day_slot_groupings": day_slot_groupings}

        # FIX: Added a check to ensure self.factory is not None
        if not self.factory:
            raise RuntimeError("VariableFactory not initialized.")

        shared_variables = SharedVariables(
            x_vars=MappingProxyType(variables["x"]),
            y_vars=MappingProxyType(variables["y"]),
            z_vars=MappingProxyType(variables["z"]),
            u_vars=MappingProxyType(variables["u"]),
            unused_seats_vars=MappingProxyType(variables["unused_seats"]),
            daily_exam_count_vars=MappingProxyType(variables["daily_exam_counts"]),
            precomputed_data=precomputed_data,
            variable_creation_stats=self.factory.get_creation_stats(),
        )

        self.encoding_stats["total_time"] = time.time() - encoding_start_time
        logger.info(f"Encoding completed in {self.encoding_stats['total_time']:.2f}s")
        return shared_variables

    def initialize_factory(
        self, viable_y_vars: Optional[Set] = None, viable_u_vars: Optional[Set] = None
    ):
        logger.info("Initializing VariableFactory...")
        self.factory = VariableFactory(
            model=self.model,
            problem=self.problem,
            viable_y_vars=viable_y_vars,
            viable_u_vars=viable_u_vars,
        )
        logger.info("VariableFactory initialized.")

    def create_all_variables(self) -> Dict[str, Dict]:
        """Creates all variables for the model."""
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

        for exam_id in self.problem.exams:
            for slot_id in self.problem.timeslots:
                variables["x"][(exam_id, slot_id)] = self.factory.get_x_var(
                    exam_id, slot_id
                )
                variables["z"][(exam_id, slot_id)] = self.factory.get_z_var(
                    exam_id, slot_id
                )

        for room_id, room in self.problem.rooms.items():
            for slot_id in self.problem.timeslots:
                variables["unused_seats"][(room_id, slot_id)] = (
                    self.factory.get_unused_seats_var(
                        room_id, slot_id, room.exam_capacity
                    )
                )

        for exam_id in self.problem.exams:
            for room_id in self.problem.rooms:
                for slot_id in self.problem.timeslots:
                    y_var = self.factory.get_y_var(exam_id, room_id, slot_id)
                    if y_var is not None:
                        variables["y"][(exam_id, room_id, slot_id)] = y_var

        if invigilators:
            # First, create daily exam count vars (this is fine)
            for inv_id in invigilators:
                for day_id in self.problem.days:
                    variables["daily_exam_counts"][(inv_id, day_id)] = (
                        self.factory.get_daily_exam_count_var(inv_id, day_id)
                    )

            # CRITICAL FIX: Create u_vars based on valid y_vars
            for exam_id, room_id, slot_id in variables["y"].keys():
                for inv_id in invigilators:
                    u_var = self.factory.get_u_var(inv_id, exam_id, room_id, slot_id)
                    if u_var is not None:
                        variables["u"][(inv_id, exam_id, room_id, slot_id)] = u_var

        return variables

    def build_day_slot_groupings(self) -> Dict[str, List[UUID]]:
        day_slot_groupings = {}
        for day_id, day in self.problem.days.items():
            slot_ids = [timeslot.id for timeslot in day.timeslots]
            day_slot_groupings[str(day_id)] = slot_ids
        return day_slot_groupings

    def _add_basic_constraints(self, variables: Dict[str, Dict]):
        logger.info("Adding basic structural constraints...")
        y_vars_by_exam_slot = defaultdict(list)
        for (exam_id, room_id, slot_id), y_var in variables["y"].items():
            y_vars_by_exam_slot[(exam_id, slot_id)].append(y_var)

        for (exam_id, slot_id), y_vars_list in y_vars_by_exam_slot.items():
            x_var = variables["x"].get((exam_id, slot_id))
            if x_var is not None:
                self.model.Add(sum(y_vars_list) == x_var)
