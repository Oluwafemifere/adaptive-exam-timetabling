# scheduling_engine/constraints/soft_constraints/student_travel.py

"""
Student Travel Soft Constraint

This constraint minimizes student travel between exam locations by optimizing
room assignments based on student movement patterns, building proximity,
and transportation convenience.
"""

from typing import Dict, List, Any, Optional, Tuple, DefaultDict
from uuid import UUID
import logging
from collections import defaultdict
from dataclasses import dataclass
import math

from ..enhanced_base_constraint import EnhancedBaseConstraint
from ...core.constraint_registry import (
    ConstraintDefinition,
    ConstraintType,
    ConstraintCategory,
    ConstraintViolation,
    ConstraintSeverity,
)
from ...core.problem_model import ExamSchedulingProblem
from ...core.solution import TimetableSolution

logger = logging.getLogger(__name__)


@dataclass
class StudentTravelViolation:
    """Represents a student travel inconvenience"""

    violation_type: str  # 'long_distance', 'cross_building', 'short_gap_travel', 'accessibility_issue'
    student_id: UUID
    exam_sequence: List[Tuple[UUID, UUID, UUID]]  # [(exam_id, room_id, time_slot_id)]
    source_room_id: UUID
    destination_room_id: UUID
    travel_distance: float  # Estimated distance
    travel_time_minutes: float  # Estimated travel time
    gap_between_exams_minutes: float  # Time gap between exams
    severity: float = 1.0


class StudentTravelConstraint(EnhancedBaseConstraint):
    """
    Soft constraint optimizing student travel convenience.

    This constraint minimizes the travel burden on students by considering
    the physical distance and time required to move between exam locations,
    especially for consecutive exams with short gaps.

    Supports database configuration for:
    - Maximum reasonable travel time thresholds
    - Critical gap thresholds for travel optimization
    - Building change and floor change penalties
    - Distance-based penalty calculations
    """

    def __init__(self, **kwargs):
        super().__init__(
            constraint_id="STUDENT_TRAVEL",
            name="Student Travel Optimization",
            constraint_type=ConstraintType.SOFT,
            category=ConstraintCategory.CONVENIENCE_CONSTRAINTS,
            weight=0.4,
            parameters={
                "max_reasonable_travel_time": 15,
                "critical_gap_threshold": 30,
                "building_change_penalty": 200,
                "floor_change_penalty": 50,
                "distance_penalty_per_meter": 0.1,
                "accessibility_priority": True,
                "transportation_consideration": True,
                "travel_calculation_method": "euclidean",
            },
            **kwargs,
        )

        self.student_exam_mapping: DefaultDict[UUID, List[UUID]] = defaultdict(list)
        self.room_locations: Dict[UUID, Dict[str, Any]] = {}
        self.building_coordinates: Dict[UUID, Tuple[float, float]] = {}
        self.travel_matrix: Dict[Tuple[UUID, UUID], float] = {}
        self.time_slot_ordering: Dict[UUID, int] = {}

    def get_definition(self) -> ConstraintDefinition:
        """Get constraint definition for registration"""
        return ConstraintDefinition(
            constraint_id=self.constraint_id,
            name=self.name,
            description="Minimizes student travel between exam locations",
            constraint_type=self.constraint_type,
            category=self.category,
            parameters=self.parameters,
            validation_rules=[
                "Minimize travel distance between consecutive exams",
                "Prioritize same-building exam sequences",
                "Consider accessibility requirements",
                "Balance travel convenience with room utilization",
                "Account for transportation availability",
            ],
            constraint_class=type(self),
            is_configurable=True,
        )

    def _initialize_implementation(
        self,
        problem: "ExamSchedulingProblem",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize constraint with location and student data"""
        try:
            self.student_exam_mapping.clear()
            self.room_locations.clear()
            self.building_coordinates.clear()
            self.travel_matrix.clear()
            self.time_slot_ordering.clear()

            # Build student-exam mapping
            for registration in problem.course_registrations.values():
                student_id = registration.student_id
                course_id = registration.course_id

                # Find exams for this course
                course_exams = [
                    exam
                    for exam in problem.exams.values()
                    if exam.course_id == course_id
                ]

                for exam in course_exams:
                    self.student_exam_mapping[student_id].append(exam.id)

            # Extract building and room location information
            self._initialize_location_data(problem)

            # Build travel distance matrix
            self._build_travel_matrix()

            # Create time slot ordering
            sorted_slots = sorted(
                problem.time_slots.values(),
                key=lambda s: (
                    getattr(s, "date", "9999-12-31"),
                    getattr(s, "start_time", "23:59"),
                ),
            )

            for i, slot in enumerate(sorted_slots):
                self.time_slot_ordering[slot.id] = i

            logger.info(
                f"Initialized student travel constraint: "
                f"{len(self.student_exam_mapping)} students, "
                f"{len(self.room_locations)} rooms, "
                f"{len(self.building_coordinates)} buildings"
            )

        except Exception as e:
            logger.error(f"Error initializing student travel constraint: {e}")
            raise

    def _initialize_location_data(self, problem: "ExamSchedulingProblem") -> None:
        """Initialize location data for buildings and rooms"""
        try:
            # Extract building information
            building_info = {}
            buildings = getattr(problem, "buildings", {})

            for building in buildings.values():
                building_info[building.id] = {
                    "name": getattr(building, "name", ""),
                    "code": getattr(building, "code", ""),
                    "coordinates": getattr(building, "coordinates", None),
                }

                # Set default coordinates if not provided
                coords = getattr(building, "coordinates", None)
                if coords and len(coords) >= 2:
                    self.building_coordinates[building.id] = (coords[0], coords[1])
                else:
                    # Use simple grid-based default coordinates
                    building_index = len(self.building_coordinates)
                    self.building_coordinates[building.id] = (
                        (building_index % 10) * 100,  # x coordinate
                        (building_index // 10) * 100,  # y coordinate
                    )

            # Extract room location information
            for room in problem.rooms.values():
                building_id = getattr(room, "building_id", None)
                floor_number = getattr(room, "floor_number", 1)

                self.room_locations[room.id] = {
                    "building_id": building_id,
                    "building_info": building_info.get(building_id, {}),
                    "floor_number": floor_number,
                    "accessibility_features": getattr(
                        room, "accessibility_features", []
                    ),
                    "coordinates": self._calculate_room_coordinates(
                        room.id, building_id, floor_number
                    ),
                }

        except Exception as e:
            logger.error(f"Error initializing location data: {e}")

    def _calculate_room_coordinates(
        self, room_id: UUID, building_id: Optional[UUID], floor_number: int
    ) -> Tuple[float, float]:
        """Calculate estimated coordinates for a room"""
        try:
            if building_id and building_id in self.building_coordinates:
                building_x, building_y = self.building_coordinates[building_id]

                # Add floor offset (rooms on different floors are slightly apart)
                floor_offset = floor_number * 2

                # Add room-specific offset (simple hash-based distribution)
                room_hash = hash(str(room_id)) % 100
                room_offset_x = (room_hash % 10) * 5
                room_offset_y = ((room_hash // 10) % 10) * 5

                return (
                    building_x + room_offset_x + floor_offset,
                    building_y + room_offset_y + floor_offset,
                )
            else:
                # Default coordinates if building not found
                room_hash = hash(str(room_id)) % 10000
                return (room_hash % 100, room_hash // 100)

        except Exception as e:
            logger.error(f"Error calculating room coordinates: {e}")
            return (0.0, 0.0)

    def _build_travel_matrix(self) -> None:
        """Build matrix of travel distances between all room pairs"""
        try:
            room_ids = list(self.room_locations.keys())

            for i, room1_id in enumerate(room_ids):
                for j, room2_id in enumerate(room_ids):
                    if i <= j:  # Only calculate upper triangle (symmetric matrix)
                        distance = self._calculate_travel_distance(room1_id, room2_id)
                        self.travel_matrix[(room1_id, room2_id)] = distance
                        self.travel_matrix[(room2_id, room1_id)] = distance  # Symmetric

            logger.info(
                f"Built travel matrix with {len(self.travel_matrix)} distance calculations"
            )

        except Exception as e:
            logger.error(f"Error building travel matrix: {e}")

    def _calculate_travel_distance(self, room1_id: UUID, room2_id: UUID) -> float:
        """Calculate travel distance between two rooms"""
        try:
            if room1_id == room2_id:
                return 0.0

            room1_info = self.room_locations.get(room1_id, {})
            room2_info = self.room_locations.get(room2_id, {})

            # Get room coordinates
            coords1 = room1_info.get("coordinates", (0, 0))
            coords2 = room2_info.get("coordinates", (0, 0))

            # Basic Euclidean distance
            dx = coords2[0] - coords1[0]
            dy = coords2[1] - coords1[1]
            base_distance = math.sqrt(dx * dx + dy * dy)

            # Add penalties for building/floor changes
            building1 = room1_info.get("building_id")
            building2 = room2_info.get("building_id")
            floor1 = room1_info.get("floor_number", 1)
            floor2 = room2_info.get("floor_number", 1)

            distance_penalty = 0.0

            # Different buildings add significant travel time
            if building1 != building2:
                distance_penalty += self.get_parameter("building_change_penalty", 200)
            # Different floors within same building
            elif abs(floor1 - floor2) > 0:
                distance_penalty += abs(floor1 - floor2) * self.get_parameter(
                    "floor_change_penalty", 50
                )

            return base_distance + distance_penalty

        except Exception as e:
            logger.error(f"Error calculating travel distance: {e}")
            return 1000.0  # Large default distance

    def _evaluate_implementation(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """Evaluate constraint against solution"""
        violations = []

        try:
            # Component 1: Consecutive exam travel violations
            travel_violations = self._evaluate_travel_violations(problem, solution)
            violations.extend(travel_violations)

            # Component 2: Overall distribution violations
            distribution_violations = self._evaluate_distribution_violations(
                problem, solution
            )
            violations.extend(distribution_violations)

        except Exception as e:
            logger.error(f"Error evaluating student travel constraint: {e}")

        return violations

    def _evaluate_travel_violations(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """Evaluate travel violations for consecutive exams"""
        violations = []

        try:
            critical_gap = self.get_parameter("critical_gap_threshold", 30)

            for student_id, exam_ids in self.student_exam_mapping.items():
                if len(exam_ids) <= 1:
                    continue

                # Get this student's exam schedule with locations
                student_schedule = []
                for exam_id in exam_ids:
                    assignment = solution.assignments.get(exam_id)
                    if assignment and assignment.time_slot_id and assignment.room_ids:
                        slot_order = self.time_slot_ordering.get(
                            assignment.time_slot_id, 0
                        )
                        # Use first room assignment for simplicity
                        room_id = assignment.room_ids[0]
                        student_schedule.append(
                            (exam_id, room_id, assignment.time_slot_id, slot_order)
                        )

                if len(student_schedule) <= 1:
                    continue

                # Sort by time slot order
                student_schedule.sort(key=lambda x: x[3])

                # Check travel violations for consecutive exams
                for i in range(len(student_schedule) - 1):
                    exam1_id, room1_id, slot1_id, order1 = student_schedule[i]
                    exam2_id, room2_id, slot2_id, order2 = student_schedule[i + 1]

                    # Calculate time gap between exams
                    gap_slots = order2 - order1
                    gap_minutes = gap_slots * 180  # Assume 3-hour average slot duration

                    # Get travel distance
                    travel_distance = self.travel_matrix.get(
                        (room1_id, room2_id), 1000.0
                    )

                    # Check for violations
                    if travel_distance > 200 or (
                        travel_distance > 100 and gap_minutes < 60
                    ):
                        severity = min(1.0, travel_distance / 500)
                        if gap_minutes < 60:
                            severity = min(1.0, severity * (60 / max(gap_minutes, 10)))

                        penalty = travel_distance * self.get_parameter(
                            "distance_penalty_per_meter", 0.1
                        )

                        if gap_minutes < critical_gap:
                            penalty *= 2  # Double penalty for critical gaps

                        violation = ConstraintViolation(
                            constraint_id=self.id,
                            violation_id=UUID(),
                            severity=(
                                ConstraintSeverity.MEDIUM
                                if travel_distance > 200
                                else ConstraintSeverity.LOW
                            ),
                            affected_exams=[exam1_id, exam2_id],
                            affected_resources=[student_id, room1_id, room2_id],
                            description=f"Student {student_id} travels {travel_distance:.0f}m "
                            f"in {gap_minutes:.0f}min gap between exams",
                            penalty=penalty,
                        )
                        violations.append(violation)

        except Exception as e:
            logger.error(f"Error evaluating travel violations: {e}")

        return violations

    def _evaluate_distribution_violations(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """Evaluate overall spatial distribution violations"""
        violations = []

        try:
            # Count cross-building movements
            total_movements = 0
            cross_building_movements = 0

            for student_id, exam_ids in self.student_exam_mapping.items():
                if len(exam_ids) <= 1:
                    continue

                # Get buildings for this student's exams
                student_buildings = []
                for exam_id in exam_ids:
                    assignment = solution.assignments.get(exam_id)
                    if assignment and assignment.room_ids:
                        room_id = assignment.room_ids[0]
                        room_info = self.room_locations.get(room_id, {})
                        building_id = room_info.get("building_id")
                        if building_id:
                            student_buildings.append(building_id)

                if len(student_buildings) <= 1:
                    continue

                # Count movements between buildings
                for i in range(len(student_buildings) - 1):
                    total_movements += 1
                    if student_buildings[i] != student_buildings[i + 1]:
                        cross_building_movements += 1

            # Overall cross-building movement penalty
            if total_movements > 0:
                cross_building_ratio = cross_building_movements / total_movements

                if cross_building_ratio > 0.3:  # More than 30% cross-building movements
                    penalty = (cross_building_ratio - 0.3) * 1000

                    violation = ConstraintViolation(
                        constraint_id=self.id,
                        violation_id=UUID(),
                        severity=ConstraintSeverity.MEDIUM,
                        affected_exams=[],
                        affected_resources=[],
                        description=f"High cross-building movement rate: {cross_building_ratio:.1%} "
                        f"({cross_building_movements}/{total_movements})",
                        penalty=penalty,
                    )
                    violations.append(violation)

        except Exception as e:
            logger.error(f"Error evaluating distribution violations: {e}")

        return violations

    def _estimate_travel_time(self, distance: float) -> float:
        """Estimate travel time based on distance"""
        # Assume walking speed of 5 km/h (83.3 m/min)
        # Add 2 minutes base time for room finding, etc.
        base_time = 2.0
        walking_time = distance / 83.3
        return base_time + walking_time

    def validate_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Validate constraint parameters"""
        errors = super().validate_parameters(parameters)

        max_travel = parameters.get("max_reasonable_travel_time", 15)
        if max_travel <= 0:
            errors.append("max_reasonable_travel_time must be positive")

        critical_gap = parameters.get("critical_gap_threshold", 30)
        if critical_gap <= 0:
            errors.append("critical_gap_threshold must be positive")

        building_penalty = parameters.get("building_change_penalty", 200)
        floor_penalty = parameters.get("floor_change_penalty", 50)

        if building_penalty < 0 or floor_penalty < 0:
            errors.append("Penalty values cannot be negative")

        distance_penalty = parameters.get("distance_penalty_per_meter", 0.1)
        if distance_penalty < 0:
            errors.append("distance_penalty_per_meter cannot be negative")

        return errors

    def get_travel_statistics(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> Dict[str, Any]:
        """Get detailed statistics about student travel patterns"""
        # Collect travel statistics
        total_students = len(self.student_exam_mapping)
        students_with_travel = 0
        total_travel_distance = 0.0
        cross_building_movements = 0
        total_movements = 0
        travel_distances = []

        for student_id, exam_ids in self.student_exam_mapping.items():
            if len(exam_ids) <= 1:
                continue

            students_with_travel += 1
            student_distance = 0.0
            student_buildings = set()

            # Get this student's exam locations
            student_rooms = []
            for exam_id in exam_ids:
                assignment = solution.assignments.get(exam_id)
                if assignment and assignment.room_ids:
                    room_id = assignment.room_ids[0]
                    student_rooms.append(room_id)

                    # Track buildings
                    room_info = self.room_locations.get(room_id, {})
                    building_id = room_info.get("building_id")
                    if building_id:
                        student_buildings.add(building_id)

            # Calculate travel distances for consecutive exams
            for i in range(len(student_rooms) - 1):
                room1_id = student_rooms[i]
                room2_id = student_rooms[i + 1]

                distance = self.travel_matrix.get((room1_id, room2_id), 0)
                student_distance += distance
                travel_distances.append(distance)

                # Check for cross-building movement
                room1_building = self.room_locations.get(room1_id, {}).get(
                    "building_id"
                )
                room2_building = self.room_locations.get(room2_id, {}).get(
                    "building_id"
                )

                total_movements += 1
                if room1_building != room2_building:
                    cross_building_movements += 1

            total_travel_distance += student_distance

        avg_travel_distance = total_travel_distance / max(students_with_travel, 1)
        cross_building_ratio = cross_building_movements / max(total_movements, 1)

        return {
            "total_students": total_students,
            "students_with_travel": students_with_travel,
            "average_travel_distance": avg_travel_distance,
            "total_travel_distance": total_travel_distance,
            "cross_building_movements": cross_building_movements,
            "total_movements": total_movements,
            "cross_building_ratio": cross_building_ratio,
            "travel_distances": {
                "min": min(travel_distances) if travel_distances else 0,
                "max": max(travel_distances) if travel_distances else 0,
                "average": sum(travel_distances) / max(len(travel_distances), 1),
            },
            "constraint_parameters": self.parameters,
        }

    def clone(
        self,
        new_weight: Optional[float] = None,
        new_parameters: Optional[Dict[str, Any]] = None,
    ) -> "StudentTravelConstraint":
        """Create a copy of this constraint with optional modifications"""
        kwargs = {
            "parameters": self.parameters.copy(),
            "database_config": self.database_config.copy(),
        }

        if new_parameters:
            kwargs["parameters"].update(new_parameters)

        clone = StudentTravelConstraint(**kwargs)

        if new_weight is not None:
            clone.weight = new_weight

        return clone
