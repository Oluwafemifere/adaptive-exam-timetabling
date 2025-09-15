# scheduling_engine/core/solution.py

"""
FIXED Solution representation with enhanced conflict detection and validation.

Key Fixes:
- Enhanced conflict detection algorithms
- Proper student overlap validation
- Comprehensive solution quality checking
- Better error handling and reporting
"""

from typing import Dict, List, Optional, Any, Set, Tuple, TYPE_CHECKING
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
import logging
from .constraint_types import ConstraintSeverity
from collections import defaultdict

if TYPE_CHECKING:
    from .problem_model import ExamSchedulingProblem

logger = logging.getLogger(__name__)


class SolutionStatus(Enum):
    INCOMPLETE = "incomplete"
    FEASIBLE = "feasible"
    OPTIMAL = "optimal"
    INFEASIBLE = "infeasible"
    INVALID = "invalid"


class AssignmentStatus(Enum):
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"
    CONFLICT = "conflict"
    INVALID = "invalid"


@dataclass
class ExamAssignment:
    exam_id: UUID
    time_slot_id: Optional[UUID] = None
    room_ids: List[UUID] = field(default_factory=list)
    assigned_date: Optional[date] = None
    status: AssignmentStatus = AssignmentStatus.UNASSIGNED
    conflicts: List[str] = field(default_factory=list)
    room_allocations: Dict[UUID, int] = field(default_factory=dict)

    def is_complete(self) -> bool:
        return (
            self.time_slot_id is not None
            and len(self.room_ids) > 0
            and self.assigned_date is not None
        )

    def total_capacity(self) -> int:
        return sum(self.room_allocations.values())


@dataclass
class ConflictReport:
    conflict_id: UUID
    conflict_type: str
    severity: ConstraintSeverity
    affected_exams: List[UUID]
    affected_students: List[UUID] = field(default_factory=list)
    affected_resources: List[UUID] = field(default_factory=list)
    description: str = ""
    resolution_suggestions: List[str] = field(default_factory=list)


@dataclass
class SolutionStatistics:
    total_exams: int = 0
    assigned_exams: int = 0
    unassigned_exams: int = 0
    student_conflicts: int = 0
    room_conflicts: int = 0
    time_conflicts: int = 0
    room_utilization_percentage: float = 0.0
    time_slot_utilization_percentage: float = 0.0


class TimetableSolution:
    """
    FIXED solution class with enhanced conflict detection and validation.
    """

    def __init__(
        self, problem: "ExamSchedulingProblem", solution_id: Optional[UUID] = None
    ):
        self.id = solution_id or uuid4()
        self.problem = problem
        self.created_at = datetime.now()
        self.last_modified = datetime.now()
        self.status = SolutionStatus.INCOMPLETE
        self.objective_value: float = float("inf")
        self.fitness_score: float = 0.0

        self.assignments: Dict[UUID, ExamAssignment] = {
            eid: ExamAssignment(exam_id=eid) for eid in problem.exams
        }

        self.conflicts: Dict[UUID, ConflictReport] = {}
        self.statistics = SolutionStatistics()

    def assign(
        self,
        exam_id: UUID,
        date_: date,
        slot_id: UUID,
        rooms: List[UUID],
        allocations: Dict[UUID, int],
    ):
        """Assign exam to specific date, time slot, and rooms."""
        asm = ExamAssignment(
            exam_id=exam_id,
            time_slot_id=slot_id,
            room_ids=rooms.copy(),
            assigned_date=date_,
            status=AssignmentStatus.ASSIGNED,
            room_allocations=allocations.copy(),
        )

        self.assignments[exam_id] = asm
        self.last_modified = datetime.now()

    def get_completion_percentage(self) -> float:
        """Calculate percentage of exams with complete assignments."""
        assigned = sum(1 for a in self.assignments.values() if a.is_complete())
        return (assigned / len(self.assignments)) * 100 if self.assignments else 0

    def is_feasible(self) -> bool:
        """FIXED: Check if solution is feasible (complete and conflict-free)."""
        return (
            self.get_completion_percentage() == 100
            and len(self.detect_conflicts_fixed()) == 0
        )

    def calculate_objective_value(self) -> float:
        """Calculate objective value based on conflicts and completion."""
        conflicts = self.detect_conflicts_fixed()
        completion = self.get_completion_percentage()

        # Penalize conflicts heavily, reward completion
        conflict_penalty = len(conflicts) * 10
        completion_bonus = completion

        return conflict_penalty - completion_bonus

    def get_students_for_exam_enhanced(self, exam_id: UUID) -> Set[UUID]:
        """FIXED: Enhanced student retrieval for exam using multiple methods."""
        students = set()

        # Method 1: Direct exam student access
        exam = self.problem.exams.get(exam_id)
        if exam and hasattr(exam, "_students"):
            students.update(exam._students)

        # Method 2: Course registration mapping
        if exam:
            course_students = self.problem.get_students_for_course(exam.course_id)
            students.update(course_students)

        # Method 3: Problem-level method
        exam_students = self.problem.get_students_for_exam(exam_id)
        students.update(exam_students)

        # Method 4: Registration data lookup
        if hasattr(self.problem, "_course_students") and exam:
            course_id = exam.course_id
            if course_id in self.problem._course_students:
                students.update(self.problem._course_students[course_id])

        return students

    def detect_conflicts_fixed(self) -> List[ConflictReport]:
        """
        FIXED: Enhanced conflict detection with comprehensive validation.

        Detects:
        1. Student temporal overlaps (same student, same time, different exams)
        2. Student same-room conflicts (different exams with shared students in same room/time)
        3. Room double-booking (multiple exams in same room/time exceeding capacity)
        """
        conflicts: List[ConflictReport] = []

        # Group assignments by time slot for efficient conflict checking
        by_slot: Dict[Tuple[date, UUID], List[ExamAssignment]] = {}
        for assignment in self.assignments.values():
            if assignment.is_complete():
                assert assignment.assigned_date is not None
                assert assignment.time_slot_id is not None
                key = (assignment.assigned_date, assignment.time_slot_id)
                by_slot.setdefault(key, []).append(assignment)

        # Check conflicts for each time slot
        for (day, slot_id), slot_assignments in by_slot.items():
            if len(slot_assignments) <= 1:
                continue  # No conflicts possible with single exam

            # 1. FIXED: Student temporal overlap detection
            conflicts.extend(
                self._detect_student_temporal_conflicts(slot_assignments, day, slot_id)
            )

            # 2. FIXED: Student same-room conflicts
            conflicts.extend(
                self._detect_student_room_conflicts(slot_assignments, day, slot_id)
            )

            # 3. FIXED: Room capacity conflicts
            conflicts.extend(
                self._detect_room_capacity_conflicts(slot_assignments, day, slot_id)
            )

        # Update internal conflicts dict
        self.conflicts = {c.conflict_id: c for c in conflicts}

        logger.info(f"FIXED conflict detection found {len(conflicts)} total conflicts")
        return conflicts

    def _detect_student_temporal_conflicts(
        self, slot_assignments: List[ExamAssignment], day: date, slot_id: UUID
    ) -> List[ConflictReport]:
        """Detect students scheduled for multiple exams at the same time."""
        conflicts = []
        student_exam_map: Dict[UUID, List[UUID]] = {}

        # Build student -> exams mapping for this time slot
        for assignment in slot_assignments:
            exam_students = self.get_students_for_exam_enhanced(assignment.exam_id)
            for student_id in exam_students:
                if student_id not in student_exam_map:
                    student_exam_map[student_id] = []
                student_exam_map[student_id].append(assignment.exam_id)

        # Find students with multiple exams
        for student_id, exam_list in student_exam_map.items():
            if len(exam_list) > 1:
                conflicts.append(
                    ConflictReport(
                        conflict_id=uuid4(),
                        conflict_type="student_temporal_conflict",
                        severity=ConstraintSeverity.CRITICAL,
                        affected_exams=exam_list,
                        affected_students=[student_id],
                        description=f"Student {student_id} has {len(exam_list)} overlapping exams at {day} {slot_id}",
                        resolution_suggestions=[
                            "Reschedule conflicting exams to different time slots"
                        ],
                    )
                )

        return conflicts

    def _detect_student_room_conflicts(
        self, slot_assignments: List[ExamAssignment], day: date, slot_id: UUID
    ) -> List[ConflictReport]:
        """Detect student conflicts when multiple exams share the same room."""
        conflicts = []

        # Group assignments by room
        room_assignments: Dict[UUID, List[ExamAssignment]] = {}
        for assignment in slot_assignments:
            for room_id in assignment.room_ids:
                if room_id not in room_assignments:
                    room_assignments[room_id] = []
                room_assignments[room_id].append(assignment)

        # Check each room for student conflicts
        for room_id, room_exams in room_assignments.items():
            if len(room_exams) <= 1:
                continue  # No conflicts with single exam

            # Check all pairs of exams in this room
            for i, exam1 in enumerate(room_exams):
                for exam2 in room_exams[i + 1 :]:
                    students1 = self.get_students_for_exam_enhanced(exam1.exam_id)
                    students2 = self.get_students_for_exam_enhanced(exam2.exam_id)

                    overlap = students1 & students2
                    if overlap:
                        conflicts.append(
                            ConflictReport(
                                conflict_id=uuid4(),
                                conflict_type="student_room_conflict",
                                severity=ConstraintSeverity.HIGH,
                                affected_exams=[exam1.exam_id, exam2.exam_id],
                                affected_students=list(overlap),
                                affected_resources=[room_id],
                                description=f"{len(overlap)} students conflict in room {room_id} at {day} {slot_id}",
                                resolution_suggestions=[
                                    "Assign conflicting exams to different rooms"
                                ],
                            )
                        )

        return conflicts

    def _detect_room_capacity_conflicts(
        self, slot_assignments: List[ExamAssignment], day: date, slot_id: UUID
    ) -> List[ConflictReport]:
        """Detect room capacity violations."""
        conflicts = []

        # Calculate room usage
        room_usage: Dict[UUID, int] = {}
        room_exams: Dict[UUID, List[UUID]] = {}

        for assignment in slot_assignments:
            for room_id in assignment.room_ids:
                capacity_used = assignment.room_allocations.get(room_id, 0)
                room_usage[room_id] = room_usage.get(room_id, 0) + capacity_used

                if room_id not in room_exams:
                    room_exams[room_id] = []
                room_exams[room_id].append(assignment.exam_id)

        # Check capacity violations
        for room_id, total_usage in room_usage.items():
            room = self.problem.rooms.get(room_id)
            if not room:
                continue

            # Calculate effective capacity (with overbooking if allowed)
            base_capacity = room.capacity
            is_overbookable = getattr(room, "overbookable", False)
            overbook_rate = getattr(self.problem, "overbook_rate", 0.10)

            effective_capacity = base_capacity
            if is_overbookable:
                effective_capacity = int(base_capacity * (1 + overbook_rate))

            if total_usage > effective_capacity:
                conflicts.append(
                    ConflictReport(
                        conflict_id=uuid4(),
                        conflict_type="room_capacity_conflict",
                        severity=ConstraintSeverity.HIGH,
                        affected_exams=room_exams[room_id],
                        affected_resources=[room_id],
                        description=f"Room {room_id} overcapacity: {total_usage}/{effective_capacity} at {day} {slot_id}",
                        resolution_suggestions=[
                            "Redistribute students to additional rooms",
                            "Use larger room",
                        ],
                    )
                )

        return conflicts

    # Legacy method for backward compatibility
    def detect_conflicts(self) -> List[ConflictReport]:
        """Legacy method - delegates to fixed version."""
        return self.detect_conflicts_fixed()

    def update_statistics(self):
        """Update solution statistics based on current state."""
        stats = SolutionStatistics()
        stats.total_exams = len(self.assignments)
        stats.assigned_exams = sum(
            1 for a in self.assignments.values() if a.is_complete()
        )
        stats.unassigned_exams = stats.total_exams - stats.assigned_exams

        conflicts = self.detect_conflicts_fixed()
        stats.student_conflicts = sum(
            1
            for c in conflicts
            if c.conflict_type in ["student_temporal_conflict", "student_room_conflict"]
        )
        stats.room_conflicts = sum(
            1 for c in conflicts if c.conflict_type == "room_capacity_conflict"
        )
        stats.time_conflicts = sum(
            1
            for c in conflicts
            if c.conflict_type
            not in [
                "student_temporal_conflict",
                "student_room_conflict",
                "room_capacity_conflict",
            ]
        )

        # Calculate utilization
        used_rooms = {
            r for a in self.assignments.values() if a.is_complete() for r in a.room_ids
        }
        stats.room_utilization_percentage = (
            len(used_rooms) / len(self.problem.rooms) * 100
            if self.problem.rooms
            else 0.0
        )

        used_slots = {
            a.time_slot_id for a in self.assignments.values() if a.is_complete()
        }
        stats.time_slot_utilization_percentage = (
            len(used_slots) / len(self.problem.time_slots) * 100
            if self.problem.time_slots
            else 0.0
        )

        self.statistics = stats

    def to_dict(self) -> Dict[str, Any]:
        """Convert solution to dictionary format."""
        self.update_statistics()

        return {
            "solution_id": str(self.id),
            "status": self.status.value,
            "objective_value": self.objective_value,
            "fitness_score": self.fitness_score,
            "completion_percentage": self.get_completion_percentage(),
            "is_feasible": self.is_feasible(),
            "assignments": {
                str(eid): {
                    "time_slot_id": str(a.time_slot_id) if a.time_slot_id else None,
                    "assigned_date": (
                        a.assigned_date.isoformat() if a.assigned_date else None
                    ),
                    "room_ids": [str(r) for r in a.room_ids],
                    "status": a.status.value,
                    "conflicts": a.conflicts,
                    "room_allocations": {
                        str(r): cap for r, cap in a.room_allocations.items()
                    },
                }
                for eid, a in self.assignments.items()
            },
            "conflicts": [
                {
                    "conflict_id": str(c.conflict_id),
                    "type": c.conflict_type,
                    "severity": c.severity.value,
                    "description": c.description,
                    "affected_exams": [str(e) for e in c.affected_exams],
                    "affected_students": [str(s) for s in c.affected_students],
                    "affected_resources": [str(r) for r in c.affected_resources],
                    "resolution_suggestions": c.resolution_suggestions,
                }
                for c in self.conflicts.values()
            ],
            "statistics": {
                "total_exams": self.statistics.total_exams,
                "assigned_exams": self.statistics.assigned_exams,
                "unassigned_exams": self.statistics.unassigned_exams,
                "student_conflicts": self.statistics.student_conflicts,
                "room_conflicts": self.statistics.room_conflicts,
                "time_conflicts": self.statistics.time_conflicts,
                "room_utilization_percentage": self.statistics.room_utilization_percentage,
                "time_slot_utilization_percentage": self.statistics.time_slot_utilization_percentage,
            },
        }

    def show_gui_viewer(self, title: Optional[str] = None) -> Any:
        """
        Launch the GUI viewer for interactive timetable visualization.
        """
        logger.info("🖥️ Launching GUI viewer for timetable solution...")

        # Validate GUI requirements first
        if not self.validate_gui_requirements():
            logger.warning("⚠️ GUI requirements not met, cannot display GUI")
            self.print_solution_summary()
            return None

        try:
            # Import GUI module (lazy import to avoid dependency issues)
            from scheduling_engine.gui import show_timetable_gui

            # Update solution statistics before displaying
            self.update_statistics()

            # Detect conflicts for display
            conflicts = self.detect_conflicts()
            logger.info(f"📊 Solution has {len(conflicts)} conflicts to display")

            # Create and show GUI
            gui_viewer = show_timetable_gui(self.problem, self)

            logger.info("✅ GUI viewer launched successfully")
            return gui_viewer

        except ImportError as e:
            error_msg = f"GUI components not available: {e}"
            logger.error(f"❌ {error_msg}")

            # Fallback: print solution summary to console
            print("\n" + "=" * 60)
            print("📅 TIMETABLE SOLUTION SUMMARY")
            print("=" * 60)
            self.print_solution_summary()
            print("=" * 60)

            raise ImportError(f"Cannot display GUI: {error_msg}")

        except Exception as e:
            logger.error(f"❌ Failed to launch GUI viewer: {e}")

            # Fallback: print solution summary
            print(f"\n❌ GUI Error: {e}")
            print("📋 Displaying text summary instead:")
            self.print_solution_summary()

            raise

    def print_solution_summary(self):
        """
        Print a comprehensive text-based summary of the solution.
        This serves as a fallback when GUI is not available.
        """
        print(f"\n📊 Solution Statistics:")
        print(f"   Total Exams: {len(self.assignments)}")

        assigned = sum(1 for a in self.assignments.values() if a.is_complete())
        completion = self.get_completion_percentage()
        print(
            f"   Assigned Exams: {assigned}/{len(self.assignments)} ({completion:.1f}%)"
        )

        conflicts = self.detect_conflicts()
        print(f"   Conflicts: {len(conflicts)}")

        if self.is_feasible():
            print("   Status: ✅ FEASIBLE")
        else:
            print("   Status: ⚠️ HAS CONFLICTS")

        # Room utilization
        used_rooms = set()
        for assignment in self.assignments.values():
            if assignment.is_complete():
                used_rooms.update(assignment.room_ids)

        room_util = (
            len(used_rooms) / len(self.problem.rooms) * 100 if self.problem.rooms else 0
        )
        print(
            f"   Room Utilization: {len(used_rooms)}/{len(self.problem.rooms)} ({room_util:.1f}%)"
        )

        # Time slot utilization
        used_slots = {
            a.time_slot_id for a in self.assignments.values() if a.is_complete()
        }
        slot_util = (
            len(used_slots) / len(self.problem.time_slots) * 100
            if self.problem.time_slots
            else 0
        )
        print(
            f"   Time Slot Utilization: {len(used_slots)}/{len(self.problem.time_slots)} ({slot_util:.1f}%)"
        )

        # Show some assignments
        print(f"\n📋 Sample Assignments:")
        count = 0
        for exam_id, assignment in self.assignments.items():
            if assignment.is_complete() and count < 5:  # Show first 5
                exam = self.problem.exams.get(exam_id)
                assert assignment.time_slot_id
                time_slot = self.problem.time_slots.get(assignment.time_slot_id)

                if exam and time_slot:
                    room_codes = []
                    for room_id in assignment.room_ids:
                        room = self.problem.rooms.get(room_id)
                        if room:
                            room_codes.append(room.code)

                    print(
                        f"   • Exam {str(exam.id)[:8]}... → {assignment.assigned_date} at {time_slot.start_time.strftime('%H:%M')}"
                    )
                    print(
                        f"     Rooms: {', '.join(room_codes)} | Students: {exam.expected_students}"
                    )
                    count += 1

        if assigned > 5:
            print(f"   ... and {assigned - 5} more assigned exams")

        # Show conflicts if any
        if conflicts:
            print(f"\n⚠️  Detected Conflicts:")
            for i, conflict in enumerate(conflicts[:3], 1):  # Show first 3
                print(f"   {i}. {conflict.conflict_type}: {conflict.description}")

            if len(conflicts) > 3:
                print(f"   ... and {len(conflicts) - 3} more conflicts")

        print()

    def validate_gui_requirements(self) -> bool:
        """
        Validate that the solution has the necessary data for GUI display.

        Returns:
            bool: True if GUI can be displayed, False otherwise
        """
        try:
            # Check essential data
            if not self.problem:
                logger.warning("No problem instance available")
                return False

            if not hasattr(self.problem, "exams") or not self.problem.exams:
                logger.warning("No exams in problem")
                return False

            if not hasattr(self.problem, "time_slots") or not self.problem.time_slots:
                logger.warning("No time slots in problem")
                return False

            if not hasattr(self.problem, "rooms") or not self.problem.rooms:
                logger.warning("No rooms in problem")
                return False

            # Check assignments
            if not self.assignments:
                logger.warning("No assignments in solution")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating GUI requirements: {e}")
            return False

    # Enhanced solution analysis methods

    def get_detailed_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive solution statistics for GUI display.

        Returns:
            Dict containing detailed solution statistics
        """
        self.update_statistics()

        # Basic statistics
        total_exams = len(self.assignments)
        assigned_exams = sum(1 for a in self.assignments.values() if a.is_complete())
        completion_rate = (assigned_exams / total_exams * 100) if total_exams > 0 else 0

        # Resource utilization
        used_rooms = set()
        room_usage_count = defaultdict(int)
        for assignment in self.assignments.values():
            if assignment.is_complete():
                for room_id in assignment.room_ids:
                    used_rooms.add(room_id)
                    room_usage_count[room_id] += 1

        room_utilization = (
            (len(used_rooms) / len(self.problem.rooms) * 100)
            if self.problem.rooms
            else 0
        )

        # Time utilization
        used_slots = {
            a.time_slot_id for a in self.assignments.values() if a.is_complete()
        }
        slot_utilization = (
            (len(used_slots) / len(self.problem.time_slots) * 100)
            if self.problem.time_slots
            else 0
        )

        # Conflicts
        conflicts = self.detect_conflicts()
        conflict_types = defaultdict(int)
        for conflict in conflicts:
            conflict_types[conflict.conflict_type] += 1

        # Student statistics
        total_students = sum(
            exam.expected_students for exam in self.problem.exams.values()
        )
        avg_students_per_exam = (
            total_students / len(self.problem.exams) if self.problem.exams else 0
        )

        # Fix: Handle case where room_usage_count might be empty
        most_used_room = None
        if room_usage_count:
            # Use a lambda function to avoid type checking issues with max()
            most_used_room = max(
                room_usage_count.keys(), key=lambda k: room_usage_count[k]
            )

        return {
            "basic": {
                "total_exams": total_exams,
                "assigned_exams": assigned_exams,
                "unassigned_exams": total_exams - assigned_exams,
                "completion_rate": completion_rate,
                "is_feasible": self.is_feasible(),
                "objective_value": self.objective_value,
                "fitness_score": self.fitness_score,
            },
            "resources": {
                "total_rooms": len(self.problem.rooms),
                "used_rooms": len(used_rooms),
                "room_utilization": room_utilization,
                "total_time_slots": len(self.problem.time_slots),
                "used_time_slots": len(used_slots),
                "slot_utilization": slot_utilization,
                "most_used_room": most_used_room,
            },
            "students": {
                "total_students": total_students,
                "avg_students_per_exam": avg_students_per_exam,
                "total_registrations": (
                    len(self.problem.students)
                    if hasattr(self.problem, "students")
                    else 0
                ),
            },
            "conflicts": {
                "total_conflicts": len(conflicts),
                "conflict_types": dict(conflict_types),
                "has_conflicts": len(conflicts) > 0,
            },
            "time_analysis": {
                "exam_period_days": (
                    len(self.problem.days) if hasattr(self.problem, "days") else 0
                ),
                "peak_usage": (
                    max(
                        sum(
                            1
                            for a in self.assignments.values()
                            if a.is_complete() and a.time_slot_id == slot_id
                        )
                        for slot_id in self.problem.time_slots
                    )
                    if self.problem.time_slots
                    else 0
                ),
            },
        }

    def export_for_gui(self) -> Dict[str, Any]:
        """
        Export solution data in format optimized for GUI display.

        Returns:
            Dict containing GUI-optimized solution data
        """
        gui_data = {
            "metadata": {
                "solution_id": str(self.id),
                "created_at": self.created_at.isoformat(),
                "last_modified": self.last_modified.isoformat(),
                "status": self.status.value,
            },
            "statistics": self.get_detailed_statistics(),
            "assignments": {},
            "conflicts": [],
            "calendar_data": defaultdict(lambda: defaultdict(list)),
            "room_schedules": defaultdict(list),
            "color_coding": {},
        }

        # Process assignments for GUI display
        for exam_id, assignment in self.assignments.items():
            exam = self.problem.exams.get(exam_id)
            if not exam:
                continue

            assignment_data = {
                "exam_id": str(exam_id),
                "course_id": str(exam.course_id),
                "status": assignment.status.value,
                "is_complete": assignment.is_complete(),
                "expected_students": exam.expected_students,
                "duration_minutes": exam.duration_minutes,
            }

            if assignment.is_complete():
                # Fix: Ensure assigned_date is not None before calling isoformat()
                assigned_date_str = (
                    assignment.assigned_date.isoformat()
                    if assignment.assigned_date
                    else ""
                )
                time_slot_id_str = (
                    str(assignment.time_slot_id) if assignment.time_slot_id else ""
                )

                assignment_data.update(
                    {
                        "assigned_date": assigned_date_str,
                        "time_slot_id": time_slot_id_str,
                        "room_ids": [str(rid) for rid in assignment.room_ids],
                        "room_allocations": {
                            str(k): v for k, v in assignment.room_allocations.items()
                        },
                    }
                )

                # Add to calendar data for grid display
                if assignment.assigned_date:
                    date_key = assignment.assigned_date.isoformat()
                    time_key = str(assignment.time_slot_id)
                    gui_data["calendar_data"][date_key][time_key].append(
                        assignment_data
                    )

                # Add to room schedules
                for room_id in assignment.room_ids:
                    gui_data["room_schedules"][str(room_id)].append(assignment_data)

            gui_data["assignments"][str(exam_id)] = assignment_data

        # Process conflicts
        conflicts = self.detect_conflicts()
        for conflict in conflicts:
            conflict_data = {
                "conflict_id": str(conflict.conflict_id),
                "type": conflict.conflict_type,
                "severity": conflict.severity.value,
                "description": conflict.description,
                "affected_exams": [str(eid) for eid in conflict.affected_exams],
                "affected_students": [str(sid) for sid in conflict.affected_students],
                "affected_resources": [str(rid) for rid in conflict.affected_resources],
                "suggestions": conflict.resolution_suggestions,
            }
            gui_data["conflicts"].append(conflict_data)

        return gui_data
