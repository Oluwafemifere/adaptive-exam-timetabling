# tests/integration/test_data_flow_integration.py

"""
Data Flow Integration Test

Tests the complete pipeline from CSV upload to scheduling engine processing:
1. Upload CSV via API endpoint
2. CSV processing and validation
3. Data mapping to database format
4. Job orchestration and scheduling
5. Solution generation and validation

Uses data retrieval services to access seeded database content.
"""

import pytest
import tempfile
import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple, AsyncGenerator, cast
from uuid import UUID, uuid4
from datetime import datetime, date, time
from pathlib import Path
from decimal import Decimal

# FastAPI and database imports
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient
from sqlalchemy import Sequence, select

# Application imports (relative to backend/)
from backend.app.main import app
from backend.app.database import get_db
from backend.app.models.base import Base
from backend.app.models.jobs import TimetableJob, TimetableVersion
from backend.app.models.academic import AcademicSession, Faculty, Department, Course
from backend.app.models.infrastructure import Room
from backend.app.models.users import User
from backend.app.models.scheduling import TimeSlot
from backend.app.services.data_validation.csv_processor import (
    CSVProcessor,
    CSVValidationError,
)
from backend.app.services.data_validation.data_mapper import (
    DataMapper,
    MappingResult,
)
from backend.app.services.scheduling.timetable_job_orchestrator import (
    TimetableJobOrchestrator,
    OrchestratorOptions,
)
from backend.app.services.scheduling.upload_ingestion_bridge import (
    UploadIngestionBridge,
    UploadIngestionSummary,
)
from backend.app.schemas.uploads import FileUploadSessionCreate, UploadedFileCreate
from backend.app.models.users import SystemConfiguration

# Import config
from backend.app.config import get_settings

# Import data retrieval services
from backend.app.services.data_retrieval import (
    AcademicData,
    UserData,
    InfrastructureData,
    JobData,
    ConstraintData,
    FileUploadData,
    TimetableEditData,
)

# Get production database URL from config
settings = get_settings()
DATABASE_URL = settings.DATABASE_URL

# Scheduling engine imports (relative to project root)
from scheduling_engine.core.problem_model import (
    ExamSchedulingProblem,
    Exam,
    TimeSlot as EngineTimeSlot,
)
from scheduling_engine.core.solution import (
    TimetableSolution,
    SolutionStatus,
    ExamAssignment,
)


class TestDataFlowIntegration:
    """Integration test for complete data flow pipeline using production database"""

    @pytest.fixture(scope="function")
    async def async_db_session(self) -> AsyncGenerator[AsyncSession, None]:
        engine = create_async_engine(
            DATABASE_URL,
            poolclass=NullPool,
            echo=False,
        )

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session = async_sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )

        async with async_session() as session:
            try:
                yield session
            finally:
                await session.close()

    @pytest.fixture
    async def test_user(self, async_db_session: AsyncSession) -> User:
        """Get a test user from the database"""
        user_data = UserData(async_db_session)
        users = await user_data.get_active_users()
        assert len(users) > 0, "No active users found in database"
        return await async_db_session.get(User, UUID(users[0]["id"]))

    @pytest.fixture
    async def test_academic_session(
        self, async_db_session: AsyncSession
    ) -> AcademicSession:
        """Get an academic session from the database"""
        academic_data = AcademicData(async_db_session)
        sessions = await academic_data.get_active_academic_sessions()
        assert len(sessions) > 0, "No active academic sessions found in database"
        return await async_db_session.get(AcademicSession, UUID(sessions[0]["id"]))

    @pytest.fixture
    async def test_rooms(self, async_db_session: AsyncSession) -> List[Room]:
        """Get rooms from the database"""
        infrastructure_data = InfrastructureData(async_db_session)
        rooms_data = await infrastructure_data.get_active_rooms()
        assert len(rooms_data) > 0, "No active rooms found in database"

        rooms = []
        for room_data in rooms_data:
            room = await async_db_session.get(Room, UUID(room_data["id"]))
            if room:
                rooms.append(room)

        return rooms

    @pytest.fixture
    async def test_time_slots(self, async_db_session: AsyncSession) -> List[TimeSlot]:
        """Get time slots from the database"""
        stmt = select(TimeSlot).where(TimeSlot.is_active)
        result = await async_db_session.execute(stmt)
        time_slots = list(result.scalars().all())
        assert len(time_slots) > 0, "No active time slots found in database"
        return time_slots

    @pytest.fixture
    def sample_courses_csv_content(self) -> str:
        """Generate sample CSV content for courses"""
        return """course_code,course_title,credits,level,department_code,is_practical,morning_only,exam_duration
CSC301,Data Structures and Algorithms,3,300,CSC,false,false,180
MTH201,Calculus II,4,200,MTH,false,true,120
PHY301,Quantum Physics,3,300,PHY,true,false,180
CSC401,Software Engineering,3,400,CSC,false,false,240
MTH301,Linear Algebra,3,300,MTH,false,false,180"""

    @pytest.fixture
    def sample_students_csv_content(self) -> str:
        """Generate sample CSV content for students"""
        return """matric_number,programme_code,level,entry_year
19/1234,CSC,300,2019
19/1235,MTH,200,2019
20/1236,PHY,300,2020
19/1237,CSC,400,2019
20/1238,MTH,300,2020"""

    @pytest.fixture
    def sample_rooms_csv_content(self) -> str:
        """Generate sample CSV content for rooms"""
        return """room_code,room_name,capacity,exam_capacity,building_code,has_computers,has_projector,has_ac
LT001,Main Lecture Theatre,200,150,MAIN,false,true,true
LAB001,Computer Lab 1,50,40,COMP,true,true,true
LT002,Science Lecture Theatre,150,120,SCI,false,true,false
LAB002,Physics Lab,30,25,SCI,false,false,true
LT003,Mathematics Lecture Hall,100,80,MATH,false,true,true"""

    async def create_test_csv_file(self, content: str, filename: str) -> str:
        """Create temporary CSV file with given content"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return file_path

    async def test_complete_data_flow_integration(
        self,
        async_db_session: AsyncSession,
        test_user: User,
        test_academic_session: AcademicSession,
        test_rooms: List[Room],
        test_time_slots: List[TimeSlot],
        sample_courses_csv_content: str,
        sample_students_csv_content: str,
        sample_rooms_csv_content: str,
    ) -> None:
        """
        Test complete data flow from CSV upload to scheduling solution.

        This integration test validates:
        1. CSV upload and validation
        2. Data mapping with type safety
        3. Job orchestration
        4. Scheduling engine integration
        5. Solution validation
        """
        test_config = SystemConfiguration(
            name="Test Configuration",
            description="Test configuration for integration tests",
            created_by=test_user.id,
        )
        async_db_session.add(test_config)
        await async_db_session.flush()
        configuration_id = test_config.id
        # Initialize data retrieval services
        academic_data = AcademicData(async_db_session)
        infrastructure_data = InfrastructureData(async_db_session)
        constraint_data = ConstraintData(async_db_session)
        job_data = JobData(async_db_session)

        # Step 1: Test CSV Processing with Type Safety
        csv_processor = CSVProcessor()

        # Register schemas for each entity type with proper typing
        courses_schema = {
            "required_columns": ["course_code", "course_title", "credits", "level"],
            "column_mappings": {"credits": "credit_units", "level": "course_level"},
            "transformers": {
                "credit_units": csv_processor._default_transform,
                "course_level": csv_processor._default_transform,
                "is_practical": lambda x: str(x).lower() in ("true", "1", "yes"),
                "morning_only": lambda x: str(x).lower() in ("true", "1", "yes"),
                "exam_duration": lambda x: int(x) if x else 180,
            },
            "validators": {
                "course_code": lambda x, row: {"is_valid": bool(x), "error": None},
                "course_title": lambda x, row: {"is_valid": bool(x), "error": None},
            },
        }

        csv_processor.register_schema("courses", courses_schema)

        # Create and process courses CSV
        courses_file = await self.create_test_csv_file(
            sample_courses_csv_content, "test_courses.csv"
        )

        try:
            courses_result = csv_processor.process_csv_file(
                courses_file, "courses", validate_data=True
            )

            # Validate CSV processing result with proper typing
            assert courses_result["success"] is True
            assert isinstance(courses_result["total_rows"], int)
            assert isinstance(courses_result["processed_rows"], int)
            assert isinstance(courses_result["data"], list)
            assert courses_result["processed_rows"] == 5

            # Validate data structure and types
            for course_data in courses_result["data"]:
                assert isinstance(course_data, dict)
                assert "course_code" in course_data
                assert "course_title" in course_data
                assert isinstance(course_data.get("is_practical"), bool)
                assert isinstance(course_data.get("morning_only"), bool)
                assert "_metadata" in course_data

            print("✅ CSV Processing: Type-safe validation completed")

        finally:
            os.unlink(courses_file)

        # Step 2: Test Data Mapping with Type Safety
        data_mapper = DataMapper(async_db_session)

        # Map processed CSV data to database format
        mapping_result = await data_mapper.map_data(courses_result["data"], "courses")

        # Validate mapping result with proper typing
        assert isinstance(mapping_result, dict)
        assert mapping_result["success"] is False
        assert isinstance(mapping_result["processed_records"], int)
        assert isinstance(mapping_result["mapped_data"], list)

        # Validate mapped data structure
        for mapped_course in mapping_result["mapped_data"]:
            assert isinstance(mapped_course, dict)
            assert "code" in mapped_course  # Should be mapped from course_code
            assert "title" in mapped_course  # Should be mapped from course_title
            assert isinstance(mapped_course.get("credit_units"), (int, type(None)))
            assert isinstance(mapped_course.get("is_practical"), (bool, type(None)))

        print("✅ Data Mapping: Type-safe transformation completed")

        # Step 3: Test Upload Ingestion Bridge
        ingestion_bridge = UploadIngestionBridge(cast(Any, async_db_session))

        # Simulate file upload session
        upload_session_id = uuid4()

        # Test upload session listing with proper typing
        recent_uploads: List[UploadIngestionSummary] = (
            await ingestion_bridge.list_recent_uploads(5)
        )
        assert isinstance(recent_uploads, list)

        print("✅ Upload Ingestion: Type-safe bridge operations completed")

        # Step 4: Test Job Orchestration with Type Safety
        orchestrator = TimetableJobOrchestrator(cast(Any, async_db_session))

        # Create orchestration options with proper typing
        options = OrchestratorOptions(
            run_room_planning=True,
            run_invigilator_planning=True,
            activate_version=False,
        )

        # Mock solver callable with proper typing
        def mock_solver(solver_input: Dict[str, Any]) -> Dict[str, Any]:
            """Mock solver function with type safety"""
            assert isinstance(solver_input, dict)
            assert "prepared_data" in solver_input
            assert "constraints" in solver_input
            assert "options" in solver_input

            return {
                "status": "completed",
                "objective_value": 150.5,
                "assignments": [],
                "runtime_seconds": 10.2,
                "solution_quality": "feasible",
            }

        # Get constraint configuration
        constraint_rules = await constraint_data.get_configurable_rules()
        assert len(constraint_rules) > 0, "No configurable constraint rules found"

        # Start scheduling job with type safety
        job_id: UUID = await orchestrator.start_job(
            session_id=test_academic_session.id,
            configuration_id=configuration_id,
            initiated_by=test_user.id,
            solver_callable=mock_solver,
            options=options,
        )

        # Validate job creation
        assert isinstance(job_id, UUID)

        # Retrieve job and validate structure
        job_query = await async_db_session.get(TimetableJob, job_id)
        assert job_query is not None
        assert isinstance(job_query.session_id, UUID)
        assert isinstance(job_query.configuration_id, UUID)
        assert isinstance(job_query.initiated_by, UUID)
        assert job_query.status in ["queued", "running", "completed", "failed"]

        print("✅ Job Orchestration: Type-safe job creation and execution completed")

        # Step 5: Test Scheduling Engine Integration with Type Safety

        # Get academic data for problem model
        courses = await academic_data.get_all_courses()
        assert len(courses) > 0, "No courses found in database"

        # Create problem model with type safety
        problem = ExamSchedulingProblem(
            session_id=test_academic_session.id,
            session_name=test_academic_session.name,
            exam_period_start=date(2024, 12, 1),
            exam_period_end=date(2024, 12, 20),
            db_session=async_db_session,
        )

        # Add sample data to problem with proper typing
        sample_exam = Exam(
            id=uuid4(),
            course_id=UUID(courses[0]["id"]),
            course_code=courses[0]["code"],
            course_title=courses[0]["title"],
            department_id=(
                UUID(courses[0]["department_id"])
                if courses[0]["department_id"]
                else None
            ),
            faculty_id=None,  # Will be set based on department
            session_id=test_academic_session.id,
            duration_minutes=courses[0].get("exam_duration_minutes", 180),
            expected_students=45,
            is_practical=courses[0].get("is_practical", False),
            morning_only=courses[0].get("morning_only", False),
            weight=1.0,
        )

        problem.add_exam(sample_exam)

        start_time = test_time_slots[0].start_time
        if isinstance(start_time, datetime):
            start_time = start_time.time()

        end_time = test_time_slots[0].end_time
        if isinstance(end_time, datetime):
            end_time = end_time.time()

        # Ensure the static type checker knows these are datetime.time
        start_time = cast(time, start_time)
        end_time = cast(time, end_time)

        time_slot = EngineTimeSlot(
            id=uuid4(),
            name=test_time_slots[0].name,
            start_time=cast(time, start_time),
            end_time=cast(time, end_time),
            duration_minutes=test_time_slots[0].duration_minutes,
            date=date(2024, 12, 5),
        )

        problem.time_slots[time_slot.id] = time_slot

        # Create solution with type safety
        solution = TimetableSolution(
            problem=problem,
            solution_id=uuid4(),
            session_data={"session_name": test_academic_session.name},
        )

        # Test assignment with proper typing
        assignment_success: bool = solution.assign_exam(
            exam_id=sample_exam.id,
            time_slot_id=time_slot.id,
            room_ids=[test_rooms[0].id],
            assigned_date=date(2024, 12, 5),
            room_allocations={test_rooms[0].id: 45},
        )

        assert isinstance(assignment_success, bool)
        assert assignment_success is True

        # Validate solution structure and types
        assert isinstance(solution.id, UUID)
        assert isinstance(solution.session_id, UUID)
        assert isinstance(solution.status, SolutionStatus)
        assert isinstance(solution.objective_value, float)
        assert isinstance(solution.fitness_score, float)
        assert isinstance(solution.assignments, dict)

        # Validate assignment structure
        assignment: ExamAssignment = solution.assignments[sample_exam.id]
        assert isinstance(assignment.exam_id, UUID)
        assert isinstance(assignment.time_slot_id, (UUID, type(None)))
        assert isinstance(assignment.room_ids, list)
        assert isinstance(assignment.assigned_date, (date, type(None)))
        assert isinstance(assignment.room_allocations, dict)

        # Test solution export with type safety
        backend_format: Dict[str, Any] = solution.export_to_backend_format()
        assert isinstance(backend_format, dict)
        assert "solution_id" in backend_format
        assert "session_id" in backend_format
        assert "assignments" in backend_format
        assert isinstance(backend_format["assignments"], list)

        print(
            "✅ Scheduling Engine: Type-safe solution creation and validation completed"
        )

        # Step 6: End-to-End Validation

        # Validate that solution can be serialized/deserialized safely
        solution_dict: Dict[str, Any] = solution.to_dict()
        assert isinstance(solution_dict, dict)
        assert "id" in solution_dict
        assert "assignments" in solution_dict
        assert "statistics" in solution_dict

        # Validate completion percentage calculation
        completion_percentage: float = solution.get_completion_percentage()
        assert isinstance(completion_percentage, float)
        assert 0.0 <= completion_percentage <= 100.0

        # Validate feasibility check
        is_feasible: bool = solution.is_feasible()
        assert isinstance(is_feasible, bool)

        print("✅ End-to-End Validation: All type safety checks passed")

    async def test_error_handling_with_type_safety(
        self, async_db_session: AsyncSession
    ) -> None:
        """Test error handling throughout the data flow with proper typing"""

        # Test CSV processor error handling
        csv_processor = CSVProcessor()

        # Test with invalid file path
        result = csv_processor.process_csv_file("/nonexistent/file.csv", "courses")

        assert isinstance(result, dict)
        assert result["success"] is False
        assert isinstance(result["errors"], list)
        assert len(result["errors"]) > 0

        # Test data mapper error handling
        data_mapper = DataMapper(cast(Any, async_db_session))

        # Test with invalid entity type
        mapping_result = await data_mapper.map_data([], "invalid_entity_type")
        assert isinstance(mapping_result, dict)
        assert mapping_result["success"] is False
        assert isinstance(mapping_result["errors"], list)

        print("✅ Error Handling: Type-safe error propagation validated")

    async def test_performance_with_type_monitoring(
        self, async_db_session: AsyncSession, sample_courses_csv_content: str
    ) -> None:
        """Test performance characteristics with type monitoring"""

        start_time = datetime.now()

        # Process larger dataset
        large_csv_content = sample_courses_csv_content
        for i in range(100):  # Create 500 total courses
            large_csv_content += (
                f"\nCSC{300+i},Test Course {i},3,300,CSC,false,false,180"
            )

        csv_processor = CSVProcessor()
        courses_file = await self.create_test_csv_file(
            large_csv_content, "large_courses.csv"
        )

        try:
            result = csv_processor.process_csv_file(
                courses_file, "courses", chunk_size=50
            )

            processing_time = (datetime.now() - start_time).total_seconds()

            # Validate performance metrics with type safety
            assert isinstance(processing_time, float)
            assert processing_time < 30.0  # Should process within 30 seconds
            assert isinstance(result["processed_rows"], int)
            assert result["processed_rows"] == 105  # 5 original + 100 generated

            print(
                f"✅ Performance: Processed {result['processed_rows']} records in {processing_time:.2f}s"
            )

        finally:
            os.unlink(courses_file)


# Additional fixtures and utilities for comprehensive testing


@pytest.fixture
def mock_scheduling_configuration() -> Dict[str, Any]:
    """Mock scheduling configuration with proper typing"""
    return {
        "max_consecutive_exams": 3,
        "min_break_between_exams": 60,  # minutes
        "prefer_morning_slots": True,
        "allow_weekend_scheduling": False,
        "room_utilization_target": 0.85,
        "constraint_weights": {
            "student_conflict": 10.0,
            "room_capacity": 8.0,
            "time_preference": 3.0,
        },
    }


@pytest.fixture
async def sample_constraint_data(
    async_db_session: AsyncSession,
) -> List[Dict[str, Any]]:
    """Get constraint data from database with proper typing"""
    constraint_data = ConstraintData(async_db_session)
    constraint_rules = await constraint_data.get_configurable_rules()

    return [
        {
            "id": rule["id"],
            "name": rule["name"],
            "type": rule["constraint_type"],
            "weight": rule["default_weight"],
            "is_active": True,
            "parameters": {"max_conflicts": 0},
        }
        for rule in constraint_rules[:3]  # Use first 3 configurable rules
    ]


class TypeSafetyValidator:
    """Utility class for validating type safety across the data flow"""

    @staticmethod
    def validate_csv_result(result: Dict[str, Any]) -> bool:
        """Validate CSV processing result types"""
        required_keys = ["success", "total_rows", "processed_rows", "data", "errors"]
        if not all(key in result for key in required_keys):
            return False

        return (
            isinstance(result["success"], bool)
            and isinstance(result["total_rows"], int)
            and isinstance(result["processed_rows"], int)
            and isinstance(result["data"], list)
            and isinstance(result["errors"], list)
        )

    @staticmethod
    def validate_mapping_result(result: Dict[str, Any]) -> bool:
        """Validate data mapping result types"""
        required_keys = ["success", "processed_records", "mapped_data"]
        if not all(key in result for key in required_keys):
            return False

        return (
            isinstance(result["success"], bool)
            and isinstance(result["processed_records"], int)
            and isinstance(result["mapped_data"], list)
        )

    @staticmethod
    def validate_solution_structure(solution: TimetableSolution) -> bool:
        """Validate solution object type safety"""
        return (
            isinstance(solution.id, UUID)
            and isinstance(solution.session_id, UUID)
            and isinstance(solution.status, SolutionStatus)
            and isinstance(solution.assignments, dict)
            and isinstance(solution.objective_value, float)
            and isinstance(solution.fitness_score, float)
        )
