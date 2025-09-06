# scheduling_engine/utils/validation.py

"""
Comprehensive validation utilities for scheduling engine solutions.
Provides constraint validation, solution quality assessment, and
feasibility checking based on constraint programming principles.
"""

import time
from typing import Dict, List, Any, Optional, Set, Tuple, DefaultDict, Type
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from abc import ABC, abstractmethod
import json


class ValidationLevel(Enum):
    """Levels of validation strictness"""

    BASIC = "basic"  # Essential constraints only
    STANDARD = "standard"  # Common constraint checks
    COMPREHENSIVE = "comprehensive"  # All constraint categories
    STRICT = "strict"  # Maximum validation with detailed analysis


class ConstraintType(Enum):
    """Types of constraints for validation"""

    HARD = "hard"  # Must be satisfied (feasibility)
    SOFT = "soft"  # Preferred but can be violated (optimization)
    PREFERENCE = "preference"  # Nice-to-have (quality)


class ViolationType(Enum):
    """Types of constraint violations"""

    STUDENT_CONFLICT = "student_conflict"
    ROOM_CAPACITY = "room_capacity"
    TIME_AVAILABILITY = "time_availability"
    ROOM_AVAILABILITY = "room_availability"
    STAFF_AVAILABILITY = "staff_availability"
    PRECEDENCE = "precedence"
    RESOURCE_LIMIT = "resource_limit"
    DURATION_MISMATCH = "duration_mismatch"
    EXAM_REQUIREMENTS = "exam_requirements"
    FACULTY_SEPARATION = "faculty_separation"


@dataclass
class ConstraintViolation:
    """Individual constraint violation with details"""

    violation_type: ViolationType
    constraint_type: ConstraintType
    severity: float  # 0.0 (minor) to 1.0 (critical)
    entities_involved: List[str]  # IDs of entities involved
    description: str
    suggested_fix: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert violation to dictionary for serialization"""
        return {
            "violation_type": self.violation_type.value,
            "constraint_type": self.constraint_type.value,
            "severity": self.severity,
            "entities_involved": self.entities_involved,
            "description": self.description,
            "suggested_fix": self.suggested_fix,
            "metadata": self.metadata,
        }


@dataclass
class ValidationResult:
    """Comprehensive validation result"""

    is_valid: bool
    is_feasible: bool
    validation_level: ValidationLevel
    total_violations: int
    critical_violations: int
    violations: List[ConstraintViolation] = field(default_factory=list)
    quality_score: float = 0.0
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    validation_timestamp: Optional[str] = None

    def get_violations_by_type(
        self, violation_type: ViolationType
    ) -> List[ConstraintViolation]:
        """Get all violations of a specific type"""
        return [v for v in self.violations if v.violation_type == violation_type]

    def get_violations_by_severity(
        self, min_severity: float
    ) -> List[ConstraintViolation]:
        """Get violations above a minimum severity threshold"""
        return [v for v in self.violations if v.severity >= min_severity]

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization"""
        return {
            "is_valid": self.is_valid,
            "is_feasible": self.is_feasible,
            "validation_level": self.validation_level.value,
            "total_violations": self.total_violations,
            "critical_violations": self.critical_violations,
            "violations": [v.to_dict() for v in self.violations],
            "quality_score": self.quality_score,
            "performance_metrics": self.performance_metrics,
            "validation_timestamp": self.validation_timestamp,
        }


class ConstraintValidator(ABC):
    """Abstract base class for constraint validators"""

    @abstractmethod
    def validate(self, solution_data: Dict[str, Any]) -> List[ConstraintViolation]:
        """Validate constraints and return any violations found"""
        pass

    @abstractmethod
    def get_constraint_type(self) -> ConstraintType:
        """Get the type of constraints this validator checks"""
        pass

    @abstractmethod
    def get_violation_type(self) -> ViolationType:
        """Get the type of violations this validator detects"""
        pass


class StudentConflictValidator(ConstraintValidator):
    """Validates that no student has conflicting exam schedules"""

    def validate(self, solution_data: Dict[str, Any]) -> List[ConstraintViolation]:
        violations = []

        # Get exam assignments and student registrations
        exam_assignments = solution_data.get("exam_assignments", [])
        student_registrations = solution_data.get("student_registrations", [])

        # Build student-to-exams mapping
        student_exams: DefaultDict[str, List[str]] = defaultdict(list)
        for reg in student_registrations:
            student_exams[reg["student_id"]].append(reg["course_id"])

        # Build exam time mapping
        exam_times = {}
        for assignment in exam_assignments:
            exam_times[assignment["exam_id"]] = {
                "date": assignment.get("exam_date"),
                "time_slot": assignment.get("time_slot_id"),
                "start_time": assignment.get("start_time"),
                "end_time": assignment.get("end_time"),
            }

        # Check for conflicts
        for student_id, course_ids in student_exams.items():
            student_exam_times = []
            for course_id in course_ids:
                # Find exam for this course
                exam_id = None
                for assignment in exam_assignments:
                    if assignment.get("course_id") == course_id:
                        exam_id = assignment["exam_id"]
                        break

                if exam_id and exam_id in exam_times:
                    student_exam_times.append((exam_id, exam_times[exam_id]))

            # Check for time conflicts
            for i, (exam1_id, time1) in enumerate(student_exam_times):
                for j, (exam2_id, time2) in enumerate(
                    student_exam_times[i + 1 :], i + 1
                ):
                    if self._times_overlap(time1, time2):
                        violations.append(
                            ConstraintViolation(
                                violation_type=ViolationType.STUDENT_CONFLICT,
                                constraint_type=ConstraintType.HARD,
                                severity=1.0,  # Critical violation
                                entities_involved=[student_id, exam1_id, exam2_id],
                                description=f"Student {student_id} has conflicting exams {exam1_id} and {exam2_id}",
                                suggested_fix="Reschedule one of the conflicting exams to a different time slot",
                            )
                        )

        return violations

    def _times_overlap(self, time1: Dict[str, Any], time2: Dict[str, Any]) -> bool:
        """Check if two time periods overlap"""
        # Same date check
        if time1.get("date") != time2.get("date"):
            return False

        # Same time slot check (simplified - could be more sophisticated)
        if time1.get("time_slot") == time2.get("time_slot"):
            return True

        # Detailed time overlap check if start/end times available
        start1 = time1.get("start_time")
        end1 = time1.get("end_time")
        start2 = time2.get("start_time")
        end2 = time2.get("end_time")

        if all([start1, end1, start2, end2]):
            # Add type checks to ensure we're comparing comparable types
            if (
                isinstance(end1, str)
                and isinstance(start2, str)
                and isinstance(end2, str)
                and isinstance(start1, str)
            ):
                return not (end1 <= start2 or end2 <= start1)
            # Handle other types if necessary (e.g., datetime objects)
            # For now, return False if types are not as expected
            return False

        return False

    def get_constraint_type(self) -> ConstraintType:
        return ConstraintType.HARD

    def get_violation_type(self) -> ViolationType:
        return ViolationType.STUDENT_CONFLICT


class RoomCapacityValidator(ConstraintValidator):
    """Validates room capacity constraints"""

    def validate(self, solution_data: Dict[str, Any]) -> List[ConstraintViolation]:
        violations = []

        exam_assignments = solution_data.get("exam_assignments", [])
        room_assignments = solution_data.get("room_assignments", [])
        rooms = solution_data.get("rooms", [])

        # Build room capacity mapping
        room_capacities = {}
        for room in rooms:
            room_capacities[room["id"]] = {
                "capacity": room.get("capacity", 0),
                "exam_capacity": room.get("exam_capacity", room.get("capacity", 0)),
            }

        # Check capacity violations
        for assignment in exam_assignments:
            exam_id = assignment["exam_id"]
            expected_students = assignment.get("expected_students", 0)

            # Find room assignments for this exam
            exam_rooms = [ra for ra in room_assignments if ra["exam_id"] == exam_id]

            total_allocated_capacity = 0
            for room_assignment in exam_rooms:
                room_id = room_assignment["room_id"]
                allocated = room_assignment.get("allocated_capacity", 0)

                if room_id in room_capacities:
                    room_exam_capacity = room_capacities[room_id]["exam_capacity"]

                    # Check if allocated capacity exceeds room capacity
                    if allocated > room_exam_capacity:
                        violations.append(
                            ConstraintViolation(
                                violation_type=ViolationType.ROOM_CAPACITY,
                                constraint_type=ConstraintType.HARD,
                                severity=0.9,
                                entities_involved=[exam_id, room_id],
                                description=f"Exam {exam_id} allocated {allocated} students to room {room_id} with capacity {room_exam_capacity}",
                                suggested_fix=f"Reduce allocation or find larger room",
                            )
                        )

                    total_allocated_capacity += allocated

            # Check if total capacity is sufficient
            if expected_students > total_allocated_capacity:
                shortage = expected_students - total_allocated_capacity
                violations.append(
                    ConstraintViolation(
                        violation_type=ViolationType.ROOM_CAPACITY,
                        constraint_type=ConstraintType.HARD,
                        severity=min(1.0, shortage / expected_students),
                        entities_involved=[exam_id],
                        description=f"Exam {exam_id} has capacity shortage of {shortage} students",
                        suggested_fix="Allocate additional rooms or increase room capacities",
                    )
                )

        return violations

    def get_constraint_type(self) -> ConstraintType:
        return ConstraintType.HARD

    def get_violation_type(self) -> ViolationType:
        return ViolationType.ROOM_CAPACITY


class StaffAvailabilityValidator(ConstraintValidator):
    """Validates staff availability and workload constraints"""

    def validate(self, solution_data: Dict[str, Any]) -> List[ConstraintViolation]:
        violations = []

        exam_assignments = solution_data.get("exam_assignments", [])
        staff_assignments = solution_data.get("staff_assignments", [])
        staff = solution_data.get("staff", [])
        staff_unavailability = solution_data.get("staff_unavailability", [])

        # Build staff constraints mapping
        staff_constraints = {}
        for s in staff:
            staff_constraints[s["id"]] = {
                "max_daily_sessions": s.get("max_daily_sessions", 3),
                "max_consecutive_sessions": s.get("max_consecutive_sessions", 2),
                "can_invigilate": s.get("can_invigilate", True),
            }

        # Build unavailability mapping
        unavailable: DefaultDict[
            str, Set[Tuple[Optional[str], Optional[str], Optional[str]]]
        ] = defaultdict(set)
        for ua in staff_unavailability:
            key = (ua["staff_id"], ua.get("unavailable_date"), ua.get("time_slot_id"))
            unavailable[ua["staff_id"]].add(key)

        # Check staff assignments
        staff_workload: DefaultDict[str, DefaultDict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

        for staff_assignment in staff_assignments:
            staff_id = staff_assignment["staff_id"]
            exam_id = staff_assignment["exam_id"]

            # Find exam details
            exam_details = None
            for assignment in exam_assignments:
                if assignment["exam_id"] == exam_id:
                    exam_details = assignment
                    break

            if not exam_details:
                continue

            exam_date = exam_details.get("exam_date")
            time_slot_id = exam_details.get("time_slot_id")

            # Check availability
            unavail_key = (staff_id, exam_date, time_slot_id)
            if staff_id in unavailable and unavail_key in unavailable[staff_id]:
                violations.append(
                    ConstraintViolation(
                        violation_type=ViolationType.STAFF_AVAILABILITY,
                        constraint_type=ConstraintType.HARD,
                        severity=1.0,
                        entities_involved=[staff_id, exam_id],
                        description=f"Staff {staff_id} assigned to exam {exam_id} during unavailable time",
                        suggested_fix="Assign different staff member or reschedule exam",
                    )
                )

            # Check capability
            if (
                staff_id in staff_constraints
                and not staff_constraints[staff_id]["can_invigilate"]
            ):
                violations.append(
                    ConstraintViolation(
                        violation_type=ViolationType.STAFF_AVAILABILITY,
                        constraint_type=ConstraintType.HARD,
                        severity=0.8,
                        entities_involved=[staff_id, exam_id],
                        description=f"Staff {staff_id} assigned to exam but cannot invigilate",
                        suggested_fix="Assign different qualified staff member",
                    )
                )

            # Track daily workload
            if exam_date:
                staff_workload[staff_id][exam_date] += 1

        # Check workload constraints
        for staff_id, daily_loads in staff_workload.items():
            if staff_id in staff_constraints:
                max_daily = staff_constraints[staff_id]["max_daily_sessions"]

                for date, session_count in daily_loads.items():
                    if session_count > max_daily:
                        excess = session_count - max_daily
                        violations.append(
                            ConstraintViolation(
                                violation_type=ViolationType.STAFF_AVAILABILITY,
                                constraint_type=ConstraintType.SOFT,
                                severity=min(1.0, excess / max_daily),
                                entities_involved=[staff_id],
                                description=f"Staff {staff_id} assigned {session_count} sessions on {date}, exceeding limit of {max_daily}",
                                suggested_fix="Redistribute assignments or increase staff limits",
                            )
                        )

        return violations

    def get_constraint_type(self) -> ConstraintType:
        return ConstraintType.HARD

    def get_violation_type(self) -> ViolationType:
        return ViolationType.STAFF_AVAILABILITY


class ExamRequirementsValidator(ConstraintValidator):
    """Validates exam-specific requirements (duration, special needs, etc.)"""

    def validate(self, solution_data: Dict[str, Any]) -> List[ConstraintViolation]:
        violations = []

        exam_assignments = solution_data.get("exam_assignments", [])
        exams = solution_data.get("exams", [])
        time_slots = solution_data.get("time_slots", [])
        rooms = solution_data.get("rooms", [])

        # Build lookup mappings
        exam_details = {e["id"]: e for e in exams}
        time_slot_details = {ts["id"]: ts for ts in time_slots}
        room_details = {r["id"]: r for r in rooms}

        for assignment in exam_assignments:
            exam_id = assignment["exam_id"]
            time_slot_id = assignment.get("time_slot_id")

            if exam_id not in exam_details:
                continue

            exam = exam_details[exam_id]

            # Check duration requirements
            if time_slot_id and time_slot_id in time_slot_details:
                time_slot = time_slot_details[time_slot_id]
                required_duration = exam.get("duration_minutes", 180)
                available_duration = time_slot.get("duration_minutes", 180)

                if required_duration > available_duration:
                    violations.append(
                        ConstraintViolation(
                            violation_type=ViolationType.DURATION_MISMATCH,
                            constraint_type=ConstraintType.HARD,
                            severity=1.0,
                            entities_involved=[exam_id, time_slot_id],
                            description=f"Exam {exam_id} requires {required_duration} minutes but time slot only provides {available_duration}",
                            suggested_fix="Assign to longer time slot or adjust exam duration",
                        )
                    )

            # Check morning-only requirements
            if exam.get("morning_only", False) and time_slot_id in time_slot_details:
                time_slot = time_slot_details[time_slot_id]
                start_time = time_slot.get("start_time", "")
                if isinstance(start_time, str) and start_time >= "12:00":
                    violations.append(
                        ConstraintViolation(
                            violation_type=ViolationType.EXAM_REQUIREMENTS,
                            constraint_type=ConstraintType.HARD,
                            severity=0.7,
                            entities_involved=[exam_id, time_slot_id],
                            description=f"Morning-only exam {exam_id} scheduled in afternoon slot",
                            suggested_fix="Reschedule to morning time slot",
                        )
                    )

            # Check practical exam requirements
            if exam.get("is_practical", False):
                # Find rooms assigned to this exam
                room_assignments = solution_data.get("room_assignments", [])
                exam_rooms = [
                    ra["room_id"] for ra in room_assignments if ra["exam_id"] == exam_id
                ]

                for room_id in exam_rooms:
                    if room_id in room_details:
                        room = room_details[room_id]
                        if not room.get("has_computers", False):
                            violations.append(
                                ConstraintViolation(
                                    violation_type=ViolationType.EXAM_REQUIREMENTS,
                                    constraint_type=ConstraintType.HARD,
                                    severity=0.9,
                                    entities_involved=[exam_id, room_id],
                                    description=f"Practical exam {exam_id} assigned to room {room_id} without computers",
                                    suggested_fix="Assign to computer lab or provide portable equipment",
                                )
                            )

        return violations

    def get_constraint_type(self) -> ConstraintType:
        return ConstraintType.HARD

    def get_violation_type(self) -> ViolationType:
        return ViolationType.EXAM_REQUIREMENTS


class SolutionQualityAssessor:
    """Assesses overall solution quality beyond constraint compliance"""

    def __init__(self):
        self.quality_metrics = [
            "student_travel_minimization",
            "room_utilization_efficiency",
            "staff_workload_balance",
            "exam_distribution_evenness",
            "facility_resource_optimization",
        ]

    def assess_quality(
        self, solution_data: Dict[str, Any], violations: List[ConstraintViolation]
    ) -> Dict[str, Any]:
        """Comprehensive solution quality assessment"""

        quality_scores = {}

        # Base score from constraint compliance
        total_violations = len(violations)
        critical_violations = len([v for v in violations if v.severity > 0.8])

        constraint_score = max(
            0.0, 1.0 - (critical_violations * 0.2) - (total_violations * 0.05)
        )
        quality_scores["constraint_compliance"] = constraint_score

        # Student travel assessment
        travel_score = self._assess_student_travel(solution_data)
        quality_scores["student_travel"] = travel_score

        # Room utilization assessment
        utilization_score = self._assess_room_utilization(solution_data)
        quality_scores["room_utilization"] = utilization_score

        # Staff workload balance
        workload_score = self._assess_staff_workload_balance(solution_data)
        quality_scores["staff_balance"] = workload_score

        # Time distribution assessment
        distribution_score = self._assess_exam_distribution(solution_data)
        quality_scores["exam_distribution"] = distribution_score

        # Overall weighted score
        weights = {
            "constraint_compliance": 0.4,
            "student_travel": 0.2,
            "room_utilization": 0.15,
            "staff_balance": 0.15,
            "exam_distribution": 0.1,
        }

        overall_score = sum(
            quality_scores.get(metric, 0.0) * weight
            for metric, weight in weights.items()
        )

        return {
            "overall_score": overall_score,
            "component_scores": quality_scores,
            "weights": weights,
            "assessment_timestamp": time.time(),
        }

    def _assess_student_travel(self, solution_data: Dict[str, Any]) -> float:
        """Assess student travel burden between consecutive exams"""
        # Simplified implementation - would need building/room location data
        exam_assignments = solution_data.get("exam_assignments", [])
        room_assignments = solution_data.get("room_assignments", [])

        if not exam_assignments or not room_assignments:
            return 0.5  # Neutral score if no data

        # For now, assume better distribution = higher score
        # Real implementation would calculate actual travel distances
        unique_rooms_used = len(set(ra["room_id"] for ra in room_assignments))
        total_room_assignments = len(room_assignments)

        if total_room_assignments > 0:
            room_diversity = unique_rooms_used / total_room_assignments
            return min(1.0, room_diversity * 1.5)  # Reward room diversity

        return 0.5

    def _assess_room_utilization(self, solution_data: Dict[str, Any]) -> float:
        """Assess efficiency of room utilization"""
        room_assignments = solution_data.get("room_assignments", [])
        rooms = solution_data.get("rooms", [])

        if not room_assignments or not rooms:
            return 0.5

        room_capacities = {
            r["id"]: r.get("exam_capacity", r.get("capacity", 0)) for r in rooms
        }

        utilization_rates = []
        for assignment in room_assignments:
            room_id = assignment["room_id"]
            allocated = assignment.get("allocated_capacity", 0)

            if room_id in room_capacities and room_capacities[room_id] > 0:
                utilization = allocated / room_capacities[room_id]
                utilization_rates.append(min(1.0, utilization))

        if utilization_rates:
            avg_utilization = sum(utilization_rates) / len(utilization_rates)
            # Reward high utilization but penalize over-utilization
            return max(0.0, min(1.0, avg_utilization))

        return 0.5

    def _assess_staff_workload_balance(self, solution_data: Dict[str, Any]) -> float:
        """Assess balance of staff workload distribution"""
        staff_assignments = solution_data.get("staff_assignments", [])

        if not staff_assignments:
            return 0.5

        # Count assignments per staff member
        staff_loads: DefaultDict[str, int] = defaultdict(int)
        for assignment in staff_assignments:
            staff_loads[assignment["staff_id"]] += 1

        if len(staff_loads) < 2:
            return 0.5

        # Calculate coefficient of variation (lower is better balance)
        loads = list(staff_loads.values())
        mean_load = sum(loads) / len(loads)

        if mean_load > 0:
            variance = sum((load - mean_load) ** 2 for load in loads) / len(loads)
            std_dev = variance**0.5
            cv = std_dev / mean_load

            # Convert CV to score (0 = perfect balance, higher CV = lower score)
            balance_score = max(0.0, 1.0 - cv)
            return balance_score

        return 0.5

    def _assess_exam_distribution(self, solution_data: Dict[str, Any]) -> float:
        """Assess temporal distribution of exams"""
        exam_assignments = solution_data.get("exam_assignments", [])

        if not exam_assignments:
            return 0.5

        # Count exams per day
        daily_counts: DefaultDict[str, int] = defaultdict(int)
        for assignment in exam_assignments:
            exam_date = assignment.get("exam_date")
            if exam_date:
                daily_counts[exam_date] += 1

        if len(daily_counts) < 2:
            return 0.5

        # Calculate distribution evenness
        counts = list(daily_counts.values())
        mean_count = sum(counts) / len(counts)

        if mean_count > 0:
            variance = sum((count - mean_count) ** 2 for count in counts) / len(counts)
            std_dev = variance**0.5
            cv = std_dev / mean_count  # Fixed: use mean_count instead of mean_load

            # Reward even distribution
            evenness_score = max(0.0, 1.0 - cv * 0.5)
            return evenness_score

        return 0.5


class ComprehensiveSolutionValidator:
    """
    Main validation engine that coordinates all constraint validators
    and quality assessment for comprehensive solution validation.
    """

    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        self.validation_level = validation_level
        self.validators: List[ConstraintValidator] = []
        self.quality_assessor = SolutionQualityAssessor()

        # Register standard validators
        self._register_default_validators()

    def _register_default_validators(self):
        """Register the default set of constraint validators"""
        self.validators = [
            StudentConflictValidator(),
            RoomCapacityValidator(),
            StaffAvailabilityValidator(),
            ExamRequirementsValidator(),
        ]

    def add_validator(self, validator: ConstraintValidator):
        """Add a custom validator to the validation pipeline"""
        self.validators.append(validator)

    def remove_validator(self, validator_type: type):
        """Remove validators of a specific type"""
        self.validators = [
            v for v in self.validators if not isinstance(v, validator_type)
        ]

    def validate_solution(
        self,
        solution_data: Dict[str, Any],
        include_quality_assessment: bool = True,
        detailed_logging: bool = False,
    ) -> ValidationResult:
        """
        Comprehensive solution validation with constraint checking
        and quality assessment.
        """
        start_time = time.time()

        all_violations = []
        validation_metadata: Dict[str, Any] = {
            "validators_run": [],
            "validation_times": {},
        }

        # Run all constraint validators
        for validator in self.validators:
            validator_start = time.time()

            try:
                violations = validator.validate(solution_data)
                all_violations.extend(violations)

                validator_time = time.time() - validator_start
                validator_name = validator.__class__.__name__

                validation_metadata["validators_run"].append(validator_name)
                validation_metadata["validation_times"][validator_name] = validator_time

                if detailed_logging:
                    print(
                        f"Validator {validator_name}: {len(violations)} violations found in {validator_time:.3f}s"
                    )

            except Exception as e:
                # Log validator error but continue with other validators
                validation_metadata[f"error_{validator.__class__.__name__}"] = str(e)
                if detailed_logging:
                    print(f"Error in validator {validator.__class__.__name__}: {e}")

        # Analyze violations
        total_violations = len(all_violations)
        critical_violations = len([v for v in all_violations if v.severity > 0.8])

        # Determine feasibility and validity
        hard_violations = [
            v for v in all_violations if v.constraint_type == ConstraintType.HARD
        ]
        is_feasible = len(hard_violations) == 0
        is_valid = is_feasible and critical_violations == 0

        # Quality assessment
        quality_score = 0.0
        if include_quality_assessment:
            quality_start = time.time()
            quality_results = self.quality_assessor.assess_quality(
                solution_data, all_violations
            )
            quality_score = quality_results.get("overall_score", 0.0)
            validation_metadata["quality_assessment_time"] = time.time() - quality_start
            validation_metadata["quality_details"] = quality_results

        total_time = time.time() - start_time

        # Create result
        result = ValidationResult(
            is_valid=is_valid,
            is_feasible=is_feasible,
            validation_level=self.validation_level,
            total_violations=total_violations,
            critical_violations=critical_violations,
            violations=all_violations,
            quality_score=quality_score,
            performance_metrics={
                "total_validation_time": total_time,
                "validators_count": len(self.validators),
                **validation_metadata,
            },
            validation_timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        return result

    def validate_incremental_change(
        self, solution_data: Dict[str, Any], change_description: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate only the constraints affected by an incremental change
        for efficient re-validation after modifications.
        """
        # Identify affected validators based on change type
        affected_validators = self._identify_affected_validators(change_description)

        # Temporarily store all validators and set only affected ones
        all_validators = self.validators
        self.validators = affected_validators

        try:
            # Run validation on affected constraints only
            result = self.validate_solution(
                solution_data, include_quality_assessment=False
            )
            result.performance_metrics["incremental_validation"] = True
            result.performance_metrics["affected_validators"] = len(affected_validators)
            return result

        finally:
            # Restore all validators
            self.validators = all_validators

    def _identify_affected_validators(
        self, change_description: Dict[str, Any]
    ) -> List[ConstraintValidator]:
        """Identify which validators need to run based on the type of change made"""
        change_type = change_description.get("change_type", "unknown")
        affected_entities = change_description.get("affected_entities", [])

        # Map change types to relevant validators
        validator_mapping = {
            "exam_time_change": [StudentConflictValidator, StaffAvailabilityValidator],
            "room_assignment_change": [RoomCapacityValidator],
            "staff_assignment_change": [StaffAvailabilityValidator],
            "exam_requirements_change": [ExamRequirementsValidator],
        }

        relevant_validator_types = validator_mapping.get(
            change_type, [type(v) for v in self.validators]
        )

        # Convert to tuple for isinstance check
        relevant_validator_types_tuple: Tuple[Type[ConstraintValidator], ...] = tuple(
            relevant_validator_types  # type: ignore
        )

        # Return instances of relevant validator types
        return [
            v for v in self.validators if isinstance(v, relevant_validator_types_tuple)
        ]

    def generate_validation_report(self, result: ValidationResult) -> Dict[str, Any]:
        """Generate a comprehensive validation report"""

        # Group violations by type and severity
        violations_by_type = defaultdict(list)
        violations_by_severity: Dict[str, List[ConstraintViolation]] = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
        }

        for violation in result.violations:
            violations_by_type[violation.violation_type.value].append(violation)

            if violation.severity > 0.8:
                violations_by_severity["critical"].append(violation)
            elif violation.severity > 0.6:
                violations_by_severity["high"].append(violation)
            elif violation.severity > 0.4:
                violations_by_severity["medium"].append(violation)
            else:
                violations_by_severity["low"].append(violation)

        # Generate summary statistics
        violation_summary = {
            violation_type: len(violations)
            for violation_type, violations in violations_by_type.items()
        }

        severity_summary = {
            severity: len(violations)
            for severity, violations in violations_by_severity.items()
        }

        # Create comprehensive report
        report = {
            "validation_summary": {
                "is_valid": result.is_valid,
                "is_feasible": result.is_feasible,
                "validation_level": result.validation_level.value,
                "quality_score": result.quality_score,
                "validation_timestamp": result.validation_timestamp,
            },
            "violation_statistics": {
                "total_violations": result.total_violations,
                "critical_violations": result.critical_violations,
                "violations_by_type": violation_summary,
                "violations_by_severity": severity_summary,
            },
            "detailed_violations": [v.to_dict() for v in result.violations],
            "performance_metrics": result.performance_metrics,
            "recommendations": self._generate_recommendations(result),
        }

        return report

    def _generate_recommendations(self, result: ValidationResult) -> List[str]:
        """Generate actionable recommendations based on validation results"""
        recommendations = []

        if not result.is_feasible:
            recommendations.append(
                "Solution is infeasible. Address hard constraint violations first."
            )

        if result.critical_violations > 0:
            recommendations.append(
                f"Resolve {result.critical_violations} critical violations before deployment."
            )

        if result.quality_score < 0.6:
            recommendations.append(
                "Solution quality is below acceptable threshold. Consider optimization."
            )

        # Specific recommendations based on violation types
        violation_types = {v.violation_type for v in result.violations}

        if ViolationType.STUDENT_CONFLICT in violation_types:
            recommendations.append(
                "Student scheduling conflicts detected. Review time slot assignments."
            )

        if ViolationType.ROOM_CAPACITY in violation_types:
            recommendations.append(
                "Room capacity issues found. Consider room reallocation or capacity adjustments."
            )

        if ViolationType.STAFF_AVAILABILITY in violation_types:
            recommendations.append(
                "Staff availability problems identified. Review staff assignments and constraints."
            )

        return recommendations

    def export_validation_results(
        self, result: ValidationResult, filepath: str, format: str = "json"
    ):
        """Export validation results to file"""
        report = self.generate_validation_report(result)

        if format.lower() == "json":
            with open(filepath, "w") as f:
                json.dump(report, f, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Utility functions for validation
def quick_validate(
    solution_data: Dict[str, Any], level: ValidationLevel = ValidationLevel.BASIC
) -> bool:
    """Quick validation check returning only feasibility status"""
    validator = ComprehensiveSolutionValidator(validation_level=level)
    result = validator.validate_solution(
        solution_data, include_quality_assessment=False
    )
    return result.is_feasible


def validate_with_report(solution_data: Dict[str, Any]) -> Dict[str, Any]:
    """Comprehensive validation with full report generation"""
    validator = ComprehensiveSolutionValidator(
        validation_level=ValidationLevel.COMPREHENSIVE
    )
    result = validator.validate_solution(solution_data, include_quality_assessment=True)
    return validator.generate_validation_report(result)
