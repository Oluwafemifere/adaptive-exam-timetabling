# scheduling_engine/tests/unit/test_solution.py

"""
Comprehensive tests for solution representation and management.
"""

import math
import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID, uuid4
from datetime import datetime, date, time as dt_time

from scheduling_engine.core.solution import (
    TimetableSolution,
    ExamAssignment,
    ConflictReport,
    SolutionStatistics,
    AssignmentStatus,
    SolutionStatus,
)
from scheduling_engine.core.problem_model import (
    ExamSchedulingProblem,
    Exam,
    TimeSlot,
    Room,
    Student,
)
from scheduling_engine.core.constraint_types import ConstraintSeverity


class TestExamAssignment:
    """Tests for ExamAssignment dataclass"""

    def test_exam_assignment_initialization(self):
        """Test ExamAssignment initialization"""
        exam_id = uuid4()
        assignment = ExamAssignment(exam_id=exam_id)

        assert assignment.exam_id == exam_id
        assert assignment.time_slot_id is None
        assert assignment.room_ids == []
        assert assignment.assigned_date is None
        assert assignment.status == AssignmentStatus.UNASSIGNED
        assert assignment.assignment_priority == 0.0
        assert assignment.conflicts == []
        assert assignment.room_allocations == {}
        assert assignment.backend_data == {}

    def test_exam_assignment_completion_check(self):
        """Test is_complete method"""
        exam_id = uuid4()
        time_slot_id = uuid4()
        room_id = uuid4()
        exam_date = date(2024, 1, 15)

        # Test incomplete assignment
        incomplete = ExamAssignment(exam_id=exam_id)
        assert not incomplete.is_complete()

        # Test complete assignment
        complete = ExamAssignment(
            exam_id=exam_id,
            time_slot_id=time_slot_id,
            room_ids=[room_id],
            assigned_date=exam_date,
        )
        assert complete.is_complete()

        # Test partial completion (no rooms)
        no_rooms = ExamAssignment(
            exam_id=exam_id, time_slot_id=time_slot_id, assigned_date=exam_date
        )
        assert not no_rooms.is_complete()

        # Test partial completion (no time slot)
        no_time_slot = ExamAssignment(
            exam_id=exam_id, room_ids=[room_id], assigned_date=exam_date
        )
        assert not no_time_slot.is_complete()

        # Test partial completion (no date)
        no_date = ExamAssignment(
            exam_id=exam_id, time_slot_id=time_slot_id, room_ids=[room_id]
        )
        assert not no_date.is_complete()

    def test_exam_assignment_capacity_calculation(self):
        """Test capacity calculation methods"""
        exam_id = uuid4()
        room1_id = uuid4()
        room2_id = uuid4()

        assignment = ExamAssignment(exam_id=exam_id)

        # Test empty allocation
        assert assignment.get_total_capacity() == 0

        # Test with allocations
        assignment.add_room_allocation(room1_id, 25)
        assignment.add_room_allocation(room2_id, 30)

        assert assignment.get_total_capacity() == 55
        assert assignment.room_allocations[room1_id] == 25
        assert assignment.room_allocations[room2_id] == 30
        assert room1_id in assignment.room_ids
        assert room2_id in assignment.room_ids

    def test_exam_assignment_backend_format(self):
        """Test conversion to backend format"""
        exam_id = uuid4()
        time_slot_id = uuid4()
        room_id = uuid4()
        exam_date = date(2024, 1, 15)

        assignment = ExamAssignment(
            exam_id=exam_id,
            time_slot_id=time_slot_id,
            room_ids=[room_id],
            assigned_date=exam_date,
            status=AssignmentStatus.ASSIGNED,
        )
        assignment.add_room_allocation(room_id, 30)

        backend_format = assignment.to_backend_format()

        assert backend_format["exam_id"] == str(exam_id)
        assert backend_format["time_slot_id"] == str(time_slot_id)
        assert backend_format["exam_date"] == exam_date.isoformat()
        assert len(backend_format["room_assignments"]) == 1
        assert backend_format["room_assignments"][0]["room_id"] == str(room_id)
        assert backend_format["room_assignments"][0]["allocated_capacity"] == 30
        assert backend_format["status"] == "scheduled"


class TestConflictReport:
    """Tests for ConflictReport dataclass"""

    def test_conflict_report_initialization(self):
        """Test ConflictReport initialization"""
        conflict_id = uuid4()
        exam_id = uuid4()
        student_id = uuid4()
        room_id = uuid4()

        report = ConflictReport(
            conflict_id=conflict_id,
            conflict_type="student_conflict",
            severity=ConstraintSeverity.HIGH,
            affected_exams=[exam_id],
            affected_students=[student_id],
            affected_resources=[room_id],
            description="Test conflict",
            resolution_suggestions=["Move exam"],
            constraint_violation_type="overlap",
            backend_data={"key": "value"},
        )

        assert report.conflict_id == conflict_id
        assert report.conflict_type == "student_conflict"
        assert report.severity == ConstraintSeverity.HIGH
        assert report.affected_exams == [exam_id]
        assert report.affected_students == [student_id]
        assert report.affected_resources == [room_id]
        assert report.description == "Test conflict"
        assert report.resolution_suggestions == ["Move exam"]
        assert report.constraint_violation_type == "overlap"
        assert report.backend_data == {"key": "value"}


class TestSolutionStatistics:
    """Tests for SolutionStatistics dataclass"""

    def test_solution_statistics_initialization(self):
        """Test SolutionStatistics initialization"""
        stats = SolutionStatistics()

        assert stats.total_exams == 0
        assert stats.assigned_exams == 0
        assert stats.unassigned_exams == 0
        assert stats.hard_constraint_violations == 0
        assert stats.soft_constraint_violations == 0
        assert stats.student_conflicts == 0
        assert stats.room_conflicts == 0
        assert stats.time_conflicts == 0
        assert stats.room_utilization_percentage == 0.0
        assert stats.time_slot_utilization_percentage == 0.0
        assert stats.student_satisfaction_score == 0.0
        assert stats.solution_time_seconds == 0.0
        assert stats.iterations_required == 0
        assert stats.memory_usage_mb == 0.0
        assert stats.faculty_distribution == {}
        assert stats.department_distribution == {}
        assert stats.practical_exam_allocation == {}

    def test_solution_statistics_custom_values(self):
        """Test SolutionStatistics with custom values"""
        stats = SolutionStatistics(
            total_exams=100,
            assigned_exams=95,
            unassigned_exams=5,
            hard_constraint_violations=2,
            soft_constraint_violations=10,
            student_conflicts=3,
            room_conflicts=1,
            time_conflicts=2,
            room_utilization_percentage=85.5,
            time_slot_utilization_percentage=75.0,
            student_satisfaction_score=0.8,
            solution_time_seconds=120.5,
            iterations_required=1000,
            memory_usage_mb=256.0,
            faculty_distribution={"Science": 50, "Arts": 45},
            department_distribution={"Physics": 20, "Chemistry": 25},
            practical_exam_allocation={"computer_lab": 15, "regular": 5},
        )

        assert stats.total_exams == 100
        assert stats.assigned_exams == 95
        assert stats.unassigned_exams == 5
        assert stats.hard_constraint_violations == 2
        assert stats.soft_constraint_violations == 10
        assert stats.student_conflicts == 3
        assert stats.room_conflicts == 1
        assert stats.time_conflicts == 2
        assert stats.room_utilization_percentage == 85.5
        assert stats.time_slot_utilization_percentage == 75.0
        assert stats.student_satisfaction_score == 0.8
        assert stats.solution_time_seconds == 120.5
        assert stats.iterations_required == 1000
        assert stats.memory_usage_mb == 256.0
        assert stats.faculty_distribution == {"Science": 50, "Arts": 45}
        assert stats.department_distribution == {"Physics": 20, "Chemistry": 25}
        assert stats.practical_exam_allocation == {"computer_lab": 15, "regular": 5}


class TestTimetableSolution:
    """Tests for TimetableSolution class functionality"""

    @pytest.fixture
    def setup_basic_problem(self):
        """Set up a basic problem for testing"""
        problem = ExamSchedulingProblem(session_id=uuid4(), session_name="Test Session")

        # Add time slot
        time_slot = TimeSlot(
            id=uuid4(),
            name="Morning Slot",
            start_time=dt_time(9, 0),
            end_time=dt_time(12, 0),
            duration_minutes=180,
        )
        problem.time_slots[time_slot.id] = time_slot

        # Add room
        room = Room(
            id=uuid4(),
            code="ROOM001",
            name="Test Room",
            capacity=50,
            exam_capacity=45,
            has_computers=True,
        )
        problem.rooms[room.id] = room

        # Add students
        student1 = Student(
            id=uuid4(), matric_number="STU001", programme_id=uuid4(), current_level=200
        )
        student2 = Student(
            id=uuid4(), matric_number="STU002", programme_id=uuid4(), current_level=200
        )
        problem.students[student1.id] = student1
        problem.students[student2.id] = student2

        # Add exams
        exam1 = Exam(
            id=uuid4(),
            course_id=uuid4(),
            course_code="TEST001",
            course_title="Test Course",
            expected_students=30,
            duration_minutes=180,
            is_practical=True,
        )
        exam2 = Exam(
            id=uuid4(),
            course_id=uuid4(),
            course_code="TEST002",
            course_title="Test Course 2",
            expected_students=25,
            duration_minutes=180,
        )
        problem.exams[exam1.id] = exam1
        problem.exams[exam2.id] = exam2

        # Register students for exams
        problem.exam_student_assignments[exam1.id] = {student1.id, student2.id}
        problem.exam_student_assignments[exam2.id] = {student1.id, student2.id}

        return problem

    def test_timetable_solution_initialization(self, setup_basic_problem):
        """Test TimetableSolution initialization"""
        problem = setup_basic_problem
        solution = TimetableSolution(problem)

        assert solution.problem == problem
        assert solution.session_id == problem.session_id
        assert solution.status == SolutionStatus.INCOMPLETE
        assert solution.objective_value == float("inf")
        assert solution.fitness_score == 0.0
        assert solution.constraint_violations == {}
        assert solution.conflicts == {}
        assert isinstance(solution.statistics, SolutionStatistics)
        assert solution.solver_phase is None
        assert solution.generation == 0
        assert solution.parent_solutions == []
        assert solution.backend_services == {}

        # Should have empty assignments for all exams
        assert len(solution.assignments) == len(problem.exams)
        for exam_id in problem.exams:
            assert exam_id in solution.assignments
            assert solution.assignments[exam_id].exam_id == exam_id
            assert solution.assignments[exam_id].status == AssignmentStatus.UNASSIGNED

    def test_assign_exam_success(self, setup_basic_problem):
        """Test successful exam assignment"""
        problem = setup_basic_problem
        solution = TimetableSolution(problem)

        exam_id = next(iter(problem.exams.keys()))
        time_slot_id = next(iter(problem.time_slots.keys()))
        room_id = next(iter(problem.rooms.keys()))
        exam_date = date(2024, 1, 15)

        success = solution.assign_exam(
            exam_id=exam_id,
            time_slot_id=time_slot_id,
            room_ids=[room_id],
            assigned_date=exam_date,
        )

        assert success is True
        assignment = solution.assignments[exam_id]
        assert assignment.time_slot_id == time_slot_id
        assert assignment.room_ids == [room_id]
        assert assignment.assigned_date == exam_date
        assert assignment.status == AssignmentStatus.ASSIGNED
        assert assignment.get_total_capacity() == 30  # Expected students

    def test_assign_exam_failure(self, setup_basic_problem):
        """Test exam assignment failure cases"""
        problem = setup_basic_problem
        solution = TimetableSolution(problem)

        # Test with non-existent exam
        success = solution.assign_exam(
            exam_id=uuid4(),  # Not in problem
            time_slot_id=uuid4(),
            room_ids=[uuid4()],
            assigned_date=date(2024, 1, 15),
        )
        assert success is False

        # Test with custom allocations
        exam_id = next(iter(problem.exams.keys()))
        time_slot_id = next(iter(problem.time_slots.keys()))
        room_id = next(iter(problem.rooms.keys()))

        success = solution.assign_exam(
            exam_id=exam_id,
            time_slot_id=time_slot_id,
            room_ids=[room_id],
            assigned_date=date(2024, 1, 15),
            room_allocations={room_id: 25},  # Custom allocation
        )
        assert success is True
        assert solution.assignments[exam_id].room_allocations[room_id] == 25

    def test_unassign_exam(self, setup_basic_problem):
        """Test exam unassignment"""
        problem = setup_basic_problem
        solution = TimetableSolution(problem)

        exam_id = next(iter(problem.exams.keys()))
        time_slot_id = next(iter(problem.time_slots.keys()))
        room_id = next(iter(problem.rooms.keys()))

        # First assign the exam
        solution.assign_exam(
            exam_id=exam_id,
            time_slot_id=time_slot_id,
            room_ids=[room_id],
            assigned_date=date(2024, 1, 15),
        )

        # Then unassign it
        success = solution.unassign_exam(exam_id)
        assert success is True
        assert solution.assignments[exam_id].time_slot_id is None
        assert solution.assignments[exam_id].room_ids == []
        assert solution.assignments[exam_id].assigned_date is None
        assert solution.assignments[exam_id].status == AssignmentStatus.UNASSIGNED

        # Test unassigning non-existent exam
        success = solution.unassign_exam(uuid4())
        assert success is False

    def test_validate_assignment(self, setup_basic_problem):
        """Test assignment validation"""
        problem = setup_basic_problem
        solution = TimetableSolution(problem)

        exam_id = next(iter(problem.exams.keys()))
        time_slot_id = next(iter(problem.time_slots.keys()))
        room_id = next(iter(problem.rooms.keys()))

        # Create a valid assignment
        assignment = ExamAssignment(
            exam_id=exam_id,
            time_slot_id=time_slot_id,
            room_ids=[room_id],
            assigned_date=date(2024, 1, 15),
        )
        assignment.add_room_allocation(room_id, 30)

        # Validate the assignment
        solution._validate_assignment(assignment)
        assert assignment.status == AssignmentStatus.ASSIGNED
        assert assignment.conflicts == []

        # Test with insufficient capacity
        assignment.room_allocations[room_id] = 20  # Less than expected
        solution._validate_assignment(assignment)
        assert assignment.status == AssignmentStatus.CONFLICT
        assert len(assignment.conflicts) > 0

        # Test with non-computer room for practical exam
        non_computer_room = Room(
            id=uuid4(),
            code="ROOM002",
            name="Non-Computer Room",
            capacity=50,
            exam_capacity=45,
            has_computers=False,  # No computers
        )
        problem.rooms[non_computer_room.id] = non_computer_room

        assignment.room_ids = [non_computer_room.id]
        assignment.room_allocations = {non_computer_room.id: 30}
        solution._validate_assignment(assignment)
        assert assignment.status == AssignmentStatus.CONFLICT
        assert any("computers" in conflict for conflict in assignment.conflicts)

    def test_detect_conflicts(self, setup_basic_problem):
        """Test conflict detection"""
        problem = setup_basic_problem
        solution = TimetableSolution(problem)

        # Get exam IDs
        exam_ids = list(problem.exams.keys())
        time_slot_id = next(iter(problem.time_slots.keys()))
        room_id = next(iter(problem.rooms.keys()))
        exam_date = date(2024, 1, 15)

        # Assign both exams to the same time slot and room
        solution.assign_exam(
            exam_id=exam_ids[0],
            time_slot_id=time_slot_id,
            room_ids=[room_id],
            assigned_date=exam_date,
        )

        solution.assign_exam(
            exam_id=exam_ids[1],
            time_slot_id=time_slot_id,
            room_ids=[room_id],  # Same room - should create room conflict
            assigned_date=exam_date,
        )

        # Detect conflicts
        conflicts = solution.detect_conflicts()

        # Should find at least a room conflict
        assert len(conflicts) > 0
        assert any(conflict.conflict_type == "room_conflict" for conflict in conflicts)
        assert len(solution.conflicts) == len(conflicts)

    def test_calculate_objective_value(self, setup_basic_problem):
        """Test objective value calculation"""
        problem = setup_basic_problem
        solution = TimetableSolution(problem)

        exam_ids = list(problem.exams.keys())
        time_slot_id = next(iter(problem.time_slots.keys()))
        room_id = next(iter(problem.rooms.keys()))

        # Assign both exams first
        exam_date = date(2024, 1, 15)
        for exam_id in exam_ids:
            solution.assign_exam(
                exam_id=exam_id,
                time_slot_id=time_slot_id,
                room_ids=[room_id],
                assigned_date=exam_date,
            )

        # Set due date to past for first exam (should create tardiness)
        problem.exams[exam_ids[0]].due_date = datetime(2024, 1, 10, 9, 0)

        objective_value = solution.calculate_objective_value()
        assert objective_value > 0  # Should have positive tardiness

        # Unassign first exam and check penalty
        solution.unassign_exam(exam_ids[0])
        objective_value = solution.calculate_objective_value()
        # Only one exam unassigned now, penalty should be 1000.0
        assert math.isclose(objective_value, 1000.0 + 7.5)

    def test_calculate_fitness_score(self, setup_basic_problem):
        """Test fitness score calculation"""
        problem = setup_basic_problem
        solution = TimetableSolution(problem)

        # Mock objective value and conflict detection
        with patch.object(
            solution, "calculate_objective_value", return_value=50.0
        ), patch.object(
            solution, "get_completion_percentage", return_value=100.0
        ), patch.object(
            solution, "detect_conflicts", return_value=[]
        ):

            fitness = solution.calculate_fitness_score()
            assert 0 <= fitness <= 1.0

        # Test with infinite objective value
        with patch.object(
            solution, "calculate_objective_value", return_value=float("inf")
        ):
            fitness = solution.calculate_fitness_score()
            assert fitness == 0.0

    def test_solution_completion_checks(self, setup_basic_problem):
        """Test solution completion checks"""
        problem = setup_basic_problem
        solution = TimetableSolution(problem)

        # Initially incomplete
        assert not solution.is_complete()
        assert solution.get_completion_percentage() == 0.0

        # Assign all exams
        time_slot_id = next(iter(problem.time_slots.keys()))
        room_id = next(iter(problem.rooms.keys()))
        exam_date = date(2024, 1, 15)

        for exam_id in problem.exams:
            solution.assign_exam(
                exam_id=exam_id,
                time_slot_id=time_slot_id,
                room_ids=[room_id],
                assigned_date=exam_date,
            )

        # Should be complete now
        assert solution.is_complete()
        assert solution.get_completion_percentage() == 100.0

    def test_solution_copy(self, setup_basic_problem):
        """Test solution copying"""
        problem = setup_basic_problem
        solution = TimetableSolution(problem)

        # Assign an exam
        exam_id = next(iter(problem.exams.keys()))
        time_slot_id = next(iter(problem.time_slots.keys()))
        room_id = next(iter(problem.rooms.keys()))

        solution.assign_exam(
            exam_id=exam_id,
            time_slot_id=time_slot_id,
            room_ids=[room_id],
            assigned_date=date(2024, 1, 15),
        )

        # Copy the solution
        copy = solution.copy()

        # Verify it's a different object with same data
        assert copy.id != solution.id
        assert copy.problem == solution.problem
        assert len(copy.assignments) == len(solution.assignments)
        assert copy.assignments[exam_id].time_slot_id == time_slot_id
        assert copy.assignments[exam_id].room_ids == [room_id]

    def test_solution_serialization(self, setup_basic_problem):
        """Test solution serialization to dict"""
        problem = setup_basic_problem
        solution = TimetableSolution(problem)

        # Assign an exam
        exam_id = next(iter(problem.exams.keys()))
        time_slot_id = next(iter(problem.time_slots.keys()))
        room_id = next(iter(problem.rooms.keys()))

        solution.assign_exam(
            exam_id=exam_id,
            time_slot_id=time_slot_id,
            room_ids=[room_id],
            assigned_date=date(2024, 1, 15),
        )

        # Convert to dict
        solution_dict = solution.to_dict()

        # Verify structure
        assert "id" in solution_dict
        assert "problem_id" in solution_dict
        assert "session_id" in solution_dict
        assert "status" in solution_dict
        assert "created_at" in solution_dict
        assert "last_modified" in solution_dict
        assert "objective_value" in solution_dict
        assert "fitness_score" in solution_dict
        assert "completion_percentage" in solution_dict
        assert "is_feasible" in solution_dict
        assert "assignments" in solution_dict
        assert "statistics" in solution_dict
        assert "conflicts" in solution_dict
        assert "solver_metadata" in solution_dict

        # Verify assignment data
        assignment_key = str(exam_id)
        assert assignment_key in solution_dict["assignments"]
        assignment_data = solution_dict["assignments"][assignment_key]
        assert assignment_data["exam_id"] == str(exam_id)
        assert assignment_data["time_slot_id"] == str(time_slot_id)
        assert assignment_data["room_ids"] == [str(room_id)]


if __name__ == "__main__":
    pytest.main([__file__])
