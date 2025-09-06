# scheduling_engine/constraints/hard_constraints/time_availability.py

"""
Time Availability Hard Constraint

This constraint ensures that exams are only scheduled during available time slots
and that time-based restrictions are respected. This includes staff availability,
room availability, and institutional time policies.
"""

from typing import (
    Dict,
    List,
    Set,
    Any,
    Optional,
    DefaultDict,
    Protocol,
)
from uuid import UUID
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time, date

# optional helper parser
from dateutil import parser as _dateutil_parser

from ..enhanced_base_constraint import EnhancedBaseConstraint
from ...core.constraint_registry import (
    ConstraintDefinition,
    ConstraintType,
    ConstraintCategory,
    ConstraintViolation,
    ConstraintSeverity,
)
from ...core import ExamSchedulingProblem, TimetableSolution, TimeSlot

logger = logging.getLogger(__name__)


def _extract_weekday(time_slot) -> Optional[str]:
    """
    Extract weekday name (e.g. 'Monday') from a TimeSlot-like object.
    Returns None if no valid date is found.
    """
    try:
        if hasattr(time_slot, "date") and isinstance(time_slot.date, date):
            return time_slot.date.strftime("%A")  # e.g. "Monday"
        elif hasattr(time_slot, "earliest_start") and isinstance(
            time_slot.earliest_start, datetime
        ):
            return time_slot.earliest_start.strftime("%A")
    except Exception:
        return None
    return None


@dataclass
class TimeAvailabilityViolation:
    """Represents a time availability violation"""

    entity_type: str
    entity_id: UUID
    time_slot_id: UUID
    exam_ids: List[UUID]
    violation_type: str
    restriction_reason: str
    severity: float = 1.0


class TimeAvailabilityConstraint(EnhancedBaseConstraint):
    _is_initialized: bool = False

    def __init__(self, **kwargs):
        super().__init__(
            constraint_id="TIME_AVAILABILITY",
            name="Time Availability",
            constraint_type=ConstraintType.HARD,
            category=ConstraintCategory.TEMPORAL_CONSTRAINTS,
            weight=1.0,
            parameters={
                "enforce_slot_availability": True,
                "check_staff_availability": True,
                "check_room_availability": True,
                "respect_academic_calendar": True,
                "allow_weekend_exams": False,
                "earliest_exam_time": "08:00",
                "latest_exam_time": "18:00",
                "blocked_dates": [],
                "unavailable_penalty": 75000,
            },
            **kwargs,
        )
        self._is_initialized = False
        self.available_slots: Set[UUID] = set()
        self.staff_unavailability: DefaultDict[UUID, Set[UUID]] = defaultdict(set)
        self.room_availability: DefaultDict[UUID, Set[UUID]] = defaultdict(set)

    def get_definition(self) -> ConstraintDefinition:
        return ConstraintDefinition(
            constraint_id=self.constraint_id,
            name=self.name,
            description="Ensures exams are only scheduled during available time periods",
            constraint_type=self.constraint_type,
            category=self.category,
            parameters=self.parameters,
            validation_rules=[
                "Exams only scheduled in available time slots",
                "Staff unavailability periods respected",
                "Room availability windows honored",
                "Academic calendar restrictions followed",
                "Institutional time policies enforced",
            ],
            constraint_class=type(self),
            is_configurable=True,
        )

    def _initialize_implementation(
        self,
        problem: "ExamSchedulingProblem",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            self.available_slots.clear()
            self.staff_unavailability.clear()
            self.room_availability.clear()

            allow_weekends = self.get_parameter("allow_weekend_exams", False)
            earliest_time = self.get_parameter("earliest_exam_time", "08:00")
            latest_time = self.get_parameter("latest_exam_time", "18:00")
            blocked_dates = self.get_parameter("blocked_dates", [])

            for time_slot in problem.time_slots.values():
                if self._is_slot_available(
                    time_slot, allow_weekends, earliest_time, latest_time, blocked_dates
                ):
                    self.available_slots.add(time_slot.id)

            staff_unavail_data = getattr(problem, "staff_unavailability", [])
            for unavail in staff_unavail_data:
                staff_id = getattr(unavail, "staff_id", None)
                slot_id = getattr(unavail, "time_slot_id", None)
                if staff_id and slot_id:
                    self.staff_unavailability[staff_id].add(slot_id)

            for room in problem.rooms.values():
                room_available_slots = set(self.available_slots)

                room_restrictions = getattr(room, "availability_restrictions", None)
                if room_restrictions:
                    restricted_slots = self._parse_room_restrictions(
                        room_restrictions, problem.time_slots.values()
                    )
                    room_available_slots -= restricted_slots

                self.room_availability[room.id] = room_available_slots

            logger.info(
                f"Initialized time availability: {len(self.available_slots)} available slots, "
                f"{len(self.staff_unavailability)} staff with restrictions, "
                f"{len(self.room_availability)} rooms checked"
            )
            self._is_initialized = True
        except Exception as e:
            logger.error(f"Error initializing time availability constraint: {e}")
            raise

    def _evaluate_implementation(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        violations = []
        try:
            for exam_id, assignment in solution.assignments.items():
                if not assignment.time_slot_id:
                    continue

                time_slot_id = assignment.time_slot_id

                if time_slot_id not in self.available_slots:
                    violation = ConstraintViolation(
                        constraint_id=self.id,
                        violation_id=UUID(),
                        severity=ConstraintSeverity.CRITICAL,
                        affected_exams=[exam_id],
                        affected_resources=[time_slot_id],
                        description=f"Exam {exam_id} scheduled in unavailable slot {time_slot_id}",
                        penalty=self.get_parameter("unavailable_penalty", 75000),
                    )
                    violations.append(violation)

                if assignment.room_ids:
                    for room_id in assignment.room_ids:
                        room_available_slots = self.room_availability.get(
                            room_id, set()
                        )
                        if time_slot_id not in room_available_slots:
                            violation = ConstraintViolation(
                                constraint_id=self.id,
                                violation_id=UUID(),
                                severity=ConstraintSeverity.HIGH,
                                affected_exams=[exam_id],
                                affected_resources=[room_id],
                                description=f"Exam {exam_id} assigned to room {room_id} "
                                f"which is unavailable in slot {time_slot_id}",
                                penalty=self.get_parameter("unavailable_penalty", 75000)
                                * 0.8,
                            )
                            violations.append(violation)
        except Exception as e:
            logger.error(f"Error evaluating time availability constraint: {e}")

        return violations

    def _is_slot_available(
        self,
        time_slot,
        allow_weekends: bool,
        earliest_time: str,
        latest_time: str,
        blocked_dates: List[str],
    ) -> bool:
        try:
            if hasattr(time_slot, "is_active") and not time_slot.is_active:
                return False

            if hasattr(time_slot, "start_time"):
                slot_start = str(time_slot.start_time)
                if slot_start < earliest_time or slot_start > latest_time:
                    return False

            if not allow_weekends:
                day_of_week = _extract_weekday(time_slot)
                if day_of_week in ["Saturday", "Sunday"]:
                    return False

            if blocked_dates and hasattr(time_slot, "date"):
                slot_date = None
                try:
                    if isinstance(time_slot.date, date):
                        slot_date = time_slot.date.isoformat()
                    else:
                        slot_date = str(time_slot.date)
                    if slot_date in blocked_dates:
                        return False
                except Exception:
                    pass

            return True
        except Exception as e:
            logger.error(f"Error checking slot availability: {e}")
            return False

    def _parse_room_restrictions(self, restrictions: Any, time_slots) -> Set[UUID]:
        restricted_slots = set()
        try:
            if isinstance(restrictions, dict):
                unavailable_days = restrictions.get("unavailable_days", [])
                for slot in time_slots:
                    day_of_week = _extract_weekday(slot)
                    if day_of_week and day_of_week in unavailable_days:
                        restricted_slots.add(slot.id)

                unavailable_times = restrictions.get("unavailable_times", [])
                for time_range in unavailable_times:
                    if "-" in time_range:
                        start_time, end_time = time_range.split("-")
                        for slot in time_slots:
                            if hasattr(slot, "start_time"):
                                slot_time = str(slot.start_time)
                                if start_time <= slot_time <= end_time:
                                    restricted_slots.add(slot.id)

                maintenance_slots = restrictions.get("maintenance_slots", [])
                for slot_id_str in maintenance_slots:
                    try:
                        slot_id = UUID(slot_id_str)
                        restricted_slots.add(slot_id)
                    except ValueError:
                        logger.warning(
                            f"Invalid slot ID in restrictions: {slot_id_str}"
                        )
        except Exception as e:
            logger.error(f"Error parsing room restrictions: {e}")

        return restricted_slots

    def validate_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        errors = super().validate_parameters(parameters)

        for time_param in ["earliest_exam_time", "latest_exam_time"]:
            time_str = parameters.get(time_param)
            if time_str:
                try:
                    time.fromisoformat(time_str)
                except ValueError:
                    errors.append(f"Invalid time format for {time_param}: {time_str}")

        blocked_dates = parameters.get("blocked_dates", [])
        for date_str in blocked_dates:
            try:
                date.fromisoformat(date_str)
            except ValueError:
                errors.append(f"Invalid date format in blocked_dates: {date_str}")

        penalty = parameters.get("unavailable_penalty", 75000)
        if penalty <= 0:
            errors.append("unavailable_penalty must be positive")

        return errors

    def get_availability_statistics(
        self, problem: "ExamSchedulingProblem"
    ) -> Dict[str, Any]:
        if not self._is_initialized:
            self.initialize(problem)

        total_slots = len(problem.time_slots)
        available_slot_count = len(self.available_slots)
        availability_ratio = available_slot_count / max(total_slots, 1)

        total_staff = len(getattr(problem, "staff", []))
        staff_with_restrictions = len(self.staff_unavailability)

        if staff_with_restrictions > 0:
            avg_unavailable_slots = (
                sum(len(slots) for slots in self.staff_unavailability.values())
                / staff_with_restrictions
            )
        else:
            avg_unavailable_slots = 0

        return {
            "total_time_slots": total_slots,
            "available_slots": available_slot_count,
            "blocked_slots": total_slots - available_slot_count,
            "availability_ratio": availability_ratio,
            "total_staff": total_staff,
            "staff_with_restrictions": staff_with_restrictions,
            "average_unavailable_slots_per_staff": avg_unavailable_slots,
            "availability_pressure": (
                "high"
                if availability_ratio < 0.7
                else "medium" if availability_ratio < 0.9 else "low"
            ),
            "room_availability": {
                str(room_id): len(available_slots)
                for room_id, available_slots in self.room_availability.items()
            },
        }

    def get_blocked_time_analysis(
        self, problem: "ExamSchedulingProblem"
    ) -> Dict[str, Any]:
        if not self._is_initialized:
            self.initialize(problem)

        blocked_slots = set(problem.time_slots.keys()) - self.available_slots

        blocking_reasons = {
            "weekend_blocks": 0,
            "time_policy_blocks": 0,
            "date_blocks": 0,
            "inactive_slots": 0,
        }

        earliest_time = self.get_parameter("earliest_exam_time", "08:00")
        latest_time = self.get_parameter("latest_exam_time", "18:00")
        allow_weekends = self.get_parameter("allow_weekend_exams", False)
        blocked_dates = self.get_parameter("blocked_dates", [])

        for slot_id in blocked_slots:
            slot = problem.time_slots.get(slot_id)
            if not slot:
                continue

            if hasattr(slot, "is_active") and not slot.is_active:
                blocking_reasons["inactive_slots"] += 1
            else:
                day_of_week = _extract_weekday(slot)
                if not allow_weekends and day_of_week in ["Saturday", "Sunday"]:
                    blocking_reasons["weekend_blocks"] += 1
                elif hasattr(slot, "start_time"):
                    slot_start = str(slot.start_time)
                    if slot_start < earliest_time or slot_start > latest_time:
                        blocking_reasons["time_policy_blocks"] += 1
                elif hasattr(slot, "date") and str(slot.date) in blocked_dates:
                    blocking_reasons["date_blocks"] += 1

        return {
            "total_blocked_slots": len(blocked_slots),
            "blocking_reasons": blocking_reasons,
            "blocked_slot_ids": [str(sid) for sid in blocked_slots],
        }

    def clone(
        self,
        new_weight: Optional[float] = None,
        new_parameters: Optional[Dict[str, Any]] = None,
    ) -> "TimeAvailabilityConstraint":
        kwargs = {
            "parameters": self.parameters.copy(),
            "database_config": self.database_config.copy(),
        }

        if new_parameters:
            kwargs["parameters"].update(new_parameters)

        clone = TimeAvailabilityConstraint(**kwargs)

        if new_weight is not None:
            clone.weight = new_weight

        return clone
