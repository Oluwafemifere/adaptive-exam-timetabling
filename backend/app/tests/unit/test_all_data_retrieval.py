# backend/app/tests/unit/test_all_data_retrieval.py

"""
Comprehensive test for all data retrieval modules following the pattern
of the existing test_data_retrieval.py
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import date

from app.services.data_retrieval.academic_data import AcademicData
from app.services.data_retrieval.user_data import UserData
from app.services.data_retrieval.infrastructure_data import InfrastructureData
from app.services.data_retrieval.job_data import JobData
from app.services.data_retrieval.constraint_data import ConstraintData
from app.services.data_retrieval.audit_data import AuditData
from app.services.data_retrieval.file_upload_data import FileUploadData
from app.services.data_retrieval.timetable_edit_data import TimetableEditData
from app.services.data_retrieval.scheduling_data import SchedulingData
from app.services.data_retrieval.conflict_analysis import ConflictAnalysis

from sqlalchemy import text
from sqlalchemy import func, case, select


class TestAllDataRetrieval:
    """Comprehensive test for all data retrieval services using existing database"""

    @pytest.mark.asyncio
    async def test_academic_data_service(self, test_session):
        """Test AcademicData service methods"""
        academic_data = AcademicData(test_session)

        # Test get all academic sessions
        sessions = await academic_data.get_all_academic_sessions()
        assert isinstance(sessions, list)
        print(f"Found {len(sessions)} academic sessions")

        # Test get active academic sessions
        active_sessions = await academic_data.get_active_academic_sessions()
        assert isinstance(active_sessions, list)
        print(f"Found {len(active_sessions)} active academic sessions")

        # Test get all faculties
        faculties = await academic_data.get_all_faculties()
        assert isinstance(faculties, list)
        print(f"Found {len(faculties)} faculties")

        # Test get all departments
        departments = await academic_data.get_all_departments()
        assert isinstance(departments, list)
        print(f"Found {len(departments)} departments")

        # Test get all programmes
        programmes = await academic_data.get_all_programmes()
        assert isinstance(programmes, list)
        print(f"Found {len(programmes)} programmes")

        # Test get all courses
        courses = await academic_data.get_all_courses()
        assert isinstance(courses, list)
        print(f"Found {len(courses)} courses")

        # Test get all students
        students = await academic_data.get_all_students()
        assert isinstance(students, list)
        print(f"Found {len(students)} students")

        # Test with specific session if exists
        if sessions:
            session_id = sessions[0]["id"]
            registrations = await academic_data.get_registrations_for_session(
                session_id
            )
            assert isinstance(registrations, list)
            print(f"Found {len(registrations)} registrations for session {session_id}")

            stats = await academic_data.get_registration_statistics_by_session(
                session_id
            )
            assert isinstance(stats, dict)
            print(f"Registration statistics: {stats}")

    @pytest.mark.asyncio
    async def test_user_data_service(self, test_session):
        """Test UserData service methods"""
        user_data = UserData(test_session)

        # Test get all users
        users = await user_data.get_all_users()
        assert isinstance(users, list)
        print(f"Found {len(users)} users")

        # Test get active users
        active_users = await user_data.get_active_users()
        assert isinstance(active_users, list)
        print(f"Found {len(active_users)} active users")

        # Test get all user roles
        roles = await user_data.get_all_user_roles()
        assert isinstance(roles, list)
        print(f"Found {len(roles)} user roles")

        # Test get all system configurations
        configs = await user_data.get_all_system_configurations()
        assert isinstance(configs, list)
        print(f"Found {len(configs)} system configurations")

        # Test get system events
        events = await user_data.get_system_events()
        assert isinstance(events, list)
        print(f"Found {len(events)} system events")

        if users:
            user_id = users[0]["id"]
            notifications = await user_data.get_user_notifications(user_id)
            assert isinstance(notifications, list)
            print(f"Found {len(notifications)} notifications for user {user_id}")

    @pytest.mark.asyncio
    async def test_infrastructure_data_service(self, test_session):
        """Test InfrastructureData service methods"""
        infrastructure_data = InfrastructureData(test_session)

        # Test get all buildings
        buildings = await infrastructure_data.get_all_buildings()
        assert isinstance(buildings, list)
        print(f"Found {len(buildings)} buildings")

        # Test get active buildings
        active_buildings = await infrastructure_data.get_active_buildings()
        assert isinstance(active_buildings, list)
        print(f"Found {len(active_buildings)} active buildings")

        # Test get all room types
        room_types = await infrastructure_data.get_all_room_types()
        assert isinstance(room_types, list)
        print(f"Found {len(room_types)} room types")

        # Test get all rooms
        rooms = await infrastructure_data.get_all_rooms()
        assert isinstance(rooms, list)
        print(f"Found {len(rooms)} rooms")

        # Test get active rooms
        active_rooms = await infrastructure_data.get_active_rooms()
        assert isinstance(active_rooms, list)
        print(f"Found {len(active_rooms)} active rooms")

        # Test building statistics
        building_stats = await infrastructure_data.get_building_statistics()
        assert isinstance(building_stats, list)
        print(f"Building statistics: {len(building_stats)} buildings with stats")

        # Test room utilization summary
        utilization = await infrastructure_data.get_room_utilization_summary()
        assert isinstance(utilization, dict)
        print(f"Room utilization summary: {utilization}")

    @pytest.mark.asyncio
    async def test_job_data_service(self, test_session):
        """Test JobData service methods"""
        job_data = JobData(test_session)

        # Test get all timetable jobs
        jobs = await job_data.get_all_timetable_jobs()
        assert isinstance(jobs, list)
        print(f"Found {len(jobs)} timetable jobs")

        # Test get all timetable versions
        versions = await job_data.get_all_timetable_versions()
        assert isinstance(versions, list)
        print(f"Found {len(versions)} timetable versions")

        # Test get running jobs
        running_jobs = await job_data.get_running_jobs()
        assert isinstance(running_jobs, list)
        print(f"Found {len(running_jobs)} running jobs")

        # Test job statistics
        stats = await job_data.get_job_statistics()
        assert isinstance(stats, dict)
        print(f"Job statistics: {stats}")

        # Test performance metrics
        metrics = await job_data.get_performance_metrics()
        assert isinstance(metrics, list)
        print(f"Found {len(metrics)} performance metrics")

    @pytest.mark.asyncio
    async def test_constraint_data_service(self, test_session):
        """Test ConstraintData service methods"""
        constraint_data = ConstraintData(test_session)

        # Test get all constraint categories
        categories = await constraint_data.get_all_constraint_categories()
        assert isinstance(categories, list)
        print(f"Found {len(categories)} constraint categories")

        # Test get all constraint rules
        rules = await constraint_data.get_all_constraint_rules()
        assert isinstance(rules, list)
        print(f"Found {len(rules)} constraint rules")

        # Test get active constraint rules
        active_rules = await constraint_data.get_active_constraint_rules()
        assert isinstance(active_rules, list)
        print(f"Found {len(active_rules)} active constraint rules")

        # Test get configurable rules
        configurable_rules = await constraint_data.get_configurable_rules()
        assert isinstance(configurable_rules, list)
        print(f"Found {len(configurable_rules)} configurable rules")

        # Test constraint statistics
        stats = await constraint_data.get_constraint_statistics()
        assert isinstance(stats, dict)
        print(f"Constraint statistics: {stats}")

    @pytest.mark.asyncio
    async def test_audit_data_service(self, test_session):
        """Test AuditData service methods"""
        audit_data = AuditData(test_session)

        # Test get all audit logs
        logs = await audit_data.get_all_audit_logs(limit=50)
        assert isinstance(logs, list)
        print(f"Found {len(logs)} audit logs")

        # Test audit statistics
        stats = await audit_data.get_audit_statistics()
        assert isinstance(stats, dict)
        print(f"Audit statistics: {stats}")

        # Test unique actions
        actions = await audit_data.get_unique_actions()
        assert isinstance(actions, list)
        print(f"Found {len(actions)} unique audit actions")

        # Test unique entity types
        entity_types = await audit_data.get_unique_entity_types()
        assert isinstance(entity_types, list)
        print(f"Found {len(entity_types)} unique entity types")

    @pytest.mark.asyncio
    async def test_file_upload_data_service(self, test_session):
        """Test FileUploadData service methods"""
        file_upload_data = FileUploadData(test_session)

        # Test get all upload sessions
        sessions = await file_upload_data.get_all_upload_sessions()
        assert isinstance(sessions, list)
        print(f"Found {len(sessions)} upload sessions")

        # Test get all uploaded files
        files = await file_upload_data.get_all_uploaded_files(limit=50)
        assert isinstance(files, list)
        print(f"Found {len(files)} uploaded files")

        # Test get active upload sessions
        active_sessions = await file_upload_data.get_active_upload_sessions()
        assert isinstance(active_sessions, list)
        print(f"Found {len(active_sessions)} active upload sessions")

        # Test upload statistics
        stats = await file_upload_data.get_upload_statistics()
        assert isinstance(stats, dict)
        print(f"Upload statistics: {stats}")

        # Test recent uploads
        recent = await file_upload_data.get_recent_uploads(limit=10)
        assert isinstance(recent, list)
        print(f"Found {len(recent)} recent uploads")

    @pytest.mark.asyncio
    async def test_timetable_edit_data_service(self, test_session):
        """Test TimetableEditData service methods"""
        timetable_edit_data = TimetableEditData(test_session)

        # Test get all timetable edits
        edits = await timetable_edit_data.get_all_timetable_edits(limit=50)
        assert isinstance(edits, list)
        print(f"Found {len(edits)} timetable edits")

        # Test get pending edits
        pending_edits = await timetable_edit_data.get_pending_edits()
        assert isinstance(pending_edits, list)
        print(f"Found {len(pending_edits)} pending edits")

        # Test edit statistics
        stats = await timetable_edit_data.get_edit_statistics()
        assert isinstance(stats, dict)
        print(f"Edit statistics: {stats}")

        # Test unique edit types
        edit_types = await timetable_edit_data.get_unique_edit_types()
        assert isinstance(edit_types, list)
        print(f"Found {len(edit_types)} unique edit types")

        # Test recent edits
        recent = await timetable_edit_data.get_recent_edits(limit=10)
        assert isinstance(recent, list)
        print(f"Found {len(recent)} recent edits")

    @pytest.mark.asyncio
    async def test_existing_services_still_work(self, test_session):
        """Ensure existing services still work properly"""

        # Test SchedulingData
        scheduling_data = SchedulingData(test_session)

        result = await test_session.execute(
            text("SELECT id FROM exam_system.academic_sessions LIMIT 1")
        )
        session_id = result.scalar()

        if session_id:
            scheduling_data_result = (
                await scheduling_data.get_scheduling_data_for_session(session_id)
            )
            assert isinstance(scheduling_data_result, dict)
            assert "session_id" in scheduling_data_result
            assert "exams" in scheduling_data_result
            assert "time_slots" in scheduling_data_result
            assert "rooms" in scheduling_data_result
            print(f"SchedulingData service working correctly for session {session_id}")

        # Test ConflictAnalysis
        conflict_analysis = ConflictAnalysis(test_session)

        room_utilization = await conflict_analysis.get_room_utilization()
        assert isinstance(room_utilization, dict)
        print(f"ConflictAnalysis service working correctly")

    @pytest.mark.asyncio
    async def test_comprehensive_data_integration(self, test_session):
        """Test integration between different data retrieval services"""

        # Initialize all services
        academic_data = AcademicData(test_session)
        user_data = UserData(test_session)
        infrastructure_data = InfrastructureData(test_session)
        job_data = JobData(test_session)

        # Test integration: Get session -> Get jobs for session
        sessions = await academic_data.get_all_academic_sessions()
        if sessions:
            session_id = sessions[0]["id"]
            jobs_for_session = await job_data.get_jobs_by_session(session_id)
            assert isinstance(jobs_for_session, list)
            print(
                f"Integration test: Found {len(jobs_for_session)} jobs for session {session_id}"
            )

        # Test integration: Get users -> Get jobs by user
        users = await user_data.get_all_users()
        if users:
            user_id = users[0]["id"]
            user_jobs = await job_data.get_jobs_by_user(user_id)
            assert isinstance(user_jobs, list)
            print(f"Integration test: Found {len(user_jobs)} jobs for user {user_id}")

        # Test integration: Get buildings -> Get rooms by building
        buildings = await infrastructure_data.get_all_buildings()
        if buildings:
            building_id = buildings[0]["id"]
            building_rooms = await infrastructure_data.get_rooms_by_building(
                building_id
            )
            assert isinstance(building_rooms, list)
            print(
                f"Integration test: Found {len(building_rooms)} rooms for building {building_id}"
            )

        print("Comprehensive data integration test completed successfully!")
