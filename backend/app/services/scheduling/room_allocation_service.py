# backend/app/services/scheduling/room_allocation_service.py

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from dataclasses import dataclass, field
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from ...services.data_retrieval import (
    SchedulingData,
    InfrastructureData,
    ConstraintData,
)

logger = logging.getLogger(__name__)


@dataclass
class RoomAssignmentProposal:
    exam_id: UUID
    rooms: List[Dict[str, Any]] = field(
        default_factory=list
    )  # [{room_id, allocated_capacity, is_primary}]


class RoomAllocationService:
    """
    Capacity-aware room allocation helper that produces feasible room sets per exam
    under basic temporal constraints and room feature requirements.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.scheduling_data = SchedulingData(session)
        self.infrastructure_data = InfrastructureData(session)
        self.constraint_data = ConstraintData(session)

    async def plan_room_allocations(
        self,
        session_id: UUID,
        prefer_single_room: bool = True,
        respect_practical_rooms: bool = True,
    ) -> List[RoomAssignmentProposal]:
        data = await self.scheduling_data.get_scheduling_data_for_session(session_id)
        exams = list(data.get("exams", [])) if data.get("exams") else []
        rooms = list(data.get("rooms", [])) if data.get("rooms") else []
        time_slots = {}
        for ts in data.get("time_slots", []):
            if isinstance(ts, dict) and ts.get("id"):
                time_slots[ts["id"]] = ts

        # Sort rooms by descending exam capacity to try to fit in fewer rooms
        sorted_rooms = sorted(
            rooms,
            key=lambda r: (r.get("exam_capacity") or r.get("capacity") or 0),
            reverse=True,
        )

        proposals: List[RoomAssignmentProposal] = []
        occupied: Dict[Tuple[str, str], UUID] = {}  # (room_id, date_key) -> exam_id

        for exam in exams:
            needed = int(exam.get("expected_students") or 0)
            if needed <= 0:
                proposals.append(
                    RoomAssignmentProposal(exam_id=UUID(exam["id"]), rooms=[])
                )
                continue

            # Filter rooms by basic features (practical, projector, etc.) if requested
            candidate_rooms = [
                r for r in sorted_rooms if bool(r.get("is_active", True))
            ]
            if respect_practical_rooms and bool(exam.get("is_practical", False)):
                candidate_rooms = [
                    r for r in candidate_rooms if bool(r.get("has_computers", False))
                ]

            # Temporal key to avoid double-booking: per date + time slot
            date_key = (
                f"{exam.get('exam_date') or 'NA'}::{exam.get('time_slot_id') or 'NA'}"
            )

            chosen: List[Dict[str, Any]] = []
            remaining = needed

            # Try to use one room if possible
            if prefer_single_room:
                for r in candidate_rooms:
                    rid = r.get("id")
                    cap = int(r.get("exam_capacity") or r.get("capacity") or 0)
                    if not rid or cap <= 0:
                        continue
                    if (rid, date_key) in occupied:
                        continue
                    # Morning-only course guard: ensure slot starts in AM if required
                    if bool(exam.get("morning_only", False)) and exam.get(
                        "time_slot_id"
                    ):
                        ts = time_slots.get(exam["time_slot_id"])
                        if (
                            not ts
                            or not ts.get("start_time")
                            or str(ts["start_time"]) >= "12:00"
                        ):
                            continue
                    if cap >= remaining:
                        chosen.append(
                            {
                                "room_id": rid,
                                "allocated_capacity": remaining,
                                "is_primary": True,
                            }
                        )
                        remaining = 0
                        occupied[(rid, date_key)] = UUID(exam["id"])
                        break

            # If still remaining, pack multiple rooms
            if remaining > 0:
                for r in candidate_rooms:
                    if remaining <= 0:
                        break
                    rid = r.get("id")
                    cap = int(r.get("exam_capacity") or r.get("capacity") or 0)
                    if not rid or cap <= 0:
                        continue
                    if (rid, date_key) in occupied:
                        continue
                    # morning-only guard
                    if bool(exam.get("morning_only", False)) and exam.get(
                        "time_slot_id"
                    ):
                        ts = time_slots.get(exam["time_slot_id"])
                        if (
                            not ts
                            or not ts.get("start_time")
                            or str(ts["start_time"]) >= "12:00"
                        ):
                            continue
                    alloc = min(cap, remaining)
                    if alloc <= 0:
                        continue
                    chosen.append(
                        {
                            "room_id": rid,
                            "allocated_capacity": alloc,
                            "is_primary": len(chosen) == 0,
                        }
                    )
                    remaining -= alloc
                    occupied[(rid, date_key)] = UUID(exam["id"])

            proposals.append(
                RoomAssignmentProposal(exam_id=UUID(exam["id"]), rooms=chosen)
            )

        return proposals

    async def validate_room_plan(
        self,
        proposals: List[RoomAssignmentProposal],
        session_id: UUID,
    ) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        # Build room-time occupancy map to detect double booking
        occupancy: Dict[Tuple[UUID, str], UUID] = {}
        data = await self.scheduling_data.get_scheduling_data_for_session(session_id)
        exams = {UUID(e["id"]): e for e in data.get("exams", []) if e.get("id")}
        rooms = {r.get("id"): r for r in data.get("rooms", []) if r.get("id")}

        for proposal in proposals:
            exam = exams.get(proposal.exam_id)
            if not exam:
                warnings.append(f"Exam not found for proposal {proposal.exam_id}")
                continue
            date_key = (
                f"{exam.get('exam_date') or 'NA'}::{exam.get('time_slot_id') or 'NA'}"
            )

            # capacity checks and occupancy checks
            total = 0
            for chunk in proposal.rooms:
                rid = chunk.get("room_id")
                alloc = int(chunk.get("allocated_capacity") or 0)
                if not rid or alloc <= 0:
                    errors.append(f"Invalid room allocation in exam {proposal.exam_id}")
                    continue
                room = rooms.get(rid)
                cap = (
                    int(room.get("exam_capacity") or room.get("capacity") or 0)
                    if room
                    else 0
                )
                if alloc > cap:
                    errors.append(
                        f"Allocated {alloc} exceeds room capacity {cap} for room {rid} in exam {proposal.exam_id}"
                    )
                if (UUID(rid), date_key) in occupancy:
                    errors.append(f"Room {rid} double-booked at {date_key}")
                else:
                    occupancy[(UUID(rid), date_key)] = proposal.exam_id
                total += alloc

            expected = int(exam.get("expected_students") or 0)
            if total < expected:
                warnings.append(
                    f"Exam {proposal.exam_id} capacity shortfall: {total} < {expected}"
                )

        return {"errors": errors, "warnings": warnings}
