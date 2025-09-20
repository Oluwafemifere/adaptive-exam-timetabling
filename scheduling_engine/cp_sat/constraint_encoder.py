# FIXED: constraint_encoder.py
# Minimal pruning to preserve all necessary variables
from typing import TYPE_CHECKING
from datetime import date, timedelta
from types import MappingProxyType
from ortools.sat.python import cp_model
from dataclasses import dataclass
from typing import Dict, Set, Any, List, Optional, Union, Tuple
import logging
import math
import uuid
from uuid import UUID
import random
import time
import psutil
import os

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..core.problem_model import (
        ExamSchedulingProblem,
    )


class VariableFactory:
    """Factory for creating canonical variables with UUID keys only"""

    def __init__(self, model):
        self.model = model
        self.cache = {}
        self.creation_stats = {"x_vars": 0, "z_vars": 0, "y_vars": 0, "u_vars": 0}

    def get_x_var(self, exam_id: UUID, slot_id: UUID):
        """Create exam start variable with UUID naming"""
        key = f"x_{exam_id}_{slot_id}"
        if key not in self.cache:
            self.cache[key] = self.model.NewBoolVar(key)
            self.creation_stats["x_vars"] += 1
        return self.cache[key]

    def get_z_var(self, exam_id: UUID, slot_id: UUID):
        """z variables for exam-slot occupancy with UUID keys"""
        key = f"z_{exam_id}_{slot_id}"
        if key not in self.cache:
            self.cache[key] = self.model.NewBoolVar(key)
            self.creation_stats["z_vars"] += 1
        return self.cache[key]

    def get_y_var(self, exam_id: UUID, room_id: UUID, slot_id: UUID):
        """Create room assignment variable with UUID naming"""
        key = f"y_{exam_id}_{room_id}_{slot_id}"
        if key not in self.cache:
            self.cache[key] = self.model.NewBoolVar(key)
            self.creation_stats["y_vars"] += 1
        return self.cache[key]

    def get_u_var(
        self, invigilator_id: UUID, exam_id: UUID, room_id: UUID, slot_id: UUID
    ):
        """Create invigilator assignment variable with UUID naming"""
        key = f"u_{invigilator_id}_{exam_id}_{room_id}_{slot_id}"
        if key not in self.cache:
            self.cache[key] = self.model.NewBoolVar(key)
            self.creation_stats["u_vars"] += 1
        return self.cache[key]

    def get_stats(self):
        """Get variable creation statistics"""
        return self.creation_stats.copy()


@dataclass(frozen=True)
class SharedVariables:
    """Shared variables with UUID key types"""

    x_vars: MappingProxyType  # (exam_id: UUID, slot_id: UUID) -> BoolVar
    z_vars: MappingProxyType  # (exam_id: UUID, slot_id: UUID) -> BoolVar
    y_vars: MappingProxyType  # (exam_id: UUID, room_id: UUID, slot_id: UUID) -> BoolVar
    u_vars: MappingProxyType  # (invigilator_id: UUID, exam_id: UUID, room_id: UUID, slot_id: UUID) -> BoolVar
    precomputed_data: MappingProxyType  # All precomputed data


class ConstraintEncoder:
    """Constraint encoder with minimal pruning to preserve schedule integrity"""

    def __init__(self, problem, model: cp_model.CpModel):
        self.problem = problem
        self.model = model
        self.factory = VariableFactory(model)

    def encode(self) -> SharedVariables:
        """Encode with UUID keys only and minimal pruning"""
        logger.info("Starting UUID-only variable encoding with minimal pruning...")

        # CRITICAL FIX: Use Day-centric timeslot access
        if not hasattr(self.problem, "days") or not self.problem.days:
            logger.error("CRITICAL: Problem model missing required 'days' attribute")
            raise AttributeError(
                "Problem model missing required 'days' attribute. "
                "Ensure the problem instance has a 'days' property populated with Day objects."
            )

        timeslots = self.problem.timeslots
        if not timeslots:
            logger.error("CRITICAL: Problem timeslots is empty")
            raise ValueError(
                "Problem timeslots dictionary is empty. "
                "Ensure days are properly generated in the problem instance."
            )

        logger.info(
            f"Problem has {len(timeslots)} timeslots from {len(self.problem.days)} days"
        )

        # Precompute all required data with UUID keys
        precomputed = self._precompute_all_data()

        # Create variables using precomputed data
        x_vars = self._create_x_vars(precomputed)
        z_vars = self._create_z_vars(precomputed)
        y_vars = self._create_y_vars(precomputed)
        u_vars = self._create_u_vars(precomputed)

        # Add binding constraints
        logger.info("Adding binding constraints: sum(y) == x")
        for (exam_id, slot_id), x_var in x_vars.items():
            room_vars = [
                y_vars.get((exam_id, room_id, slot_id), self.model.NewConstant(0))
                for room_id in precomputed["allowed_rooms"].get(exam_id, [])
            ]
            if room_vars:
                self.model.Add(sum(room_vars) == x_var)

        return SharedVariables(
            x_vars=MappingProxyType(x_vars),
            z_vars=MappingProxyType(z_vars),
            y_vars=MappingProxyType(y_vars),
            u_vars=MappingProxyType(u_vars),
            precomputed_data=MappingProxyType(precomputed),
        )

    def _precompute_all_data(self) -> Dict[str, Any]:
        """Precompute data with minimal pruning"""
        day_slot_groupings = self._precompute_day_slot_groupings()

        precomputed_data = {
            "day_slot_groupings": day_slot_groupings,
            "conflict_pairs": self._precompute_conflict_pairs_enhanced(),
            "allowed_start_slots": self._precompute_allowed_start_slots(
                day_slot_groupings
            ),
            "student_exams": self._precompute_student_exams_enhanced(),
            "room_metadata": self._precompute_room_metadata(),
            "invigilator_availability": self._precompute_invigilator_availability_enhanced(),
            "allowed_rooms": self._precompute_allowed_rooms_enhanced(),
            "potential_y_combinations": self._precompute_potential_y_combinations(),
        }

        return precomputed_data

    def _precompute_potential_y_combinations(self) -> Set[Tuple[UUID, UUID, UUID]]:
        """Precompute all potential exam-room-slot combinations"""
        combinations = set()

        for exam_id in self.problem.exams:
            for room_id in self.problem.rooms:
                for slot_id in self.problem.timeslots:
                    combinations.add((exam_id, room_id, slot_id))

        return combinations

    def _precompute_conflict_pairs_enhanced(self) -> Set[Tuple[UUID, UUID]]:
        """Compute student conflict pairs with ALL student data"""
        logger.info("Computing student conflict pairs with ALL student data...")
        conflict_pairs = set()

        if (
            not hasattr(self.problem, "_student_courses")
            or not self.problem._student_courses
        ):
            logger.error("CRITICAL: No student course data - NO CONFLICTS GENERATED!")
            return conflict_pairs

        # Create course to exam mapping
        course_to_exams = {}
        for exam in self.problem.exams.values():
            course_id = exam.course_id
            if course_id not in course_to_exams:
                course_to_exams[course_id] = []
            course_to_exams[course_id].append(exam.id)

        # Process ALL students
        for student_id, course_ids in self.problem._student_courses.items():
            student_exam_ids = []
            for course_id in course_ids:
                if course_id in course_to_exams:
                    student_exam_ids.extend(course_to_exams[course_id])

            # Create conflict pairs
            if len(student_exam_ids) > 1:
                exam_ids_list = list(student_exam_ids)
                for i in range(len(exam_ids_list)):
                    for j in range(i + 1, len(exam_ids_list)):
                        exam1_id = exam_ids_list[i]
                        exam2_id = exam_ids_list[j]
                        pair = (min(exam1_id, exam2_id), max(exam1_id, exam2_id))
                        conflict_pairs.add(pair)

        logger.info(
            f"Generated {len(conflict_pairs)} conflict pairs from ALL student data"
        )
        return conflict_pairs

    def _precompute_student_exams_enhanced(self) -> Dict[UUID, Set[UUID]]:
        """Compute ALL student-exam mappings"""
        logger.info("Computing ALL student-exam mappings...")
        student_exams = {}

        if (
            not hasattr(self.problem, "_student_courses")
            or not self.problem._student_courses
        ):
            logger.error("CRITICAL: No student course data for mappings!")
            return student_exams

        # Create course to exam mapping
        course_to_exams = {}
        for exam in self.problem.exams.values():
            course_id = exam.course_id
            if course_id not in course_to_exams:
                course_to_exams[course_id] = []
            course_to_exams[course_id].append(exam.id)

        # Process ALL students
        for student_id, course_ids in self.problem._student_courses.items():
            student_exams[student_id] = set()
            for course_id in course_ids:
                if course_id in course_to_exams:
                    for exam_id in course_to_exams[course_id]:
                        student_exams[student_id].add(exam_id)

        return student_exams

    def _precompute_allowed_start_slots(
        self, day_slot_groupings: Dict[str, List[UUID]]
    ) -> List[Tuple[UUID, UUID]]:
        """Precompute allowed start slots for all exams"""
        allowed_start_slots = []

        for exam_id, exam in self.problem.exams.items():
            # Calculate required slots based on duration
            slots_needed = math.ceil(exam.duration_minutes / 180.0)

            for day_key, slot_ids in day_slot_groupings.items():
                if len(slot_ids) < slots_needed:
                    continue

                # Allow starts only where exam fits within day
                for start_idx in range(0, len(slot_ids) - slots_needed + 1):
                    start_slot_id = slot_ids[start_idx]
                    allowed_start_slots.append((exam_id, start_slot_id))

        return allowed_start_slots

    def _precompute_room_metadata(self) -> Dict[UUID, Dict]:
        """Enhanced room metadata with UUID keys"""
        room_metadata = {}
        for room_id, room in self.problem.rooms.items():
            room_metadata[room_id] = {
                "capacity": getattr(
                    room, "exam_capacity", getattr(room, "capacity", 0)
                ),
                "has_computers": getattr(room, "has_computers", False),
            }
        return room_metadata

    def _precompute_allowed_rooms_enhanced(self) -> Dict[UUID, Set[UUID]]:
        allowed_rooms = {}

        for exam_id, exam in self.problem.exams.items():
            exam_enrollment = getattr(exam, "expected_students", 0)
            viable_rooms = set()

            for room_id, room in self.problem.rooms.items():
                room_capacity = getattr(
                    room, "exam_capacity", getattr(room, "capacity", 0)
                )

                # Ensure room can accommodate at least 80% of students
                if room_capacity >= exam_enrollment * 0.8:
                    viable_rooms.add(room_id)

            allowed_rooms[exam_id] = viable_rooms

            if not viable_rooms:
                logger.error(
                    f"No viable rooms found for exam {exam_id} with {exam_enrollment} students"
                )

        return allowed_rooms

    def _precompute_day_slot_groupings(self) -> Dict[str, List[UUID]]:
        """Precompute day-slot groupings using Day data structure"""
        logger.info("Precomputing day-slot groupings from Day objects...")
        day_slots = {}

        for day in self.problem.days.values():
            day_key = day.date.isoformat()
            day_slots[day_key] = [slot.id for slot in day.timeslots]

        return day_slots

    def _precompute_invigilator_availability_enhanced(self) -> Dict[UUID, Dict]:
        """Precompute invigilator availability data"""
        invigilator_availability = {}
        invigilators = getattr(self.problem, "invigilators", {})

        for inv_id, invigilator in invigilators.items():
            invigilator_availability[inv_id] = {
                "max_students_per_exam": getattr(
                    invigilator, "max_students_per_exam", 50
                ),
                "max_concurrent_exams": getattr(invigilator, "max_concurrent_exams", 1),
            }

        return invigilator_availability

    def _create_x_vars(
        self, precomputed: Dict[str, Any]
    ) -> Dict[Tuple[UUID, UUID], Any]:
        """Create start variables for all allowed combinations"""
        x_vars = {}
        allowed_start_slots = precomputed["allowed_start_slots"]

        for exam_id, slot_id in allowed_start_slots:
            var = self.factory.get_x_var(exam_id, slot_id)
            x_vars[(exam_id, slot_id)] = var

        logger.info(f"Created {len(x_vars)} start variables")
        return x_vars

    def _create_z_vars(
        self, precomputed: Dict[str, Any]
    ) -> Dict[Tuple[UUID, UUID], Any]:
        """Create occupancy variables mirroring x variables"""
        z_vars = {}
        allowed_start_slots = precomputed["allowed_start_slots"]

        for exam_id, slot_id in allowed_start_slots:
            var = self.factory.get_z_var(exam_id, slot_id)
            z_vars[(exam_id, slot_id)] = var

        logger.info(f"Created {len(z_vars)} occupancy variables")
        return z_vars

    def _create_y_vars(
        self, precomputed: Dict[str, Any]
    ) -> Dict[Tuple[UUID, UUID, UUID], Any]:
        """Create room assignment variables for all potential combinations"""
        y_vars = {}
        potential_combinations = precomputed["potential_y_combinations"]

        for exam_id, room_id, slot_id in potential_combinations:
            # Check if room is allowed for this exam
            allowed_rooms = precomputed["allowed_rooms"].get(exam_id, set())
            if room_id in allowed_rooms:
                var = self.factory.get_y_var(exam_id, room_id, slot_id)
                y_vars[(exam_id, room_id, slot_id)] = var

        logger.info(f"Created {len(y_vars)} room assignment variables")
        return y_vars

    def _create_u_vars(
        self, precomputed: Dict[str, Any]
    ) -> Dict[Tuple[UUID, UUID, UUID, UUID], Any]:
        """Create invigilator assignment variables"""
        u_vars = {}
        invigilator_availability = precomputed["invigilator_availability"]
        y_combinations = precomputed["potential_y_combinations"]

        if not invigilator_availability:
            logger.info("No invigilators - zero u variables created")
            return u_vars

        # Create u variables for all valid combinations
        for exam_id, room_id, slot_id in y_combinations:
            for inv_id in invigilator_availability:
                var = self.factory.get_u_var(inv_id, exam_id, room_id, slot_id)
                u_vars[(inv_id, exam_id, room_id, slot_id)] = var

        logger.info(f"Created {len(u_vars)} invigilator assignment variables")
        return u_vars
