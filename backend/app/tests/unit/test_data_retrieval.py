"""
Test for data retrieval using existing database with exam_system schema
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from app.services.data_retrieval.scheduling_data import SchedulingData
from sqlalchemy import text


class TestSchedulingData:
    """Test for SchedulingData service using existing database"""

    @pytest.mark.asyncio
    async def test_get_exams_for_session(self, test_session):
        """Test getting exams for a session."""
        scheduling_data = SchedulingData(test_session)

        # Check if there are any academic sessions in the database
        result = await test_session.execute(
            text("SELECT id FROM exam_system.academic_sessions LIMIT 1")
        )
        session_id = result.scalar()

        if session_id:
            exams = await scheduling_data._get_exams_for_session(session_id)
            assert isinstance(exams, list)
            print(f"Found {len(exams)} exams for session {session_id}")
        else:
            non_existent_id = uuid4()
            exams = await scheduling_data._get_exams_for_session(non_existent_id)
            assert isinstance(exams, list)
            assert len(exams) == 0
            print("Tested with non-existent session ID (no sessions in database)")

    @pytest.mark.asyncio
    async def test_get_time_slots(self, test_session):
        """Test getting time slots from database."""
        scheduling_data = SchedulingData(test_session)
        time_slots = await scheduling_data._get_time_slots()

        assert isinstance(time_slots, list)
        print(f"Found {len(time_slots)} time slots in database")

    @pytest.mark.asyncio
    async def test_get_rooms(self, test_session):
        """Test getting rooms from database."""
        scheduling_data = SchedulingData(test_session)
        rooms = await scheduling_data._get_rooms()

        assert isinstance(rooms, list)
        print(f"Found {len(rooms)} rooms in database")

    @pytest.mark.asyncio
    async def test_get_available_staff(self, test_session):
        """Test getting available staff from database."""
        scheduling_data = SchedulingData(test_session)
        staff = await scheduling_data._get_available_staff()

        assert isinstance(staff, list)
        print(f"Found {len(staff)} available staff members in database")

    @pytest.mark.asyncio
    async def test_get_scheduling_data_for_session(self, test_session):
        """Test getting complete scheduling data for a session."""
        scheduling_data = SchedulingData(test_session)

        result = await test_session.execute(
            text("SELECT id FROM exam_system.academic_sessions LIMIT 1")
        )
        session_id = result.scalar()

        if session_id:
            data = await scheduling_data.get_scheduling_data_for_session(session_id)

            assert isinstance(data, dict)
            assert "session_id" in data
            assert "exams" in data
            assert "time_slots" in data
            assert "rooms" in data
            assert "staff" in data
            assert "staff_unavailability" in data
            assert "course_registrations" in data
            assert "metadata" in data

            print(f"Retrieved scheduling data for session {session_id}")
            print(f"Exams: {len(data['exams'])}")
            print(f"Time slots: {len(data['time_slots'])}")
            print(f"Rooms: {len(data['rooms'])}")
            print(f"Staff: {len(data['staff'])}")
            print(f"Course registrations: {len(data['course_registrations'])}")
        else:
            non_existent_id = uuid4()
            try:
                data = await scheduling_data.get_scheduling_data_for_session(
                    non_existent_id
                )
                print(
                    "get_scheduling_data_for_session did not raise an exception for non-existent session"
                )
            except Exception as e:
                print(
                    f"get_scheduling_data_for_session raised exception for non-existent session: {e}"
                )

    @pytest.mark.asyncio
    async def test_get_courses_with_registrations(self, test_session):
        """Test getting courses with registration counts."""
        scheduling_data = SchedulingData(test_session)

        result = await test_session.execute(
            text("SELECT id FROM exam_system.academic_sessions LIMIT 1")
        )
        session_id = result.scalar()

        if session_id:
            courses = await scheduling_data.get_courses_with_registrations(session_id)
            assert isinstance(courses, list)
            print(
                f"Found {len(courses)} courses with registrations for session {session_id}"
            )
        else:
            print("No academic sessions found in database")

    @pytest.mark.asyncio
    async def test_get_students_for_session(self, test_session):
        """Test getting students for a session."""
        scheduling_data = SchedulingData(test_session)

        result = await test_session.execute(
            text("SELECT id FROM exam_system.academic_sessions LIMIT 1")
        )
        session_id = result.scalar()

        if session_id:
            students = await scheduling_data.get_students_for_session(session_id)
            assert isinstance(students, list)
            print(f"Found {len(students)} students for session {session_id}")
        else:
            print("No academic sessions found in database")
