# COMPREHENSIVE FIX - Solution Extractor Enhancement
# MODIFIED for UUID-only usage AND proper room sharing validation
# Key Issues Fixed:
# 1. Removed string conversion functions
# 2. Updated variable lookups to use UUID keys directly
# 3. Removed normalize_id usage
# 4. Updated all internal processing to work with UUIDs
# 5. Fixed variable key consistency
# 6. FIXED room conflict detection to allow valid room sharing
# 7. REMOVED all conflict resolution functionality - only detection now

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
from datetime import date

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

        # Statistics tracking
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
        """Extract solution with UUID keys and comprehensive validation"""
        logger.info("Starting UUID-only solution extraction...")
        solution = TimetableSolution(self.problem)

        try:
            if not self.has_solution():
                logger.warning("No solution found to extract")
                solution.status = SolutionStatus.INVALID
                return solution

            # Extract assignments using UUID keys
            self.extract_assignments_comprehensive(solution)

            # Detect conflicts with proper room sharing logic
            conflicts_found = len(solution.detect_conflicts_fixed())
            self.extraction_stats["conflicts_detected"] = conflicts_found

            # Validate assignments and update statuses
            self.validate_assignments(solution)
            solution.update_assignment_statuses()

            # Ensure all exams have at least a placeholder assignment
            self.ensure_all_exams_assigned(solution)

            # MODIFIED: Update all statistics and quality metrics before returning
            solution.update_statistics()
            solution.update_soft_constraint_metrics(self.problem)

            if solution.is_feasible():
                solution.status = SolutionStatus.FEASIBLE
            else:
                solution.status = SolutionStatus.INFEASIBLE

            self.log_extraction_results(solution, conflicts_found)
            return solution

        except Exception as e:
            logger.error(f"UUID-only solution extraction failed: {e}")
            logger.debug(f"Traceback:\n{traceback.format_exc()}")
            solution.status = SolutionStatus.INVALID
            return solution

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
        # This can be a fallback if X variables yield no results
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
                # A simple heuristic: choose the earliest timeslot as the start time
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
            if i == len(room_list) - 1:  # Last room gets the rest
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
        # Implement completion percentage calculation
        return 0.0  # Placeholder
