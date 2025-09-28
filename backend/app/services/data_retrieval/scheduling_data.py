# FIXED VERSION - Service for retrieving scheduling data from the database and preparing it for the scheduling engine
import logging
from typing import Any, List, Dict, cast, Optional
from uuid import UUID
from datetime import date as ddate, time as dtime, datetime as ddatetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models import (
    Staff,
    StaffUnavailability,
    Exam,
    ExamRoom,
    TimeSlot,
    Room,
    Course,
    Student,
    CourseRegistration,
    Programme,
    ExamInvigilator,
    TimetableAssignment,
    ExamDepartment,
    Department,
    Building,
    User,
)

logger = logging.getLogger(__name__)


class SchedulingData:
    """Service for retrieving all data needed for scheduling"""

    def __init__(self, session: AsyncSession):
        self.session = session
        logger.debug("SchedulingData service initialized with session")

    async def get_scheduling_data_for_session(self, session_id: UUID) -> Dict:
        """Retrieves all data needed for scheduling a specific academic session"""
        logger.info(f"Retrieving scheduling data for session {session_id}")
        logger.info(f"=== DATA RETRIEVAL START for session {session_id} ===")

        exams = await self.get_exams_for_session(session_id)
        logger.info(f"📊 EXAMS RETRIEVED: {len(exams)} exams")

        # Add detailed exam validation logging
        exams_with_students = 0
        exams_without_students = []
        for exam in exams:
            if exam.get("expected_students", 0) > 0:
                exams_with_students += 1
            else:
                exams_without_students.append(
                    {
                        "id": exam.get("id"),
                        "course_code": exam.get("course_code", "Unknown"),
                        "expected_students": exam.get("expected_students", 0),
                    }
                )

        logger.info(
            f"📈 EXAM STATISTICS: {exams_with_students} with students, {len(exams_without_students)} without"
        )
        if exams_without_students:
            logger.warning(
                f"🚨 PHANTOM EXAMS DETECTED at DB level: {exams_without_students}"
            )

        # Log course registrations analysis
        course_registrations = await self.get_course_registrations(session_id)
        courses_with_registrations = set(
            reg["course_id"] for reg in course_registrations
        )
        exam_course_ids = set(exam["course_id"] for exam in exams)
        orphaned_exams = exam_course_ids - courses_with_registrations

        if orphaned_exams:
            logger.error(
                f"🔴 ORPHANED EXAMS: {len(orphaned_exams)} exams have courses with no registrations: {list(orphaned_exams)[:5]}..."
            )

        # Staff/Invigilator logging
        staff = await self.get_available_staff()
        can_invigilate = sum(1 for s in staff if s.get("can_invigilate", False))
        logger.info(f"👥 STAFF: {len(staff)} total, {can_invigilate} can invigilate")

        if can_invigilate == 0:
            logger.error("🚨 CRITICAL: No staff members can invigilate!")
        try:
            # Get all the data
            exams = await self.get_exams_for_session(session_id)
            timeslots = await self.get_timeslots()
            rooms = await self.get_rooms()
            staff = await self.get_available_staff()
            staff_unavailability = await self.get_staff_unavailability(session_id)
            course_registrations = await self.get_course_registrations(session_id)
            timetable_assignments = await self.get_timetable_assignments(session_id)
            students = await self.get_students_for_session(session_id)

            result = {
                "session_id": session_id,
                "exams": exams,
                "timeslots": timeslots,
                "rooms": rooms,
                "staff": staff,
                "students": students,
                "staff_unavailability": staff_unavailability,
                "course_registrations": course_registrations,
                "timetable_assignments": timetable_assignments,
                "metadata": {
                    "total_exams": len(exams),
                    "total_rooms": len(rooms),
                    "total_staff": len(staff),
                    "total_students": len(
                        set(reg["student_id"] for reg in course_registrations)
                    ),
                    "total_assignments": len(timetable_assignments),
                },
            }

            logger.info(
                f"Successfully retrieved scheduling data for session {session_id}: "
                f"{len(exams)} exams, {len(rooms)} rooms, {len(staff)} staff, "
                f"{result['metadata']['total_students']} students, {len(timetable_assignments)} assignments"
            )

            return result

        except Exception as e:
            logger.error(
                f"Error retrieving scheduling data for session {session_id}: {str(e)}"
            )
            raise

    async def validate_course_exam_consistency(
        self, session_id: UUID
    ) -> Dict[str, Any]:
        """Validate that all exams have corresponding course registrations"""
        logger.info(f"🔍 VALIDATING course-exam consistency for session {session_id}")

        exams = await self.get_exams_for_session(session_id)
        registrations = await self.get_course_registrations(session_id)

        exam_courses = {exam["course_id"] for exam in exams}
        registered_courses = {reg["course_id"] for reg in registrations}

        consistency_report = {
            "total_exams": len(exams),
            "total_courses_with_exams": len(exam_courses),
            "total_courses_with_registrations": len(registered_courses),
            "orphaned_exams": list(exam_courses - registered_courses),
            "registered_but_no_exam": list(registered_courses - exam_courses),
            "phantom_exam_details": [],
        }

        # Detailed phantom exam analysis
        for exam in exams:
            course_id = exam["course_id"]
            if course_id not in registered_courses:
                consistency_report["phantom_exam_details"].append(
                    {
                        "exam_id": exam["id"],
                        "course_id": course_id,
                        "course_code": exam.get("course_code"),
                        "expected_students": exam.get("expected_students", 0),
                    }
                )

        logger.info(f"📋 CONSISTENCY REPORT: {consistency_report}")
        return consistency_report

    async def get_exams_for_session(self, session_id: UUID) -> List[Dict]:
        """FIXED - Get all exams for a specific session with course details"""
        logger.debug(f"Retrieving exams for session {session_id}")

        try:
            # FIXED: Include all needed JOINs in the query
            stmt = (
                select(Exam)
                .options(
                    # Load course with department information
                    selectinload(Exam.course).selectinload(Course.department),
                    # Load exam room assignments
                    selectinload(Exam.exam_rooms).selectinload(ExamRoom.room),
                    # Load exam department associations
                    selectinload(Exam.exam_departments).selectinload(
                        ExamDepartment.department
                    ),
                    # Load invigilator assignments
                    selectinload(Exam.invigilators),
                    # Load timetable assignments
                    selectinload(Exam.timetable_assignments),
                )
                .where(
                    and_(
                        Exam.session_id == session_id,
                        Exam.status.in_(["pending", "scheduled", "confirmed"]),
                    )
                )
            )

            result = await self.session.execute(stmt)
            exams = result.scalars().all()

            exam_list = []
            for exam in exams:
                # Extract room assignments
                room_assignments = [
                    {
                        "room_id": er.room_id,
                        "allocated_capacity": er.allocated_capacity,
                        "is_primary": er.is_primary,
                    }
                    for er in exam.exam_rooms
                ]

                # Extract department assignments
                department_assignments = [
                    {
                        "department_id": ed.department_id,
                        "department_name": (
                            ed.department.name if ed.department else None
                        ),
                    }
                    for ed in exam.exam_departments
                ]

                # Extract invigilator assignments
                invigilator_assignments = [
                    {
                        "staff_id": inv.staff_id,
                        "room_id": inv.room_id,
                        "timeslot_id": inv.time_slot_id if inv.time_slot_id else None,
                        "is_chief_invigilator": inv.is_chief_invigilator,
                        "assigned_at": (
                            cast(ddatetime, inv.assigned_at).isoformat()
                            if inv.assigned_at
                            else None
                        ),
                    }
                    for inv in exam.invigilators
                ]

                # Extract timetable assignments
                timetable_assignments = [
                    {
                        "assignment_id": ta.id,
                        "room_id": ta.room_id,
                        "day": cast(ddate, ta.day).isoformat() if ta.day else None,
                        "timeslot_id": ta.time_slot_id,
                        "student_count": ta.student_count,
                        "is_confirmed": ta.is_confirmed,
                    }
                    for ta in exam.timetable_assignments
                ]

                # FIXED: Include all required fields from course and department
                exam_data = {
                    "id": exam.id,
                    "course_id": exam.course_id,
                    # FIXED: Add course details that were missing
                    "course_code": exam.course.code if exam.course else None,
                    "course_title": exam.course.title if exam.course else None,
                    "course_level": exam.course.course_level if exam.course else None,
                    "course_is_practical": (
                        exam.course.is_practical if exam.course else False
                    ),
                    "morning_only": exam.course.morning_only if exam.course else False,
                    "department_name": (
                        exam.course.department.name
                        if exam.course and exam.course.department
                        else None
                    ),
                    "session_id": exam.session_id,
                    "timeslot_id": exam.time_slot_id if exam.time_slot_id else None,
                    "exam_date": (
                        cast(ddate, exam.exam_date).isoformat()
                        if exam.exam_date is not None
                        else None
                    ),
                    "duration_minutes": exam.duration_minutes,
                    "expected_students": exam.expected_students,
                    "requires_special_arrangements": exam.requires_special_arrangements,
                    "status": exam.status,
                    "notes": exam.notes,
                    "is_practical": exam.is_practical,
                    "requires_projector": exam.requires_projector,
                    "is_common": exam.is_common,
                    "room_assignments": room_assignments,
                    "department_assignments": department_assignments,
                    "invigilator_assignments": invigilator_assignments,
                    "timetable_assignments": timetable_assignments,
                }
                exam_list.append(exam_data)

            logger.debug(f"Retrieved {len(exam_list)} exams for session {session_id}")
            return exam_list

        except Exception as e:
            logger.error(f"Error retrieving exams for session {session_id}: {str(e)}")
            raise

    async def get_timeslots(self) -> List[Dict]:
        """Get all active time slots"""
        logger.debug("Retrieving all active time slots")

        try:
            stmt = select(TimeSlot).where(TimeSlot.is_active)
            result = await self.session.execute(stmt)
            timeslots = result.scalars().all()

            result_list = [
                {
                    "id": ts.id,
                    "name": ts.name,
                    # FIXED: Keep time objects as time objects, don't convert to strings
                    "start_time": ts.start_time,
                    "end_time": ts.end_time,
                    "duration_minutes": ts.duration_minutes,
                    "is_active": ts.is_active,
                }
                for ts in timeslots
            ]

            logger.debug(f"Retrieved {len(result_list)} active time slots")
            return result_list

        except Exception as e:
            logger.error(f"Error retrieving time slots: {str(e)}")
            raise

    async def get_rooms(self) -> List[Dict]:
        """FIXED - Get all active rooms with building and type information"""
        logger.debug("Retrieving all active rooms")

        try:
            # FIXED: Include building information in the query
            stmt = (
                select(Room)
                .options(selectinload(Room.building), selectinload(Room.room_type))
                .where(Room.is_active)
            )

            result = await self.session.execute(stmt)
            rooms = result.scalars().all()

            result_list = []
            for room in rooms:
                room_data = {
                    "id": room.id,
                    "building_id": room.building_id,
                    # FIXED: Include building information
                    "building_name": (
                        room.building.name if room.building is not None else None
                    ),
                    "building_code": (
                        room.building.code if room.building is not None else None
                    ),
                    "room_type_id": (
                        room.room_type_id if room.room_type_id is not None else None
                    ),
                    "room_type_name": (
                        room.room_type.name if room.room_type is not None else None
                    ),
                    "code": room.code,
                    "name": room.name,
                    "capacity": room.capacity,
                    "exam_capacity": room.exam_capacity or room.capacity,
                    "floor_number": room.floor_number,
                    "has_projector": room.has_projector,
                    "has_ac": room.has_ac,
                    "has_computers": room.has_computers,
                    "accessibility_features": room.accessibility_features or "",
                    "overbookable": room.overbookable,
                    "max_inv_per_room": room.max_inv_per_room,
                    # FIXED: Keep field name as adjacency_pairs (will be handled in data prep service)
                    "adjacency_pairs": room.adjacency_pairs,
                    "is_active": room.is_active,
                    "notes": room.notes,
                }
                result_list.append(room_data)

            logger.debug(f"Retrieved {len(result_list)} active rooms")
            return result_list

        except Exception as e:
            logger.error(f"Error retrieving rooms: {str(e)}")
            raise

    async def get_available_staff(self) -> List[Dict]:
        """FIXED - Get all staff who can invigilate with user information"""
        logger.debug("Retrieving available staff who can invigilate")

        try:
            # FIXED: Include user information for name and email
            stmt = (
                select(Staff)
                .options(
                    selectinload(Staff.department),
                    selectinload(Staff.user),  # FIXED: Include user relationship
                )
                .where(and_(Staff.is_active, Staff.can_invigilate))
            )

            result = await self.session.execute(stmt)
            staff = result.scalars().all()

            result_list = []
            for s in staff:
                staff_data = {
                    "id": s.id,
                    "staff_number": s.staff_number,
                    # FIXED: Get name and email from user relationship
                    "name": (
                        f"{s.user.first_name} {s.user.last_name}".strip()
                        if s.user
                        else f"Staff {s.staff_number}"
                    ),
                    "email": (
                        s.user.email if s.user else f"{s.staff_number}@university.edu"
                    ),
                    "staff_type": s.staff_type,
                    "position": s.position,
                    "department_id": s.department_id if s.department_id else None,
                    # FIXED: Include department name
                    "department_name": s.department.name if s.department else None,
                    "can_invigilate": s.can_invigilate,
                    "max_daily_sessions": s.max_daily_sessions,
                    "max_consecutive_sessions": s.max_consecutive_sessions,
                    "user_id": s.user_id if s.user_id else None,
                    "is_active": s.is_active,
                }
                result_list.append(staff_data)

            logger.debug(f"Retrieved {len(result_list)} available staff")
            return result_list

        except Exception as e:
            logger.error(f"Error retrieving available staff: {str(e)}")
            raise

    async def get_staff_unavailability(self, session_id: UUID) -> List[Dict]:
        """Get staff unavailability for the session"""
        logger.debug(f"Retrieving staff unavailability for session {session_id}")

        try:
            stmt = (
                select(StaffUnavailability)
                .options(
                    selectinload(StaffUnavailability.staff),
                    selectinload(StaffUnavailability.time_slot),
                )
                .where(StaffUnavailability.session_id == session_id)
            )

            result = await self.session.execute(stmt)
            unavailabilities = result.scalars().all()

            result_list = [
                {
                    "id": u.id,
                    "staff_id": u.staff_id,
                    "staff_number": u.staff.staff_number if u.staff else None,
                    "session_id": u.session_id,
                    "unavailable_date": (
                        cast(ddate, u.unavailable_date).isoformat()
                        if u.unavailable_date is not None
                        else None
                    ),
                    "timeslot_id": u.time_slot_id if u.time_slot_id else None,
                    "timeslot_name": u.time_slot.name if u.time_slot else None,
                    "reason": u.reason,
                }
                for u in unavailabilities
            ]

            logger.debug(
                f"Retrieved {len(result_list)} staff unavailability records for session {session_id}"
            )
            return result_list

        except Exception as e:
            logger.error(
                f"Error retrieving staff unavailability for session {session_id}: {str(e)}"
            )
            raise

    async def get_course_registrations(self, session_id: UUID) -> List[Dict]:
        """Get all course registrations for the session"""
        logger.debug(f"Retrieving course registrations for session {session_id}")

        try:
            stmt = (
                select(CourseRegistration)
                .options(
                    selectinload(CourseRegistration.student).selectinload(
                        Student.programme
                    ),
                    selectinload(CourseRegistration.course),
                )
                .where(CourseRegistration.session_id == session_id)
            )

            result = await self.session.execute(stmt)
            registrations = result.scalars().all()

            result_list = [
                {
                    "id": reg.id,
                    "student_id": reg.student_id,
                    "student_matric": reg.student.matric_number,
                    "student_level": reg.student.current_level,
                    "programme_id": reg.student.programme_id,
                    "programme_name": reg.student.programme.name,
                    "course_id": reg.course_id,
                    "course_code": reg.course.code,
                    "course_title": reg.course.title,
                    "session_id": reg.session_id,
                    "registration_type": reg.registration_type,
                    "registered_at": (
                        cast(ddatetime, reg.registered_at).isoformat()
                        if reg.registered_at is not None
                        else None
                    ),
                }
                for reg in registrations
            ]

            logger.debug(
                f"Retrieved {len(result_list)} course registrations for session {session_id}"
            )
            return result_list

        except Exception as e:
            logger.error(
                f"Error retrieving course registrations for session {session_id}: {str(e)}"
            )
            raise

    async def get_timetable_assignments(self, session_id: UUID) -> List[Dict]:
        """Get all timetable assignments for the session"""
        logger.debug(f"Retrieving timetable assignments for session {session_id}")

        try:
            stmt = (
                select(TimetableAssignment)
                .options(
                    selectinload(TimetableAssignment.exam).selectinload(Exam.course),
                    selectinload(TimetableAssignment.room),
                    selectinload(TimetableAssignment.time_slot),
                )
                .join(Exam)
                .where(Exam.session_id == session_id)
            )

            result = await self.session.execute(stmt)
            assignments = result.scalars().all()

            result_list = [
                {
                    "id": assignment.id,
                    "exam_id": assignment.exam_id,
                    "room_id": assignment.room_id,
                    "day": (
                        cast(ddate, assignment.day).isoformat()
                        if assignment.day
                        else None
                    ),
                    "timeslot_id": assignment.time_slot_id,
                    "student_count": assignment.student_count,
                    "is_confirmed": assignment.is_confirmed,
                    "exam_code": (
                        assignment.exam.course.code
                        if assignment.exam and assignment.exam.course
                        else None
                    ),
                    "room_code": assignment.room.code if assignment.room else None,
                    "timeslot_name": (
                        assignment.time_slot.name if assignment.time_slot else None
                    ),
                }
                for assignment in assignments
            ]

            logger.debug(
                f"Retrieved {len(result_list)} timetable assignments for session {session_id}"
            )
            return result_list

        except Exception as e:
            logger.error(
                f"Error retrieving timetable assignments for session {session_id}: {str(e)}"
            )
            raise

    # Additional helper methods remain the same...
    async def get_courses_with_registrations(self, session_id: UUID) -> List[Dict]:
        """Get courses with their registration counts for a session"""
        logger.info(
            f"Retrieving courses with registration counts for session {session_id}"
        )

        try:
            stmt = (
                select(
                    Course.id,
                    Course.code,
                    Course.title,
                    Course.credit_units,
                    Course.course_level,
                    Course.is_practical,
                    Course.morning_only,
                    Course.exam_duration_minutes,
                    func.count(CourseRegistration.student_id).label("student_count"),
                )
                .join(CourseRegistration, CourseRegistration.course_id == Course.id)
                .where(CourseRegistration.session_id == session_id)
                .group_by(Course.id)
            )

            result = await self.session.execute(stmt)
            courses = result.all()

            result_list = [
                {
                    "id": course.id,
                    "code": course.code,
                    "title": course.title,
                    "credit_units": course.credit_units,
                    "course_level": course.course_level,
                    "is_practical": course.is_practical,
                    "morning_only": course.morning_only,
                    "exam_duration_minutes": course.exam_duration_minutes,
                    "student_count": course.student_count,
                }
                for course in courses
            ]

            logger.info(
                f"Retrieved {len(result_list)} courses with registration counts for session {session_id}"
            )
            return result_list

        except Exception as e:
            logger.error(
                f"Error retrieving courses with registrations for session {session_id}: {str(e)}"
            )
            raise

    async def get_students_for_session(self, session_id: UUID) -> List[Dict]:
        """Get all students registered for courses in the session"""
        logger.info(f"Retrieving students for session {session_id}")

        try:
            stmt = (
                select(Student)
                .options(
                    selectinload(Student.programme).selectinload(Programme.department)
                )
                .join(CourseRegistration, CourseRegistration.student_id == Student.id)
                .where(CourseRegistration.session_id == session_id)
                .distinct()
            )

            result = await self.session.execute(stmt)
            students = result.scalars().all()

            result_list = [
                {
                    "id": student.id,
                    "matric_number": student.matric_number,
                    "programme_id": student.programme_id,
                    "programme_name": student.programme.name,
                    "department_name": (
                        student.programme.department.name
                        if student.programme and student.programme.department
                        else None
                    ),
                    "current_level": student.current_level,
                    "entry_year": student.entry_year,
                    "student_type": student.student_type,
                    "special_needs": student.special_needs or "",
                    "is_active": student.is_active,
                }
                for student in students
            ]

            logger.info(
                f"Retrieved {len(result_list)} students for session {session_id}"
            )
            return result_list

        except Exception as e:
            logger.error(
                f"Error retrieving students for session {session_id}: {str(e)}"
            )
            raise
