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
        self,
        final_solution: TimetableSolution,
        phase1_results_for_group: Dict,
    ):
        """
        FIXED: Extracts assignments from a start-time-group subproblem and updates
        the final solution object. This now correctly populates room and invigilator
        assignments for the entire duration of each exam in the group.
        """
        if not self.has_solution():
            logger.error(
                "No solution found for the Phase 2 subproblem. Cannot extract."
            )
            return

        # 1. Extract all room assignments from the subproblem's y_vars.
        # This correctly identifies which rooms each exam is assigned to.
        # Key: exam_id, Value: set of room_ids
        exam_room_map = defaultdict(set)
        for (exam_id, room_id, slot_id), y_var in self.y_vars.items():
            if self.solver.Value(y_var):
                exam_room_map[exam_id].add(room_id)

        # 2. Extract invigilator assignments with full time-slot context.
        # The map is now correctly keyed by both room and slot to be time-aware.
        # Key: (room_id, slot_id), Value: set of invigilator_ids
        room_slot_invigilator_map = defaultdict(set)
        for (inv_id, room_id, slot_id), w_var in self.w_vars.items():
            if self.solver.Value(w_var):
                room_slot_invigilator_map[(room_id, slot_id)].add(inv_id)

        # 3. Update the final solution object for each exam in this start-time group.
        # This loop now correctly combines the above maps to find the right invigilators for each exam.
        for exam_id in phase1_results_for_group.keys():
            assignment = final_solution.assignments.get(exam_id)
            if not assignment:
                logger.warning(
                    f"Attempted to update a non-existent assignment for exam {exam_id}. Skipping."
                )
                continue

            assigned_rooms_set = exam_room_map.get(exam_id, set())
            if not assigned_rooms_set:
                logger.error(
                    f"CRITICAL: Solver found a solution, but no rooms were assigned to exam {exam_id}. The problem may be infeasible."
                )
                assignment.status = AssignmentStatus.INVALID
                continue

            # Determine the exact time slots this specific exam occupies using its start time from Phase 1
            start_slot_id = phase1_results_for_group[exam_id][0]
            occupied_slots = self.problem.get_occupancy_slots(exam_id, start_slot_id)

            # Collect all unique invigilators assigned to this exam's rooms ONLY during its occupied slots
            all_invigilators_for_this_exam = set()
            for room_id in assigned_rooms_set:
                for slot_id in occupied_slots:
                    # Look up invigilators for this specific room AT this specific slot
                    invigilators_in_room_at_time = room_slot_invigilator_map.get(
                        (room_id, slot_id), set()
                    )
                    all_invigilators_for_this_exam.update(invigilators_in_room_at_time)

            # Populate the assignment object with the correctly filtered data
            assignment.room_ids = list(assigned_rooms_set)
            assignment.invigilator_ids = list(all_invigilators_for_this_exam)
            assignment.room_allocations = self.calculate_room_allocations(
                exam_id, assigned_rooms_set
            )

            # Update status if all required fields are now present
            if assignment.is_complete():
                assignment.status = AssignmentStatus.ASSIGNED
            else:
                logger.warning(
                    f"Assignment for exam {exam_id} is still not complete after extraction."
                )

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
