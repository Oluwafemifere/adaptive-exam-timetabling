# scheduling_engine/cp_sat/solution_extractor.py

from collections import defaultdict
import logging
import traceback
from typing import TYPE_CHECKING, Dict, Set, Any, Optional, List, Tuple
from uuid import UUID

from scheduling_engine.core.solution import (
    TimetableSolution,
    ExamAssignment,
    AssignmentStatus,
    SolutionStatus,
)
from datetime import date, datetime

# --- START OF MODIFICATION ---
from backend.app.utils.celery_task_utils import task_progress_tracker

# --- END OF MODIFICATION ---


if TYPE_CHECKING:
    from scheduling_engine.core.problem_model import ExamSchedulingProblem, Exam


logger = logging.getLogger(__name__)


class SolutionExtractor:
    """Extractor for the two-phase (Timetable -> Full Pack) model."""

    def __init__(self, problem: "ExamSchedulingProblem", shared_vars, solver):
        self.problem = problem
        self.solver = solver
        self.shared_vars = shared_vars
        self.x_vars = shared_vars.x_vars
        self.y_vars = shared_vars.y_vars
        self.z_vars = shared_vars.z_vars
        self.w_vars = shared_vars.w_vars
        # --- START OF MODIFICATION ---
        self.task_context: Optional[Any] = None
        # --- END OF MODIFICATION ---

    def extract_phase1_solution(self) -> Dict[UUID, Tuple[UUID, date]]:
        """
        Extracts the result of the Phase 1 solve: a mapping of each exam
        to its assigned (start_slot_id, date).
        """
        if not self.has_solution():
            return {}

        exam_slot_map = {}
        for (exam_id, slot_id), x_var in self.x_vars.items():
            if self.solver.Value(x_var) == 1:
                day = self.problem.get_day_for_timeslot(slot_id)
                if day:
                    exam_slot_map[exam_id] = (slot_id, day.date)
                else:
                    logger.error(f"Could not find day for slot {slot_id}!")
        return exam_slot_map

    @task_progress_tracker(
        start_progress=80,
        end_progress=85,
        phase="extracting_solution",
        message="Extracting final assignments...",
    )
    async def extract_full_solution(
        self, final_solution: TimetableSolution, phase1_results: Dict
    ):
        """
        Extracts all room and invigilator assignments from the full Phase 2 model
        and populates the final solution object.
        """
        if not self.has_solution():
            logger.error("No solution found for the full Phase 2 model.")
            return

        # 1. Populate the time assignments from Phase 1 results
        for exam_id, (slot_id, day_date) in phase1_results.items():
            asm = ExamAssignment(
                exam_id=exam_id,
                time_slot_id=slot_id,
                assigned_date=day_date,
                status=AssignmentStatus.UNASSIGNED,
            )
            final_solution.assignments[exam_id] = asm

        # 2. Pre-calculate assigned rooms for each exam's occupied slots
        exam_room_map = defaultdict(lambda: defaultdict(list))
        for (exam_id, room_id, slot_id), y_var in self.y_vars.items():
            if self.solver.Value(y_var):
                exam_room_map[exam_id][slot_id].append(room_id)

        # 3. Pre-calculate assigned invigilators for each room and slot
        invigilator_room_map = defaultdict(lambda: defaultdict(set))
        for (inv_id, room_id, slot_id), w_var in self.w_vars.items():
            if self.solver.Value(w_var):
                invigilator_room_map[slot_id][room_id].add(inv_id)

        # 4. Assemble the final assignments
        for exam_id, assignment in final_solution.assignments.items():
            start_slot_id, _ = phase1_results.get(exam_id, (None, None))
            if not start_slot_id:
                continue

            occupied_slots = self.problem.get_occupancy_slots(exam_id, start_slot_id)

            # The rooms assigned are those from the start slot
            assigned_rooms = exam_room_map.get(exam_id, {}).get(start_slot_id, [])
            assignment.room_ids = assigned_rooms

            # The invigilators assigned are the union of all invigilators
            # in the assigned rooms across all occupied slots.
            assigned_invigilators = set()
            for slot_id in occupied_slots:
                for room_id in assigned_rooms:
                    invigilators_in_room = invigilator_room_map.get(slot_id, {}).get(
                        room_id, set()
                    )
                    assigned_invigilators.update(invigilators_in_room)

            assignment.invigilator_ids = list(assigned_invigilators)
            assignment.room_allocations = self.calculate_room_allocations(
                exam_id, set(assigned_rooms)
            )

            if assignment.is_complete():
                assignment.status = AssignmentStatus.ASSIGNED

    def has_solution(self) -> bool:
        """Checks if the solver found a valid solution."""
        try:
            status_name = self.solver.StatusName()
            return status_name in ["OPTIMAL", "FEASIBLE"]
        except Exception:
            return False

    def calculate_room_allocations(
        self, exam_id: UUID, rooms: Set[UUID]
    ) -> Dict[UUID, int]:
        """Calculate room allocations for an exam"""
        allocations = {}
        exam = self.problem.exams.get(exam_id)
        if not exam or not rooms:
            return {}

        students_to_allocate = exam.expected_students
        room_list = sorted(
            list(rooms),
            key=lambda r_id: self.problem.rooms[r_id].exam_capacity,
            reverse=True,
        )

        for i, room_id in enumerate(room_list):
            room = self.problem.rooms[room_id]
            if i == len(room_list) - 1:
                allocations[room_id] = students_to_allocate
            else:
                assigned = min(students_to_allocate, room.exam_capacity)
                allocations[room_id] = assigned
                students_to_allocate -= assigned
            if students_to_allocate <= 0:
                break
        return allocations
