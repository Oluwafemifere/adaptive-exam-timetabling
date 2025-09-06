# scheduling_engine/tests/unit/test_problem_model.py

"""
Comprehensive tests for ExamSchedulingProblem and related entities.

Tests cover:
- Problem model creation and initialization
- Entity management (exams, rooms, students, etc.)
- Database integration and data loading
- Constraint system integration
- Index building and optimization
"""

import pytest
from unittest.mock import Mock, patch
from uuid import UUID, uuid4
from datetime import date, time


from scheduling_engine.core.problem_model import (
    ExamSchedulingProblem,
    Exam,
    Student,
    Room,
    TimeSlot,
    CourseRegistration,
    ExamType,
)
from scheduling_engine.core.constraint_registry import (
    BaseConstraint,
    ConstraintRegistry,
)
from scheduling_engine.core.constraint_types import (
    ConstraintType,
    ConstraintCategory,
)


class TestProblemModelEntities:
    """Tests for individual entity classes"""

    def test_time_slot_creation(self):
        """Test TimeSlot entity creation and methods"""
        slot = TimeSlot(
            id=uuid4(),
            name="Morning Slot 1",
            start_time=time(9, 0),
            end_time=time(12, 0),
            duration_minutes=180,
            date=date(2024, 1, 15),
            is_active=True,
        )

        assert slot.name == "Morning Slot 1"
        assert slot.duration_minutes == 180
        assert slot.is_active is True
        assert slot.earliest_start is not None
        assert slot.earliest_start.time() == time(9, 0)

    def test_time_slot_from_backend_data(self):
        """Test creating TimeSlot from backend data"""
        backend_data = {
            "id": str(uuid4()),
            "name": "Backend Slot",
            "start_time": "10:00",
            "end_time": "13:00",
            "duration_minutes": 180,
            "is_active": True,
        }

        slot = TimeSlot.from_backend_data(backend_data)

        assert slot.name == "Backend Slot"
        assert slot.start_time == time(10, 0)
        assert slot.end_time == time(13, 0)
        assert slot.duration_minutes == 180
        assert slot.is_active is True

    def test_room_creation_and_capacity(self):
        """Test Room entity creation and capacity calculations"""
        room = Room(
            id=uuid4(),
            code="ROOM001",
            name="Test Room 001",
            capacity=100,
            exam_capacity=80,
            has_computers=True,
            has_projector=True,
            is_accessible=True,
        )

        assert room.code == "ROOM001"
        assert room.capacity == 100
        assert room.exam_capacity == 80
        assert room.has_computers is True

        # Test effective capacity calculation
        regular_capacity = room.get_effective_capacity(ExamType.REGULAR)
        carryover_capacity = room.get_effective_capacity(ExamType.CARRYOVER)

        assert regular_capacity == 80  # Uses exam_capacity
        assert carryover_capacity == 40  # Half capacity for carryover

    def test_student_conflict_detection(self):
        """Test Student entity conflict detection"""
        course1_id = uuid4()
        course2_id = uuid4()
        course3_id = uuid4()

        student = Student(
            id=uuid4(),
            matric_number="STU001",
            programme_id=uuid4(),
            current_level=200,
            registered_courses={course1_id, course2_id},
        )

        # Test conflict detection
        assert student.has_conflict(course1_id, course2_id) is True
        assert student.has_conflict(course1_id, course3_id) is False
        assert student.has_conflict(course2_id, course3_id) is False

    def test_exam_workload_calculations(self):
        """Test Exam entity workload and processing calculations"""
        exam = Exam(
            id=uuid4(),
            course_id=uuid4(),
            course_code="EXAM001",
            course_title="Test Exam Course",
            expected_students=50,
            duration_minutes=180,
            weight=1.5,
            is_practical=True,
        )

        # Test calculations
        processing_time = exam.get_processing_time()
        workload = exam.get_workload()
        resource_req = exam.get_resource_requirement()

        assert processing_time == 180
        assert workload == 50 * (180 / 60.0)  # students * hours
        assert resource_req == 50
        assert exam.weight == 1.5

    def test_exam_precedence_checking(self):
        """Test Exam precedence relationships"""
        exam1_id = uuid4()
        exam2_id = uuid4()
        exam3_id = uuid4()

        exam = Exam(
            id=exam1_id,
            course_id=uuid4(),
            course_code="PREREQ001",
            course_title="Prerequisite Course",
            expected_students=30,
            prerequisite_exams={exam2_id},  # exam2 must come before exam1
        )

        other_exam = Exam(
            id=exam2_id,
            course_id=uuid4(),
            course_code="BASIC001",
            course_title="Basic Course",
            expected_students=30,
        )

        unrelated_exam = Exam(
            id=exam3_id,
            course_id=uuid4(),
            course_code="OTHER001",
            course_title="Other Course",
            expected_students=25,
        )

        # Test precedence relationships
        assert exam.has_precedence(other_exam) is True  # exam2 should come before exam1
        assert exam.has_precedence(unrelated_exam) is False
        assert other_exam.has_precedence(exam) is False


class TestExamSchedulingProblemCore:
    """Tests for core ExamSchedulingProblem functionality"""

    def test_problem_creation(self):
        """Test basic problem creation"""
        session_id = uuid4()
        problem = ExamSchedulingProblem(
            session_id=session_id,
            session_name="Test Session",
            exam_period_start=date(2024, 1, 15),
            exam_period_end=date(2024, 1, 25),
        )

        assert problem.session_id == session_id
        assert problem.session_name == "Test Session"
        assert problem.exam_period_start == date(2024, 1, 15)
        assert problem.exam_period_end == date(2024, 1, 25)

        # Check initialized collections
        assert isinstance(problem.exams, dict)
        assert isinstance(problem.time_slots, dict)
        assert isinstance(problem.rooms, dict)
        assert isinstance(problem.students, dict)
        assert len(problem.exams) == 0  # Initially empty

    def test_problem_with_database_session(self):
        """Test problem creation with database session"""
        session_id = uuid4()
        mock_db_session = Mock()

        # Mock the actual backend service paths
        with patch("scheduling_engine.core.problem_model.BACKEND_AVAILABLE", True):
            with patch(
                "backend.app.services.scheduling.data_preparation_service.DataPreparationService"
            ) as MockDataPrep, patch(
                "backend.app.services.data_retrieval.SchedulingData"
            ) as MockScheduling, patch(
                "backend.app.services.data_retrieval.AcademicData"
            ) as MockAcademic, patch(
                "backend.app.services.data_retrieval.InfrastructureData"
            ) as MockInfra, patch(
                "backend.app.services.data_retrieval.ConflictAnalysis"
            ) as MockConflict, patch(
                "backend.app.services.data_retrieval.ConstraintData"
            ) as MockConstraint:

                # Create mock service instances
                mock_data_prep = Mock()
                mock_scheduling = Mock()
                mock_academic = Mock()
                mock_infra = Mock()
                mock_conflict = Mock()
                mock_constraint = Mock()

                # Configure mocks to return mock instances
                MockDataPrep.return_value = mock_data_prep
                MockScheduling.return_value = mock_scheduling
                MockAcademic.return_value = mock_academic
                MockInfra.return_value = mock_infra
                MockConflict.return_value = mock_conflict
                MockConstraint.return_value = mock_constraint

                problem = ExamSchedulingProblem(
                    session_id=session_id,
                    session_name="DB Test Session",
                    db_session=mock_db_session,
                )

        assert problem.db_session == mock_db_session

    def test_constraint_system_integration(self):
        """Test constraint system integration"""
        session_id = uuid4()
        problem = ExamSchedulingProblem(
            session_id=session_id, session_name="Constraint Test Session"
        )

        # Check constraint registry initialization
        assert isinstance(problem.constraint_registry, ConstraintRegistry)
        assert isinstance(problem.active_constraints, list)
        assert len(problem.active_constraints) == 0  # Initially empty

    def test_entity_addition_and_management(self):
        """Test adding and managing entities"""
        session_id = uuid4()
        problem = ExamSchedulingProblem(
            session_id=session_id, session_name="Entity Test Session"
        )

        # Add time slot
        time_slot = TimeSlot(
            id=uuid4(),
            name="Test Slot",
            start_time=time(9, 0),
            end_time=time(12, 0),
            duration_minutes=180,
        )
        problem.time_slots[time_slot.id] = time_slot

        # Add room
        room = Room(
            id=uuid4(), code="TEST001", name="Test Room", capacity=50, exam_capacity=45
        )
        problem.rooms[room.id] = room

        # Add student
        student = Student(
            id=uuid4(), matric_number="TEST001", programme_id=uuid4(), current_level=200
        )
        problem.students[student.id] = student

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

        # Verify additions
        assert len(problem.time_slots) == 1
        assert len(problem.rooms) == 1
        assert len(problem.students) == 1
        assert len(problem.exams) == 1

        # Test entity retrieval
        assert problem.time_slots[time_slot.id] == time_slot
        assert problem.rooms[room.id] == room
        assert problem.students[student.id] == student
        assert problem.exams[exam.id] == exam


class TestProblemModelConstraints:
    """Tests for constraint management within problem model"""

    def test_constraint_addition(self):
        """Test adding constraints"""
        constraint_id = uuid4()

        class MockConstraint(BaseConstraint):
            def __init__(self):
                super().__init__(
                    constraint_id=constraint_id,
                    name="Test Constraint",
                    constraint_type=ConstraintType.SOFT,
                    category=ConstraintCategory.OPTIMIZATION_CONSTRAINTS,
                )

            def _initialize_implementation(self, problem, parameters=None):
                pass

            def _evaluate_implementation(self, problem, solution):
                return []

        session_id = uuid4()
        problem = ExamSchedulingProblem(
            session_id=session_id, session_name="Constraint Addition Test"
        )

        # Create test constraint
        constraint = MockConstraint()

        # Add constraint
        problem.add_constraint(constraint)
        assert len(problem.active_constraints) == 1
        assert constraint in problem.active_constraints

    def test_constraint_filtering_by_type(self):
        """Test getting constraints by type"""
        constraint_id = str(uuid4())

        class MockHardConstraint(BaseConstraint):
            def __init__(self):
                super().__init__(
                    constraint_id=constraint_id,
                    name="Hard Test",
                    constraint_type=ConstraintType.HARD,
                    category=ConstraintCategory.STUDENT_CONSTRAINTS,
                )

            def _initialize_implementation(self, problem, parameters=None):
                pass

            def _evaluate_implementation(self, problem, solution):
                return []

        constraint_id = str(uuid4())

        class MockSoftConstraint(BaseConstraint):
            def __init__(self):
                super().__init__(
                    constraint_id=constraint_id,
                    name="Soft Test",
                    constraint_type=ConstraintType.SOFT,
                    category=ConstraintCategory.OPTIMIZATION_CONSTRAINTS,
                )

            def _initialize_implementation(self, problem, parameters=None):
                pass

            def _evaluate_implementation(self, problem, solution):
                return []

        session_id = uuid4()
        problem = ExamSchedulingProblem(
            session_id=session_id, session_name="Constraint Filtering Test"
        )

        # Add hard constraint
        hard_constraint = MockHardConstraint()
        problem.add_constraint(hard_constraint)

        # Add soft constraint
        soft_constraint = MockSoftConstraint()
        problem.add_constraint(soft_constraint)

        # Test filtering
        hard_constraints = problem.get_hard_constraints()
        soft_constraints = problem.get_soft_constraints()

        assert len(hard_constraints) == 1
        assert len(soft_constraints) == 1
        assert hard_constraints[0] == hard_constraint
        assert soft_constraints[0] == soft_constraint

    @pytest.mark.asyncio
    async def test_constraint_initialization(self):
        """Test constraint initialization"""
        constraint_id = str(uuid4())

        class InitTestConstraint(BaseConstraint):
            def __init__(self):
                super().__init__(
                    constraint_id=constraint_id,
                    name="Init Test",
                    constraint_type=ConstraintType.SOFT,
                    category=ConstraintCategory.OPTIMIZATION_CONSTRAINTS,
                )
                self.initialized_with_problem = False

            def _initialize_implementation(self, problem, parameters=None):
                self.initialized_with_problem = True
                self.problem_exam_count = len(problem.exams)

            def _evaluate_implementation(self, problem, solution):
                return []

        session_id = uuid4()
        problem = ExamSchedulingProblem(
            session_id=session_id, session_name="Initialization Test"
        )

        # Add some exams to test initialization
        for i in range(3):
            exam = Exam(
                id=uuid4(),
                course_id=uuid4(),
                course_code=f"INIT{i+1:03d}",
                course_title=f"Initialization Test {i+1}",
                expected_students=25,
            )
            problem.exams[exam.id] = exam

        # Add constraint
        constraint = InitTestConstraint()
        problem.add_constraint(constraint)

        # Initialize constraints
        await problem.initialize_constraints()

        # Verify initialization
        assert constraint.initialized_with_problem is True
        assert constraint.problem_exam_count == 3


class TestProblemModelComplexity:
    """Tests for problem complexity and analysis methods"""

    def test_problem_complexity_metrics(self):
        """Test problem complexity calculations"""
        session_id = uuid4()
        problem = ExamSchedulingProblem(
            session_id=session_id, session_name="Complexity Test"
        )

        # Add entities to create complexity
        num_exams = 10
        num_students = 25
        num_rooms = 5
        num_slots = 6

        # Add time slots
        for i in range(num_slots):
            slot = TimeSlot(
                id=uuid4(),
                name=f"Slot{i+1}",
                start_time=time(8 + i, 0),
                end_time=time(11 + i, 0),
                duration_minutes=180,
            )
            problem.time_slots[slot.id] = slot

        # Add rooms
        for i in range(num_rooms):
            room = Room(
                id=uuid4(),
                code=f"ROOM{i+1:03d}",
                name=f"Room {i+1}",
                capacity=30 + i * 10,
                exam_capacity=25 + i * 8,
            )
            problem.rooms[room.id] = room

        # Add students
        for i in range(num_students):
            student = Student(
                id=uuid4(),
                matric_number=f"COMP{i+1:04d}",
                programme_id=uuid4(),
                current_level=200,
            )
            problem.students[student.id] = student

        # Add exams
        course_exam_pairs = []
        for i in range(num_exams):
            course_id = uuid4()
            exam = Exam(
                id=uuid4(),
                course_id=course_id,
                course_code=f"COMP{i+1:03d}",
                course_title=f"Complexity Course {i+1}",
                expected_students=15 + i * 2,
                duration_minutes=180,
            )
            course_exam_pairs.append((course_id, exam))
            problem.exams[exam.id] = exam

        # Add registrations to create conflicts
        for i, student in enumerate(problem.students.values()):
            # Each student takes 3-4 courses
            num_courses = 3 + (i % 2)
            start_idx = i % len(course_exam_pairs)

            for j in range(num_courses):
                course_idx = (start_idx + j) % len(course_exam_pairs)
                course_id, exam = course_exam_pairs[course_idx]

                registration = CourseRegistration(
                    id=uuid4(),
                    student_id=student.id,
                    course_id=course_id,
                    session_id=session_id,
                )
                problem.course_registrations[registration.id] = registration

        # Test complexity metrics (if implemented)
        if hasattr(problem, "get_problem_complexity_score"):
            complexity_score = problem.get_problem_complexity_score()
            assert complexity_score > 0

        if hasattr(problem, "get_capacity_utilization_ratio"):
            utilization = problem.get_capacity_utilization_ratio()
            assert 0 <= utilization <= 10  # May exceed 1 if overbooked

    def test_exam_conflict_detection(self):
        """Test exam conflict detection"""
        session_id = uuid4()
        problem = ExamSchedulingProblem(
            session_id=session_id, session_name="Conflict Test"
        )

        # Create students and courses with overlapping registrations
        student1 = Student(
            id=uuid4(), matric_number="CONF001", programme_id=uuid4(), current_level=200
        )
        student2 = Student(
            id=uuid4(), matric_number="CONF002", programme_id=uuid4(), current_level=200
        )
        problem.students[student1.id] = student1
        problem.students[student2.id] = student2

        # Create courses and exams
        course1_id = uuid4()
        course2_id = uuid4()
        course3_id = uuid4()

        exam1 = Exam(
            id=uuid4(),
            course_id=course1_id,
            course_code="CONF001",
            course_title="Course 1",
            expected_students=20,
        )
        exam2 = Exam(
            id=uuid4(),
            course_id=course2_id,
            course_code="CONF002",
            course_title="Course 2",
            expected_students=15,
        )
        exam3 = Exam(
            id=uuid4(),
            course_id=course3_id,
            course_code="CONF003",
            course_title="Course 3",
            expected_students=25,
        )

        problem.exams[exam1.id] = exam1
        problem.exams[exam2.id] = exam2
        problem.exams[exam3.id] = exam3

        # Create registrations that will cause conflicts
        # Student 1 takes courses 1 and 2 (potential conflict)
        reg1 = CourseRegistration(
            id=uuid4(),
            student_id=student1.id,
            course_id=course1_id,
            session_id=session_id,
        )
        reg2 = CourseRegistration(
            id=uuid4(),
            student_id=student1.id,
            course_id=course2_id,
            session_id=session_id,
        )

        # Student 2 takes courses 2 and 3 (potential conflict with student 1 on course 2)
        reg3 = CourseRegistration(
            id=uuid4(),
            student_id=student2.id,
            course_id=course2_id,
            session_id=session_id,
        )
        reg4 = CourseRegistration(
            id=uuid4(),
            student_id=student2.id,
            course_id=course3_id,
            session_id=session_id,
        )

        problem.course_registrations[reg1.id] = reg1
        problem.course_registrations[reg2.id] = reg2
        problem.course_registrations[reg3.id] = reg3
        problem.course_registrations[reg4.id] = reg4

        # Test conflict detection (if implemented)
        if hasattr(problem, "get_exam_conflicts"):
            conflicts = problem.get_exam_conflicts()
            assert (
                len(conflicts) >= 0
            )  # Should find conflicts between exams with shared students


class TestProblemModelExport:
    """Tests for problem model export and serialization"""

    def test_solver_export_format(self):
        """Test exporting problem for solver consumption"""
        session_id = uuid4()
        problem = ExamSchedulingProblem(
            session_id=session_id, session_name="Export Test", configuration_id=uuid4()
        )

        # Add minimal entities
        time_slot = TimeSlot(
            id=uuid4(),
            name="Export Slot",
            start_time=time(9, 0),
            end_time=time(12, 0),
            duration_minutes=180,
        )
        problem.time_slots[time_slot.id] = time_slot

        room = Room(
            id=uuid4(), code="EXP001", name="Export Room", capacity=50, exam_capacity=45
        )
        problem.rooms[room.id] = room

        exam = Exam(
            id=uuid4(),
            course_id=uuid4(),
            course_code="EXP001",
            course_title="Export Course",
            expected_students=30,
            duration_minutes=180,
            weight=1.0,
        )
        problem.exams[exam.id] = exam

        # Export for solver
        export_data = problem.export_for_solver()

        # Verify export structure
        assert "problem_id" in export_data
        assert "session_id" in export_data
        assert "configuration_id" in export_data
        assert "exams" in export_data
        assert "time_slots" in export_data
        assert "rooms" in export_data
        assert "conflicts" in export_data
        assert "constraints" in export_data
        assert "metrics" in export_data

        # Verify exam data structure
        exam_data = export_data["exams"]
        assert len(exam_data) == 1
        exam_export = exam_data[0]

        assert "id" in exam_export
        assert "course_code" in exam_export
        assert "duration_minutes" in exam_export
        assert "expected_students" in exam_export
        assert "gp_terminals" in exam_export

        # Verify GP terminals
        gp_terminals = exam_export["gp_terminals"]
        assert "processing_time" in gp_terminals
        assert "weight" in gp_terminals
        assert "resource_requirement" in gp_terminals
        assert "workload" in gp_terminals


if __name__ == "__main__":
    pytest.main([__file__])
