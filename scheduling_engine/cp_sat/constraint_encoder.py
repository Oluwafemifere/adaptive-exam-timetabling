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
import multiprocessing
from itertools import product

from scheduling_engine.data_flow_tracker import track_data_flow
from scheduling_engine.genetic_algorithm import GAProcessor, GAInput, GAResult

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..core.problem_model import ExamSchedulingProblem, Invigilator


def _u_var_creation_worker(
    args: Tuple[List[Tuple], List[UUID], Dict[UUID, Set[UUID]]],
) -> List[Tuple]:
    """
    Worker function for parallel u_var creation.
    It receives only pickleable data and returns parameters for variable creation.
    """
    y_var_keys_chunk, invigilator_ids, invigilator_available_slots = args
    creation_params = []

    for exam_id, room_id, slot_id in y_var_keys_chunk:
        for inv_id in invigilator_ids:
            # The critical pruning step
            if (
                inv_id in invigilator_available_slots
                and slot_id not in invigilator_available_slots[inv_id]
            ):
                continue

            creation_params.append((inv_id, exam_id, room_id, slot_id))

    return creation_params


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
    Variable factory that supports optional pre-filtering of
    start time variables (X-vars) based on GA results.
    """

    def __init__(
        self,
        model,
        problem,
        promising_x_vars: Optional[Set] = None,
    ):
        self.model = model
        self.problem = problem
        self.variable_cache = {}
        self.stats = VariableCreationStats()
        self.creation_start_time = time.time()

        self.promising_x_vars = promising_x_vars
        self.filtering_enabled = promising_x_vars is not None

        if self.filtering_enabled:
            assert promising_x_vars is not None
            logger.info(
                f"VariableFactory initialized in FILTERING mode. Promising X-vars: {len(promising_x_vars)}"
            )
        else:
            logger.info("VariableFactory initialized in SIMPLE mode (no filtering).")

    def get_x_var(self, exam_id: UUID, slot_id: UUID):
        """Create X variable (exam start) only if it's in the promising set."""
        key = f"x_{exam_id}_{slot_id}"
        if self.filtering_enabled:
            assert self.promising_x_vars is not None
            if (exam_id, slot_id) not in self.promising_x_vars:
                return None  # Prune this variable

        if key not in self.variable_cache:
            self.variable_cache[key] = self.model.NewBoolVar(key)
            self.stats.x_vars_created += 1
        return self.variable_cache[key]

    def get_y_var(self, exam_id: UUID, room_id: UUID, slot_id: UUID):
        """Create Y variable (room assignment) without any filtering."""
        key = f"y_{exam_id}_{room_id}_{slot_id}"
        if key not in self.variable_cache:
            self.variable_cache[key] = self.model.NewBoolVar(key)
            self.stats.y_vars_created += 1
        return self.variable_cache[key]

    def get_u_var(
        self, invigilator_id: UUID, exam_id: UUID, room_id: UUID, slot_id: UUID
    ):
        """Create U variable (invigilator assignment) without any filtering."""
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
    now with an optional GA pre-filtering step for start times.
    """

    def __init__(self, problem, model, use_ga_filter: bool = True):
        self.problem = problem
        self.model = model
        self.factory: Optional[VariableFactory] = None
        self.use_ga_filter = use_ga_filter
        self.encoding_stats = defaultdict(float)

    @track_data_flow("encode_constraints", include_stats=True)
    def encode(self) -> SharedVariables:
        """Encoding process with optional GA filtering."""
        encoding_start_time = time.time()
        logger.info("Starting constraint encoding...")

        promising_x_vars: Optional[Set] = None
        if self.use_ga_filter:
            logger.info("GA pre-filtering is ENABLED. Running GAProcessor...")
            ga_start_time = time.time()
            ga_result = self._run_ga_pre_filter()
            ga_duration = time.time() - ga_start_time
            if ga_result:
                promising_x_vars = ga_result.promising_x_vars
                logger.info(f"GA run completed in {ga_duration:.2f}s.")
                logger.info(f"GA produced {len(promising_x_vars)} promising X-vars.")
            else:
                logger.warning(
                    "GA pre-filtering failed or returned no results. Falling back to simple mode."
                )

        self.initialize_factory(promising_x_vars)

        creation_start_time = time.time()
        variables = self.create_all_variables()
        self.encoding_stats["variable_creation_time"] = (
            time.time() - creation_start_time
        )

        if self.factory:
            self.factory.log_statistics()

        day_slot_groupings = self.build_day_slot_groupings()
        precomputed_data = {"day_slot_groupings": day_slot_groupings}

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

    def _run_ga_pre_filter(self) -> Optional[GAResult]:
        """Prepares input for the GA, runs it, and returns the results."""
        try:
            ga_input = GAInput(
                exam_ids=list(self.problem.exams.keys()),
                timeslot_ids=list(self.problem.timeslots.keys()),
                room_info={
                    rid: {"id": rid, "capacity": r.exam_capacity}
                    for rid, r in self.problem.rooms.items()
                },
                exam_info={
                    eid: {
                        "id": eid,
                        "size": e.expected_students,
                        "duration_minutes": e.duration_minutes,
                    }
                    for eid, e in self.problem.exams.items()
                },
                invigilator_info={
                    iid: {
                        "id": iid,
                        "availability_by_slot": set(self.problem.timeslots.keys()),
                    }
                    for iid, i in self.problem.invigilators.items()
                },
                student_exam_map=self._get_student_exam_mappings(),
                ga_params={
                    "pop_size": 100,
                    "generations": 50,
                    "cx_prob": 0.7,
                    "mut_prob": 0.2,
                    "mut_indpb": 0.05,
                    "tournsize": 3,
                    "top_n_pct": 0.2,
                    "max_exams_per_day": self.problem.max_exams_per_day,
                    "slot_duration_minutes": self.problem.base_slot_duration_minutes,
                    "slot_to_day_map": {
                        slot.id: day.id
                        for day in self.problem.days.values()
                        for slot in day.timeslots
                    },
                },
            )
            processor = GAProcessor(ga_input)
            return processor.run()
        except Exception as e:
            logger.error(f"GA pre-filtering process failed: {e}", exc_info=True)
            return None

    def _get_student_exam_mappings(self) -> Dict[UUID, List[UUID]]:
        """Helper to extract student-to-exam mappings for the GA."""
        student_map = defaultdict(list)
        for exam_id, exam in self.problem.exams.items():
            if hasattr(exam, "students"):
                for student_id in exam.students.keys():
                    student_map[student_id].append(exam_id)
        return dict(student_map)

    def initialize_factory(self, promising_x_vars: Optional[Set] = None):
        logger.info("Initializing VariableFactory...")
        self.factory = VariableFactory(
            model=self.model,
            problem=self.problem,
            promising_x_vars=promising_x_vars,
        )
        logger.info("VariableFactory initialized.")

    def create_all_variables(self) -> Dict[str, Dict]:
        """
        MODIFIED: Creates all variables for the model using a multi-stage cascading prune.
        1. Pruned X-vars are created based on GA output.
        2. A map of suitable rooms for each exam (based on capacity) is pre-computed.
        3. A set of potentially occupied slots is calculated from pruned X-vars.
        4. Y-vars are only created for (exam, slot) in the potential set AND for (exam, room) in the suitable map.
        5. A map of available slots for each invigilator is pre-computed.
        6. U-vars are created based on the final pruned set of Y-vars AND invigilator availability.
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

        # --- STAGE 1: Create pruned X-vars and all Z-vars ---
        for exam_id in self.problem.exams:
            for slot_id in self.problem.timeslots:
                x_var = self.factory.get_x_var(exam_id, slot_id)
                if x_var is not None:
                    variables["x"][(exam_id, slot_id)] = x_var

                variables["z"][(exam_id, slot_id)] = self.factory.get_z_var(
                    exam_id, slot_id
                )

        # --- OPTIMIZATION: STAGE 2: Pre-compute suitable rooms for each exam ---
        suitable_rooms_per_exam = defaultdict(list)
        for exam_id, exam in self.problem.exams.items():
            for room_id, room in self.problem.rooms.items():
                if room.exam_capacity >= exam.expected_students:
                    suitable_rooms_per_exam[exam_id].append(room_id)

        # --- STAGE 3: Pre-compute potential occupancy based on pruned X-vars ---
        potential_occupancy = set()
        for exam_id, start_slot_id in variables["x"].keys():
            day = self.problem.get_day_for_timeslot(start_slot_id)
            if not day:
                continue
            duration_slots = self.problem.get_exam_duration_in_slots(exam_id)
            try:
                start_index = [ts.id for ts in day.timeslots].index(start_slot_id)
                for i in range(duration_slots):
                    if start_index + i < len(day.timeslots):
                        occupied_slot_id = day.timeslots[start_index + i].id
                        potential_occupancy.add((exam_id, occupied_slot_id))
            except ValueError:
                continue

        # --- STAGE 4: Create Y-vars using BOTH potential occupancy and suitable rooms ---
        for exam_id, slot_id in potential_occupancy:
            for room_id in suitable_rooms_per_exam.get(exam_id, []):
                y_var = self.factory.get_y_var(exam_id, room_id, slot_id)
                if y_var is not None:
                    variables["y"][(exam_id, room_id, slot_id)] = y_var

        # --- Other variable creation ---
        for room_id, room in self.problem.rooms.items():
            for slot_id in self.problem.timeslots:
                variables["unused_seats"][(room_id, slot_id)] = (
                    self.factory.get_unused_seats_var(
                        room_id, slot_id, room.exam_capacity
                    )
                )

        # --- START OF FIX #2: Correctly calculate invigilator availability ---
        invigilator_available_slots = defaultdict(set)
        if invigilators:
            logger.info(
                "Pre-computing invigilator availability for slot-based pruning..."
            )
            for inv_id, invigilator in invigilators.items():
                # unavailability_data is a dict like: { 'YYYY-MM-DD': ['Morning', 'Evening'] }
                unavailability_data = getattr(invigilator, "availability", {})

                # Iterate through all possible timeslots in the problem
                for day in self.problem.days.values():
                    day_str = str(day.date)
                    unavailable_periods_for_day = unavailability_data.get(day_str, [])

                    for timeslot in day.timeslots:
                        # A slot is unavailable if its period name is in the list for that day, or if 'all' is listed.
                        is_unavailable = (
                            "all" in unavailable_periods_for_day
                            or timeslot.name in unavailable_periods_for_day
                        )

                        # If the slot is NOT unavailable, it is available.
                        if not is_unavailable:
                            invigilator_available_slots[inv_id].add(timeslot.id)
            logger.info(
                f"Built availability map for {len(invigilator_available_slots)} invigilators."
            )
        # --- END OF FIX #2 ---

        # --- STAGE 6 - Parallel U-Var Creation ---
        if invigilators:
            for inv_id in invigilators:
                for day_id in self.problem.days:
                    variables["daily_exam_counts"][(inv_id, day_id)] = (
                        self.factory.get_daily_exam_count_var(inv_id, day_id)
                    )

            logger.info(
                f"Preparing to create U-variables in PARALLEL using {multiprocessing.cpu_count()} cores..."
            )

            # 1. Get ONLY the keys of y_vars, which are pickleable
            y_var_keys = list(variables["y"].keys())

            # 2. Determine number of processes and create chunks of keys
            num_processes = (
                min(multiprocessing.cpu_count(), len(y_var_keys)) if y_var_keys else 1
            )

            all_u_var_params = []
            # --- START OF FIX #1: Prevent multiprocessing crash on Windows ---
            # Using multiprocessing.Pool inside a Celery task on Windows is problematic
            # due to how modules are pickled and imported in spawned processes ('spawn' vs 'fork').
            # Forcing serial execution on Windows is the most robust fix to prevent crashes.
            if sys.platform != "win32" and num_processes > 1 and len(y_var_keys) > 100:
                # --- END OF FIX #1 ---
                chunk_size = (len(y_var_keys) + num_processes - 1) // num_processes
                chunks = [
                    y_var_keys[i : i + chunk_size]
                    for i in range(0, len(y_var_keys), chunk_size)
                ]

                # 3. Prepare arguments with only pickleable data
                worker_args = [
                    (chunk, list(invigilators.keys()), invigilator_available_slots)
                    for chunk in chunks
                ]

                # 4. Run the parallel pool
                with multiprocessing.Pool(processes=num_processes) as pool:
                    results = pool.map(_u_var_creation_worker, worker_args)

                all_u_var_params = [param for sublist in results for param in sublist]

            else:  # Fallback to serial for single-core or small workloads
                logger.info(
                    "Workload is small, single-core/Windows detected, or multiprocessing is disabled; creating U-variables serially."
                )
                all_u_var_params = _u_var_creation_worker(
                    (y_var_keys, list(invigilators.keys()), invigilator_available_slots)
                )

            # 5. Centralized variable creation in the main process
            logger.info(
                f"Received {len(all_u_var_params)} parameter sets for U-var creation. Now creating variables..."
            )
            for params in all_u_var_params:
                u_var = self.factory.get_u_var(*params)
                if u_var is not None:
                    variables["u"][params] = u_var

            logger.info(f"Successfully created {len(variables['u'])} u_vars.")

        return variables

    def build_day_slot_groupings(self) -> Dict[str, List[UUID]]:
        day_slot_groupings = {}
        for day_id, day in self.problem.days.items():
            slot_ids = [timeslot.id for timeslot in day.timeslots]
            day_slot_groupings[str(day_id)] = slot_ids
        return day_slot_groupings
