# tests/integration/test_constraints_integration.py
import logging
import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4, UUID
from datetime import datetime, date, time
from typing import Dict, List, Any, Optional
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import db_manager, init_db
from backend.app.core.config import settings
from scheduling_engine.constraints import ConstraintFactory
from scheduling_engine.constraints.constraint_manager import ConstraintManager
from scheduling_engine.core import (
    ExamSchedulingProblem,
    TimetableSolution,
    ExamAssignment,
    SolutionStatus,
)
from scheduling_engine.constraints.hard_constraints import (
    NoStudentConflictConstraint,
    RoomCapacityConstraint,
    TimeAvailabilityConstraint,
    CarryoverPriorityConstraint,
)
from scheduling_engine.constraints.soft_constraints import (
    ExamDistributionConstraint,
    RoomUtilizationConstraint,
    InvigilatorBalanceConstraint,
    StudentTravelConstraint,
)
from backend.app.models.scheduling import Exam, TimeSlot, Staff, StaffUnavailability
from backend.app.models.infrastructure import Room
from backend.app.models.scheduling import StaffUnavailability
from scheduling_engine.core.problem_model import (
    ExamSchedulingProblem,
    Exam,
    Room,
    TimeSlot,
    Student,
    Staff,
    CourseRegistration,
    ExamType,
)

logger = logging.getLogger(__name__)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def init_test_database():
    """Initialize and create schema/tables for each test."""
    try:
        # Initialize database
        await init_db(database_url=settings.DATABASE_URL, create_tables=True)
        yield
    finally:
        # Clean up after test
        try:
            await db_manager.drop_all_tables("exam_system")
        except Exception as e:
            print(f"Warning during cleanup: {e}")
        await db_manager.close()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_session():
    """Create a test database session"""
    async with db_manager.get_session() as session:
        yield session


@pytest_asyncio.fixture
async def sample_problem_data():
    """Create sample problem data for testing constraints"""
    # This would typically come from the database
    return {
        "exams": {
            UUID("12345678-1234-5678-1234-567812345678"): {
                "id": UUID("12345678-1234-5678-1234-567812345678"),
                "course_id": UUID("22345678-1234-5678-1234-567812345678"),
                "expected_students": 50,
                "duration_minutes": 120,
                "is_practical": False,
                "requires_projector": True,
                "requires_special_arrangements": False,
                "departments": [UUID("32345678-1234-5678-1234-567812345678")],
            },
            UUID("12345678-1234-5678-1234-567812345679"): {
                "id": UUID("12345678-1234-5678-1234-567812345679"),
                "course_id": UUID("22345678-1234-5678-1234-567812345679"),
                "expected_students": 30,
                "duration_minutes": 90,
                "is_practical": True,
                "requires_projector": False,
                "requires_special_arrangements": True,
                "departments": [UUID("32345678-1234-5678-1234-567812345678")],
            },
        },
        "rooms": {
            UUID("42345678-1234-5678-1234-567812345678"): {
                "id": UUID("42345678-1234-5678-1234-567812345678"),
                "code": "LHA",
                "name": "Lecture Hall A",
                "capacity": 100,
                "exam_capacity": 80,
                "has_computers": False,
                "has_projector": True,
                "is_accessible": True,
                "availability_restrictions": {
                    "unavailable_days": ["Saturday", "Sunday"],
                    "unavailable_times": ["18:00-20:00"],
                },
            },
            UUID("42345678-1234-5678-1234-567812345679"): {
                "id": UUID("42345678-1234-5678-1234-567812345679"),
                "name": "Computer Lab B",
                "code": "COM",
                "capacity": 40,
                "exam_capacity": 35,
                "has_computers": True,
                "has_projector": False,
                "is_accessible": True,
                "availability_restrictions": {},
            },
        },
        "time_slots": {
            UUID("52345678-1234-5678-1234-567812345678"): {
                "id": UUID("52345678-1234-5678-1234-567812345678"),
                "name": "Morning Slot",
                "duration_minutes": 120,
                "date": date(2024, 6, 15),
                "start_time": time(9, 0),
                "end_time": time(11, 0),
                "is_active": True,
            },
            UUID("52345678-1234-5678-1234-567812345679"): {
                "id": UUID("52345678-1234-5678-1234-567812345679"),
                "name": "Afternoon Slot",
                "duration_minutes": 120,
                "date": date(2024, 6, 15),
                "start_time": time(14, 0),
                "end_time": time(16, 0),
                "is_active": True,
            },
        },
        "students": {
            UUID("62345678-1234-5678-1234-567812345678"): {
                "id": UUID("62345678-1234-5678-1234-567812345678"),
                "matric_number": "STU001",
                "name": "Student One",
                "is_carryover": False,
                "has_failed_exams": False,
            },
            UUID("62345678-1234-5678-1234-567812345679"): {
                "id": UUID("62345678-1234-5678-1234-567812345679"),
                "matric_number": "STU002",
                "name": "Student Two",
                "is_carryover": True,
                "has_failed_exams": True,
            },
        },
        "course_registrations": [
            {
                "student_id": UUID("62345678-1234-5678-1234-567812345678"),
                "course_id": UUID("22345678-1234-5678-1234-567812345678"),
                "registration_type": "regular",
            },
            {
                "student_id": UUID("62345678-1234-5678-1234-567812345679"),
                "course_id": UUID("22345678-1234-5678-1234-567812345678"),
                "registration_type": "carryover",
            },
            {
                "student_id": UUID("62345678-1234-5678-1234-567812345678"),
                "course_id": UUID("22345678-1234-5678-1234-567812345679"),
                "registration_type": "regular",
            },
        ],
        "staff": {
            UUID("72345678-1234-5678-1234-567812345678"): {
                "id": UUID("72345678-1234-5678-1234-567812345678"),
                "staff_number": "STAFF001",  # Added missing staff number
                "staff_type": "academic",  # Added missing staff type
                "position": "Professor",  # Added missing position
                "name": "Professor One",
                "can_invigilate": True,
                "max_daily_sessions": 2,
                "max_weekly_sessions": 8,
                "max_consecutive_sessions": 4,
                "department_id": UUID("32345678-1234-5678-1234-567812345678"),
            }
        },
        "staff_unavailability": [
            {
                "staff_id": UUID("72345678-1234-5678-1234-567812345678"),
                "time_slot_id": UUID("52345678-1234-5678-1234-567812345679"),
                "reason": "Department meeting",
            }
        ],
    }


@pytest_asyncio.fixture
async def sample_problem(sample_problem_data):
    """Create a sample ExamSchedulingProblem for testing"""
    problem = ExamSchedulingProblem(
        session_id=UUID("12345678-1234-5678-1234-567812345670"),
        session_name="Test Session",
    )

    # Add exams using core problem model
    for exam_id, exam_data in sample_problem_data["exams"].items():
        exam = Exam(
            id=exam_id,
            course_id=exam_data["course_id"],
            course_code=exam_data.get("course_code", "TEST101"),
            course_title=exam_data.get("course_title", "Test Course"),
            duration_minutes=exam_data["duration_minutes"],
            expected_students=exam_data["expected_students"],
            is_practical=exam_data["is_practical"],
            requires_special_arrangements=exam_data["requires_special_arrangements"],
            exam_type=ExamType.REGULAR,
        )
        problem.add_exam(exam)

    # Add rooms using core problem model
    for room_id, room_data in sample_problem_data["rooms"].items():
        room = Room(
            id=room_id,
            code=room_data["code"],
            name=room_data["name"],
            capacity=room_data["capacity"],
            exam_capacity=room_data["exam_capacity"],
            has_computers=room_data["has_computers"],
            has_projector=room_data["has_projector"],
            is_accessible=room_data["is_accessible"],
        )
        problem.add_room(room)

    # Add time slots using core problem model
    for ts_id, ts_data in sample_problem_data["time_slots"].items():
        time_slot = TimeSlot(
            id=ts_id,
            name=ts_data["name"],
            start_time=ts_data["start_time"],
            end_time=ts_data["end_time"],
            duration_minutes=ts_data["duration_minutes"],
            date=ts_data["date"],
        )
        problem.add_time_slot(time_slot)

    # Add students using core problem model
    for student_id, student_data in sample_problem_data["students"].items():
        student = Student(
            id=student_id,
            matric_number=student_data["matric_number"],
            programme_id=UUID(
                "82345678-1234-5678-1234-567812345678"
            ),  # dummy programme
            current_level=student_data.get("current_level", 100),
            special_needs=student_data.get("special_needs", False),
        )
        problem.add_student(student)

    # Add course registrations using core problem model
    for reg in sample_problem_data["course_registrations"]:
        registration = CourseRegistration(
            id=uuid4(),
            student_id=reg["student_id"],
            course_id=reg["course_id"],
            session_id=problem.session_id,
            registration_type=reg["registration_type"],
        )
        problem.add_student_registration(registration)

    # Add staff using core problem model
    for staff_id, staff_data in sample_problem_data["staff"].items():
        staff = Staff(
            id=staff_id,
            staff_number=staff_data["staff_number"],
            staff_type=staff_data["staff_type"],
            position=staff_data["position"],
            department_id=staff_data["department_id"],
            can_invigilate=staff_data["can_invigilate"],
            max_daily_sessions=staff_data["max_daily_sessions"],
            max_consecutive_sessions=staff_data["max_consecutive_sessions"],
        )
        problem.add_staff(staff)

    # Add staff unavailability
    # for su in sample_problem_data["staff_unavailability"]:
    #     unavailability = StaffUnavailability(
    #         id=uuid4(),
    #         staff_id=su["staff_id"],
    #         time_slot_id=su["time_slot_id"],
    #         reason=su.get("reason"),
    #         created_at=datetime.utcnow(),
    #         updated_at=datetime.utcnow(),
    #     )
    #     problem.add_staff_unavailability(unavailability)

    return problem


@pytest_asyncio.fixture
async def sample_solution(sample_problem):
    """Create a sample solution for testing"""
    # Create solution using the correct constructor
    solution = TimetableSolution(
        problem=sample_problem, solution_id=UUID("82345678-1234-5678-1234-567812345678")
    )

    # Now assign exams using the assign_exam method
    # Assign first exam to first time slot and room
    success1 = solution.assign_exam(
        exam_id=UUID("12345678-1234-5678-1234-567812345678"),
        time_slot_id=UUID("52345678-1234-5678-1234-567812345678"),
        room_ids=[UUID("42345678-1234-5678-1234-567812345678")],
        assigned_date=date(2024, 6, 15),
        room_allocations={UUID("42345678-1234-5678-1234-567812345678"): 50},
    )

    # Assign second exam to second time slot and room
    success2 = solution.assign_exam(
        exam_id=UUID("12345678-1234-5678-1234-567812345679"),
        time_slot_id=UUID("52345678-1234-5678-1234-567812345679"),
        room_ids=[UUID("42345678-1234-5678-1234-567812345679")],
        assigned_date=date(2024, 6, 15),
        room_allocations={UUID("42345678-1234-5678-1234-567812345679"): 30},
    )

    # Update solution status if assignments were successful
    if success1 and success2:
        solution.status = SolutionStatus.FEASIBLE
        solution.objective_value = 0.0
        solution.calculate_fitness_score()
        solution.update_statistics()

    return solution


@pytest_asyncio.fixture
async def constraint_manager(test_session):
    """Create a constraint manager instance"""
    return ConstraintManager(db_session=test_session)


@pytest_asyncio.fixture
async def constraint_factory(test_session):
    """Create a constraint factory instance"""
    return ConstraintFactory(db_session=test_session)


@pytest.mark.integration
class TestConstraintsIntegration:
    """Integration tests for constraint system with real database"""

    @pytest.mark.asyncio
    async def test_constraint_manager_initialization(self, constraint_manager):
        """Test that constraint manager can be initialized"""
        assert constraint_manager is not None
        assert constraint_manager.db_session is not None

        # Test loading default configuration
        summary = await constraint_manager.load_configuration()
        assert summary is not None
        assert summary.total_constraints > 0
        assert summary.hard_constraints > 0
        assert summary.soft_constraints > 0

    @pytest.mark.asyncio
    async def test_constraint_factory_creation(self, constraint_factory):
        """Test that constraint factory can create constraints"""
        # Test creating individual constraints
        constraint = (
            await constraint_factory.create_constraint_instance(  # CHANGED METHOD NAME
                "NO_STUDENT_CONFLICT"
            )
        )
        logger.info(f"Created constraint: {constraint}")
        assert constraint is not None
        assert constraint.constraint_id == "NO_STUDENT_CONFLICT"
        assert constraint.constraint_type.value == "hard"

    @pytest.mark.asyncio
    async def test_constraint_evaluation(
        self, constraint_manager, sample_problem, sample_solution
    ):
        """Test constraint evaluation with sample data"""
        # Load default constraints
        await constraint_manager.load_configuration()

        # Evaluate constraints
        results = constraint_manager.evaluate_all_constraints(
            sample_problem, sample_solution
        )

        # Check results structure
        assert "total_violations" in results
        assert "total_penalty" in results
        assert "constraint_results" in results
        assert "hard_constraint_violations" in results
        assert "soft_constraint_violations" in results
        assert "evaluation_time" in results

        # The sample solution should be feasible (no hard constraint violations)
        assert results["is_feasible"] is True
        assert results["hard_constraint_violations"] == 0

    @pytest.mark.asyncio
    async def test_no_student_conflict_constraint(
        self, sample_problem, sample_solution
    ):
        """Test specific constraint: No Student Conflict"""
        constraint = NoStudentConflictConstraint()

        # Initialize with problem data
        constraint.initialize(sample_problem)

        # Evaluate with solution
        violations = constraint.evaluate(sample_problem, sample_solution)

        # Should not have violations with this solution
        assert len(violations) == 0

        # Test with a problematic solution (same student, same timeslot)
        # Create a copy of the solution
        bad_solution = sample_solution.copy()

        # Modify the second exam to use the same time slot as the first
        bad_solution.assign_exam(
            exam_id=UUID("12345678-1234-5678-1234-567812345679"),
            time_slot_id=UUID(
                "52345678-1234-5678-1234-567812345678"
            ),  # Same as first exam
            room_ids=[UUID("42345678-1234-5678-1234-567812345679")],
            assigned_date=date(2024, 6, 15),
            room_allocations={UUID("42345678-1234-5678-1234-567812345679"): 30},
        )

        violations = constraint.evaluate(sample_problem, bad_solution)
        assert len(violations) > 0  # Should detect conflict

    @pytest.mark.asyncio
    async def test_room_capacity_constraint(self, sample_problem, sample_solution):
        """Test specific constraint: Room Capacity"""
        constraint = RoomCapacityConstraint()

        # Initialize with problem data
        constraint.initialize(sample_problem)

        # Evaluate with solution
        violations = constraint.evaluate(sample_problem, sample_solution)

        # Should not have violations with this solution
        assert len(violations) == 0

        # Test with a problematic solution (over capacity)
        bad_solution = sample_solution.copy()

        # Assign more students than room capacity
        bad_solution.assign_exam(
            exam_id=UUID("12345678-1234-5678-1234-567812345678"),
            time_slot_id=UUID("52345678-1234-5678-1234-567812345678"),
            room_ids=[UUID("42345678-1234-5678-1234-567812345678")],
            assigned_date=date(2024, 6, 15),
            room_allocations={
                UUID("42345678-1234-5678-1234-567812345678"): 150
            },  # Exceeds capacity
        )

        violations = constraint.evaluate(sample_problem, bad_solution)
        assert len(violations) > 0  # Should detect capacity violation

    @pytest.mark.asyncio
    async def test_constraint_parameter_validation(self, constraint_manager):
        """Test constraint parameter validation"""
        await constraint_manager.load_configuration()

        logger.info(
            f"Active constraints: {[c.constraint_id for c in constraint_manager.active_constraints]}"
        )

        # Test valid parameter update
        success = constraint_manager.update_constraint_parameters(
            "ROOM_CAPACITY", {"capacity_buffer_percent": 10.0}
        )
        logger.info(f"Parameter update result: {success}")
        assert success is True

        # Test invalid parameter update
        success = constraint_manager.update_constraint_parameters(
            "ROOM_CAPACITY", {"capacity_buffer_percent": -5.0}
        )
        logger.info(f"Invalid parameter update result: {success}")
        assert success is False  # Should fail validation

    @pytest.mark.asyncio
    async def test_constraint_performance_statistics(self, constraint_manager):
        """Test constraint performance tracking"""
        await constraint_manager.load_configuration()

        stats = constraint_manager.get_performance_statistics()
        assert "total_evaluations" in stats
        assert "total_evaluation_time" in stats
        assert "average_evaluation_time" in stats
        assert "active_constraints" in stats

    @pytest.mark.asyncio
    async def test_constraint_configuration_export(self, constraint_manager):
        """Test exporting constraint configuration"""
        await constraint_manager.load_configuration()

        config = constraint_manager.export_configuration()
        assert "configuration_id" in config
        assert "metadata" in config
        assert "constraints" in config
        assert "summary" in config
        assert "performance_stats" in config

        # Should have the expected constraints
        constraint_codes = [c["constraint_id"] for c in config["constraints"]]
        assert "NO_STUDENT_CONFLICT" in constraint_codes
        assert "ROOM_CAPACITY" in constraint_codes
        assert "EXAM_DISTRIBUTION" in constraint_codes

    @pytest.mark.asyncio
    async def test_database_configuration_loading(
        self, constraint_manager, test_session
    ):
        """Test loading constraint configuration from database"""
        # This test would require actual database configuration data
        # For now, test that the method exists and can be called
        try:
            # Try with a non-existent configuration ID
            summary = await constraint_manager.load_configuration(uuid4())
            assert summary is not None  # Should fall back to default
        except Exception as e:
            pytest.fail(f"Loading configuration failed: {e}")

    @pytest.mark.asyncio
    async def test_constraint_lifecycle_management(self, constraint_manager):
        """Test adding, removing, and updating constraints"""
        await constraint_manager.load_configuration()

        initial_count = len(constraint_manager.active_constraints)

        # Test adding a constraint
        new_constraint = ExamDistributionConstraint(weight=0.8)
        success = constraint_manager.add_constraint(new_constraint)
        assert success is True
        assert len(constraint_manager.active_constraints) == initial_count + 1

        # Test removing a constraint
        success = constraint_manager.remove_constraint("EXAM_DISTRIBUTION")
        assert success is True
        assert len(constraint_manager.active_constraints) == initial_count

        # Test updating constraint weight
        success = constraint_manager.update_constraint_weight("ROOM_UTILIZATION", 0.7)
        assert success is True
        constraint = constraint_manager.get_constraint_by_id("ROOM_UTILIZATION")
        assert constraint.weight == 0.7


@pytest.mark.integration
class TestConstraintFactoryIntegration:
    """Integration tests for constraint factory with database"""

    @pytest.mark.asyncio
    async def test_factory_constraint_creation(self, constraint_factory):
        """Test creating constraints through factory"""
        constraint = (
            await constraint_factory.create_constraint_instance(  # CHANGED METHOD NAME
                "NO_STUDENT_CONFLICT",
                weight=1.0,
                parameters={"check_cross_registration": True},
            )
        )
        assert constraint is not None
        assert constraint.constraint_id == "NO_STUDENT_CONFLICT"
        assert constraint.weight == 1.0

    @pytest.mark.asyncio
    async def test_factory_constraint_set_creation(self, constraint_factory):
        """Test creating complete constraint sets"""
        constraints = await constraint_factory.create_constraint_set_for_session(
            session_id=uuid4()
        )
        assert constraints is not None
        assert len(constraints) > 0

        # Should include both hard and soft constraints
        hard_constraints = [c for c in constraints if c.constraint_type.value == "hard"]
        soft_constraints = [c for c in constraints if c.constraint_type.value == "soft"]

        assert len(hard_constraints) > 0
        assert len(soft_constraints) > 0

    @pytest.mark.asyncio
    async def test_factory_available_constraints(self, constraint_factory):
        """Test retrieving available constraint definitions"""
        constraints = constraint_factory.get_available_constraints()
        assert constraints is not None
        assert len(constraints) > 0

        # Should include expected constraint types
        assert "NO_STUDENT_CONFLICT" in constraints
        assert "ROOM_CAPACITY" in constraints
        assert "EXAM_DISTRIBUTION" in constraints


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
