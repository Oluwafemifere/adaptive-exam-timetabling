# backend/app/services/scheduling/data_preparation_service.py

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple, Any, DefaultDict
from uuid import UUID
from dataclasses import dataclass, field
from collections import defaultdict
import logging

from sqlalchemy.ext.asyncio import AsyncSession

# Retrieval services
from app.services.data_retrieval import (
    SchedulingData,
    AcademicData,
    InfrastructureData,
    FileUploadData,
    ConflictAnalysis,
)

# Helpers
from app.services.data_retrieval.helpers import iso_date_range

logger = logging.getLogger(__name__)


@dataclass
class PreparedDataset:
    session_id: UUID
    exams: List[Dict[str, Any]] = field(default_factory=list)
    time_slots: List[Dict[str, Any]] = field(default_factory=list)
    rooms: List[Dict[str, Any]] = field(default_factory=list)
    staff: List[Dict[str, Any]] = field(default_factory=list)
    staff_unavailability: List[Dict[str, Any]] = field(default_factory=list)
    course_registrations: List[Dict[str, Any]] = field(default_factory=list)
    indices: Dict[str, Any] = field(default_factory=dict)
    validations: Dict[str, Any] = field(default_factory=dict)


class DataPreparationService:
    """
    Gathers, validates, normalizes, and indexes all data necessary to run an
    exam timetable generation for a specific academic session.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.scheduling_data = SchedulingData(session)
        self.academic_data = AcademicData(session)
        self.infrastructure_data = InfrastructureData(session)
        self.file_upload_data = FileUploadData(session)
        self.conflict_analysis = ConflictAnalysis(session)

    async def build_dataset(self, session_id: UUID) -> PreparedDataset:
        data = await self.scheduling_data.get_scheduling_data_for_session(session_id)
        exams = list(data.get("exams", [])) if data.get("exams") else []
        time_slots = list(data.get("time_slots", [])) if data.get("time_slots") else []
        rooms = list(data.get("rooms", [])) if data.get("rooms") else []
        staff = list(data.get("staff", [])) if data.get("staff") else []
        unavailability = (
            list(data.get("staff_unavailability", []))
            if data.get("staff_unavailability")
            else []
        )
        registrations = (
            list(data.get("course_registrations", []))
            if data.get("course_registrations")
            else []
        )

        # Validate and normalize
        validations = await self._validate_integrity(
            session_id=session_id,
            exams=exams,
            rooms=rooms,
            time_slots=time_slots,
            staff=staff,
            registrations=registrations,
        )
        registrations = self._deduplicate_registrations(registrations)
        indices = self._build_indices(exams, rooms, staff, time_slots, registrations)

        return PreparedDataset(
            session_id=session_id,
            exams=exams,
            time_slots=time_slots,
            rooms=rooms,
            staff=staff,
            staff_unavailability=unavailability,
            course_registrations=registrations,
            indices=indices,
            validations=validations,
        )

    async def _validate_integrity(
        self,
        session_id: UUID,
        exams: List[Dict[str, Any]],
        rooms: List[Dict[str, Any]],
        time_slots: List[Dict[str, Any]],
        staff: List[Dict[str, Any]],
        registrations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        issues: Dict[str, Any] = {"errors": [], "warnings": [], "metrics": {}}

        # Referential checks: all exam course_ids and session_ids exist
        course_ids_in_exams: Set[str] = {
            e["course_id"] for e in exams if e.get("course_id")
        }
        dept_program_checks = await self.academic_data.get_all_departments()
        if not dept_program_checks:
            issues["warnings"].append(
                "No departments found; verify academic seed data"
            )  # warn only

        # Timeslot sanity: duration, start < end, etc.
        for ts in time_slots:
            start = ts.get("start_time")
            end = ts.get("end_time")
            duration = ts.get("duration_minutes") or 0
            if not start or not end or duration <= 0:
                issues["errors"].append(
                    f"Invalid time slot definition: {ts.get('id') or 'unknown'}"
                )

        # Room capacity sanity
        for r in rooms:
            cap = r.get("capacity") or 0
            exam_cap = r.get("exam_capacity") or cap
            if cap <= 0 or exam_cap <= 0:
                issues["errors"].append(
                    f"Invalid room capacity for room {r.get('id') or r.get('code') or 'unknown'}"
                )

        # Conflict metrics: high-level student “same-session” multi-registrations (informational)
        try:
            conflicts = await self.conflict_analysis.get_student_conflicts(
                str(session_id)
            )
            issues["metrics"]["multi_course_students"] = len(conflicts)
        except Exception as exc:
            logger.warning("ConflictAnalysis failed: %s", exc)
            issues["warnings"].append(
                "ConflictAnalysis failed; proceeding with defaults"
            )

        # Registration course references
        reg_missing = 0
        course_ids_from_reg: Set[str] = {
            reg["course_id"] for reg in registrations if reg.get("course_id")
        }
        for cid in course_ids_from_reg:
            if cid not in course_ids_in_exams:
                reg_missing += 1
        if reg_missing > 0:
            issues["warnings"].append(
                f"{reg_missing} registration records reference courses without scheduled exams"
            )

        return issues

    def _deduplicate_registrations(
        self, registrations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        seen: Set[Tuple[str, str]] = set()
        unique: List[Dict[str, Any]] = []
        for reg in registrations:
            key = (str(reg.get("student_id")), str(reg.get("course_id")))
            if key not in seen:
                seen.add(key)
                unique.append(reg)
        return unique

    def _build_indices(
        self,
        exams: List[Dict[str, Any]],
        rooms: List[Dict[str, Any]],
        staff: List[Dict[str, Any]],
        time_slots: List[Dict[str, Any]],
        registrations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        by_course: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
        by_room: Dict[str, Dict[str, Any]] = {}
        by_staff: Dict[str, Dict[str, Any]] = {}
        by_timeslot: Dict[str, Dict[str, Any]] = {}
        student_to_courses: DefaultDict[str, Set[str]] = defaultdict(set)

        for e in exams:
            cid = e.get("course_id")
            if cid:
                by_course[cid].append(e)

        for r in rooms:
            rid = r.get("id")
            if rid:
                by_room[rid] = r

        for s in staff:
            sid = s.get("id")
            if sid:
                by_staff[sid] = s

        for ts in time_slots:
            tsid = ts.get("id")
            if tsid:
                by_timeslot[tsid] = ts

        for reg in registrations:
            if reg.get("student_id") and reg.get("course_id"):
                student_to_courses[reg["student_id"]].add(reg["course_id"])

        return {
            "exams_by_course": by_course,
            "rooms_by_id": by_room,
            "staff_by_id": by_staff,
            "timeslots_by_id": by_timeslot,
            "student_to_courses": student_to_courses,
        }
