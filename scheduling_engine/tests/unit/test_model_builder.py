# scheduling_engine/tests/unit/test_model_builder.py

"""
Tests for CPSATModelBuilder class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID, uuid4
from datetime import datetime, time, date

from ortools.sat.python import cp_model

from scheduling_engine.cp_sat.model_builder import CPSATModelBuilder
from scheduling_engine.core.problem_model import (
    ExamSchedulingProblem,
    Exam,
    Room,
    TimeSlot,
)
from scheduling_engine.core.solution import (
    TimetableSolution,
    ExamAssignment,
    AssignmentStatus,
)
from scheduling_engine.config import CPSATConfig


class TestModelBuilder:
    """Tests for CPSATModelBuilder functionality"""

    def test_model_builder_initialization(self):
        """Test model builder initialization"""
        config = CPSATConfig(
            time_limit_seconds=300, num_workers=4, use_hint_from_previous=True
        )

        builder = CPSATModelBuilder(config)

        assert builder.config == config
        assert builder.model is None
        assert builder.problem is None
        assert builder.variables == {}

    def test_build_model(self):
        """Test model building"""
        builder = CPSATModelBuilder()

        # Create a minimal problem instance
        problem = ExamSchedulingProblem(session_id=uuid4(), session_name="Test")

        # Add some entities
        exam = Exam(
            id=uuid4(),
            course_id=uuid4(),
            course_code="TEST001",
            course_title="Test Course",
            expected_students=30,
            duration_minutes=180,
        )
        problem.exams[exam.id] = exam

        room = Room(
            id=uuid4(), code="ROOM001", name="Test Room", capacity=50, exam_capacity=45
        )
        problem.rooms[room.id] = room

        time_slot = TimeSlot(
            id=uuid4(),
            name="Morning Slot",
            start_time=time(9, 0),
            end_time=time(12, 0),
            duration_minutes=180,
        )
        problem.time_slots[time_slot.id] = time_slot

        model = builder.build_model(problem)

        assert model is not None
        assert builder.problem == problem
        assert len(builder.variables) > 0

    def test_create_decision_variables(self):
        """Test decision variable creation"""
        builder = CPSATModelBuilder()
        builder.model = cp_model.CpModel()

        # Create a minimal problem instance
        problem = ExamSchedulingProblem(session_id=uuid4(), session_name="Test")

        # Add exam
        exam = Exam(
            id=uuid4(),
            course_id=uuid4(),
            course_code="TEST001",
            course_title="Test Course",
            expected_students=30,
            duration_minutes=180,
        )
        problem.exams[exam.id] = exam

        builder.problem = problem

        builder._create_decision_variables()

        assert len(builder.exam_start_vars) == 1
        assert len(builder.exam_end_vars) == 1
        assert len(builder.variables) >= 2  # At least start and end vars

    def test_calculate_time_horizon(self):
        """Test time horizon calculation"""
        builder = CPSATModelBuilder()

        # Test with exam period dates (but no time slots - should return 24 hours)
        problem = ExamSchedulingProblem(
            session_id=uuid4(),
            session_name="Test",
            exam_period_start=date(2024, 1, 15),
            exam_period_end=date(2024, 1, 20),
        )
        builder.problem = problem

        horizon = builder._calculate_time_horizon()

        # Without time slots, returns 24 hours * 60 minutes
        assert horizon == 6 * 24 * 60

        # Test without dates (still no time slots - should return 24 hours)
        problem.exam_period_start = None
        problem.exam_period_end = None
        horizon = builder._calculate_time_horizon()

        # Without time slots, returns 24 hours * 60 minutes
        assert horizon == 7 * 24 * 60

    def test_is_room_compatible(self):
        """Test room compatibility check"""
        builder = CPSATModelBuilder()

        # Create exam and room
        exam = Exam(
            id=uuid4(),
            course_id=uuid4(),
            course_code="TEST001",
            course_title="Test Course",
            expected_students=30,
            duration_minutes=180,
            is_practical=False,
        )

        room = Room(
            id=uuid4(),
            code="ROOM001",
            name="Test Room",
            capacity=50,
            exam_capacity=45,
            has_computers=False,
            is_active=True,
        )

        # Test compatible
        assert builder._is_room_compatible(exam, room) is True

        # Test incompatible capacity
        exam.expected_students = 60
        assert builder._is_room_compatible(exam, room) is False

        # Test incompatible practical exam
        exam.expected_students = 30
        exam.is_practical = True
        assert builder._is_room_compatible(exam, room) is False

        # Test inactive room
        exam.is_practical = False
        room.is_active = False
        assert builder._is_room_compatible(exam, room) is False

    def test_add_basic_constraints(self):
        """Test adding basic constraints"""
        builder = CPSATModelBuilder()
        builder.model = cp_model.CpModel()

        # Create a minimal problem instance
        problem = ExamSchedulingProblem(session_id=uuid4(), session_name="Test")

        # Add exam
        exam = Exam(
            id=uuid4(),
            course_id=uuid4(),
            course_code="TEST001",
            course_title="Test Course",
            expected_students=30,
            duration_minutes=180,
            release_time=datetime(2024, 1, 15, 9, 0),
        )
        problem.exams[exam.id] = exam

        builder.problem = problem

        # Create variables first
        builder._create_decision_variables()

        # Then add constraints
        builder._add_basic_constraints()

        # Should have added constraints without error

    def test_add_resource_constraints(self):
        """Test adding resource constraints"""
        builder = CPSATModelBuilder()
        builder.model = cp_model.CpModel()

        # Create a minimal problem instance
        problem = ExamSchedulingProblem(session_id=uuid4(), session_name="Test")

        # Add exam
        exam = Exam(
            id=uuid4(),
            course_id=uuid4(),
            course_code="TEST001",
            course_title="Test Course",
            expected_students=30,
            duration_minutes=180,
        )
        problem.exams[exam.id] = exam

        # Add room
        room = Room(
            id=uuid4(), code="ROOM001", name="Test Room", capacity=50, exam_capacity=45
        )
        problem.rooms[room.id] = room

        builder.problem = problem

        # Create variables first
        builder._create_decision_variables()

        # Then add constraints
        builder._add_resource_constraints()

        # Should have added constraints without error

    def test_add_precedence_constraints(self):
        """Test adding precedence constraints"""
        builder = CPSATModelBuilder()
        builder.model = cp_model.CpModel()

        # Create a minimal problem instance
        problem = ExamSchedulingProblem(session_id=uuid4(), session_name="Test")

        # Add exams with precedence
        exam1 = Exam(
            id=uuid4(),
            course_id=uuid4(),
            course_code="PREREQ",
            course_title="Prerequisite Course",
            expected_students=30,
            duration_minutes=180,
        )

        exam2 = Exam(
            id=uuid4(),
            course_id=uuid4(),
            course_code="ADVANCED",
            course_title="Advanced Course",
            expected_students=25,
            duration_minutes=120,
            prerequisite_exams={exam1.id},
        )

        problem.exams[exam1.id] = exam1
        problem.exams[exam2.id] = exam2

        builder.problem = problem

        # Create variables first
        builder._create_decision_variables()

        # Then add constraints
        builder._add_precedence_constraints()

        # Should have added constraints without error

    def test_add_objective_function(self):
        """Test adding objective function"""
        builder = CPSATModelBuilder()
        builder.model = cp_model.CpModel()

        # Create a minimal problem instance
        problem = ExamSchedulingProblem(session_id=uuid4(), session_name="Test")

        # Add exam with due date
        exam = Exam(
            id=uuid4(),
            course_id=uuid4(),
            course_code="TEST001",
            course_title="Test Course",
            expected_students=30,
            duration_minutes=180,
            due_date=datetime(2024, 1, 15, 12, 0),
            weight=1.5,
        )
        problem.exams[exam.id] = exam

        builder.problem = problem

        # Create variables first
        builder._create_decision_variables()

        # Then add objective
        builder._add_objective_function()

        # Should have added objective without error

    def test_add_solution_hint(self):
        """Test adding solution hint"""
        builder = CPSATModelBuilder()
        builder.model = cp_model.CpModel()

        # Create a minimal problem instance
        problem = ExamSchedulingProblem(session_id=uuid4(), session_name="Test")

        # Add exam
        exam_id = uuid4()
        exam = Exam(
            id=exam_id,
            course_id=uuid4(),
            course_code="TEST001",
            course_title="Test Course",
            expected_students=30,
            duration_minutes=180,
        )
        problem.exams[exam.id] = exam

        # Add room
        room_id = uuid4()
        room = Room(
            id=room_id, code="ROOM001", name="Test Room", capacity=50, exam_capacity=45
        )
        problem.rooms[room.id] = room

        # Add time slot
        time_slot_id = uuid4()
        time_slot = TimeSlot(
            id=time_slot_id,
            name="Morning Slot",
            start_time=time(9, 0),
            end_time=time(12, 0),
            duration_minutes=180,
        )
        problem.time_slots[time_slot.id] = time_slot

        builder.problem = problem

        # Create variables first
        builder._create_decision_variables()

        # Create hint solution
        hint_solution = TimetableSolution(problem=problem, solution_id=uuid4())
        assignment = ExamAssignment(exam_id=exam_id)
        assignment.time_slot_id = time_slot_id
        assignment.room_ids = [room_id]
        assignment.status = AssignmentStatus.ASSIGNED
        hint_solution.assignments[exam_id] = assignment

        # Add hint
        builder._add_solution_hint(hint_solution)

        # Should have added hints without error

    def test_get_model_statistics(self):
        """Test getting model statistics"""
        builder = CPSATModelBuilder()

        # Create a minimal problem instance
        problem = ExamSchedulingProblem(session_id=uuid4(), session_name="Test")

        # Add exam
        exam = Exam(
            id=uuid4(),
            course_id=uuid4(),
            course_code="TEST001",
            course_title="Test Course",
            expected_students=30,
            duration_minutes=180,
        )
        problem.exams[exam.id] = exam

        # Add room
        room = Room(
            id=uuid4(), code="ROOM001", name="Test Room", capacity=50, exam_capacity=45
        )
        problem.rooms[room.id] = room

        # Add time slot
        time_slot = TimeSlot(
            id=uuid4(),
            name="Morning Slot",
            start_time=time(9, 0),
            end_time=time(12, 0),
            duration_minutes=180,
        )
        problem.time_slots[time_slot.id] = time_slot

        builder.build_model(problem)

        stats = builder.get_model_statistics()

        assert "total_variables" in stats
        assert "exams" in stats
        assert "rooms" in stats
        assert "time_slots" in stats

    def test_validate_model(self):
        """Test model validation"""
        builder = CPSATModelBuilder()

        # Create a minimal problem instance
        problem = ExamSchedulingProblem(session_id=uuid4(), session_name="Test")

        # Add exam
        exam = Exam(
            id=uuid4(),
            course_id=uuid4(),
            course_code="TEST001",
            course_title="Test Course",
            expected_students=30,
            duration_minutes=180,
        )
        problem.exams[exam.id] = exam

        # Add room
        room = Room(
            id=uuid4(), code="ROOM001", name="Test Room", capacity=50, exam_capacity=45
        )
        problem.rooms[room.id] = room

        builder.build_model(problem)

        validation = builder.validate_model()

        assert "errors" in validation
        assert "warnings" in validation

    def test_get_variables(self):
        """Test getting variables"""
        builder = CPSATModelBuilder()

        # Create a minimal problem instance
        problem = ExamSchedulingProblem(session_id=uuid4(), session_name="Test")

        # Add exam
        exam = Exam(
            id=uuid4(),
            course_id=uuid4(),
            course_code="TEST001",
            course_title="Test Course",
            expected_students=30,
            duration_minutes=180,
        )
        problem.exams[exam.id] = exam

        builder.build_model(problem)

        variables = builder.get_variables()

        assert isinstance(variables, dict)
        assert len(variables) > 0


if __name__ == "__main__":
    pytest.main([__file__])
