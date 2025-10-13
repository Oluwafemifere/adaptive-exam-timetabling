# scheduling_engine/analysis/pre_solve_analyzer.py

"""
Pre-Solve Feasibility and Complexity Analyzer

This module provides an intelligent "pre-flight check" for a given scheduling problem.
It analyzes the dataset, active constraints, and locked assignments to predict:
- The likelihood of finding a feasible solution.
- An estimation of solver complexity and potential runtime issues.
- The expected solution quality based on constraint pressure.
- Specific, actionable risks and recommendations.

This analyzer uses a heuristic-based model derived from the known behavior of
the two-phase CP-SAT scheduling engine.
"""

import logging
from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from uuid import UUID

from scheduling_engine.core.problem_model import ExamSchedulingProblem, Exam, Room
from scheduling_engine.core.constraint_types import ConstraintType

logger = logging.getLogger(__name__)

# --- Data Structures for the Report ---


@dataclass
class FeasibilityPrediction:
    """Predicts the likelihood of finding a feasible solution."""

    likelihood: str = (
        "High"  # e.g., "Very High", "High", "Medium", "Low", "Very Low / Infeasible"
    )
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class RuntimePrediction:
    """Estimates the relative complexity and runtime."""

    expected_duration: str = "Medium"  # e.g., "Short", "Medium", "Long", "Very Long"
    complexity_score: float = 0.0
    key_drivers: List[str] = field(default_factory=list)


@dataclass
class QualityPrediction:
    """Predicts the quality of the final solution."""

    expected_quality: str = "Good"  # e.g., "Excellent", "Good", "Moderate", "Poor"
    potential_issues: List[str] = field(default_factory=list)


@dataclass
class AnalysisReport:
    """A comprehensive pre-solve analysis report."""

    feasibility: FeasibilityPrediction = field(default_factory=FeasibilityPrediction)
    runtime: RuntimePrediction = field(default_factory=RuntimePrediction)
    quality: QualityPrediction = field(default_factory=QualityPrediction)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "feasibility": self.feasibility.__dict__,
            "runtime": self.runtime.__dict__,
            "quality": self.quality.__dict__,
        }


class PreSolveAnalyzer:
    """Analyzes a scheduling problem to predict outcomes before solving."""

    def __init__(self, problem: ExamSchedulingProblem):
        self.problem = problem
        self.report = AnalysisReport()
        self._metrics: Dict[str, Any] = {}
        logger.info("🧠 Initialized PreSolveAnalyzer.")

    async def analyze(self) -> AnalysisReport:
        """
        Performs a comprehensive analysis of the scheduling problem.
        """
        logger.info("--- Starting Pre-Solve Analysis ---")
        try:
            self._calculate_base_metrics()
            self._analyze_feasibility()
            self._estimate_runtime()
            self._predict_solution_quality()
            self._generate_summary()
            logger.info("--- Pre-Solve Analysis Complete ---")
            return self.report
        except Exception as e:
            logger.error(f"Pre-solve analysis failed critically: {e}", exc_info=True)
            self.report.summary = "Analysis failed due to an internal error."
            self.report.feasibility.likelihood = "Unknown"
            self.report.feasibility.critical_issues.append(
                f"Error during analysis: {e}"
            )
            return self.report

    def _calculate_base_metrics(self):
        """Calculates fundamental metrics about the problem's size and density."""
        logger.info("Step 1: Calculating base metrics...")
        num_exams = len(self.problem.exams)
        num_students = len(self.problem.students)
        num_rooms = len(self.problem.rooms)
        num_timeslots = len(self.problem.timeslots)
        num_invigilators = len(self.problem.invigilators)

        total_registrations = sum(
            len(exam.students) for exam in self.problem.exams.values()
        )
        avg_exam_duration = (
            sum(e.duration_minutes for e in self.problem.exams.values()) / num_exams
            if num_exams > 0
            else 0
        )

        total_student_exam_minutes = total_registrations * avg_exam_duration
        total_slot_minutes = sum(
            ts.duration_minutes for ts in self.problem.timeslots.values()
        )

        total_seat_capacity = sum(r.exam_capacity for r in self.problem.rooms.values())
        total_student_demand = sum(
            e.expected_students for e in self.problem.exams.values()
        )

        self._metrics = {
            "num_exams": num_exams,
            "num_students": num_students,
            "num_rooms": num_rooms,
            "num_timeslots": num_timeslots,
            "num_invigilators": num_invigilators,
            "num_locks": len(self.problem.locks),
            "total_registrations": total_registrations,
            "student_density": (
                (total_student_exam_minutes / (total_slot_minutes * num_students))
                if total_slot_minutes > 0 and num_students > 0
                else 0
            ),
            "seat_pressure_ratio": (
                (total_student_demand / (total_seat_capacity * num_timeslots))
                if total_seat_capacity > 0 and num_timeslots > 0
                else float("inf")
            ),
            "active_hard_constraints": sum(
                1
                for d in self.problem.constraint_registry.get_active_constraint_classes()
                if d.constraint_type == ConstraintType.HARD
            ),
            "active_soft_constraints": sum(
                1
                for d in self.problem.constraint_registry.get_active_constraint_classes()
                if d.constraint_type == ConstraintType.SOFT
            ),
        }
        logger.info(f"Base metrics calculated: {self._metrics}")

    def _analyze_feasibility(self):
        """Analyzes the problem for potential infeasibility issues."""
        logger.info("Step 2: Analyzing feasibility...")
        feasibility = self.report.feasibility

        # Critical Checks (can make a solution impossible)
        for exam in self.problem.exams.values():
            if not any(
                self.problem.is_start_feasible(exam.id, slot_id)
                for slot_id in self.problem.timeslots
            ):
                feasibility.critical_issues.append(
                    f"Exam '{getattr(exam, 'course_code', exam.id)}' (duration: {exam.duration_minutes} min) is too long to fit into any single day's schedule."
                )

        if not self.problem.rooms:
            feasibility.critical_issues.append(
                "No rooms are defined in the dataset. Cannot schedule any exams."
            )
        else:
            largest_room_capacity = max(
                r.exam_capacity for r in self.problem.rooms.values()
            )
            for exam in self.problem.exams.values():
                if exam.expected_students > largest_room_capacity:
                    # This is only critical if the exam cannot be split. Assuming RoomAssignmentConsistency handles splits.
                    pass

        self._analyze_locks(feasibility)

        # Warnings (increase difficulty)
        if self._metrics["seat_pressure_ratio"] > 0.9:
            feasibility.warnings.append(
                f"Seat pressure ratio is very high ({self._metrics['seat_pressure_ratio']:.2f}). Room capacity is extremely tight, increasing difficulty."
            )

        if self._metrics["student_density"] > 0.3:
            feasibility.warnings.append(
                f"Student density is high ({self._metrics['student_density']:.2f}). Student schedules are very constrained, making conflicts hard to avoid."
            )

        # Final Likelihood Assessment
        if feasibility.critical_issues:
            feasibility.likelihood = "Very Low / Infeasible"
        elif self._metrics["seat_pressure_ratio"] > 1.0:
            feasibility.likelihood = "Very Low / Infeasible"
            feasibility.critical_issues.append(
                "Overall student demand exceeds total available seat-hours. A feasible solution is impossible without reducing demand or increasing capacity/time."
            )
        elif (
            len(feasibility.warnings) >= 2
            or self._metrics["num_locks"] > self._metrics["num_exams"] * 0.5
        ):
            feasibility.likelihood = "Low"
        elif len(feasibility.warnings) == 1:
            feasibility.likelihood = "Medium"
        else:
            feasibility.likelihood = "High"

    def _analyze_locks(self, feasibility: FeasibilityPrediction):
        """Analyzes locked assignments for conflicts."""
        locks_by_slot_room: Dict[Tuple[UUID, UUID], List[UUID]] = defaultdict(list)
        locks_by_slot_student: Dict[Tuple[UUID, UUID], List[UUID]] = defaultdict(list)

        for lock in self.problem.locks:
            exam_id = lock.get("exam_id")
            slot_id = lock.get("time_slot_id")
            room_ids = lock.get("room_ids", [])

            if not isinstance(exam_id, UUID) or not isinstance(slot_id, UUID):
                continue

            exam = self.problem.exams.get(exam_id)
            if not exam:
                continue

            # Check for room conflicts between locks
            for room_id in room_ids:
                if not isinstance(room_id, UUID):
                    continue

                if (slot_id, room_id) in locks_by_slot_room:
                    other_exam_id = locks_by_slot_room[(slot_id, room_id)][0]

                    other_exam = self.problem.exams.get(other_exam_id)
                    room = self.problem.rooms.get(room_id)

                    exam_name = getattr(exam, "course_code", str(exam_id))
                    other_exam_name = (
                        getattr(other_exam, "course_code", str(other_exam_id))
                        if other_exam
                        else str(other_exam_id)
                    )
                    room_name = room.code if room else str(room_id)

                    feasibility.critical_issues.append(
                        f"Lock Conflict: Exam '{exam_name}' and Exam '{other_exam_name}' are both locked into the same room ('{room_name}') at the same time."
                    )
                locks_by_slot_room[(slot_id, room_id)].append(exam_id)

            # Check for student conflicts between locks
            for student_id in exam.students.keys():
                if not isinstance(student_id, UUID):
                    continue

                if (slot_id, student_id) in locks_by_slot_student:
                    other_exam_id = locks_by_slot_student[(slot_id, student_id)][0]
                    other_exam = self.problem.exams.get(other_exam_id)

                    exam_name = getattr(exam, "course_code", str(exam_id))
                    other_exam_name = (
                        getattr(other_exam, "course_code", str(other_exam_id))
                        if other_exam
                        else str(other_exam_id)
                    )

                    feasibility.critical_issues.append(
                        f"Lock Conflict: A student is registered for both Exam '{exam_name}' and Exam '{other_exam_name}', which are locked into the same timeslot."
                    )
                locks_by_slot_student[(slot_id, student_id)].append(exam_id)

    def _estimate_runtime(self):
        """Estimates runtime based on problem size and complexity drivers."""
        logger.info("Step 3: Estimating runtime...")
        runtime = self.report.runtime

        num_x = self._metrics["num_exams"] * self._metrics["num_timeslots"]
        avg_exams_per_slot = (
            self._metrics["num_exams"] / self._metrics["num_timeslots"]
            if self._metrics["num_timeslots"] > 0
            else 0
        )
        num_y_per_group = avg_exams_per_slot * self._metrics["num_rooms"]
        num_w_per_group = self._metrics["num_invigilators"] * self._metrics["num_rooms"]

        score = (
            (num_x * 0.1)
            + (num_y_per_group * self._metrics["num_timeslots"] * 0.4)
            + (num_w_per_group * self._metrics["num_timeslots"] * 0.5)
        )

        runtime.key_drivers.append(f"Phase 1 Variables (Starts): ~{int(num_x)}")
        runtime.key_drivers.append(
            f"Phase 2 Variables (Room/Invigilator Assignments): ~{int(num_y_per_group + num_w_per_group)} per start-time group"
        )

        score *= 1 + self._metrics["student_density"]
        score *= 1 + self._metrics["active_soft_constraints"] * 0.05

        runtime.complexity_score = score

        if score > 5_000_000:
            runtime.expected_duration = "Very Long"
        elif score > 1_000_000:
            runtime.expected_duration = "Long"
        elif score > 200_000:
            runtime.expected_duration = "Medium"
        else:
            runtime.expected_duration = "Short"

    def _predict_solution_quality(self):
        """Predicts solution quality based on soft constraint pressure."""
        logger.info("Step 4: Predicting solution quality...")
        quality = self.report.quality
        active_soft_constraints = [
            d.id
            for d in self.problem.constraint_registry.get_active_constraint_classes()
            if d.constraint_type == ConstraintType.SOFT
        ]

        if not active_soft_constraints:
            quality.expected_quality = "Excellent"
            quality.potential_issues.append(
                "No active soft constraints; solution will be feasible but not optimized for any quality metrics."
            )
            return

        pressure_points = 0
        if (
            "MINIMUM_GAP" in active_soft_constraints
            and self._metrics["student_density"] > 0.25
        ):
            quality.potential_issues.append(
                "High student density will likely force many back-to-back exams, violating the 'Minimum Gap' preference."
            )
            pressure_points += 2

        if (
            "MAX_EXAMS_PER_STUDENT_PER_DAY" in active_soft_constraints
            and self._metrics["student_density"] > 0.3
        ):
            quality.potential_issues.append(
                "High student density may lead to students having more than the preferred max exams per day."
            )
            pressure_points += 2

        if (
            "INVIGILATOR_LOAD_BALANCE" in active_soft_constraints
            and self._metrics["num_invigilators"] < self._metrics["num_rooms"]
        ):
            quality.potential_issues.append(
                "Fewer invigilators than rooms suggests workload balance will be difficult to achieve."
            )
            pressure_points += 1

        if (
            "ROOM_FIT_PENALTY" in active_soft_constraints
            and self._metrics["seat_pressure_ratio"] < 0.5
        ):
            quality.potential_issues.append(
                "Low seat pressure with a room fit penalty active may result in inefficient space usage if not heavily weighted."
            )
            pressure_points += 1

        if pressure_points >= 4:
            quality.expected_quality = "Poor"
        elif pressure_points >= 2:
            quality.expected_quality = "Moderate"
        else:
            quality.expected_quality = "Good"

    def _generate_summary(self):
        """Generates a final summary text."""
        logger.info("Step 5: Generating final summary...")
        self.report.summary = (
            f"Analysis complete. Feasibility is rated '{self.report.feasibility.likelihood}'. "
            f"Expected runtime is '{self.report.runtime.expected_duration}' based on a complexity score of {self.report.runtime.complexity_score:,.0f}. "
            f"Anticipated solution quality is '{self.report.quality.expected_quality}'."
        )
