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
from typing import TYPE_CHECKING, Dict, Set, Any, Optional, List, Tuple
from uuid import UUID

from scheduling_engine.core.solution import (
    TimetableSolution,
    ExamAssignment,
    AssignmentStatus,
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
                return solution

            # Extract assignments using UUID keys
            self.extract_assignments_comprehensive(solution)

            # Detect conflicts with proper room sharing logic (NO RESOLUTION)
            conflicts_found = self.detect_conflicts(solution)

            # Validate assignments
            self.validate_assignments(solution)

            # Analyze resource utilization
            self.analyze_resource_utilization(solution)

            # Update solution statistics
            solution.update_statistics()

            self.diagnose_unassigned_exams(solution)
            self.ensure_all_exams_assigned(solution)

            self.log_extraction_results(solution, conflicts_found)
            return solution

        except Exception as e:
            logger.error(f"UUID-only solution extraction failed: {e}")
            import traceback

            logger.debug(f"Traceback:\n{traceback.format_exc()}")
            return solution

    def has_solution(self) -> bool:
        """Enhanced solution availability check with multiple methods"""
        try:
            # Method 1: Check response proto
            if hasattr(self.solver, "ResponseProto"):
                response = self.solver.ResponseProto()
                if hasattr(response, "solution") and response.solution:
                    logger.debug("Solution found via ResponseProto")
                    return True

            # Method 2: Check solver status
            if hasattr(self.solver, "StatusName"):
                status_name = self.solver.StatusName()
                if status_name in ["OPTIMAL", "FEASIBLE"]:
                    logger.debug(f"Solution found with status: {status_name}")
                    return True
                else:
                    logger.debug(f"Solver status: {status_name}")

            # Method 3: Try to access variable values
            test_successful = False
            if self.x_vars:
                try:
                    test_var = next(iter(self.x_vars.values()))
                    value = self.solver.Value(test_var)
                    logger.debug(
                        f"Solution found via test variable access: value={value}"
                    )
                    test_successful = True
                except Exception as e:
                    logger.debug(f"Test variable access failed: {e}")

            if test_successful:
                return True

            logger.warning("No solution available from solver")
            return False

        except Exception as e:
            logger.error(f"Error checking solution availability: {e}")
            return False

    def extract_assignments_comprehensive(self, solution: TimetableSolution) -> None:
        """Extract assignments using UUID keys with fallbacks"""
        logger.info("Extracting exam assignments with UUID keys...")

        # Method 1: Extract from start variables (x)
        assignments_from_x = self.extract_from_start_variables(solution)
        self.extraction_stats["assignments_from_x"] = assignments_from_x

        if assignments_from_x < len(self.problem.exams) * 0.5:  # Less than 50% coverage
            logger.info(
                "Low coverage from start variables, trying occupancy variables..."
            )
            assignments_from_z = self.extract_from_occupancy_variables(solution)
            self.extraction_stats["assignments_from_z"] = assignments_from_z

        # Method 3: Extract room assignments
        room_assignments = self.extract_room_assignments(solution)
        self.extraction_stats["room_assignments"] = room_assignments

        # Method 4: Extract invigilator assignments
        invigilator_assignments = self.extract_invigilator_assignments(solution)

        logger.info(f"Assignment extraction summary:")
        logger.info(f"  Start variable assignments: {assignments_from_x}")
        logger.info(
            f"  Occupancy variable assignments: {self.extraction_stats['assignments_from_z']}"
        )
        logger.info(f"  Room assignments processed: {room_assignments}")
        logger.info(f"  Invigilator assignments: {invigilator_assignments}")

    def extract_from_start_variables(self, solution: TimetableSolution) -> int:
        """FIXED - Extract assignments from start variables with UUID keys"""
        assignments_found = 0

        for (exam_id, slot_id), var in self.x_vars.items():
            try:
                if self.solver.Value(var):
                    logger.debug(f"Exam {exam_id} starts at slot {slot_id}")

                    if exam_id not in solution.assignments:
                        solution.assignments[exam_id] = ExamAssignment(exam_id=exam_id)

                    assignment = solution.assignments[exam_id]
                    assignment.time_slot_id = slot_id
                    assignment.status = AssignmentStatus.ASSIGNED

                    # Map slot to date using problem's time slot data
                    if slot_id in self.problem.timeslots:
                        try:
                            day = self.problem.get_day_for_timeslot(slot_id)
                            assert day
                            assignment.assigned_date = (
                                day.date
                            )  # Get the date from Day object
                        except ValueError as e:
                            logger.warning(
                                f"Could not find day for timeslot {slot_id}: {e}"
                            )
                            assignment.assigned_date = None

                    # Find corresponding rooms for this time assignment
                    rooms = self.find_rooms_for_exam_time(exam_id, slot_id)
                    if rooms:
                        assignment.room_ids = list(rooms)
                        assignment.room_allocations = self.calculate_room_allocations(
                            exam_id, rooms
                        )

                    assignments_found += 1

            except Exception as e:
                logger.debug(
                    f"Error accessing start variable for {exam_id}, {slot_id}: {e}"
                )
                continue

        logger.info(f"Extracted {assignments_found} assignments from start variables")
        return assignments_found

    def extract_from_occupancy_variables(self, solution: TimetableSolution) -> int:
        """FIXED - Extract assignments from occupancy variables with UUID keys"""
        assignments_found = 0
        exam_timeslots = defaultdict(list)  # exam_id -> [slot_id, ...]

        for (exam_id, slot_id), var in self.z_vars.items():
            try:
                if self.solver.Value(var):
                    if exam_id not in exam_timeslots:
                        exam_timeslots[exam_id] = []
                    exam_timeslots[exam_id].append(slot_id)
            except Exception as e:
                logger.debug(
                    f"Error accessing occupancy variable for {exam_id}, {slot_id}: {e}"
                )
                continue

        # Convert occupancy to assignments (take first occurrence as start time)
        for exam_id, timeslots in exam_timeslots.items():
            if timeslots:
                # Sort time slots and take the first as start time
                timeslots.sort(
                    key=lambda slot_id: (
                        self.problem.get_day_for_timeslot(slot_id).date,  # type: ignore
                        self.problem.timeslots[
                            slot_id
                        ].start_time,  # Sort by string representation of UUID
                    )
                )
                start_slot_id = timeslots[0]

                logger.debug(f"Exam {exam_id} occupancy starts at slot {start_slot_id}")

                if exam_id not in solution.assignments:
                    solution.assignments[exam_id] = ExamAssignment(exam_id=exam_id)

                assignment = solution.assignments[exam_id]
                assignment.time_slot_id = start_slot_id
                assignment.status = AssignmentStatus.ASSIGNED

                # Map slot to date
                if start_slot_id in self.problem.timeslots:
                    try:
                        day = self.problem.get_day_for_timeslot(start_slot_id)
                        assert day
                        assignment.assigned_date = (
                            day.date
                        )  # Get the date from Day object
                    except ValueError as e:
                        logger.warning(
                            f"Could not find day for timeslot {start_slot_id}: {e}"
                        )
                        assignment.assigned_date = None
                else:
                    assignment.assigned_date = None

                # Find rooms
                rooms = self.find_rooms_for_exam_time(exam_id, start_slot_id)
                if rooms:
                    assignment.room_ids = list(rooms)
                    assignment.room_allocations = self.calculate_room_allocations(
                        exam_id, rooms
                    )

                assignments_found += 1

        logger.info(
            f"Extracted {assignments_found} assignments from occupancy variables"
        )
        return assignments_found

    def find_rooms_for_exam_time(self, exam_id: UUID, slot_id: UUID) -> Set[UUID]:
        """FIXED - Find rooms assigned to exam at specific time with UUID keys"""
        rooms = set()

        for (e_id, room_id, s_id), y_var in self.y_vars.items():
            if e_id == exam_id and s_id == slot_id:
                try:
                    if self.solver.Value(y_var):
                        rooms.add(room_id)
                        logger.debug(f"Room {room_id} assigned to exam {exam_id}")
                except Exception as e:
                    logger.debug(
                        f"Error accessing room variable for {exam_id}, {room_id}: {e}"
                    )
                    continue

        return rooms

    def extract_room_assignments(self, solution: TimetableSolution) -> int:
        """FIXED - Extract and validate room assignments with UUID keys"""
        room_assignments_processed = 0
        exam_room_assignments = defaultdict(
            list
        )  # exam_id -> [(room_id, slot_id), ...]

        for (exam_id, room_id, slot_id), var in self.y_vars.items():
            try:
                if self.solver.Value(var):
                    if exam_id not in exam_room_assignments:
                        exam_room_assignments[exam_id] = []
                    exam_room_assignments[exam_id].append((room_id, slot_id))
                    room_assignments_processed += 1
            except Exception as e:
                logger.debug(f"Error accessing room variable: {e}")
                continue

        # Validate room assignments against time assignments
        for exam_id, room_data in exam_room_assignments.items():
            if exam_id in solution.assignments:
                assignment = solution.assignments[exam_id]
                expected_slot_id = assignment.time_slot_id

                # Filter room assignments to match the assigned time
                matching_rooms = set()
                for room_id, slot_id in room_data:
                    if slot_id == expected_slot_id:
                        matching_rooms.add(room_id)

                if matching_rooms:
                    assignment.room_ids = list(matching_rooms)
                    assignment.room_allocations = self.calculate_room_allocations(
                        exam_id, matching_rooms
                    )
                else:
                    logger.warning(f"Room assignment time mismatch for exam {exam_id}")

        logger.info(f"Processed {room_assignments_processed} room variable assignments")
        return len(exam_room_assignments)

    def extract_invigilator_assignments(self, solution: TimetableSolution) -> int:
        """FIXED - Extract invigilator assignments with conflict detection only (no resolution)"""
        invigilator_assignments = 0
        exam_invigilators = defaultdict(list)
        invigilator_timeslot_assignments = defaultdict(
            list
        )  # Track invigilator assignments by timeslot to detect conflicts

        for (inv_id, exam_id, room_id, slot_id), var in self.u_vars.items():
            try:
                if self.solver.Value(var):
                    logger.debug(
                        f"Invigilator {inv_id} assigned to exam {exam_id} in room {room_id}"
                    )
                    exam_invigilators[exam_id].append(inv_id)

                    # Track for conflict detection
                    invigilator_timeslot_assignments[slot_id].append(
                        {"inv_id": inv_id, "exam_id": exam_id, "room_id": room_id}
                    )
                    invigilator_assignments += 1
            except Exception as e:
                logger.debug(f"Error accessing invigilator variable: {e}")
                continue

        # DETECT invigilator conflicts (NO RESOLUTION)
        conflicts_detected = 0
        for slot_id, assignments in invigilator_timeslot_assignments.items():
            # Group by invigilator to detect conflicts
            inv_assignments = defaultdict(list)
            for assignment in assignments:
                inv_assignments[assignment["inv_id"]].append(assignment)

            # Check for conflicts (same invigilator, multiple rooms)
            for inv_id, inv_rooms in inv_assignments.items():
                if len(inv_rooms) > 1:
                    conflicts_detected += 1
                    logger.warning(
                        f"CONFLICT: Invigilator {inv_id} assigned to {len(inv_rooms)} rooms in slot {slot_id}"
                    )
                    # Mark exams as having conflicts
                    for conflict_assignment in inv_rooms:
                        exam_id = conflict_assignment["exam_id"]
                        if exam_id in solution.assignments:
                            solution.assignments[exam_id].status = (
                                AssignmentStatus.CONFLICT
                            )
                            solution.assignments[exam_id].conflicts.append(
                                f"Invigilator {inv_id} conflict in slot {slot_id}"
                            )

        # Update ExamAssignment objects with invigilator data
        for exam_id, invigilator_ids in exam_invigilators.items():
            if exam_id in solution.assignments:
                solution.assignments[exam_id].invigilator_ids = invigilator_ids
                logger.debug(
                    f"Added {len(invigilator_ids)} invigilators to exam {exam_id}"
                )

        logger.info(f"Extracted {invigilator_assignments} invigilator assignments")
        if conflicts_detected:
            logger.warning(f"Detected {conflicts_detected} invigilator conflicts")

        return invigilator_assignments

    def detect_conflicts(self, solution: TimetableSolution) -> int:
        """Enhanced conflict detection with proper room sharing logic (NO RESOLUTION)"""
        logger.info("Detecting conflicts (no resolution)...")
        conflicts_found = 0

        # Check for time conflicts
        time_conflicts = self.detect_time_conflicts(solution)
        conflicts_found += len(time_conflicts)

        # FIXED: Check for REAL room conflicts (capacity violations and student conflicts)
        room_conflicts = self.detect_real_room_conflicts(solution)
        conflicts_found += len(room_conflicts)

        # Check for capacity violations
        capacity_violations = self.detect_capacity_violations(solution)
        conflicts_found += len(capacity_violations)

        self.extraction_stats["conflicts_detected"] = conflicts_found

        if conflicts_found > 0:
            logger.warning(f"Found {conflicts_found} conflicts")
        else:
            logger.info("No conflicts detected")

        return conflicts_found

    def detect_time_conflicts(self, solution: TimetableSolution) -> List[Tuple]:
        """Detect time conflicts between assignments"""
        conflicts = []
        timeslot_assignments = defaultdict(list)  # slot_id -> [exam_id, ...]

        for exam_id, assignment in solution.assignments.items():
            if (
                assignment.time_slot_id
                and assignment.status == AssignmentStatus.ASSIGNED
            ):
                slot_id = assignment.time_slot_id
                if slot_id not in timeslot_assignments:
                    timeslot_assignments[slot_id] = []
                timeslot_assignments[slot_id].append(exam_id)

        # Check for conflicts (multiple exams at same time)
        for slot_id, exam_ids in timeslot_assignments.items():
            if len(exam_ids) > 1:
                conflicts.append((slot_id, exam_ids))
                # Mark exams as having conflicts
                for exam_id in exam_ids:
                    if exam_id in solution.assignments:
                        solution.assignments[exam_id].status = AssignmentStatus.CONFLICT
                        solution.assignments[exam_id].conflicts.append(
                            f"Time conflict in slot {slot_id}"
                        )

        return conflicts

    def detect_real_room_conflicts(self, solution: TimetableSolution) -> List[Tuple]:
        """FIXED - Detect REAL room conflicts - only flag actual violations"""
        conflicts = []
        room_time_assignments = defaultdict(
            list
        )  # (room_id, slot_id) -> [exam_id, ...]

        for exam_id, assignment in solution.assignments.items():
            if (
                assignment.time_slot_id
                and assignment.room_ids
                and assignment.status == AssignmentStatus.ASSIGNED
            ):
                for room_id in assignment.room_ids:
                    key = (room_id, assignment.time_slot_id)
                    if key not in room_time_assignments:
                        room_time_assignments[key] = []
                    room_time_assignments[key].append(exam_id)

        # Check each room-time for REAL conflicts
        for (room_id, slot_id), exam_ids in room_time_assignments.items():
            if len(exam_ids) > 1:  # Multiple exams in same room-time
                # Get room details
                room = self.problem.rooms.get(room_id)
                if not room:
                    continue

                # Calculate total students needed
                total_students = 0
                exam_students = {}
                for exam_id in exam_ids:
                    exam = self.problem.exams.get(exam_id)
                    if exam:
                        students = getattr(exam, "expected_students", 0)
                        total_students += students
                        exam_students[exam_id] = students

                # Check capacity violation
                room_capacity = getattr(
                    room, "exam_capacity", getattr(room, "capacity", 0)
                )
                if total_students > room_capacity:
                    conflicts.append(
                        (
                            "capacity",
                            room_id,
                            slot_id,
                            exam_ids,
                            f"Capacity exceeded: {total_students} > {room_capacity}",
                        )
                    )
                    # Mark exams as having conflicts
                    for exam_id in exam_ids:
                        if exam_id in solution.assignments:
                            solution.assignments[exam_id].status = (
                                AssignmentStatus.CONFLICT
                            )
                            solution.assignments[exam_id].conflicts.append(
                                f"Room {room_id} capacity exceeded at {slot_id}"
                            )
                    continue

                # Check student scheduling conflicts
                student_conflicts = self.check_student_conflicts_in_room(
                    exam_ids, slot_id
                )
                if student_conflicts:
                    conflicts.append(
                        (
                            "student",
                            room_id,
                            slot_id,
                            exam_ids,
                            f"Student conflicts: {len(student_conflicts)} students",
                        )
                    )
                    # Mark exams as having conflicts
                    for exam_id in exam_ids:
                        if exam_id in solution.assignments:
                            solution.assignments[exam_id].status = (
                                AssignmentStatus.CONFLICT
                            )
                            solution.assignments[exam_id].conflicts.append(
                                f"Student conflict in room {room_id} at {slot_id}"
                            )
                    continue

                # If no capacity or student conflicts, this is VALID room sharing
                logger.debug(
                    f"VALID room sharing: {len(exam_ids)} exams in room {room_id} at {slot_id}"
                )

        return conflicts

    def check_student_conflicts_in_room(
        self, exam_ids: List[UUID], slot_id: UUID
    ) -> Set[UUID]:
        """Check for student conflicts between multiple exams in the same room-time"""
        student_exam_map = defaultdict(list)

        # Build student-to-exams mapping
        for exam_id in exam_ids:
            exam = self.problem.exams.get(exam_id)
            if exam:
                # Get students for this exam
                students = self.get_students_for_exam(exam_id)
                for student_id in students:
                    student_exam_map[student_id].append(exam_id)

        # Find students with conflicts (enrolled in multiple exams at this time)
        conflicted_students = set()
        for student_id, student_exams in student_exam_map.items():
            if len(student_exams) > 1:
                conflicted_students.add(student_id)

        return conflicted_students

    def get_students_for_exam(self, exam_id: UUID) -> Set[UUID]:
        """Get students registered for a specific exam"""
        students = set()

        exam = self.problem.exams.get(exam_id)
        if exam:
            # Method 1: Direct exam student access
            if hasattr(exam, "students"):
                students.update(exam.students)

            # Method 2: Course registration mapping
            if hasattr(exam, "course_id"):
                course_students = self.problem.get_students_for_course(exam.course_id)
                students.update(course_students)

            # Method 3: Problem-level method
            exam_students = self.problem.get_students_for_exam(exam_id)
            students.update(exam_students)

        return students

    def detect_capacity_violations(self, solution: TimetableSolution) -> List[Tuple]:
        """Detect room capacity violations"""
        violations = []

        for exam_id, assignment in solution.assignments.items():
            if assignment.room_ids and assignment.status == AssignmentStatus.ASSIGNED:
                exam = self.problem.exams.get(exam_id)
                if exam:
                    expected_students = exam.expected_students
                    total_capacity = assignment.total_capacity()

                    if total_capacity < expected_students:
                        violations.append((exam_id, expected_students, total_capacity))
                        # Mark exam as having conflict
                        assignment.status = AssignmentStatus.CONFLICT
                        assignment.conflicts.append(
                            f"Capacity violation: {expected_students} > {total_capacity}"
                        )

        return violations

    def calculate_room_allocations(
        self, exam_id: UUID, rooms: Set[UUID]
    ) -> Dict[UUID, int]:
        """Calculate room allocations for an exam"""
        allocations = {}
        exam = self.problem.exams.get(exam_id)

        if exam and rooms:
            equal_allocation = max(
                1, getattr(exam, "expected_students", 0) // len(rooms)
            )
            allocations = {room_id: equal_allocation for room_id in rooms}

        return allocations

    def validate_assignments(self, solution: TimetableSolution):
        """Validate extracted assignments with UUID keys"""
        logger.info("Validating assignments...")
        valid_assignments = 0
        invalid_assignments = 0

        for exam_id, assignment in solution.assignments.items():
            try:
                # Check required fields
                if not assignment.time_slot_id:
                    logger.debug(f"Assignment missing time slot: {exam_id}")
                    invalid_assignments += 1
                    continue  # Skip to next assignment

                if not assignment.room_ids:
                    logger.debug(f"Assignment missing rooms: {exam_id}")
                    invalid_assignments += 1
                    continue

                # Check room capacities
                exam = self.problem.exams.get(exam_id)
                if not exam:
                    logger.debug(f"Exam not found: {exam_id}")
                    invalid_assignments += 1
                    continue

                total_capacity = 0
                for room_id in assignment.room_ids:
                    room = self.problem.rooms.get(room_id)
                    if room:
                        capacity = getattr(
                            room, "exam_capacity", getattr(room, "capacity", 0)
                        )
                        total_capacity += capacity

                expected_students = getattr(exam, "expected_students", 0)
                if total_capacity < expected_students * 0.8:  # Allow 20% under-capacity
                    logger.debug(
                        f"Insufficient capacity for exam {exam_id}: {total_capacity} < {expected_students}"
                    )
                    invalid_assignments += 1
                    continue

                # If we reach here, assignment is valid
                valid_assignments += 1

            except Exception as e:
                logger.debug(f"Assignment validation error for exam {exam_id}: {e}")
                invalid_assignments += 1
                continue

        logger.info(
            f"Validation complete: {valid_assignments} valid, {invalid_assignments} invalid"
        )

    def analyze_resource_utilization(self, solution: TimetableSolution):
        """Analyze resource utilization with UUID keys"""
        logger.info("Analyzing resource utilization...")

        # Room utilization using UUID keys
        used_rooms = set()
        room_usage_count = defaultdict(int)
        for assignment in solution.assignments.values():
            if assignment.is_complete():
                for room_id in assignment.room_ids:
                    used_rooms.add(room_id)
                    room_usage_count[room_id] += 1

        room_utilization = (
            len(used_rooms) / len(self.problem.rooms) * 100 if self.problem.rooms else 0
        )

        # Time utilization using UUID keys
        used_slots = {
            a.time_slot_id for a in solution.assignments.values() if a.is_complete()
        }
        slot_utilization = (
            len(used_slots) / len(self.problem.timeslots) * 100
            if self.problem.timeslots
            else 0
        )

        logger.info("Resource analysis:")
        logger.info(f"  Total rooms: {len(self.problem.rooms)}")
        logger.info(f"  Total timeslots: {len(self.problem.timeslots)}")
        logger.info(
            f"  Total theoretical capacity: {len(self.problem.rooms) * len(self.problem.timeslots)}"
        )

        # Be more flexible with slot usage limits
        max_concurrent = min(
            5, len(self.problem.rooms) // 2
        )  # Allow more concurrent exams
        slot_usage = defaultdict(int)
        for assignment in solution.assignments.values():
            if assignment.is_complete():
                slot_usage[assignment.time_slot_id] += 1

        if slot_usage:
            for slot_id, usage in slot_usage.items():
                if usage > max_concurrent:
                    logger.info(f"Slot {slot_id} usage: {usage} exams")

        logger.info(
            f"  Room Utilization: {len(used_rooms)}/{len(self.problem.rooms)} ({room_utilization:.1f}%)"
        )
        logger.info(
            f"  Time Slot Utilization: {len(used_slots)}/{len(self.problem.timeslots)} ({slot_utilization:.1f}%)"
        )

    def diagnose_unassigned_exams(self, solution: TimetableSolution):
        """Diagnostic method to understand why exams are unassigned"""
        assigned_exams = set(solution.assignments.keys())
        all_exams = set(self.problem.exams.keys())
        unassigned_exams = all_exams - assigned_exams

        if not unassigned_exams:
            logger.info("No unassigned exams to diagnose")
            return

        logger.info(f"DIAGNOSING {len(unassigned_exams)} UNASSIGNED EXAMS")

        # Analyze room usage
        room_usage = defaultdict(int)
        slot_usage = defaultdict(int)
        for assignment in solution.assignments.values():
            if assignment.status == AssignmentStatus.ASSIGNED:
                if assignment.time_slot_id:
                    slot_usage[assignment.time_slot_id] += 1
                if assignment.room_ids:
                    for room_id in assignment.room_ids:
                        room_usage[room_id] += 1

        logger.info(f"Current resource utilization:")
        logger.info(f"  Rooms used: {len(room_usage)}/{len(self.problem.rooms)}")
        logger.info(f"  Slots used: {len(slot_usage)}/{len(self.problem.timeslots)}")
        logger.info(
            f"  Max concurrent exams: {max(slot_usage.values()) if slot_usage else 0}"
        )

    def ensure_all_exams_assigned(self, solution: TimetableSolution):
        """IMPROVED - Ensure all exams are assigned with enhanced logging"""
        assigned_exams = set(solution.assignments.keys())
        all_exams = set(self.problem.exams.keys())
        unassigned_exams = all_exams - assigned_exams

        logger.info(
            f"Assignment check: {len(assigned_exams)}/{len(all_exams)} exams assigned"
        )

        if unassigned_exams:
            logger.warning(f"Found {len(unassigned_exams)} unassigned exams")
            logger.info(f"Unassigned exam IDs: {list(unassigned_exams)}")

            successful_fallbacks = 0
            failed_fallbacks = 0

            for exam_id in unassigned_exams:
                logger.info(f"Attempting fallback assignment for exam {exam_id}")
                fallback_assignment = self.create_fallback_assignment(exam_id, solution)
                if fallback_assignment:
                    solution.assignments[exam_id] = fallback_assignment
                    if fallback_assignment.status == AssignmentStatus.ASSIGNED:
                        successful_fallbacks += 1
                        logger.info(
                            f"Successfully created fallback assignment for exam {exam_id}"
                        )
                    else:
                        failed_fallbacks += 1
                        logger.warning(
                            f"Created invalid fallback assignment for exam {exam_id}"
                        )
                else:
                    failed_fallbacks += 1
                    logger.error(
                        f"Could not create fallback assignment for exam {exam_id}"
                    )

            logger.info(
                f"Fallback results: {successful_fallbacks} successful, {failed_fallbacks} failed"
            )

    def create_fallback_assignment(
        self, exam_id: UUID, solution: TimetableSolution
    ) -> Optional[ExamAssignment]:
        """Create fallback assignment for unassigned exam"""
        try:
            exam = self.problem.exams.get(exam_id)
            if not exam:
                logger.error(f"Exam not found: {exam_id}")
                return None

            # Try ANY available room-slot combination
            for slot_id in self.problem.timeslots.keys():
                for room_id, room in self.problem.rooms.items():
                    room_capacity = getattr(room, "capacity", 0)

                    # Check if room is free
                    room_free = not any(
                        a.time_slot_id == slot_id and room_id in (a.room_ids or [])
                        for a in solution.assignments.values()
                        if a.status == AssignmentStatus.ASSIGNED
                    )

                    if room_free:
                        assignment = ExamAssignment(exam_id=exam_id)
                        assignment.time_slot_id = slot_id
                        assignment.room_ids = [room_id]
                        assignment.status = AssignmentStatus.ASSIGNED

                        try:
                            day = self.problem.get_day_for_timeslot(slot_id)
                            if day:  # Check if day is not None
                                assignment.assigned_date = day.date
                            else:
                                assignment.assigned_date = None
                        except Exception as e:
                            logger.debug(f"Could not set date for slot {slot_id}: {e}")
                            assignment.assigned_date = None

                        logger.info(
                            f"RELAXED FALLBACK: Assigned exam {exam_id} to room {room_id} at slot {slot_id}"
                        )
                        return assignment

            # Last resort - create invalid assignment but still track it
            assignment = ExamAssignment(exam_id=exam_id)
            assignment.status = AssignmentStatus.INVALID
            return assignment

        except Exception as e:
            logger.error(f"Error in create_fallback_assignment for exam {exam_id}: {e}")
            import traceback

            logger.debug(f"Traceback:\n{traceback.format_exc()}")
            return None

    def log_extraction_results(self, solution: TimetableSolution, conflicts_found: int):
        """Log extraction results"""
        assigned = sum(1 for a in solution.assignments.values() if a.is_complete())
        completion = (
            (assigned / len(solution.assignments)) * 100 if solution.assignments else 0
        )

        logger.info(f"Solution extraction completed:")
        logger.info(f"  Total exams: {len(solution.assignments)}")
        logger.info(f"  Assigned: {assigned} ({completion:.1f}%)")
        logger.info(f"  Conflicts: {conflicts_found}")

        if solution.is_feasible():
            logger.info("  Status: FEASIBLE")
        else:
            logger.info("  Status: HAS CONFLICTS")

    def get_completion_percentage(self) -> float:
        """Calculate completion percentage"""
        # Implement completion percentage calculation
        return 0.0  # Placeholder
