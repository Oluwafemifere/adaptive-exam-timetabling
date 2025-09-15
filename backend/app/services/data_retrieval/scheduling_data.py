# backend/app/services/data_retrieval/scheduling_data.py

"""
Service for retrieving scheduling data from the database and preparing it
for the scheduling engine
"""

from typing import List, Dict, cast, Optional
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
)


class SchedulingData:
    """Service for retrieving all data needed for scheduling"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_scheduling_data_for_session(self, session_id: UUID) -> Dict:
        """
        Retrieves all data needed for scheduling a specific academic session
        """
        exams = await self._get_exams_for_session(session_id)
        time_slots = await self._get_time_slots()
        rooms = await self._get_rooms()
        staff = await self._get_available_staff()
        staff_unavailability = await self._get_staff_unavailability(session_id)
        course_registrations = await self._get_course_registrations(session_id)
        timetable_assignments = await self._get_timetable_assignments(session_id)

        return {
            "session_id": str(session_id),
            "exams": exams,
            "time_slots": time_slots,
            "rooms": rooms,
            "staff": staff,
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

    async def _get_exams_for_session(self, session_id: UUID) -> List[Dict]:
        """Get all exams for a specific session with course details"""
        stmt = (
            select(Exam)
            .options(
                selectinload(Exam.course).selectinload(Course.department),
                selectinload(Exam.exam_rooms).selectinload(ExamRoom.room),
                selectinload(Exam.exam_departments).selectinload(
                    ExamDepartment.department
                ),
                selectinload(Exam.invigilators),
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
            room_assignments = [
                {
                    "room_id": str(er.room_id),
                    "allocated_capacity": er.allocated_capacity,
                    "is_primary": er.is_primary,
                }
                for er in exam.exam_rooms
            ]

            department_assignments = [
                {
                    "department_id": str(ed.department_id),
                    "department_name": ed.department.name if ed.department else None,
                }
                for ed in exam.exam_departments
            ]

            invigilator_assignments = [
                {
                    "staff_id": str(inv.staff_id),
                    "room_id": str(inv.room_id),
                    "time_slot_id": str(inv.time_slot_id) if inv.time_slot_id else None,
                    "is_chief_invigilator": inv.is_chief_invigilator,
                    "assigned_at": (
                        cast(ddatetime, inv.assigned_at).isoformat()
                        if inv.assigned_at
                        else None
                    ),
                }
                for inv in exam.invigilators
            ]

            timetable_assignments = [
                {
                    "assignment_id": str(ta.id),
                    "room_id": str(ta.room_id),
                    "day": cast(ddate, ta.day).isoformat() if ta.day else None,
                    "time_slot_id": str(ta.time_slot_id),
                    "student_count": ta.student_count,
                    "is_confirmed": ta.is_confirmed,
                }
                for ta in exam.timetable_assignments
            ]

            exam_data = {
                "id": str(exam.id),
                "course_id": str(exam.course_id),
                "course_code": exam.course.code,
                "course_title": exam.course.title,
                "department_name": exam.course.department.name,
                "session_id": str(exam.session_id),
                "time_slot_id": str(exam.time_slot_id) if exam.time_slot_id else None,
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
                "course_level": exam.course.course_level,
                "course_is_practical": exam.course.is_practical,
                "morning_only": exam.course.morning_only,
            }

            exam_list.append(exam_data)

        return exam_list

    async def _get_time_slots(self) -> List[Dict]:
        """Get all active time slots"""
        stmt = select(TimeSlot).where(TimeSlot.is_active)
        result = await self.session.execute(stmt)
        time_slots = result.scalars().all()

        return [
            {
                "id": str(ts.id),
                "name": ts.name,
                "start_time": (
                    cast(dtime, ts.start_time).strftime("%H:%M")
                    if ts.start_time is not None
                    else None
                ),
                "end_time": (
                    cast(dtime, ts.end_time).strftime("%H:%M")
                    if ts.end_time is not None
                    else None
                ),
                "duration_minutes": ts.duration_minutes,
                "is_active": ts.is_active,
            }
            for ts in time_slots
        ]

    async def _get_rooms(self) -> List[Dict]:
        """Get all active rooms with building and type information"""
        stmt = (
            select(Room)
            .options(selectinload(Room.building), selectinload(Room.room_type))
            .where(Room.is_active)
        )

        result = await self.session.execute(stmt)
        rooms = result.scalars().all()

        return [
            {
                "id": str(room.id),
                "building_id": str(room.building_id),
                "building_name": (
                    room.building.name if room.building is not None else None
                ),
                "building_code": (
                    room.building.code if room.building is not None else None
                ),
                "room_type_id": (
                    str(room.room_type_id) if room.room_type_id is not None else None
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
                "accessibility_features": room.accessibility_features or [],
                "overbookable": room.overbookable,
                "max_inv_per_room": room.max_inv_per_room,
                "adjacency_pairs": room.adjacency_pairs,
                "is_active": room.is_active,
                "notes": room.notes,
            }
            for room in rooms
        ]

    async def _get_available_staff(self) -> List[Dict]:
        """Get all staff who can invigilate"""
        stmt = (
            select(Staff)
            .options(selectinload(Staff.department))
            .where(and_(Staff.is_active, Staff.can_invigilate))
        )

        result = await self.session.execute(stmt)
        staff = result.scalars().all()

        return [
            {
                "id": str(s.id),
                "staff_number": s.staff_number,
                "staff_type": s.staff_type,
                "position": s.position,
                "department_id": str(s.department_id) if s.department_id else None,
                "department_name": s.department.name if s.department else None,
                "can_invigilate": s.can_invigilate,
                "max_daily_sessions": s.max_daily_sessions,
                "max_consecutive_sessions": s.max_consecutive_sessions,
                "user_id": str(s.user_id) if s.user_id else None,
                "is_active": s.is_active,
            }
            for s in staff
        ]

    async def _get_staff_unavailability(self, session_id: UUID) -> List[Dict]:
        """Get staff unavailability for the session"""
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

        return [
            {
                "id": str(u.id),
                "staff_id": str(u.staff_id),
                "staff_number": u.staff.staff_number if u.staff else None,
                "session_id": str(u.session_id),
                "unavailable_date": (
                    cast(ddate, u.unavailable_date).isoformat()
                    if u.unavailable_date is not None
                    else None
                ),
                "time_slot_id": str(u.time_slot_id) if u.time_slot_id else None,
                "time_slot_name": u.time_slot.name if u.time_slot else None,
                "reason": u.reason,
            }
            for u in unavailabilities
        ]

    async def _get_course_registrations(self, session_id: UUID) -> List[Dict]:
        """Get all course registrations for the session"""
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

        return [
            {
                "id": str(reg.id),
                "student_id": str(reg.student_id),
                "student_matric": reg.student.matric_number,
                "student_level": reg.student.current_level,
                "programme_id": str(reg.student.programme_id),
                "programme_name": reg.student.programme.name,
                "course_id": str(reg.course_id),
                "course_code": reg.course.code,
                "course_title": reg.course.title,
                "session_id": str(reg.session_id),
                "registration_type": reg.registration_type,
                "registered_at": (
                    cast(ddatetime, reg.registered_at).isoformat()
                    if reg.registered_at is not None
                    else None
                ),
            }
            for reg in registrations
        ]

    async def _get_timetable_assignments(self, session_id: UUID) -> List[Dict]:
        """Get all timetable assignments for the session"""
        stmt = (
            select(TimetableAssignment)
            .options(
                selectinload(TimetableAssignment.exam),
                selectinload(TimetableAssignment.room),
                selectinload(TimetableAssignment.time_slot),
            )
            .join(Exam, TimetableAssignment.exam_id == Exam.id)
            .where(Exam.session_id == session_id)
        )

        result = await self.session.execute(stmt)
        assignments = result.scalars().all()

        return [
            {
                "id": str(assignment.id),
                "exam_id": str(assignment.exam_id),
                "room_id": str(assignment.room_id),
                "day": (
                    cast(ddate, assignment.day).isoformat() if assignment.day else None
                ),
                "time_slot_id": str(assignment.time_slot_id),
                "student_count": assignment.student_count,
                "is_confirmed": assignment.is_confirmed,
                "exam_code": (
                    assignment.exam.course.code
                    if assignment.exam and assignment.exam.course
                    else None
                ),
                "room_code": assignment.room.code if assignment.room else None,
                "time_slot_name": (
                    assignment.time_slot.name if assignment.time_slot else None
                ),
            }
            for assignment in assignments
        ]

    async def get_courses_with_registrations(self, session_id: UUID) -> List[Dict]:
        """Get courses with their registration counts for a session"""
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

        return [
            {
                "id": str(course.id),
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

    async def get_students_for_session(self, session_id: UUID) -> List[Dict]:
        """Get all students registered for courses in the session"""
        stmt = (
            select(Student)
            .options(selectinload(Student.programme).selectinload(Programme.department))
            .join(CourseRegistration, CourseRegistration.student_id == Student.id)
            .where(CourseRegistration.session_id == session_id)
            .distinct()
        )

        result = await self.session.execute(stmt)
        students = result.scalars().all()

        return [
            {
                "id": str(student.id),
                "matric_number": student.matric_number,
                "programme_id": str(student.programme_id),
                "programme_name": student.programme.name,
                "department_name": (
                    student.programme.department.name
                    if student.programme and student.programme.department
                    else None
                ),
                "current_level": student.current_level,
                "entry_year": student.entry_year,
                "student_type": student.student_type,
                "special_needs": student.special_needs or [],
                "is_active": student.is_active,
            }
            for student in students
        ]

    # Exam Invigilators methods
    async def get_exam_invigilators(
        self, exam_id: Optional[UUID] = None, staff_id: Optional[UUID] = None
    ) -> List[Dict]:
        """Get exam invigilator assignments with filters"""
        stmt = select(ExamInvigilator).options(
            selectinload(ExamInvigilator.exam),
            selectinload(ExamInvigilator.staff),
            selectinload(ExamInvigilator.room),
            selectinload(ExamInvigilator.time_slot),
        )

        if exam_id is not None:
            stmt = stmt.where(ExamInvigilator.exam_id == exam_id)
        if staff_id is not None:
            stmt = stmt.where(ExamInvigilator.staff_id == staff_id)

        result = await self.session.execute(stmt)
        invigilators = result.scalars().all()

        return [
            {
                "id": str(inv.id),
                "exam_id": str(inv.exam_id),
                "staff_id": str(inv.staff_id),
                "room_id": str(inv.room_id),
                "time_slot_id": str(inv.time_slot_id) if inv.time_slot_id else None,
                "staff_number": inv.staff.staff_number if inv.staff else None,
                "room_code": inv.room.code if inv.room else None,
                "time_slot_name": inv.time_slot.name if inv.time_slot else None,
                "is_chief_invigilator": inv.is_chief_invigilator,
                "assigned_at": (
                    cast(ddatetime, inv.assigned_at).isoformat()
                    if inv.assigned_at
                    else None
                ),
            }
            for inv in invigilators
        ]

    # Timetable Assignments methods
    async def get_timetable_assignments_by_filters(
        self,
        exam_id: Optional[UUID] = None,
        room_id: Optional[UUID] = None,
        time_slot_id: Optional[UUID] = None,
        day: Optional[ddate] = None,
        is_confirmed: Optional[bool] = None,
    ) -> List[Dict]:
        """Get timetable assignments with various filters"""
        stmt = select(TimetableAssignment).options(
            selectinload(TimetableAssignment.exam),
            selectinload(TimetableAssignment.room),
            selectinload(TimetableAssignment.time_slot),
        )

        if exam_id is not None:
            stmt = stmt.where(TimetableAssignment.exam_id == exam_id)
        if room_id is not None:
            stmt = stmt.where(TimetableAssignment.room_id == room_id)
        if time_slot_id is not None:
            stmt = stmt.where(TimetableAssignment.time_slot_id == time_slot_id)
        if day is not None:
            stmt = stmt.where(TimetableAssignment.day == day)
        if is_confirmed is not None:
            stmt = stmt.where(TimetableAssignment.is_confirmed == is_confirmed)

        result = await self.session.execute(stmt)
        assignments = result.scalars().all()

        return [
            {
                "id": str(assignment.id),
                "exam_id": str(assignment.exam_id),
                "room_id": str(assignment.room_id),
                "day": (
                    cast(ddate, assignment.day).isoformat() if assignment.day else None
                ),
                "time_slot_id": str(assignment.time_slot_id),
                "student_count": assignment.student_count,
                "is_confirmed": assignment.is_confirmed,
                "exam_code": (
                    assignment.exam.course.code
                    if assignment.exam and assignment.exam.course
                    else None
                ),
                "room_code": assignment.room.code if assignment.room else None,
                "time_slot_name": (
                    assignment.time_slot.name if assignment.time_slot else None
                ),
            }
            for assignment in assignments
        ]

    # Exam Department methods
    async def get_exam_departments(
        self, exam_id: Optional[UUID] = None, department_id: Optional[UUID] = None
    ) -> List[Dict]:
        """Get exam department associations with filters"""
        stmt = select(ExamDepartment).options(
            selectinload(ExamDepartment.exam),
            selectinload(ExamDepartment.department),
        )

        if exam_id is not None:
            stmt = stmt.where(ExamDepartment.exam_id == exam_id)
        if department_id is not None:
            stmt = stmt.where(ExamDepartment.department_id == department_id)

        result = await self.session.execute(stmt)
        exam_departments = result.scalars().all()

        return [
            {
                "id": str(ed.id),
                "exam_id": str(ed.exam_id),
                "department_id": str(ed.department_id),
                "department_name": ed.department.name if ed.department else None,
                "exam_code": (
                    ed.exam.course.code if ed.exam and ed.exam.course else None
                ),
                "created_at": (
                    cast(ddatetime, ed.created_at).isoformat()
                    if ed.created_at
                    else None
                ),
                "updated_at": (
                    cast(ddatetime, ed.updated_at).isoformat()
                    if ed.updated_at
                    else None
                ),
            }
            for ed in exam_departments
        ]
