# backend/app/services/scheduling/incremental_optimizer.py
"""
Incremental optimizer for handling manual edits to existing timetables
while maintaining constraint satisfaction and solution quality.
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import TimetableVersion, Exam, ExamRoom, ExamInvigilator
from .enhanced_engine_connector import EnhancedSchedulingEngineConnector

logger = logging.getLogger(__name__)


class IncrementalOptimizer:
    """
    Handles incremental optimization for manual timetable edits.

    Features:
    - Conflict detection and resolution
    - Local optimization around edited exams
    - Constraint validation
    - Impact analysis
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.connector = EnhancedSchedulingEngineConnector(session)

    async def apply_manual_edit(
        self,
        version_id: UUID,
        edit_data: Dict[str, Any],
        user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Apply a manual edit to an existing timetable with validation and optimization.

        Args:
            version_id: The timetable version to edit
            edit_data: The edit to apply (exam reassignment)
            user_id: User making the edit

        Returns:
            Dict containing success status and results
        """
        try:
            logger.info(f"Applying manual edit to version {version_id}")

            # Validate edit data
            validation_result = await self._validate_edit_data(edit_data)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": "Invalid edit data",
                    "validation_errors": validation_result["errors"],
                }

            # Get current timetable state
            current_state = await self._get_timetable_state(version_id)
            if not current_state:
                return {"success": False, "error": "Timetable version not found"}

            # Apply edit to create proposed state
            proposed_state = await self._apply_edit_to_state(current_state, edit_data)

            # Detect conflicts
            conflicts = await self._detect_conflicts(proposed_state, edit_data)

            if conflicts:
                # Try to resolve conflicts automatically
                resolution_result = await self._resolve_conflicts_automatically(
                    proposed_state, conflicts
                )

                if resolution_result["success"]:
                    proposed_state = resolution_result["resolved_state"]
                    conflicts = []
                else:
                    return {
                        "success": False,
                        "error": "Unresolvable conflicts detected",
                        "conflicts": conflicts,
                        "suggestions": await self._generate_conflict_suggestions(
                            conflicts
                        ),
                    }

            # Perform local optimization around affected exams
            optimized_state = await self._local_optimization(
                proposed_state, edit_data, current_state
            )

            # Calculate impact analysis
            impact_analysis = await self._calculate_edit_impact(
                current_state, optimized_state, edit_data
            )

            # Prepare final solution
            final_solution = {
                "assignments": optimized_state,
                "metadata": {
                    "edit_type": edit_data.get("edit_type", "manual"),
                    "edited_exam": edit_data.get("exam_id"),
                    "applied_at": datetime.utcnow().isoformat(),
                    "applied_by": str(user_id) if user_id else None,
                },
            }

            return {
                "success": True,
                "solution": final_solution,
                "edit_summary": {
                    "exam_id": edit_data.get("exam_id"),
                    "changes": edit_data,
                    "conflicts_resolved": len(conflicts) if conflicts else 0,
                },
                "validation_results": validation_result,
                "performance_impact": impact_analysis,
            }

        except Exception as e:
            logger.error(f"Failed to apply manual edit: {e}", exc_info=True)
            return {"success": False, "error": f"Edit application failed: {str(e)}"}

    async def _validate_edit_data(self, edit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the edit data structure and content"""

        errors = []

        # Check required fields
        required_fields = ["exam_id", "edit_type"]
        for field in required_fields:
            if field not in edit_data:
                errors.append(f"Missing required field: {field}")

        # Validate edit type
        valid_edit_types = ["time_change", "room_change", "staff_change", "combined"]
        edit_type = edit_data.get("edit_type")
        if edit_type and edit_type not in valid_edit_types:
            errors.append(f"Invalid edit type: {edit_type}")

        # Validate UUIDs
        uuid_fields = ["exam_id", "new_room_id", "new_timeslot_id"]
        for field in uuid_fields:
            if field in edit_data:
                try:
                    UUID(str(edit_data[field]))
                except ValueError:
                    errors.append(
                        f"Invalid UUID format for {field}: {edit_data[field]}"
                    )

        # Type-specific validation
        if edit_type == "time_change" and "new_timeslot_id" not in edit_data:
            errors.append("time_change edit requires new_timeslot_id")

        if edit_type == "room_change" and "new_room_id" not in edit_data:
            errors.append("room_change edit requires new_room_id")

        if edit_type == "staff_change" and "new_staff_ids" not in edit_data:
            errors.append("staff_change edit requires new_staff_ids")

        return {"valid": len(errors) == 0, "errors": errors}

    async def _get_timetable_state(self, version_id: UUID) -> Optional[Dict[str, Any]]:
        """Get current timetable state from database"""

        try:
            # Get timetable version
            version_query = select(TimetableVersion).where(
                TimetableVersion.id == version_id
            )
            version_result = await self.session.execute(version_query)
            version = version_result.scalar_one_or_none()

            if not version:
                return None

            # Get job to find session
            job = version.job
            if not job:
                return None

            # Get all exam assignments for the session
            exams_query = (
                select(Exam)
                .where(Exam.session_id == job.session_id)
                .where(Exam.status == "scheduled")
            )

            exams_result = await self.session.execute(exams_query)
            exams = exams_result.scalars().all()

            # Build state dictionary
            state = {}
            for exam in exams:
                if exam.time_slot_id:
                    # Get room assignments
                    room_query = select(ExamRoom).where(ExamRoom.exam_id == exam.id)
                    room_result = await self.session.execute(room_query)
                    room_assignments = room_result.scalars().all()

                    # Get staff assignments
                    staff_query = select(ExamInvigilator).where(
                        ExamInvigilator.exam_id == exam.id
                    )
                    staff_result = await self.session.execute(staff_query)
                    staff_assignments = staff_result.scalars().all()

                    state[str(exam.id)] = {
                        "room_id": (
                            str(room_assignments[0].room_id)
                            if room_assignments
                            else None
                        ),
                        "timeslot_id": str(exam.time_slot_id),
                        "staff_ids": [str(s.staff_id) for s in staff_assignments],
                    }

            return state

        except Exception as e:
            logger.error(f"Failed to get timetable state: {e}")
            return None

    async def _apply_edit_to_state(
        self, current_state: Dict[str, Any], edit_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply edit to current state to create proposed state"""

        proposed_state = current_state.copy()
        exam_id = str(edit_data["exam_id"])
        edit_type = edit_data["edit_type"]

        if exam_id not in proposed_state:
            proposed_state[exam_id] = {
                "room_id": None,
                "timeslot_id": None,
                "staff_ids": [],
            }

        # Apply changes based on edit type
        if edit_type in ["time_change", "combined"]:
            if "new_timeslot_id" in edit_data:
                proposed_state[exam_id]["timeslot_id"] = str(
                    edit_data["new_timeslot_id"]
                )

        if edit_type in ["room_change", "combined"]:
            if "new_room_id" in edit_data:
                proposed_state[exam_id]["room_id"] = str(edit_data["new_room_id"])

        if edit_type in ["staff_change", "combined"]:
            if "new_staff_ids" in edit_data:
                proposed_state[exam_id]["staff_ids"] = [
                    str(sid) for sid in edit_data["new_staff_ids"]
                ]

        return proposed_state

    async def _detect_conflicts(
        self, proposed_state: Dict[str, Any], edit_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect conflicts in the proposed state"""

        conflicts: List[Dict[str, Any]] = []
        edited_exam_id = str(edit_data["exam_id"])

        # Get edited exam's new assignment
        edited_assignment = proposed_state.get(edited_exam_id)
        if not edited_assignment:
            return conflicts

        new_timeslot = edited_assignment.get("timeslot_id")
        new_room = edited_assignment.get("room_id")
        new_staff = edited_assignment.get("staff_ids", [])

        # Check for time conflicts (student conflicts)
        if new_timeslot:
            time_conflicts = await self._check_student_time_conflicts(
                proposed_state, edited_exam_id, new_timeslot
            )
            conflicts.extend(time_conflicts)

        # Check for room conflicts
        if new_room and new_timeslot:
            room_conflicts = await self._check_room_conflicts(
                proposed_state, edited_exam_id, new_room, new_timeslot
            )
            conflicts.extend(room_conflicts)

        # Check for staff conflicts
        if new_staff and new_timeslot:
            staff_conflicts = await self._check_staff_conflicts(
                proposed_state, edited_exam_id, new_staff, new_timeslot
            )
            conflicts.extend(staff_conflicts)

        # Check capacity constraints
        if new_room:
            capacity_conflicts = await self._check_capacity_constraints(
                edited_exam_id, new_room
            )
            conflicts.extend(capacity_conflicts)

        return conflicts

    async def _check_student_time_conflicts(
        self, proposed_state: Dict[str, Any], edited_exam_id: str, new_timeslot: str
    ) -> List[Dict[str, Any]]:
        """Check for student conflicts in the new time slot"""

        conflicts = []

        try:
            # Get problem instance for conflict matrix
            # This is a simplified check - in practice, you'd use the conflict matrix
            for exam_id, assignment in proposed_state.items():
                if (
                    exam_id != edited_exam_id
                    and assignment.get("timeslot_id") == new_timeslot
                ):

                    # Check if students overlap (simplified)
                    conflicts.append(
                        {
                            "type": "student_conflict",
                            "conflicting_exam": exam_id,
                            "timeslot": new_timeslot,
                            "severity": "high",
                            "message": f"Students enrolled in both exams {edited_exam_id} and {exam_id}",
                        }
                    )

        except Exception as e:
            logger.error(f"Failed to check student time conflicts: {e}")

        return conflicts

    async def _check_room_conflicts(
        self,
        proposed_state: Dict[str, Any],
        edited_exam_id: str,
        new_room: str,
        new_timeslot: str,
    ) -> List[Dict[str, Any]]:
        """Check for room double-booking conflicts"""

        conflicts = []

        for exam_id, assignment in proposed_state.items():
            if (
                exam_id != edited_exam_id
                and assignment.get("room_id") == new_room
                and assignment.get("timeslot_id") == new_timeslot
            ):

                conflicts.append(
                    {
                        "type": "room_conflict",
                        "conflicting_exam": exam_id,
                        "room": new_room,
                        "timeslot": new_timeslot,
                        "severity": "high",
                        "message": f"Room {new_room} double-booked with exam {exam_id}",
                    }
                )

        return conflicts

    async def _check_staff_conflicts(
        self,
        proposed_state: Dict[str, Any],
        edited_exam_id: str,
        new_staff: List[str],
        new_timeslot: str,
    ) -> List[Dict[str, Any]]:
        """Check for staff double-booking conflicts"""

        conflicts = []

        for staff_id in new_staff:
            for exam_id, assignment in proposed_state.items():
                if (
                    exam_id != edited_exam_id
                    and assignment.get("timeslot_id") == new_timeslot
                    and staff_id in assignment.get("staff_ids", [])
                ):

                    conflicts.append(
                        {
                            "type": "staff_conflict",
                            "conflicting_exam": exam_id,
                            "staff": staff_id,
                            "timeslot": new_timeslot,
                            "severity": "medium",
                            "message": f"Staff {staff_id} double-booked with exam {exam_id}",
                        }
                    )

        return conflicts

    async def _check_capacity_constraints(
        self, edited_exam_id: str, new_room: str
    ) -> List[Dict[str, Any]]:
        """Check room capacity constraints"""

        conflicts = []

        try:
            # Get exam details
            exam_query = select(Exam).where(Exam.id == UUID(edited_exam_id))
            exam_result = await self.session.execute(exam_query)
            exam = exam_result.scalar_one_or_none()

            if exam:
                # Get room details (simplified - would use connector in practice)
                expected_students = exam.expected_students
                # room_capacity = await self._get_room_capacity(new_room)
                room_capacity = 100  # Placeholder

                if expected_students > room_capacity:
                    conflicts.append(
                        {
                            "type": "capacity_violation",
                            "room": new_room,
                            "expected_students": expected_students,
                            "room_capacity": room_capacity,
                            "severity": "high",
                            "message": f"Room capacity ({room_capacity}) insufficient for {expected_students} students",
                        }
                    )

        except Exception as e:
            logger.error(f"Failed to check capacity constraints: {e}")

        return conflicts

    async def _resolve_conflicts_automatically(
        self, proposed_state: Dict[str, Any], conflicts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Attempt to automatically resolve detected conflicts"""

        try:
            resolved_state = proposed_state.copy()
            resolved_conflicts = []

            for conflict in conflicts:
                conflict_type = conflict["type"]

                if conflict_type == "room_conflict":
                    # Try to find alternative room
                    alternative_room = await self._find_alternative_room(conflict)
                    if alternative_room:
                        conflicting_exam = conflict["conflicting_exam"]
                        resolved_state[conflicting_exam]["room_id"] = alternative_room
                        resolved_conflicts.append(conflict)

                elif conflict_type == "staff_conflict":
                    # Try to reassign staff
                    alternative_staff = await self._find_alternative_staff(conflict)
                    if alternative_staff:
                        conflicting_exam = conflict["conflicting_exam"]
                        current_staff = resolved_state[conflicting_exam]["staff_ids"]
                        # Replace conflicting staff member
                        staff_id = conflict["staff"]
                        if staff_id in current_staff:
                            current_staff.remove(staff_id)
                            current_staff.append(alternative_staff)
                        resolved_conflicts.append(conflict)

            success = len(resolved_conflicts) == len(conflicts)

            return {
                "success": success,
                "resolved_state": resolved_state,
                "resolved_conflicts": resolved_conflicts,
                "remaining_conflicts": [
                    c for c in conflicts if c not in resolved_conflicts
                ],
            }

        except Exception as e:
            logger.error(f"Failed to resolve conflicts automatically: {e}")
            return {"success": False, "error": str(e)}

    async def _find_alternative_room(self, conflict: Dict[str, Any]) -> Optional[str]:
        """Find alternative room for conflict resolution"""
        # Simplified implementation
        # In practice, this would use the room compatibility matrix
        return None

    async def _find_alternative_staff(self, conflict: Dict[str, Any]) -> Optional[str]:
        """Find alternative staff member for conflict resolution"""
        # Simplified implementation
        # In practice, this would check staff availability and constraints
        return None

    async def _generate_conflict_suggestions(
        self, conflicts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate suggestions for resolving conflicts"""

        suggestions = []

        for conflict in conflicts:
            conflict_type = conflict["type"]

            if conflict_type == "student_conflict":
                suggestions.append(
                    {
                        "type": "reschedule_one_exam",
                        "message": "Consider rescheduling one of the conflicting exams to a different time slot",
                        "affected_exams": [conflict["conflicting_exam"]],
                        "priority": "high",
                    }
                )

            elif conflict_type == "room_conflict":
                suggestions.append(
                    {
                        "type": "change_room",
                        "message": "Select a different room that is available at this time",
                        "affected_exams": [conflict["conflicting_exam"]],
                        "priority": "medium",
                    }
                )

            elif conflict_type == "capacity_violation":
                suggestions.append(
                    {
                        "type": "use_larger_room",
                        "message": "Select a room with sufficient capacity or split into multiple rooms",
                        "priority": "high",
                    }
                )

        return suggestions

    async def _local_optimization(
        self,
        proposed_state: Dict[str, Any],
        edit_data: Dict[str, Any],
        current_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Perform local optimization around the edited exam"""

        # For now, return the proposed state as-is
        # In a full implementation, this would:
        # 1. Identify exams affected by the edit
        # 2. Run a small CP-SAT/GA optimization on just those exams
        # 3. Integrate the optimized assignments back into the full state

        return proposed_state

    async def _calculate_edit_impact(
        self,
        current_state: Dict[str, Any],
        optimized_state: Dict[str, Any],
        edit_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Calculate the impact of the edit on the overall timetable"""

        # Count changes
        changed_exams = 0
        for exam_id in set(list(current_state.keys()) + list(optimized_state.keys())):
            if current_state.get(exam_id) != optimized_state.get(exam_id):
                changed_exams += 1

        # Calculate quality metrics (simplified)
        impact = {
            "exams_affected": changed_exams,
            "directly_edited": 1,
            "indirectly_affected": changed_exams - 1,
            "quality_change": 0.0,  # Would calculate actual quality difference
            "constraint_violations": 0,
            "edit_complexity": (
                "low"
                if changed_exams <= 2
                else "medium" if changed_exams <= 5 else "high"
            ),
        }

        return impact
