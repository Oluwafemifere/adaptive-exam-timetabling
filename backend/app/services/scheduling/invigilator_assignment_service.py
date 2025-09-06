# backend/app/services/scheduling/invigilator_assignment_service.py

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple, DefaultDict
from uuid import UUID
from dataclasses import dataclass, field
from collections import defaultdict
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from ...services.data_retrieval import SchedulingData, AcademicData, UserData

logger = logging.getLogger(__name__)


@dataclass
class InvigilationAssignment:
    exam_id: UUID
    staff_ids: List[UUID] = field(default_factory=list)  # ordered: first may be chief
    room_ids: List[UUID] = field(default_factory=list)


class InvigilatorAssignmentService:
    """
    Assigns invigilators to exams subject to availability, departmental context,
    max_daily_sessions, and max_consecutive_sessions.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.scheduling_data = SchedulingData(session)
        self.academic_data = AcademicData(session)
        self.user_data = UserData(session)

    async def assign_invigilators(
        self,
        session_id: UUID,
        min_per_room: int = 1,
        chief_per_exam: bool = True,
    ) -> List[InvigilationAssignment]:
        data = await self.scheduling_data.get_scheduling_data_for_session(session_id)
        exams = list(data.get("exams", [])) if data.get("exams") else []
        rooms_by_exam: Dict[str, List[str]] = {
            e["id"]: [
                ra["room_id"]
                for ra in e.get("room_assignments", [])
                if ra.get("room_id")
            ]
            for e in exams
        }
        staff = list(data.get("staff", [])) if data.get("staff") else []
        unavailability = (
            list(data.get("staff_unavailability", []))
            if data.get("staff_unavailability")
            else []
        )

        # Build unavailability maps: (staff_id, date, time_slot) -> True
        unavailable_map: Dict[Tuple[str, str, Optional[str]], bool] = {}
        for ua in unavailability:
            unavailable_map[
                (ua["staff_id"], ua.get("unavailable_date"), ua.get("time_slot_id"))
            ] = True

        # Track per-staff counts: day -> sessions count and last slot for consecutive checks
        daily_count: DefaultDict[Tuple[str, str], int] = defaultdict(int)
        last_slot: Dict[Tuple[str, str], Optional[str]] = {}

        # Index staff by department for soft matching with exam's department
        staff_by_dept: DefaultDict[Optional[str], List[Dict[str, Any]]] = defaultdict(
            list
        )
        for s in staff:
            staff_by_dept[s.get("department_id")].append(s)

        assignments: List[InvigilationAssignment] = []

        for e in exams:
            eid = e.get("id")
            if not eid:
                continue
            exam_rooms = rooms_by_exam.get(eid, [])
            if not exam_rooms:
                # No rooms allocated yet; skip for now
                assignments.append(
                    InvigilationAssignment(exam_id=UUID(eid), staff_ids=[], room_ids=[])
                )
                continue

            need = len(exam_rooms) * max(min_per_room, 1)
            # If chief invigilator requested, add one to total
            total_needed = need + (1 if chief_per_exam else 0)

            # Candidate staff: matching dept if possible, else any active invigilator-capable
            candidates = staff_by_dept.get(e.get("department_id")) or staff
            chosen: List[UUID] = []

            for cand in candidates:
                if len(chosen) >= total_needed:
                    break
                if not bool(cand.get("is_active", True)) or not bool(
                    cand.get("can_invigilate", False)
                ):
                    continue
                sid = cand.get("id")
                if not sid:
                    continue

                # Date/slot availability checks
                exam_date = e.get("exam_date")
                slot_id = e.get("time_slot_id")
                if unavailable_map.get(
                    (sid, exam_date, slot_id)
                ) or unavailable_map.get((sid, exam_date, None)):
                    continue

                # Daily limits
                max_daily = int(cand.get("max_daily_sessions") or 2)
                key = (sid, str(exam_date))
                if daily_count[key] >= max_daily:
                    continue

                # Consecutive sessions: avoid same staff in back-to-back slots if exceeding limit
                max_consec = int(cand.get("max_consecutive_sessions") or 2)
                prev_slot = last_slot.get(key)
                if prev_slot == slot_id and max_consec <= 1:
                    continue  # cannot handle consecutive if policy forbids
                # Accept staff
                chosen.append(UUID(sid))
                daily_count[key] += 1
                last_slot[key] = slot_id

            # If selected fewer than needed, leave partial assignment; orchestrator may fill later
            assignments.append(
                InvigilationAssignment(
                    exam_id=UUID(eid),
                    staff_ids=chosen,
                    room_ids=[UUID(r) for r in exam_rooms if r],
                )
            )

        return assignments

    async def build_notification_payloads(
        self,
        assignments: List[InvigilationAssignment],
        message_prefix: str = "Invigilation Assignment",
    ) -> List[Dict[str, Any]]:
        """
        Returns message payloads to be pushed to a notification system, decoupled
        from persistence to allow audit-friendly pipelines.
        """
        payloads: List[Dict[str, Any]] = []
        for asg in assignments:
            for sid in asg.staff_ids:
                payloads.append(
                    {
                        "user_id": str(sid),
                        "title": message_prefix,
                        "message": f"You have been assigned to invigilate exam {asg.exam_id}",
                        "priority": "medium",
                        "entity_type": "exam",
                        "entity_id": str(asg.exam_id),
                    }
                )
        return payloads
