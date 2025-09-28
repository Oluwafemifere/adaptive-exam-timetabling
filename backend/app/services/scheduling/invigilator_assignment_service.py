# backend/app/services/scheduling/invigilator_assignment_service.py

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, DefaultDict
from uuid import UUID
from dataclasses import dataclass, field
from collections import defaultdict
import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

# Import tracking mixin
from ..tracking_mixin import TrackingMixin

from ...services.data_retrieval import SchedulingData, AcademicData, UserData

logger = logging.getLogger(__name__)


@dataclass
class InvigilationAssignment:
    exam_id: UUID
    assignment_id: UUID = field(
        default_factory=lambda: uuid.uuid4()
    )  # Auto-generate ID
    staff_ids: List[UUID] = field(default_factory=list)  # ordered: first may be chief
    room_ids: List[UUID] = field(default_factory=list)
    assignment_metadata: Dict[str, Any] = field(default_factory=dict)  # For tracking


class InvigilatorAssignmentService(TrackingMixin):
    """
    Enhanced invigilator assignment service with automatic session and action tracking.
    Assigns invigilators to exams subject to availability, departmental context,
    max_daily_sessions, and max_consecutive_sessions.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)
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
        """Assign invigilators with comprehensive tracking."""

        # Start main assignment action
        assignment_action = self._start_action(
            action_type="invigilator_assignment",
            description=f"Assigning invigilators for session {session_id}",
            metadata={
                "session_id": str(session_id),
                "min_per_room": min_per_room,
                "chief_per_exam": chief_per_exam,
            },
        )

        try:
            await self._log_operation(
                "invigilator_assignment_started",
                {
                    "session_id": str(session_id),
                    "assignment_criteria": {
                        "min_per_room": min_per_room,
                        "chief_per_exam": chief_per_exam,
                    },
                },
            )

            # Data retrieval phase
            data_action = self._start_action(
                "data_retrieval", "Retrieving scheduling and staff data"
            )

            data = await self.scheduling_data.get_scheduling_data_for_session(
                session_id
            )
            exams = list(data.get("exams", [])) if data.get("exams") else []

            # Build rooms by exam mapping
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

            self._end_action(
                data_action,
                "completed",
                {
                    "exams_count": len(exams),
                    "staff_count": len(staff),
                    "unavailability_records": len(unavailability),
                    "exams_with_rooms": sum(
                        1 for rooms in rooms_by_exam.values() if rooms
                    ),
                },
            )

            # Build unavailability and tracking maps
            availability_action = self._start_action(
                "availability_processing", "Processing staff availability"
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
            staff_by_dept: DefaultDict[Optional[str], List[Dict[str, Any]]] = (
                defaultdict(list)
            )
            total_available_staff = 0

            for s in staff:
                if bool(s.get("is_active", True)) and bool(
                    s.get("can_invigilate", False)
                ):
                    staff_by_dept[s.get("department_id")].append(s)
                    total_available_staff += 1

            self._end_action(
                availability_action,
                "completed",
                {
                    "total_staff": len(staff),
                    "available_invigilators": total_available_staff,
                    "departments_with_staff": len(staff_by_dept),
                    "unavailability_constraints": len(unavailable_map),
                },
            )

            assignments: List[InvigilationAssignment] = []

            # Process each exam
            for exam_idx, exam in enumerate(exams):
                exam_action = self._start_action(
                    "exam_assignment",
                    f"Assigning invigilators for exam {exam.get('id', 'unknown')}",
                    metadata={"exam_index": exam_idx, "total_exams": len(exams)},
                )

                eid = exam.get("id")
                if not eid:
                    assignment = InvigilationAssignment(
                        exam_id=uuid.uuid4(),  # Generate dummy ID for invalid exam
                        staff_ids=[],
                        room_ids=[],
                        assignment_metadata={
                            "assignment_status": "skipped",
                            "reason": "invalid_exam_id",
                            "tracking_context": self._get_current_context(),
                        },
                    )
                    assignments.append(assignment)
                    self._end_action(
                        exam_action, "skipped", {"reason": "invalid_exam_id"}
                    )
                    continue

                exam_rooms = rooms_by_exam.get(eid, [])
                if not exam_rooms:
                    # No rooms allocated yet; skip for now
                    assignment = InvigilationAssignment(
                        exam_id=eid,
                        staff_ids=[],
                        room_ids=[],
                        assignment_metadata={
                            "assignment_status": "skipped",
                            "reason": "no_rooms_allocated",
                            "tracking_context": self._get_current_context(),
                        },
                    )
                    assignments.append(assignment)
                    self._end_action(
                        exam_action, "skipped", {"reason": "no_rooms_allocated"}
                    )
                    continue

                # Calculate staffing requirements
                requirement_action = self._start_action(
                    "requirement_calculation", "Calculating staffing requirements"
                )

                need = len(exam_rooms) * max(min_per_room, 1)
                # If chief invigilator requested, add one to total
                total_needed = need + (1 if chief_per_exam else 0)

                # Candidate staff: matching dept if possible, else any active invigilator-capable
                dept_candidates = staff_by_dept.get(exam.get("department_id"))
                candidates = dept_candidates if dept_candidates else staff

                self._end_action(
                    requirement_action,
                    "completed",
                    {
                        "rooms_count": len(exam_rooms),
                        "base_need": need,
                        "total_needed": total_needed,
                        "candidate_pool_size": len(candidates),
                        "using_department_match": dept_candidates is not None,
                    },
                )

                # Staff selection process
                selection_action = self._start_action(
                    "staff_selection", "Selecting available staff"
                )

                chosen: List[UUID] = []
                selection_log = []

                for cand_idx, cand in enumerate(candidates):
                    if len(chosen) >= total_needed:
                        break

                    # Basic eligibility check
                    if not bool(cand.get("is_active", True)) or not bool(
                        cand.get("can_invigilate", False)
                    ):
                        selection_log.append(
                            {
                                "staff_id": cand.get("id"),
                                "status": "ineligible",
                                "reason": "not_active_or_cannot_invigilate",
                            }
                        )
                        continue

                    sid = cand.get("id")
                    if not sid:
                        selection_log.append(
                            {
                                "staff_id": None,
                                "status": "ineligible",
                                "reason": "missing_id",
                            }
                        )
                        continue

                    # Date/slot availability checks
                    exam_date = exam.get("exam_date")
                    slot_id = exam.get("time_slot_id")

                    if unavailable_map.get(
                        (sid, exam_date, slot_id)
                    ) or unavailable_map.get((sid, exam_date, None)):
                        selection_log.append(
                            {
                                "staff_id": sid,
                                "status": "unavailable",
                                "reason": "time_conflict",
                                "exam_date": exam_date,
                                "slot_id": slot_id,
                            }
                        )
                        continue

                    # Daily limits check
                    max_daily = int(cand.get("max_daily_sessions") or 2)
                    key = (sid, str(exam_date))
                    if daily_count[key] >= max_daily:
                        selection_log.append(
                            {
                                "staff_id": sid,
                                "status": "unavailable",
                                "reason": "daily_limit_exceeded",
                                "current_count": daily_count[key],
                                "max_daily": max_daily,
                            }
                        )
                        continue

                    # Consecutive sessions check
                    max_consec = int(cand.get("max_consecutive_sessions") or 2)
                    prev_slot = last_slot.get(key)
                    if prev_slot == slot_id and max_consec <= 1:
                        selection_log.append(
                            {
                                "staff_id": sid,
                                "status": "unavailable",
                                "reason": "consecutive_limit_exceeded",
                                "previous_slot": prev_slot,
                                "current_slot": slot_id,
                            }
                        )
                        continue  # cannot handle consecutive if policy forbids

                    # Accept staff member
                    chosen.append(sid)
                    daily_count[key] += 1
                    last_slot[key] = slot_id

                    selection_log.append(
                        {
                            "staff_id": sid,
                            "status": "selected",
                            "is_chief": len(chosen) == 1 and chief_per_exam,
                            "daily_count_after": daily_count[key],
                        }
                    )

                self._end_action(
                    selection_action,
                    "completed",
                    {
                        "candidates_evaluated": len(candidates),
                        "staff_selected": len(chosen),
                        "selection_rate": (
                            (len(chosen) / total_needed * 100)
                            if total_needed > 0
                            else 0
                        ),
                        "fulfillment_status": (
                            "complete" if len(chosen) >= total_needed else "partial"
                        ),
                    },
                )

                # Create assignment with comprehensive metadata
                assignment = InvigilationAssignment(
                    exam_id=eid,
                    staff_ids=chosen,
                    room_ids=[UUID(str(r)) for r in exam_rooms if r],
                    assignment_metadata={
                        "assignment_status": (
                            "complete" if len(chosen) >= total_needed else "partial"
                        ),
                        "required_staff": total_needed,
                        "assigned_staff": len(chosen),
                        "shortfall": max(0, total_needed - len(chosen)),
                        "rooms_covered": len(exam_rooms),
                        "has_chief_invigilator": chief_per_exam and len(chosen) > 0,
                        "selection_summary": {
                            "total_candidates": len(candidates),
                            "eligible_candidates": sum(
                                1
                                for log in selection_log
                                if log["status"] != "ineligible"
                            ),
                            "availability_issues": sum(
                                1
                                for log in selection_log
                                if log["status"] == "unavailable"
                            ),
                        },
                        "tracking_context": self._get_current_context(),
                    },
                )

                assignments.append(assignment)

                assignment_status = (
                    "completed" if len(chosen) >= total_needed else "partial"
                )
                self._end_action(
                    exam_action,
                    assignment_status,
                    {
                        "staff_assigned": len(chosen),
                        "requirement_met": len(chosen) >= total_needed,
                    },
                )

            # Generate summary statistics
            total_assignments = len(assignments)
            complete_assignments = sum(
                1
                for a in assignments
                if a.assignment_metadata.get("assignment_status") == "complete"
            )
            partial_assignments = sum(
                1
                for a in assignments
                if a.assignment_metadata.get("assignment_status") == "partial"
            )
            skipped_assignments = sum(
                1
                for a in assignments
                if a.assignment_metadata.get("assignment_status") == "skipped"
            )

            self._end_action(
                assignment_action,
                "completed",
                {
                    "total_exams": len(exams),
                    "total_assignments": total_assignments,
                    "complete_assignments": complete_assignments,
                    "partial_assignments": partial_assignments,
                    "skipped_assignments": skipped_assignments,
                    "completion_rate": (
                        (complete_assignments / total_assignments * 100)
                        if total_assignments > 0
                        else 0
                    ),
                },
            )

            await self._log_operation(
                "invigilator_assignment_completed",
                {
                    "session_id": str(session_id),
                    "results_summary": {
                        "total_exams": len(exams),
                        "assignments_generated": total_assignments,
                        "complete_assignments": complete_assignments,
                        "partial_assignments": partial_assignments,
                        "skipped_assignments": skipped_assignments,
                        "completion_rate": (
                            (complete_assignments / total_assignments * 100)
                            if total_assignments > 0
                            else 0
                        ),
                    },
                },
            )

            return assignments

        except Exception as exc:
            self._end_action(assignment_action, "failed", {"error": str(exc)})
            await self._log_operation(
                "invigilator_assignment_failed", {"error": str(exc)}, "ERROR"
            )
            raise

    async def build_notification_payloads(
        self,
        assignments: List[InvigilationAssignment],
        message_prefix: str = "Invigilation Assignment",
    ) -> List[Dict[str, Any]]:
        """
        Build notification payloads with tracking context.
        Returns message payloads to be pushed to a notification system, decoupled
        from persistence to allow audit-friendly pipelines.
        """

        notification_action = self._start_action(
            "notification_building",
            f"Building notifications for {len(assignments)} assignments",
            metadata={"assignments_count": len(assignments)},
        )

        try:
            payloads: List[Dict[str, Any]] = []

            for assignment in assignments:
                # Skip assignments with no staff
                if not assignment.staff_ids:
                    continue

                for staff_idx, staff_id in enumerate(assignment.staff_ids):
                    is_chief = staff_idx == 0 and assignment.assignment_metadata.get(
                        "has_chief_invigilator", False
                    )

                    payload = {
                        "user_id": str(staff_id),
                        "title": message_prefix,
                        "message": f"You have been assigned to invigilate exam {assignment.exam_id}",
                        "priority": "medium",
                        "entity_type": "exam",
                        "entity_id": str(assignment.exam_id),
                        "notification_metadata": {
                            "assignment_id": str(assignment.assignment_id),
                            "is_chief_invigilator": is_chief,
                            "rooms_assigned": [
                                str(room_id) for room_id in assignment.room_ids
                            ],
                            "assignment_status": assignment.assignment_metadata.get(
                                "assignment_status", "unknown"
                            ),
                            "notification_generated_at": datetime.utcnow().isoformat(),
                            "tracking_context": self._get_current_context(),
                        },
                    }

                    payloads.append(payload)

            self._end_action(
                notification_action,
                "completed",
                {
                    "notifications_generated": len(payloads),
                    "assignments_processed": len(assignments),
                    "staff_notified": len(set(p["user_id"] for p in payloads)),
                },
            )

            await self._log_operation(
                "notifications_built",
                {
                    "notifications_count": len(payloads),
                    "unique_staff_notified": len(set(p["user_id"] for p in payloads)),
                },
            )

            return payloads

        except Exception as exc:
            self._end_action(notification_action, "failed", {"error": str(exc)})
            await self._log_operation(
                "notification_building_failed", {"error": str(exc)}, "ERROR"
            )
            raise

    def get_assignment_tracking_info(self, session_id: UUID) -> Dict[str, Any]:
        """Get comprehensive tracking information for invigilator assignment operations."""
        return {
            "session_id": str(session_id),
            "current_context": self._get_current_context(),
            "assignment_history": [
                {
                    "action_id": str(action["action_id"]),
                    "action_type": action["action_type"],
                    "description": action["description"],
                    "metadata": action.get("metadata", {}),
                    "status": action.get("status", "active"),
                    "duration_ms": action.get("duration_ms", 0),
                }
                for action in self._action_stack
            ],
        }

    async def generate_assignment_report(
        self, assignments: List[InvigilationAssignment], session_id: UUID
    ) -> Dict[str, Any]:
        """Generate comprehensive assignment report with tracking data."""

        report_action = self._start_action(
            "assignment_reporting", "Generating comprehensive assignment report"
        )

        try:
            # Analyze assignment patterns
            complete_count = sum(
                1
                for a in assignments
                if a.assignment_metadata.get("assignment_status") == "complete"
            )
            partial_count = sum(
                1
                for a in assignments
                if a.assignment_metadata.get("assignment_status") == "partial"
            )
            skipped_count = sum(
                1
                for a in assignments
                if a.assignment_metadata.get("assignment_status") == "skipped"
            )

            total_staff_assigned = sum(len(a.staff_ids) for a in assignments)
            total_rooms_covered = sum(len(a.room_ids) for a in assignments)

            # Calculate shortfalls
            total_shortfall = sum(
                a.assignment_metadata.get("shortfall", 0) for a in assignments
            )

            report = {
                "session_id": str(session_id),
                "report_generated_at": datetime.utcnow().isoformat(),
                "summary": {
                    "total_assignments": len(assignments),
                    "complete_assignments": complete_count,
                    "partial_assignments": partial_count,
                    "skipped_assignments": skipped_count,
                    "completion_rate": (
                        (complete_count / len(assignments) * 100) if assignments else 0
                    ),
                    "total_staff_assigned": total_staff_assigned,
                    "total_rooms_covered": total_rooms_covered,
                    "total_staffing_shortfall": total_shortfall,
                },
                "assignment_details": [
                    {
                        "assignment_id": str(a.assignment_id),
                        "exam_id": str(a.exam_id),
                        "staff_count": len(a.staff_ids),
                        "room_count": len(a.room_ids),
                        "status": a.assignment_metadata.get(
                            "assignment_status", "unknown"
                        ),
                        "shortfall": a.assignment_metadata.get("shortfall", 0),
                    }
                    for a in assignments
                ],
                "tracking_metadata": {
                    "report_context": self._get_current_context(),
                    "generation_timestamp": datetime.utcnow().isoformat(),
                },
            }

            self._end_action(
                report_action,
                "completed",
                {
                    "assignments_analyzed": len(assignments),
                    "report_sections": len(report.keys()),
                },
            )

            await self._log_operation(
                "assignment_report_generated",
                {"session_id": str(session_id), "report_summary": report["summary"]},
            )

            return report

        except Exception as exc:
            self._end_action(report_action, "failed", {"error": str(exc)})
            await self._log_operation(
                "assignment_report_failed", {"error": str(exc)}, "ERROR"
            )
            raise
