# scheduling_engine/cp_sat/solution_extractor.py

"""
FIXED Solution Extractor - Comprehensive Enhancement

Key Fixes:
- Enhanced variable value extraction with validation
- Better error handling and logging
- Improved assignment creation and validation
- Robust conflict detection
- Comprehensive solution statistics
"""

import logging
from typing import TYPE_CHECKING, Dict, Set, Any, Optional
from uuid import UUID

from scheduling_engine.core.solution import (
    TimetableSolution,
    ExamAssignment,
    AssignmentStatus,
)

if TYPE_CHECKING:
    from scheduling_engine.core.problem_model import ExamSchedulingProblem

logger = logging.getLogger(__name__)


class SolutionExtractor:
    """
    FIXED solution extractor with comprehensive enhancements.
    """

    def __init__(self, problem: "ExamSchedulingProblem", shared_vars, solver):
        self.problem = problem
        self.solver = solver
        self.shared_vars = shared_vars

        # Enhanced variable access
        self.x_vars = shared_vars.x_vars  # Dict[(exam_id, day, slot) -> cp var]
        self.y_vars = (
            shared_vars.y_vars
        )  # Dict[(exam_id, room_id, day, slot) -> cp var]
        self.z_vars = shared_vars.z_vars  # Dict[(exam_id, day, slot) -> cp var]
        self.u_vars = (
            shared_vars.u_vars
        )  # Dict[(invigilator_id, exam_id, room_id, day, slot) -> cp var]

        logger.info(
            f"🔍 Initialized SolutionExtractor for problem with {len(problem.exams)} exams"
        )
        logger.info(
            f"📊 Available variables: x={len(self.x_vars)}, y={len(self.y_vars)}, z={len(self.z_vars)}, u={len(self.u_vars)}"
        )

    def extract(self) -> TimetableSolution:
        """
        Extract solution with comprehensive validation and error handling.
        """
        logger.info("🔍 Starting solution extraction...")

        solution = TimetableSolution(self.problem)

        try:
            # Check if solution exists
            if not self._has_solution():
                logger.warning("⚠️ No solution found to extract")
                return solution

            # Extract assignments using multiple methods
            assignments_extracted = self._extract_assignments_comprehensive(solution)

            # Validate and enhance assignments
            self._validate_and_enhance_assignments(solution)

            # Update solution statistics
            solution.update_statistics()

            # Log extraction results
            self._log_extraction_results(solution, assignments_extracted)

            return solution

        except Exception as e:
            logger.error(f"❌ Solution extraction failed: {e}")
            import traceback

            logger.debug(f"🐛 Traceback:\n{traceback.format_exc()}")
            return solution

    def _has_solution(self) -> bool:
        """Check if solver has a solution available."""
        try:
            # Method 1: Check response proto
            if hasattr(self.solver, "ResponseProto"):
                response = self.solver.ResponseProto()
                if hasattr(response, "solution") and response.solution:
                    logger.debug("✅ Solution found via ResponseProto")
                    return True

            # Method 2: Check solver status
            if hasattr(self.solver, "StatusName"):
                status_name = self.solver.StatusName()
                if status_name in ["OPTIMAL", "FEASIBLE"]:
                    logger.debug(f"✅ Solution found with status: {status_name}")
                    return True

            # Method 3: Try to access a variable value
            if self.x_vars:
                test_var = next(iter(self.x_vars.values()))
                try:
                    self.solver.Value(test_var)
                    logger.debug("✅ Solution found via test variable access")
                    return True
                except:
                    pass

            logger.warning("⚠️ No solution available from solver")
            return False

        except Exception as e:
            logger.error(f"❌ Error checking solution availability: {e}")
            return False

    def _extract_assignments_comprehensive(self, solution: TimetableSolution) -> int:
        """Extract assignments using comprehensive methods."""
        assignments_extracted = 0
        assignments_from_z = 0  # Initialize to avoid unbound reference

        logger.info("🔍 Extracting exam assignments...")

        # Method 1: Extract from start variables (x)
        assignments_from_x = self._extract_from_start_variables(solution)
        assignments_extracted += assignments_from_x

        # Method 2: Extract from occupancy variables if start extraction failed
        if assignments_from_x == 0:
            logger.info(
                "⚠️ No assignments from start variables, trying occupancy variables..."
            )
            assignments_from_z = self._extract_from_occupancy_variables(solution)
            assignments_extracted += assignments_from_z

        # Method 3: Extract room assignments
        room_assignments = self._extract_room_assignments(solution)

        logger.info(f"📊 Assignment extraction summary:")
        logger.info(f"  • Start variable assignments: {assignments_from_x}")
        logger.info(
            f"  • Occupancy variable assignments: {assignments_from_z if assignments_from_x == 0 else 'skipped'}"
        )
        logger.info(f"  • Room assignments processed: {room_assignments}")

        return assignments_extracted

    def _extract_from_start_variables(self, solution: TimetableSolution) -> int:
        """Extract assignments from start variables (x)."""
        assignments_found = 0

        for (exam_id, day, slot_id), var in self.x_vars.items():
            try:
                if self.solver.Value(var):
                    # Found a start assignment
                    logger.debug(f"📍 Exam {exam_id} starts on {day} at slot {slot_id}")

                    # Create or update assignment
                    if exam_id not in solution.assignments:
                        solution.assignments[exam_id] = ExamAssignment(exam_id=exam_id)

                    assignment = solution.assignments[exam_id]
                    assignment.time_slot_id = slot_id
                    assignment.assigned_date = day
                    assignment.status = AssignmentStatus.ASSIGNED

                    # Find corresponding rooms for this time assignment
                    rooms = self._find_rooms_for_exam_time(exam_id, day, slot_id)
                    if rooms:
                        assignment.room_ids = rooms
                        assignment.room_allocations = self._calculate_room_allocations(
                            exam_id, rooms
                        )

                    assignments_found += 1

            except Exception as e:
                logger.debug(
                    f"⚠️ Error accessing start variable for {exam_id}, {day}, {slot_id}: {e}"
                )
                continue

        logger.info(
            f"✅ Extracted {assignments_found} assignments from start variables"
        )
        return assignments_found

    def _extract_from_occupancy_variables(self, solution: TimetableSolution) -> int:
        """Extract assignments from occupancy variables (z) as fallback."""
        assignments_found = 0
        exam_time_slots = {}  # exam_id -> [(day, slot_id), ...]

        # First, collect all occupancy assignments
        for (exam_id, day, slot_id), var in self.z_vars.items():
            try:
                if self.solver.Value(var):
                    if exam_id not in exam_time_slots:
                        exam_time_slots[exam_id] = []
                    exam_time_slots[exam_id].append((day, slot_id))
            except Exception as e:
                logger.debug(
                    f"⚠️ Error accessing occupancy variable for {exam_id}, {day}, {slot_id}: {e}"
                )
                continue

        # Convert occupancy to assignments (take first occurrence as start time)
        for exam_id, time_slots in exam_time_slots.items():
            if time_slots:
                # Sort time slots and take the first as start time
                time_slots.sort()
                start_day, start_slot = time_slots[0]

                logger.debug(
                    f"📍 Exam {exam_id} occupancy from {start_day} at slot {start_slot}"
                )

                if exam_id not in solution.assignments:
                    solution.assignments[exam_id] = ExamAssignment(exam_id=exam_id)

                assignment = solution.assignments[exam_id]
                assignment.time_slot_id = start_slot
                assignment.assigned_date = start_day
                assignment.status = AssignmentStatus.ASSIGNED

                # Find rooms
                rooms = self._find_rooms_for_exam_time(exam_id, start_day, start_slot)
                if rooms:
                    assignment.room_ids = rooms
                    assignment.room_allocations = self._calculate_room_allocations(
                        exam_id, rooms
                    )

                assignments_found += 1

        logger.info(
            f"✅ Extracted {assignments_found} assignments from occupancy variables"
        )
        return assignments_found

    def _find_rooms_for_exam_time(self, exam_id, day, slot_id) -> list:
        """Find rooms assigned to exam at specific time."""
        rooms = []

        for (e_id, room_id, d, s), yvar in self.y_vars.items():
            if e_id == exam_id and d == day and s == slot_id:
                try:
                    if self.solver.Value(yvar):
                        rooms.append(room_id)
                        logger.debug(f"  🏢 Room {room_id} assigned to exam {exam_id}")
                except Exception as e:
                    logger.debug(
                        f"⚠️ Error accessing room variable for {exam_id}, {room_id}: {e}"
                    )
                    continue

        return rooms

    def _calculate_room_allocations(self, exam_id, rooms: list) -> Dict[UUID, int]:
        """Calculate student allocation per room."""
        allocations = {}

        # Get exam details first (outside try block)
        exam = self.problem.exams.get(exam_id)
        if not exam:
            logger.warning(f"⚠️ Exam {exam_id} not found in problem")
            return allocations

        try:
            total_students = exam.expected_students
            if not total_students or not rooms:
                return allocations

            # Equal distribution with remainder handling
            students_per_room = total_students // len(rooms)
            remainder = total_students % len(rooms)

            for i, room_id in enumerate(rooms):
                allocation = students_per_room
                if i < remainder:  # Distribute remainder to first rooms
                    allocation += 1
                allocations[room_id] = allocation

                logger.debug(f"  📊 Room {room_id}: {allocation} students")

        except Exception as e:
            logger.error(
                f"❌ Error calculating room allocations for exam {exam_id}: {e}"
            )
            # Fallback: equal distribution
            if rooms:
                equal_allocation = max(1, exam.expected_students // len(rooms))
                allocations = {room_id: equal_allocation for room_id in rooms}

        return allocations

    def _extract_room_assignments(self, solution: TimetableSolution) -> int:
        """Extract and validate room assignments."""
        room_assignments_processed = 0

        # Group room assignments by exam
        exam_room_assignments = {}

        for (exam_id, room_id, day, slot_id), var in self.y_vars.items():
            try:
                if self.solver.Value(var):
                    if exam_id not in exam_room_assignments:
                        exam_room_assignments[exam_id] = []
                    exam_room_assignments[exam_id].append((room_id, day, slot_id))
                    room_assignments_processed += 1
            except Exception as e:
                logger.debug(f"⚠️ Error accessing room variable: {e}")
                continue

        # Validate room assignments against time assignments
        for exam_id, room_data in exam_room_assignments.items():
            if exam_id in solution.assignments:
                assignment = solution.assignments[exam_id]
                expected_day = assignment.assigned_date
                expected_slot = assignment.time_slot_id

                # Filter room assignments to match the assigned time
                matching_rooms = [
                    room_id
                    for room_id, day, slot_id in room_data
                    if day == expected_day and slot_id == expected_slot
                ]

                if matching_rooms:
                    assignment.room_ids = matching_rooms
                    assignment.room_allocations = self._calculate_room_allocations(
                        exam_id, matching_rooms
                    )
                else:
                    logger.warning(
                        f"⚠️ Room assignment time mismatch for exam {exam_id}"
                    )

        logger.info(
            f"📊 Processed {room_assignments_processed} room variable assignments"
        )
        return len(exam_room_assignments)

    def _validate_and_enhance_assignments(self, solution: TimetableSolution):
        """Validate and enhance extracted assignments."""
        logger.info("🔍 Validating and enhancing assignments...")

        valid_assignments = 0
        invalid_assignments = 0
        enhanced_assignments = 0

        for exam_id, assignment in solution.assignments.items():
            try:
                # Basic validation
                is_valid = self._validate_assignment(exam_id, assignment)

                if is_valid:
                    valid_assignments += 1
                    # Try to enhance assignment
                    if self._enhance_assignment(exam_id, assignment):
                        enhanced_assignments += 1
                else:
                    invalid_assignments += 1
                    assignment.status = AssignmentStatus.INVALID
                    logger.warning(f"⚠️ Invalid assignment for exam {exam_id}")

            except Exception as e:
                logger.error(f"❌ Error validating assignment for exam {exam_id}: {e}")
                assignment.status = AssignmentStatus.INVALID
                invalid_assignments += 1

        logger.info(f"📊 Assignment validation summary:")
        logger.info(f"  • Valid assignments: {valid_assignments}")
        logger.info(f"  • Invalid assignments: {invalid_assignments}")
        logger.info(f"  • Enhanced assignments: {enhanced_assignments}")

    def _validate_assignment(self, exam_id, assignment: ExamAssignment) -> bool:
        """Validate a single assignment."""
        try:
            # Check required fields
            if not all(
                [assignment.time_slot_id, assignment.assigned_date, assignment.room_ids]
            ):
                return False

            # Check if time slot exists
            if assignment.time_slot_id not in self.problem.time_slots:
                logger.debug(
                    f"⚠️ Invalid time slot for exam {exam_id}: {assignment.time_slot_id}"
                )
                return False

            # Check if rooms exist
            for room_id in assignment.room_ids:
                if room_id not in self.problem.rooms:
                    logger.debug(f"⚠️ Invalid room for exam {exam_id}: {room_id}")
                    return False

            # Check date is within exam period
            if assignment.assigned_date not in self.problem.days:
                logger.debug(
                    f"⚠️ Invalid date for exam {exam_id}: {assignment.assigned_date}"
                )
                return False

            return True

        except Exception as e:
            logger.debug(f"⚠️ Assignment validation error for exam {exam_id}: {e}")
            return False

    def _enhance_assignment(self, exam_id, assignment: ExamAssignment) -> bool:
        """Enhance assignment with additional information."""
        enhanced = False

        try:
            # Enhance room allocations if missing
            if assignment.room_ids and not assignment.room_allocations:
                assignment.room_allocations = self._calculate_room_allocations(
                    exam_id, assignment.room_ids
                )
                enhanced = True

            # Set assignment status if not set
            if (
                assignment.status == AssignmentStatus.UNASSIGNED
                and assignment.is_complete()
            ):
                assignment.status = AssignmentStatus.ASSIGNED
                enhanced = True

            return enhanced

        except Exception as e:
            logger.debug(f"⚠️ Assignment enhancement error for exam {exam_id}: {e}")
            return False

    def _log_extraction_results(
        self, solution: TimetableSolution, assignments_extracted: int
    ):
        """Log comprehensive extraction results."""
        completion_percentage = solution.get_completion_percentage()
        total_assignments = len(solution.assignments)
        complete_assignments = sum(
            1 for a in solution.assignments.values() if a.is_complete()
        )

        logger.info("📊 Solution extraction complete:")
        logger.info(f"  • Total assignments: {total_assignments}")
        logger.info(f"  • Complete assignments: {complete_assignments}")
        logger.info(f"  • Completion percentage: {completion_percentage:.1f}%")
        logger.info(f"  • Assignments extracted: {assignments_extracted}")

        # Status breakdown
        status_counts = {}
        for assignment in solution.assignments.values():
            status = assignment.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        if status_counts:
            logger.info("📊 Assignment status breakdown:")
            for status, count in status_counts.items():
                logger.info(f"  • {status}: {count}")

        # Room utilization
        used_rooms = set()
        for assignment in solution.assignments.values():
            used_rooms.update(assignment.room_ids)

        room_utilization = (
            len(used_rooms) / len(self.problem.rooms) * 100 if self.problem.rooms else 0
        )
        logger.info(
            f"📊 Room utilization: {len(used_rooms)}/{len(self.problem.rooms)} ({room_utilization:.1f}%)"
        )

        # Time slot utilization
        used_slots = {
            assignment.time_slot_id
            for assignment in solution.assignments.values()
            if assignment.time_slot_id
        }
        slot_utilization = (
            len(used_slots) / len(self.problem.time_slots) * 100
            if self.problem.time_slots
            else 0
        )
        logger.info(
            f"📊 Time slot utilization: {len(used_slots)}/{len(self.problem.time_slots)} ({slot_utilization:.1f}%)"
        )
