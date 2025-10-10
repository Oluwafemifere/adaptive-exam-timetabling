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

from scheduling_engine.data_flow_tracker import track_data_flow
from scheduling_engine.genetic_algorithm import GAProcessor, GAInput, GAResult

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..core.problem_model import ExamSchedulingProblem, Invigilator, Exam


@dataclass
class VariableCreationStats:
    """Basic statistics for variable creation"""

    x_vars_created: int = 0
    y_vars_created: int = 0
    z_vars_created: int = 0
    # --- NEW: Simplified invigilator model ---
    w_vars_created: int = 0
    # --- Deprecated ---
    # task_vars_created: int = 0
    # assignment_vars_created: int = 0
    # u_vars_created: int = 0
    unused_seats_vars_created: int = 0
    daily_exam_count_vars_created: int = 0
    creation_time: float = 0.0


class VariableFactory:
    """
    MODIFIED Variable factory for the simplified invigilator model.
    """

    def __init__(
        self,
        model,
        problem,
    ):
        self.model = model
        self.problem = problem
        self.variable_cache = {}
        self.stats = VariableCreationStats()
        self.creation_start_time = time.time()
        logger.info("VariableFactory initialized.")

    def get_x_var(self, exam_id: UUID, slot_id: UUID):
        """Create X variable (exam start)."""
        key = f"x_{exam_id}_{slot_id}"
        if key not in self.variable_cache:
            self.variable_cache[key] = self.model.NewBoolVar(key)
            self.stats.x_vars_created += 1
        return self.variable_cache[key]

    def get_y_var(self, exam_id: UUID, room_id: UUID, slot_id: UUID):
        """Create Y variable (room assignment)."""
        key = f"y_{exam_id}_{room_id}_{slot_id}"
        if key not in self.variable_cache:
            self.variable_cache[key] = self.model.NewBoolVar(key)
            self.stats.y_vars_created += 1
        return self.variable_cache[key]

    def get_z_var(self, exam_id: UUID, slot_id: UUID):
        """Create Z variable (occupancy)."""
        key = f"z_{exam_id}_{slot_id}"
        if key not in self.variable_cache:
            self.variable_cache[key] = self.model.NewBoolVar(key)
            self.stats.z_vars_created += 1
        return self.variable_cache[key]

    # --- START OF NEW LOGIC ---
    def get_w_var(self, invigilator_id: UUID, room_id: UUID, slot_id: UUID):
        """Create W variable (invigilator assigned to a room in a slot)."""
        key = f"w_{invigilator_id}_{room_id}_{slot_id}"
        if key not in self.variable_cache:
            self.variable_cache[key] = self.model.NewBoolVar(key)
            self.stats.w_vars_created += 1
        return self.variable_cache[key]

    # --- END OF NEW LOGIC ---

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
            self.variable_cache[key] = self.model.NewIntVar(0, 5, key)
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
            + stats.z_vars_created
            + stats.w_vars_created
            + stats.unused_seats_vars_created
            + stats.daily_exam_count_vars_created
        )
        logger.info("=== FINAL VARIABLE CREATION STATISTICS ===")
        logger.info(f"Created {total_vars} variables in {stats.creation_time:.2f}s.")
        logger.info(f"  X (Starts): {stats.x_vars_created}")
        logger.info(f"  Y (Room Assign): {stats.y_vars_created}")
        logger.info(f"  Z (Occupancy): {stats.z_vars_created}")
        logger.info(f"  W (Invig-in-Room): {stats.w_vars_created}")
        logger.info(
            f"  Auxiliary: {stats.unused_seats_vars_created + stats.daily_exam_count_vars_created}"
        )


@dataclass(frozen=True)
class SharedVariables:
    x_vars: MappingProxyType
    z_vars: MappingProxyType
    y_vars: MappingProxyType
    # --- NEW: Simplified invigilator model ---
    w_vars: MappingProxyType  # Invigilator-in-room assignments
    # --- Deprecated ---
    # t_vars: MappingProxyType
    # a_vars: MappingProxyType
    # u_vars: MappingProxyType
    unused_seats_vars: MappingProxyType
    daily_exam_count_vars: MappingProxyType
    variable_creation_stats: VariableCreationStats
    precomputed_data: Dict[str, Any]


class ConstraintEncoder:
    """
    MODIFIED ConstraintEncoder for two-phase decomposition with heuristics.
    """

    def __init__(self, problem, model, use_ga_filter: bool = False):
        self.problem = problem
        self.model = model
        self.factory: Optional[VariableFactory] = None
        self.use_ga_filter = use_ga_filter
        self.encoding_stats = defaultdict(float)
        self.ga_result: Optional[GAResult] = None
        self.promising_x_vars: Optional[Set] = None

    @track_data_flow("encode_phase1", include_stats=True)
    def encode_phase1(self) -> SharedVariables:
        """Encodes variables for the Phase 1 (timetabling) model."""
        encoding_start_time = time.time()
        logger.info("Starting Phase 1 constraint encoding (Timetabling)...")
        self.initialize_factory()

        if self.use_ga_filter:
            logger.info("Genetic Algorithm pre-filter is enabled. Running GA...")
            self.ga_result = self._run_ga_pre_filter()
            if self.ga_result:
                self.promising_x_vars = self.ga_result.promising_x_vars
                logger.info(
                    f"GA pre-filter completed, found {len(self.promising_x_vars)} promising start variables."
                )
            else:
                logger.warning(
                    "GA pre-filter failed to produce results. Proceeding without filtering."
                )

        variables = self._create_phase1_variables(use_filter=self.use_ga_filter)
        if self.factory:
            self.factory.log_statistics()

        logger.info("Pre-computing day and slot groupings for constraint efficiency.")
        precomputed_data = {"day_slot_groupings": self.build_day_slot_groupings()}

        if not self.factory:
            raise RuntimeError("VariableFactory not initialized post-encoding.")

        shared_vars = SharedVariables(
            x_vars=MappingProxyType(variables["x"]),
            z_vars=MappingProxyType(variables["z"]),
            y_vars=MappingProxyType({}),
            w_vars=MappingProxyType({}),
            unused_seats_vars=MappingProxyType({}),
            daily_exam_count_vars=MappingProxyType({}),
            variable_creation_stats=self.factory.get_creation_stats(),
            precomputed_data=precomputed_data,
        )
        self.encoding_stats["phase1_total_time"] = time.time() - encoding_start_time
        logger.info(
            f"Phase 1 encoding complete in {self.encoding_stats['phase1_total_time']:.2f}s."
        )
        return shared_vars

    @track_data_flow("encode_phase2", include_stats=True)
    def encode_phase2_full(self, phase1_results: Dict) -> SharedVariables:
        """Encodes variables for the full Phase 2 (packing) model."""
        encoding_start_time = time.time()
        logger.info("Starting full Phase 2 encoding (Packing)...")
        self.initialize_factory()

        variables = self._create_full_phase2_variables(phase1_results)
        if self.factory:
            self.factory.log_statistics()

        if not self.factory:
            raise RuntimeError("VariableFactory not initialized post-encoding.")

        logger.info("Pre-computing data for Phase 2 constraints.")
        precomputed_data = {
            "day_slot_groupings": self.build_day_slot_groupings(),
            "phase1_results": phase1_results,  # Pass results for continuity constraints
        }

        shared_vars = SharedVariables(
            x_vars=MappingProxyType({}),
            z_vars=MappingProxyType({}),
            y_vars=MappingProxyType(variables["y"]),
            w_vars=MappingProxyType(variables["w"]),
            unused_seats_vars=MappingProxyType(variables["unused_seats"]),
            daily_exam_count_vars=MappingProxyType({}),
            variable_creation_stats=self.factory.get_creation_stats(),
            precomputed_data=precomputed_data,
        )
        self.encoding_stats["phase2_full_time"] = time.time() - encoding_start_time
        logger.info(
            f"Full Phase 2 encoding complete in {self.encoding_stats['phase2_full_time']:.2f}s."
        )
        return shared_vars

    def _create_phase1_variables(self, use_filter: bool) -> Dict[str, Dict]:
        """Creates X and Z variables for the timetabling phase."""
        if not self.factory:
            raise RuntimeError("Factory not initialized")

        variables: Dict[str, Dict] = {"x": {}, "z": {}}
        candidate_starts = self._get_candidate_starts(use_filter)
        logger.info(
            f"Creating X and Z variables for {len(candidate_starts)} candidate starts."
        )

        for exam_id, start_slot_id in candidate_starts:
            variables["x"][(exam_id, start_slot_id)] = self.factory.get_x_var(
                exam_id, start_slot_id
            )
            occupancy_slot_ids = self.problem.get_occupancy_slots(
                exam_id, start_slot_id
            )
            for occ_slot_id in occupancy_slot_ids:
                if (exam_id, occ_slot_id) not in variables["z"]:
                    variables["z"][(exam_id, occ_slot_id)] = self.factory.get_z_var(
                        exam_id, occ_slot_id
                    )

        logger.info(
            f"Initial creation: {len(variables['x'])} X-vars, {len(variables['z'])} Z-vars."
        )

        logger.info("Applying robust safety net for student conflict Z-variables...")
        student_exams = self._get_student_exam_mappings()
        new_z_vars_added = 0

        for student_id, exam_ids in student_exams.items():
            if len(exam_ids) <= 1:
                continue

            all_possible_slots = set()
            for exam_id in exam_ids:
                for slot_id in self.problem.timeslots:
                    if self.problem.is_start_feasible(exam_id, slot_id):
                        all_possible_slots.add(slot_id)

            for slot_id in all_possible_slots:
                for exam_id in exam_ids:
                    if (exam_id, slot_id) not in variables["z"]:
                        variables["z"][(exam_id, slot_id)] = self.factory.get_z_var(
                            exam_id, slot_id
                        )
                        new_z_vars_added += 1

        if new_z_vars_added > 0:
            logger.info(
                f"Safety net added {new_z_vars_added} new Z-variables to prevent missed conflicts."
            )
        else:
            logger.info("Safety net did not need to add any new Z-variables.")
        return variables

    def _create_full_phase2_variables(self, phase1_results: Dict) -> Dict[str, Dict]:
        """Creates Y and W variables for the entire schedule based on fixed times."""
        if not self.factory:
            raise RuntimeError("Factory not initialized")

        variables: Dict[str, Dict] = {"y": {}, "w": {}, "unused_seats": {}}
        logger.info(
            "Creating variables for the full packing model based on Phase 1 results..."
        )

        # Group exams by slot based on Phase 1 results to apply heuristics efficiently
        exams_by_slot = defaultdict(list)
        for exam_id, (start_slot_id, _) in phase1_results.items():
            exam = self.problem.exams.get(exam_id)
            if not exam:
                logger.warning(
                    f"Exam {exam_id} from phase 1 results not found in problem model."
                )
                continue
            occupied_slots = self.problem.get_occupancy_slots(exam_id, start_slot_id)
            for slot_id in occupied_slots:
                exams_by_slot[slot_id].append(exam)

        logger.info(
            f"Found exams scheduled in {len(exams_by_slot)} different time slots."
        )

        # Create variables slot by slot, but collect them all into the main dictionary
        for slot_id, exams_in_slot in exams_by_slot.items():
            logger.info(
                f"Creating variables for slot {slot_id} which has {len(exams_in_slot)} exams."
            )
            # Create Y (exam-in-room) variables for all exams occupying this slot
            for exam in exams_in_slot:
                for room_id in self.problem.rooms:
                    y_key = (exam.id, room_id, slot_id)
                    variables["y"][y_key] = self.factory.get_y_var(*y_key)

            # --- Apply Departmental Locality Heuristic for W-variables ---
            relevant_dept_ids = {
                did for exam in exams_in_slot for did in exam.department_ids
            }
            suitable_invigilators = [
                inv
                for inv in self.problem.invigilators.values()
                if getattr(inv, "department_id", None) in relevant_dept_ids
            ]

            log_msg = f"For slot {slot_id}, found {len(relevant_dept_ids)} relevant departments. "
            if not suitable_invigilators:
                suitable_invigilators = list(self.problem.invigilators.values())
                log_msg += f"No department-specific invigilators found; using all {len(suitable_invigilators)} invigilators."
            else:
                log_msg += f"Selected {len(suitable_invigilators)} suitable invigilators based on department."
            logger.info(log_msg)

            # Create W-vars and unused_seats for this slot
            for room_id, room in self.problem.rooms.items():
                variables["unused_seats"][(room_id, slot_id)] = (
                    self.factory.get_unused_seats_var(
                        room_id, slot_id, room.exam_capacity
                    )
                )
                for inv in suitable_invigilators:
                    if self.problem.is_invigilator_available(inv.id, slot_id):
                        w_key = (inv.id, room_id, slot_id)
                        variables["w"][w_key] = self.factory.get_w_var(*w_key)

        return variables

    def _get_candidate_starts(self, use_filter: bool) -> Set[Tuple[UUID, UUID]]:
        """Determines the set of (exam, slot) start variables to create."""
        if use_filter and self.promising_x_vars:
            logger.info(
                f"GA FILTER ENABLED: Planning variables based on {len(self.promising_x_vars)} promising starts."
            )
            return self.promising_x_vars
        else:
            all_starts = {
                (eid, sid)
                for eid in self.problem.exams
                for sid in self.problem.timeslots
                if self.problem.is_start_feasible(eid, sid)
            }
            logger.info(
                f"GA FILTER DISABLED: Planning for all {len(all_starts)} feasible starts."
            )
            return all_starts

    def _run_ga_pre_filter(self) -> Optional[GAResult]:
        try:
            logger.info("Constructing GAInput for pre-filtering...")
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
            logger.info("Running GAProcessor...")
            result = processor.run()
            logger.info("GAProcessor finished.")
            return result
        except Exception as e:
            logger.error(f"GA pre-filtering process failed: {e}", exc_info=True)
            return None

    def _get_student_exam_mappings(self) -> Dict[UUID, List[UUID]]:
        logger.info("Building student-to-exam mappings...")
        student_map = defaultdict(list)
        for exam_id, exam in self.problem.exams.items():
            if hasattr(exam, "students"):
                for student_id in exam.students.keys():
                    student_map[student_id].append(exam_id)
        logger.info(f"Created mappings for {len(student_map)} students.")
        return dict(student_map)

    def initialize_factory(self):
        logger.info("Re-initializing VariableFactory...")
        self.factory = VariableFactory(
            model=self.model,
            problem=self.problem,
        )

    def build_day_slot_groupings(self) -> Dict[str, List[UUID]]:
        logger.info("Building day-to-slot-ID groupings...")
        day_slot_groupings = {}
        for day_id, day in self.problem.days.items():
            slot_ids = [timeslot.id for timeslot in day.timeslots]
            day_slot_groupings[str(day_id)] = slot_ids
        logger.info(f"Grouped slots for {len(day_slot_groupings)} days.")
        return day_slot_groupings
