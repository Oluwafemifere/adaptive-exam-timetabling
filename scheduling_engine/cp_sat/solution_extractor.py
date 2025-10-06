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

if TYPE_CHECKING:
    from scheduling_engine.core.problem_model import ExamSchedulingProblem

logger = logging.getLogger(__name__)


class SolutionExtractor:
    """FIXED - Enhanced solution extractor with UUID keys only and proper room sharing"""

    def __init__(self, problem: "ExamSchedulingProblem", shared_vars, solver):
        self.problem = problem
        self.solver = solver
        self.shared_vars = shared_vars
        self.x_vars = shared_vars.x_vars
        self.y_vars = shared_vars.y_vars
        self.z_vars = shared_vars.z_vars
        self.u_vars = shared_vars.u_vars

        self.extraction_stats = {
            "assignments_from_x": 0,
            "assignments_from_z": 0,
            "room_assignments": 0,
            "conflicts_detected": 0,
        }

        logger.info(
            f"UUID-only: Initialized SolutionExtractor for problem with {len(problem.exams)} exams"
        )
        logger.info(
            f"Available variables: x={len(self.x_vars)}, y={len(self.y_vars)}, z={len(self.z_vars)}, u={len(self.u_vars)}"
        )

    def extract(self) -> TimetableSolution:
        """Extracts the complete timetable solution from the solver."""
        solution = TimetableSolution(self.problem)
        logger.info("Extracting scheduled exams from solver...")

        assignments_found = 0  # <-- ADD a counter

        for (exam_id, slot_id), x_var in self.shared_vars.x_vars.items():
            if self.solver.Value(x_var) == 1:
                assignments_found += 1  # <-- Increment counter
                start_slot_id = slot_id
                day = self.problem.get_day_for_timeslot(start_slot_id)
                if not day:
                    logger.warning(f"Could not find day for start slot {start_slot_id}")
                    continue

                room_ids, invigilator_ids = self._extract_allocations(
                    exam_id, start_slot_id
                )

                allocations = self.calculate_room_allocations(exam_id, set(room_ids))

                solution.assign(
                    exam_id=exam_id,
                    date=day.date,
                    slot_id=start_slot_id,
                    rooms=room_ids,
                    allocations=allocations,
                    invigilator_ids=invigilator_ids,
                )

        # --- START OF MODIFICATION ---
        logger.info(
            f"Extracted {assignments_found} completed assignments from the solver."
        )
        # --- END OF MODIFICATION ---

        solution.update_statistics()
        solution.update_assignment_statuses()
        return solution

    def _extract_allocations(
        self, exam_id: UUID, start_slot_id: UUID
    ) -> Tuple[List[UUID], List[UUID]]:
        """Extracts room and invigilator UUIDs for a specific exam start."""
        assigned_room_ids = []
        assigned_invigilator_ids = []

        for (y_exam_id, room_id, y_slot_id), y_var in self.shared_vars.y_vars.items():
            if (
                y_exam_id == exam_id
                and y_slot_id == start_slot_id
                and self.solver.Value(y_var) == 1
            ):
                assigned_room_ids.append(room_id)

        invigilator_set = set()
        for (
            inv_id,
            u_exam_id,
            u_room_id,
            u_slot_id,
        ), u_var in self.shared_vars.u_vars.items():
            if (
                u_exam_id == exam_id
                and u_slot_id == start_slot_id
                and u_room_id in assigned_room_ids
                and self.solver.Value(u_var) == 1
            ):
                invigilator_set.add(inv_id)

        assigned_invigilator_ids = list(invigilator_set)

        return assigned_room_ids, assigned_invigilator_ids

    def has_solution(self) -> bool:
        """Enhanced solution availability check with multiple methods"""
        try:
            if hasattr(self.solver, "StatusName"):
                status_name = self.solver.StatusName()
                if status_name in ["OPTIMAL", "FEASIBLE"]:
                    logger.debug(f"Solution found with status: {status_name}")
                    return True
                else:
                    logger.warning(
                        f"Solver status is {status_name}, no solution available."
                    )
                    return False
            return False
        except Exception as e:
            logger.error(f"Error checking solution availability: {e}")
            return False

    def extract_assignments_comprehensive(self, solution: TimetableSolution) -> None:
        """Extract assignments using UUID keys with fallbacks"""
        logger.info("Extracting exam assignments with UUID keys...")

        assignments_from_x = self.extract_from_start_variables(solution)
        self.extraction_stats["assignments_from_x"] = assignments_from_x

        if assignments_from_x == 0:
            logger.info(
                "No assignments from start variables, trying occupancy variables..."
            )
            assignments_from_z = self.extract_from_occupancy_variables(solution)
            self.extraction_stats["assignments_from_z"] = assignments_from_z

        room_assignments = self.extract_room_assignments(solution)
        self.extraction_stats["room_assignments"] = room_assignments

        invigilator_assignments = self.extract_invigilator_assignments(solution)
        logger.info(f"Extracted {invigilator_assignments} invigilator assignments.")

    def extract_from_start_variables(self, solution: TimetableSolution) -> int:
        """FIXED - Extract assignments from start variables with UUID keys"""
        assignments_found = 0
        for (exam_id, slot_id), var in self.x_vars.items():
            try:
                if self.solver.Value(var):
                    assignment = solution.assignments.get(
                        exam_id, ExamAssignment(exam_id=exam_id)
                    )
                    assignment.time_slot_id = slot_id

                    day = self.problem.get_day_for_timeslot(slot_id)
                    if day:
                        assignment.assigned_date = day.date

                    solution.assignments[exam_id] = assignment
                    assignments_found += 1
            except Exception:
                continue
        logger.info(f"Extracted {assignments_found} time assignments from X variables.")
        return assignments_found

    def extract_from_occupancy_variables(self, solution: TimetableSolution) -> int:
        """FIXED - Extract assignments from occupancy variables with UUID keys"""
        assignments_found = 0
        exam_timeslots = defaultdict(list)
        for (exam_id, slot_id), var in self.z_vars.items():
            try:
                if self.solver.Value(var):
                    exam_timeslots[exam_id].append(slot_id)
            except Exception:
                continue

        for exam_id, timeslots in exam_timeslots.items():
            if timeslots and not solution.assignments[exam_id].is_complete():
                start_slot_id = min(
                    timeslots, key=lambda s_id: self.problem.timeslots[s_id].start_time
                )
                assignment = solution.assignments.get(
                    exam_id, ExamAssignment(exam_id=exam_id)
                )
                assignment.time_slot_id = start_slot_id
                day = self.problem.get_day_for_timeslot(start_slot_id)
                if day:
                    assignment.assigned_date = day.date
                solution.assignments[exam_id] = assignment
                assignments_found += 1
        logger.info(
            f"Extracted {assignments_found} time assignments from Z variables as fallback."
        )
        return assignments_found

    def extract_room_assignments(self, solution: TimetableSolution) -> int:
        """FIXED - Extract and validate room assignments with UUID keys"""
        room_assignments_processed = 0
        for (exam_id, room_id, slot_id), var in self.y_vars.items():
            try:
                if self.solver.Value(var):
                    assignment = solution.assignments.get(exam_id)
                    if assignment and assignment.time_slot_id == slot_id:
                        if room_id not in assignment.room_ids:
                            assignment.room_ids.append(room_id)
                        room_assignments_processed += 1
            except Exception:
                continue

        for exam_id, assignment in solution.assignments.items():
            if assignment.room_ids:
                assignment.room_allocations = self.calculate_room_allocations(
                    exam_id, set(assignment.room_ids)
                )

        logger.info(
            f"Processed {room_assignments_processed} room assignments from Y variables."
        )
        return room_assignments_processed

    def extract_invigilator_assignments(self, solution: TimetableSolution) -> int:
        """FIXED - Extract invigilator assignments with UUID keys"""
        invigilator_assignments = 0
        for (inv_id, exam_id, room_id, slot_id), var in self.u_vars.items():
            try:
                if self.solver.Value(var):
                    assignment = solution.assignments.get(exam_id)
                    if (
                        assignment
                        and assignment.time_slot_id == slot_id
                        and room_id in assignment.room_ids
                    ):
                        if inv_id not in assignment.invigilator_ids:
                            assignment.invigilator_ids.append(inv_id)
                        invigilator_assignments += 1
            except Exception:
                continue
        return invigilator_assignments

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

    def validate_assignments(self, solution: TimetableSolution):
        """Validate extracted assignments and update status."""
        for assignment in solution.assignments.values():
            if not assignment.is_complete():
                assignment.status = AssignmentStatus.UNASSIGNED
            else:
                assignment.status = AssignmentStatus.ASSIGNED

    def ensure_all_exams_assigned(self, solution: TimetableSolution):
        """Ensure all exam IDs from the problem are present in the solution's assignments."""
        for exam_id in self.problem.exams:
            if exam_id not in solution.assignments:
                solution.assignments[exam_id] = ExamAssignment(
                    exam_id=exam_id, status=AssignmentStatus.UNASSIGNED
                )

    def log_extraction_results(self, solution: TimetableSolution, conflicts_found: int):
        """Log extraction results"""
        completion = solution.get_completion_percentage()
        logger.info("--- Solution Extraction Complete ---")
        logger.info(
            f"  Status: {solution.status.value}, Feasible: {solution.is_feasible()}"
        )
        logger.info(f"  Completion: {completion:.1f}%")
        logger.info(f"  Conflicts Found: {conflicts_found}")
        logger.info("------------------------------------")

    def get_completion_percentage(self) -> float:
        """Calculate completion percentage"""
        return 0.0
