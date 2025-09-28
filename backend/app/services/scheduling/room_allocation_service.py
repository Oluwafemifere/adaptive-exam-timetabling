# backend/app/services/scheduling/room_allocation_service.py

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from dataclasses import dataclass, field
import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

# Import tracking mixin
from ..tracking_mixin import TrackingMixin

from ...services.data_retrieval import (
    SchedulingData,
    InfrastructureData,
    ConstraintData,
)

logger = logging.getLogger(__name__)


def ensure_uuid(value: Any) -> UUID:
    """
    Safely convert value to UUID object, handling both string and UUID inputs.

    Fixes ERR-001: AttributeError: 'asyncpg.pgproto.pgproto.UUID' object has no attribute 'replace'

    Args:
        value: Input value that should be converted to UUID

    Returns:
        UUID object
    """
    if isinstance(value, UUID):
        return value  # Already a UUID, use directly
    elif isinstance(value, str):
        try:
            return UUID(value)  # Convert string to UUID
        except ValueError:
            logger.warning(f"Invalid UUID string '{value}', generating new UUID")
            return uuid.uuid4()  # Generate new UUID if invalid string
    else:
        logger.warning(f"Cannot convert {type(value)} to UUID, generating new UUID")
        return uuid.uuid4()  # Generate new UUID for other types


@dataclass
class RoomAssignmentProposal:
    exam_id: UUID
    proposal_id: UUID = field(default_factory=lambda: uuid.uuid4())  # Auto-generate ID
    rooms: List[Dict[str, Any]] = field(
        default_factory=list
    )  # [{room_id, allocated_capacity, is_primary}]
    allocation_metadata: Dict[str, Any] = field(default_factory=dict)  # For tracking


class RoomAllocationService(TrackingMixin):
    """
    Enhanced capacity-aware room allocation service with automatic session and action tracking.
    Produces feasible room sets per exam under basic temporal constraints and room feature requirements.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)
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
        """Plan room allocations with comprehensive tracking."""

        # Start main allocation action
        allocation_action = self._start_action(
            action_type="room_allocation_planning",
            description=f"Planning room allocations for session {session_id}",
            metadata={
                "session_id": str(session_id),
                "prefer_single_room": prefer_single_room,
                "respect_practical_rooms": respect_practical_rooms,
            },
        )

        try:
            await self._log_operation(
                "room_allocation_started",
                {
                    "session_id": str(session_id),
                    "planning_options": {
                        "prefer_single_room": prefer_single_room,
                        "respect_practical_rooms": respect_practical_rooms,
                    },
                },
            )

            # Data retrieval phase
            data_action = self._start_action(
                "data_retrieval", "Retrieving scheduling data"
            )

            data = await self.scheduling_data.get_scheduling_data_for_session(
                session_id
            )
            exams = list(data.get("exams", [])) if data.get("exams") else []
            rooms = list(data.get("rooms", [])) if data.get("rooms") else []

            time_slots = {}
            for ts in data.get("time_slots", []):
                if isinstance(ts, dict) and ts.get("id"):
                    time_slots[ts["id"]] = ts

            self._end_action(
                data_action,
                "completed",
                {
                    "exams_count": len(exams),
                    "rooms_count": len(rooms),
                    "time_slots_count": len(time_slots),
                },
            )

            # Room sorting phase
            sort_action = self._start_action(
                "room_sorting", "Sorting rooms by capacity"
            )

            # Sort rooms by descending exam capacity to try to fit in fewer rooms
            sorted_rooms = sorted(
                rooms,
                key=lambda r: (r.get("exam_capacity") or r.get("capacity") or 0),
                reverse=True,
            )

            self._end_action(sort_action, "completed")

            proposals: List[RoomAssignmentProposal] = []
            occupied: Dict[Tuple[str, str], UUID] = {}  # (room_id, date_key) -> exam_id

            # Process each exam
            for exam_idx, exam in enumerate(exams):
                exam_action = self._start_action(
                    "exam_processing",
                    f"Processing exam {exam.get('id', 'unknown')}",
                    metadata={"exam_index": exam_idx, "total_exams": len(exams)},
                )

                needed = int(exam.get("expected_students") or 0)

                # FIXED: Use ensure_uuid instead of direct UUID() conversion
                exam_id_value = exam.get("id")
                exam_id = ensure_uuid(exam_id_value) if exam_id_value else uuid.uuid4()

                if needed <= 0 or not exam_id_value:
                    proposal = RoomAssignmentProposal(
                        exam_id=exam_id,
                        rooms=[],
                        allocation_metadata={
                            "reason": "no_students_or_invalid_id",
                            "expected_students": needed,
                            "tracking_context": self._get_current_context(),
                        },
                    )
                    proposals.append(proposal)
                    self._end_action(
                        exam_action, "skipped", {"reason": "no_students_or_invalid_id"}
                    )
                    continue

                # Room filtering phase
                filter_action = self._start_action(
                    "room_filtering", "Filtering candidate rooms"
                )

                # Filter rooms by basic features (practical, projector, etc.) if requested
                candidate_rooms = [
                    r for r in sorted_rooms if bool(r.get("is_active", True))
                ]

                if respect_practical_rooms and bool(exam.get("is_practical", False)):
                    candidate_rooms = [
                        r
                        for r in candidate_rooms
                        if bool(r.get("has_computers", False))
                    ]

                self._end_action(
                    filter_action,
                    "completed",
                    {
                        "total_rooms": len(sorted_rooms),
                        "candidate_rooms": len(candidate_rooms),
                        "filtering_criteria": {
                            "is_practical": bool(exam.get("is_practical", False)),
                            "respect_practical_rooms": respect_practical_rooms,
                        },
                    },
                )

                # Temporal key to avoid double-booking: per date + time slot
                date_key = f"{exam.get('exam_date') or 'NA'}::{exam.get('time_slot_id') or 'NA'}"

                chosen: List[Dict[str, Any]] = []
                remaining = needed

                # Single room allocation attempt
                if prefer_single_room:
                    single_room_action = self._start_action(
                        "single_room_attempt", "Attempting single room allocation"
                    )

                    for r in candidate_rooms:
                        rid = r.get("id")
                        cap = int(r.get("exam_capacity") or r.get("capacity") or 0)

                        if not rid or cap <= 0:
                            continue
                        if (rid, date_key) in occupied:
                            continue

                        # Morning-only course guard
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
                                    "allocation_timestamp": datetime.utcnow().isoformat(),
                                }
                            )
                            remaining = 0
                            # FIXED: Use ensure_uuid for the occupancy mapping
                            occupied[(rid, date_key)] = ensure_uuid(exam["id"])
                            break

                    self._end_action(
                        single_room_action,
                        "completed",
                        {
                            "single_room_found": remaining == 0,
                            "remaining_capacity_needed": remaining,
                        },
                    )

                # Multi-room allocation if still needed
                if remaining > 0:
                    multi_room_action = self._start_action(
                        "multi_room_allocation", "Allocating multiple rooms"
                    )

                    rooms_allocated = 0
                    for r in candidate_rooms:
                        if remaining <= 0:
                            break

                        rid = r.get("id")
                        cap = int(r.get("exam_capacity") or r.get("capacity") or 0)

                        if not rid or cap <= 0:
                            continue
                        if (rid, date_key) in occupied:
                            continue

                        # Morning-only guard
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
                                "allocation_timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                        remaining -= alloc
                        # FIXED: Use ensure_uuid for the occupancy mapping
                        occupied[(rid, date_key)] = ensure_uuid(exam["id"])
                        rooms_allocated += 1

                    self._end_action(
                        multi_room_action,
                        "completed",
                        {
                            "rooms_allocated": rooms_allocated,
                            "final_remaining": remaining,
                        },
                    )

                # Create proposal with tracking metadata
                proposal = RoomAssignmentProposal(
                    # FIXED: Use ensure_uuid instead of direct UUID() conversion
                    exam_id=ensure_uuid(exam["id"]),
                    rooms=chosen,
                    allocation_metadata={
                        "original_capacity_needed": needed,
                        "final_remaining": remaining,
                        "fully_allocated": remaining == 0,
                        "rooms_used": len(chosen),
                        "allocation_strategy": (
                            "single_room" if len(chosen) <= 1 else "multi_room"
                        ),
                        "date_key": date_key,
                        "tracking_context": self._get_current_context(),
                    },
                )

                proposals.append(proposal)

                self._end_action(
                    exam_action,
                    "completed",
                    {"rooms_allocated": len(chosen), "capacity_shortage": remaining},
                )

            # Summary and completion
            total_proposals = len(proposals)
            fully_allocated = sum(
                1
                for p in proposals
                if p.allocation_metadata.get("fully_allocated", False)
            )

            self._end_action(
                allocation_action,
                "completed",
                {
                    "total_proposals": total_proposals,
                    "fully_allocated": fully_allocated,
                    "partially_allocated": total_proposals - fully_allocated,
                    "success_rate": (
                        (fully_allocated / total_proposals * 100)
                        if total_proposals > 0
                        else 0
                    ),
                },
            )

            await self._log_operation(
                "room_allocation_completed",
                {
                    "session_id": str(session_id),
                    "results_summary": {
                        "total_exams": len(exams),
                        "proposals_generated": total_proposals,
                        "fully_allocated": fully_allocated,
                        "success_rate": (
                            (fully_allocated / total_proposals * 100)
                            if total_proposals > 0
                            else 0
                        ),
                    },
                },
            )

            return proposals

        except Exception as exc:
            self._end_action(allocation_action, "failed", {"error": str(exc)})
            await self._log_operation(
                "room_allocation_failed", {"error": str(exc)}, "ERROR"
            )
            raise

    async def validate_room_plan(
        self,
        proposals: List[RoomAssignmentProposal],
        session_id: UUID,
    ) -> Dict[str, Any]:
        """Validate room allocation plan with comprehensive tracking."""

        validation_action = self._start_action(
            "room_plan_validation",
            f"Validating {len(proposals)} room proposals",
            metadata={"proposals_count": len(proposals)},
        )

        try:
            errors: List[str] = []
            warnings: List[str] = []

            # Data retrieval for validation
            data_action = self._start_action(
                "validation_data_retrieval", "Retrieving validation data"
            )

            # Build room-time occupancy map to detect double booking
            occupancy: Dict[Tuple[UUID, str], UUID] = {}
            data = await self.scheduling_data.get_scheduling_data_for_session(
                session_id
            )

            # FIXED: Use ensure_uuid for exam ID conversion
            exams = {
                ensure_uuid(e["id"]): e for e in data.get("exams", []) if e.get("id")
            }
            rooms = {r.get("id"): r for r in data.get("rooms", []) if r.get("id")}

            self._end_action(
                data_action,
                "completed",
                {"exams_loaded": len(exams), "rooms_loaded": len(rooms)},
            )

            # Validate each proposal
            for proposal_idx, proposal in enumerate(proposals):
                proposal_action = self._start_action(
                    "proposal_validation",
                    f"Validating proposal {proposal_idx + 1}",
                    metadata={"proposal_id": str(proposal.proposal_id)},
                )

                exam = exams.get(proposal.exam_id)
                if not exam:
                    warnings.append(f"Exam not found for proposal {proposal.exam_id}")
                    self._end_action(
                        proposal_action, "warning", {"issue": "exam_not_found"}
                    )
                    continue

                date_key = f"{exam.get('exam_date') or 'NA'}::{exam.get('time_slot_id') or 'NA'}"

                # Capacity and occupancy checks
                total = 0
                room_conflicts = []
                capacity_issues = []

                for chunk in proposal.rooms:
                    rid = chunk.get("room_id")
                    alloc = int(chunk.get("allocated_capacity") or 0)

                    if not rid or alloc <= 0:
                        errors.append(
                            f"Invalid room allocation in exam {proposal.exam_id}"
                        )
                        capacity_issues.append({"room_id": rid, "allocation": alloc})
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
                        capacity_issues.append(
                            {"room_id": rid, "allocated": alloc, "capacity": cap}
                        )

                    # FIXED: Use ensure_uuid for room ID conversion
                    occupancy_key = (ensure_uuid(rid), date_key)
                    if occupancy_key in occupancy:
                        errors.append(f"Room {rid} double-booked at {date_key}")
                        room_conflicts.append(
                            {
                                "room_id": rid,
                                "date_key": date_key,
                                "conflicting_exam": str(occupancy[occupancy_key]),
                            }
                        )
                    else:
                        occupancy[occupancy_key] = proposal.exam_id

                    total += alloc

                expected = int(exam.get("expected_students") or 0)
                if total < expected:
                    warnings.append(
                        f"Exam {proposal.exam_id} capacity shortfall: {total} < {expected}"
                    )

                validation_result = {
                    "capacity_issues": capacity_issues,
                    "room_conflicts": room_conflicts,
                    "capacity_shortfall": max(0, expected - total),
                }

                status = "passed"
                if capacity_issues or room_conflicts:
                    status = "failed"
                elif expected > total:
                    status = "warning"

                self._end_action(proposal_action, status, validation_result)

            validation_summary = {
                "errors": errors,
                "warnings": warnings,
                "validation_metadata": {
                    "proposals_validated": len(proposals),
                    "total_errors": len(errors),
                    "total_warnings": len(warnings),
                    "tracking_context": self._get_current_context(),
                },
            }

            self._end_action(
                validation_action,
                "completed",
                {
                    "validation_passed": len(errors) == 0,
                    "issues_found": len(errors) + len(warnings),
                },
            )

            await self._log_operation(
                "room_plan_validation_completed",
                {
                    "validation_summary": {
                        "errors_count": len(errors),
                        "warnings_count": len(warnings),
                        "validation_passed": len(errors) == 0,
                    }
                },
            )

            return validation_summary

        except Exception as exc:
            self._end_action(validation_action, "failed", {"error": str(exc)})
            await self._log_operation(
                "room_plan_validation_failed", {"error": str(exc)}, "ERROR"
            )
            raise

    def get_allocation_tracking_info(self, session_id: UUID) -> Dict[str, Any]:
        """Get comprehensive tracking information for room allocation operations."""
        return {
            "session_id": str(session_id),
            "current_context": self._get_current_context(),
            "allocation_history": [
                {
                    "action_id": str(action["action_id"]),
                    "action_type": action["action_type"],
                    "description": action["description"],
                    "metadata": action.get("metadata", {}),
                    "status": action.get("status", "active"),
                }
                for action in self._action_stack
            ],
        }
