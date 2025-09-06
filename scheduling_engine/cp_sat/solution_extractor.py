# scheduling_engine/cp_sat/solution_extractor.py

"""
Solution Extractor for CP-SAT models.

Extracts solutions from CP-SAT solver and converts them into internal
solution representation. Handles both feasible and optimal solutions,
with support for partial solutions and solution quality metrics.

Based on research paper approach for resource-constrained scheduling.
"""

from typing import Dict, List, Optional, Any, DefaultDict, cast
from ortools.sat.python import cp_model
from dataclasses import dataclass, field
import logging
from uuid import UUID, uuid4
from datetime import datetime, date
from collections import defaultdict

from ..core.problem_model import ExamSchedulingProblem
from ..core.solution import (
    TimetableSolution,
    ExamAssignment,
    AssignmentStatus,
    SolutionStatus,
)
from ..core.metrics import SolutionMetrics

logger = logging.getLogger(__name__)


@dataclass
class ExtractionContext:
    """Context for solution extraction"""

    solver: cp_model.CpSolver
    model: cp_model.CpModel
    variables: Dict[str, cp_model.IntVar]
    problem: ExamSchedulingProblem
    solver_status: int
    solve_time_seconds: float


@dataclass
class SolutionExtractionResult:
    """Result of solution extraction process"""

    solution: Optional[TimetableSolution]
    extraction_successful: bool
    extraction_time_seconds: float
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class SolutionExtractor:
    """
    Extracts and validates solutions from CP-SAT solver results.

    Converts CP-SAT variable assignments back into domain-specific
    solution representation with comprehensive quality assessment.
    """

    def __init__(self):
        self.metrics_calculator = SolutionMetrics()

    def extract_solution(self, context: ExtractionContext) -> SolutionExtractionResult:
        """
        Extract solution from CP-SAT solver results.

        Args:
            context: Extraction context with solver, model, and problem data

        Returns:
            SolutionExtractionResult with extracted solution and metrics
        """
        start_time = datetime.now()
        result: SolutionExtractionResult = SolutionExtractionResult(
            solution=None, extraction_successful=False, extraction_time_seconds=0.0
        )

        try:
            logger.info(f"Extracting solution with status: {context.solver_status}")

            # Check solver status
            if context.solver_status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                result.errors.append(
                    f"No solution found. Status: {context.solver_status}"
                )
                return result

            # Extract variable assignments
            variable_assignments = self._extract_variable_assignments(context)

            # Convert to exam assignments
            exam_assignments = self._convert_to_exam_assignments(
                variable_assignments, context
            )

            # Build solution object
            solution = self._build_solution_object(exam_assignments, context)

            # Calculate quality metrics
            quality_metrics = self._calculate_solution_quality(solution, context)

            # Validate solution consistency
            validation_result = self._validate_solution_consistency(solution, context)

            result.solution = solution
            result.quality_metrics = quality_metrics

            # Safely extend warnings and errors returned from validation_result
            val_warnings = validation_result.get("warnings", [])
            if isinstance(val_warnings, list):
                result.warnings.extend(cast(List[str], val_warnings))

            val_errors = validation_result.get("errors", [])
            if isinstance(val_errors, list):
                result.errors.extend(cast(List[str], val_errors))

            result.extraction_successful = len(result.errors) == 0

            if result.extraction_successful:
                logger.info(
                    f"Successfully extracted solution with {len(exam_assignments)} assignments"
                )
            else:
                logger.warning(
                    f"Solution extraction completed with errors: {result.errors}"
                )

        except Exception as e:
            result.errors.append(f"Solution extraction failed: {str(e)}")
            logger.error(f"Solution extraction error: {e}", exc_info=True)

        finally:
            result.extraction_time_seconds = (
                datetime.now() - start_time
            ).total_seconds()

        return result

    def _extract_variable_assignments(
        self, context: ExtractionContext
    ) -> Dict[str, int]:
        """
        Extract variable assignments from CP-SAT solver.

        Returns:
            Dictionary mapping variable names to their assigned values
        """
        assignments: Dict[str, int] = {}

        try:
            for var_name, cp_var in context.variables.items():
                try:
                    assignment_value = context.solver.value(cp_var)
                    assignments[var_name] = assignment_value
                except Exception as e:
                    logger.warning(
                        f"Could not extract value for variable {var_name}: {e}"
                    )
                    assignments[var_name] = 0  # Default to unassigned

            logger.debug(f"Extracted {len(assignments)} variable assignments")

        except Exception as e:
            logger.error(f"Error extracting variable assignments: {e}")

        return assignments

    def _convert_to_exam_assignments(
        self, variable_assignments: Dict[str, int], context: ExtractionContext
    ) -> List[ExamAssignment]:
        """
        Convert CP-SAT variable assignments to exam assignments.

        Parses variable names in format 'x_{exam_id}_{room_id}_{time_slot_id}'
        and creates ExamAssignment objects for assigned exams.
        """
        exam_assignments: List[ExamAssignment] = []

        try:
            # Group assignments by exam
            exams_data: DefaultDict[UUID, Dict[str, Any]] = defaultdict(dict)

            for var_name, value in variable_assignments.items():
                if value == 1 and var_name.startswith("x_"):
                    # Parse variable name: x_{exam_id}_{room_id}_{time_slot_id}
                    try:
                        parts = var_name.split("_")
                        if len(parts) >= 4:  # x_, exam_id, room_id, time_slot_id
                            exam_id = UUID(parts[1])
                            room_id = UUID(parts[2])
                            time_slot_id = UUID(parts[3])

                            if exam_id not in exams_data:
                                exams_data[exam_id] = {
                                    "exam_id": exam_id,
                                    "room_ids": [],
                                    "time_slot_id": time_slot_id,
                                }

                            # Add room to assignment
                            if room_id not in exams_data[exam_id]["room_ids"]:
                                exams_data[exam_id]["room_ids"].append(room_id)

                    except (ValueError, IndexError) as e:
                        logger.warning(f"Could not parse variable name {var_name}: {e}")
                        continue

            # Create ExamAssignment objects
            for exam_id, exam_data in exams_data.items():
                try:
                    # Find exam object
                    exam = context.problem.exams.get(exam_id)
                    if not exam:
                        continue

                    # Get time slot
                    time_slot_id = exam_data["time_slot_id"]
                    time_slot = context.problem.time_slots.get(time_slot_id)
                    if not time_slot:
                        continue

                    # Create assignment
                    assignment = ExamAssignment(exam_id=exam_id)
                    assignment.time_slot_id = time_slot_id
                    assignment.room_ids = exam_data["room_ids"]
                    assignment.status = AssignmentStatus.ASSIGNED

                    # Set room allocations
                    for room_id in assignment.room_ids:
                        room = context.problem.rooms.get(room_id)
                        if room:
                            allocation = min(exam.expected_students, room.exam_capacity)
                            assignment.add_room_allocation(room_id, allocation)

                    exam_assignments.append(assignment)

                except Exception as e:
                    logger.warning(f"Error creating assignment for exam {exam_id}: {e}")
                    continue

            logger.info(
                f"Converted {len(exam_assignments)} exam assignments from {len(variable_assignments)} variables"
            )

        except Exception as e:
            logger.error(f"Error converting variable assignments: {e}")

        return exam_assignments

    def _build_solution_object(
        self, exam_assignments: List[ExamAssignment], context: ExtractionContext
    ) -> TimetableSolution:
        """
        Build complete solution object from exam assignments.

        Creates TimetableSolution with all necessary metadata and metrics.
        """
        try:
            # Create solution
            solution = TimetableSolution(
                problem=context.problem,
                solution_id=uuid4(),
            )

            # Add assignments
            for assignment in exam_assignments:
                if assignment.is_complete() and assignment.time_slot_id:
                    exam = context.problem.exams[assignment.exam_id]
                    solution.assign_exam(
                        exam_id=assignment.exam_id,
                        time_slot_id=assignment.time_slot_id,
                        room_ids=assignment.room_ids,
                        assigned_date=exam.exam_date or date.today(),
                        room_allocations=assignment.room_allocations,
                    )

            # Update solution status
            if context.solver_status == cp_model.OPTIMAL:
                solution.status = SolutionStatus.OPTIMAL
            else:
                solution.status = SolutionStatus.FEASIBLE

            # Calculate objective value and fitness
            solution.calculate_objective_value()
            solution.calculate_fitness_score()

            logger.info(f"Built solution object with fitness: {solution.fitness_score}")
            return solution

        except Exception as e:
            logger.error(f"Error building solution object: {e}")
            raise

    def _calculate_solution_quality(
        self, solution: TimetableSolution, context: ExtractionContext
    ) -> Dict[str, float]:
        """
        Calculate comprehensive solution quality metrics.

        Uses the metrics calculator to compute detailed quality measures.
        """
        try:
            # Use the dedicated metrics calculator
            quality_score = self.metrics_calculator.evaluate_solution_quality(
                context.problem, solution
            )

            quality_metrics = {
                "total_score": quality_score.total_score,
                "feasibility_score": quality_score.feasibility_score,
                "objective_value_score": quality_score.objective_value_score,
                "constraint_satisfaction_score": quality_score.constraint_satisfaction_score,
                "resource_utilization_score": quality_score.resource_utilization_score,
                "student_satisfaction_score": quality_score.student_satisfaction_score,
                "hard_constraint_penalty": quality_score.hard_constraint_penalty,
                "soft_constraint_penalty": quality_score.soft_constraint_penalty,
                "unassigned_exam_penalty": quality_score.unassigned_exam_penalty,
                "cp_sat_solve_time": context.solve_time_seconds,
                "cp_sat_status": str(context.solver_status),
                "variable_count": len(context.variables),
            }

            logger.debug(f"Calculated {len(quality_metrics)} quality metrics")
            return quality_metrics

        except Exception as e:
            logger.error(f"Error calculating solution quality: {e}")
            return {"error": 1.0}

    def _validate_solution_consistency(
        self, solution: TimetableSolution, context: ExtractionContext
    ) -> Dict[str, Any]:
        """
        Validate solution consistency and constraint satisfaction.

        Checks that extracted solution satisfies all hard constraints.
        """
        validation_result: Dict[str, Any] = {
            "is_consistent": True,
            "errors": [],
            "warnings": [],
            "constraint_violations": [],
        }

        try:
            # Check 1: Each exam assigned exactly once
            exam_assignment_count: DefaultDict[UUID, int] = defaultdict(int)
            for assignment in solution.assignments.values():
                if assignment.is_complete():
                    exam_assignment_count[assignment.exam_id] += 1

            for exam_id, count in exam_assignment_count.items():
                if count != 1:
                    # Ensure errors list present and typed
                    errors_list = cast(
                        List[str], validation_result.setdefault("errors", [])
                    )
                    errors_list.append(
                        f"Exam {exam_id} assigned {count} times (should be exactly 1)"
                    )
                    validation_result["is_consistent"] = False

            # Check 2: No student conflicts
            student_conflicts = self._detect_student_conflicts(solution, context)
            if student_conflicts:
                errors_list = cast(
                    List[str], validation_result.setdefault("errors", [])
                )
                constraint_list = cast(
                    List[str], validation_result.setdefault("constraint_violations", [])
                )
                for conflict in student_conflicts:
                    errors_list.append(f"Student conflict detected: {conflict}")
                constraint_list.extend(student_conflicts)
                validation_result["is_consistent"] = False

            # Check 3: Room capacity not exceeded
            capacity_violations = self._detect_capacity_violations(solution, context)
            if capacity_violations:
                warnings_list = cast(
                    List[str], validation_result.setdefault("warnings", [])
                )
                constraint_list = cast(
                    List[str], validation_result.setdefault("constraint_violations", [])
                )
                for violation in capacity_violations:
                    warnings_list.append(f"Capacity violation: {violation}")
                constraint_list.extend(capacity_violations)

            # Check 4: Time slot consistency
            time_violations = self._detect_time_violations(solution, context)
            if time_violations:
                errors_list = cast(
                    List[str], validation_result.setdefault("errors", [])
                )
                constraint_list = cast(
                    List[str], validation_result.setdefault("constraint_violations", [])
                )
                for violation in time_violations:
                    errors_list.append(f"Time violation: {violation}")
                constraint_list.extend(time_violations)
                validation_result["is_consistent"] = False

            logger.info(
                f"Solution validation: {'PASS' if validation_result['is_consistent'] else 'FAIL'} "
                f"({len(cast(List[str], validation_result.get('errors', [])))} errors, "
                f"{len(cast(List[str], validation_result.get('warnings', [])))} warnings)"
            )

        except Exception as e:
            errors_list = cast(List[str], validation_result.setdefault("errors", []))
            errors_list.append(f"Validation failed: {str(e)}")
            validation_result["is_consistent"] = False
            logger.error(f"Solution validation error: {e}")

        return validation_result

    def _detect_student_conflicts(
        self, solution: TimetableSolution, context: ExtractionContext
    ) -> List[str]:
        """Detect student scheduling conflicts"""
        conflicts: List[str] = []

        try:
            # Use the solution's built-in conflict detection
            solution.detect_conflicts()
            for conflict in solution.conflicts.values():
                if getattr(conflict, "conflict_type", "") == "student_conflict":
                    conflicts.append(getattr(conflict, "description", str(conflict)))

        except Exception as e:
            logger.error(f"Error detecting student conflicts: {e}")
            conflicts.append(f"Conflict detection failed: {str(e)}")

        return conflicts

    def _detect_capacity_violations(
        self, solution: TimetableSolution, context: ExtractionContext
    ) -> List[str]:
        """Detect room capacity violations"""
        violations: List[str] = []

        try:
            for assignment in solution.assignments.values():
                if not assignment.is_complete():
                    continue

                exam = context.problem.exams.get(assignment.exam_id)
                if not exam:
                    continue

                # Check individual room capacities
                for room_id, allocated_capacity in assignment.room_allocations.items():
                    room = context.problem.rooms.get(room_id)
                    if room and allocated_capacity > room.exam_capacity:
                        violations.append(
                            f"Room {room.code} over-allocated: "
                            f"{allocated_capacity} > {room.exam_capacity}"
                        )

        except Exception as e:
            logger.error(f"Error detecting capacity violations: {e}")
            violations.append(f"Capacity validation failed: {str(e)}")

        return violations

    def _detect_time_violations(
        self, solution: TimetableSolution, context: ExtractionContext
    ) -> List[str]:
        """Detect time-related constraint violations"""
        violations: List[str] = []

        try:
            # Use the solution's built-in conflict detection
            solution.detect_conflicts()
            for conflict in solution.conflicts.values():
                if getattr(conflict, "conflict_type", "") in [
                    "precedence_conflict",
                    "time_conflict",
                ]:
                    violations.append(getattr(conflict, "description", str(conflict)))

        except Exception as e:
            logger.error(f"Error detecting time violations: {e}")
            violations.append(f"Time validation failed: {str(e)}")

        return violations

    def extract_partial_solution(
        self, context: ExtractionContext, target_quality_threshold: float = 0.7
    ) -> SolutionExtractionResult:
        """
        Extract partial solution when full solution is not available.

        Useful for time-limited solving or when seeking intermediate results.
        """
        try:
            logger.info("Extracting partial solution")

            # Extract what assignments we have so far
            variable_assignments = self._extract_variable_assignments(context)

            # Filter to only assigned variables (value = 1)
            assigned_vars = {
                var_name: value
                for var_name, value in variable_assignments.items()
                if value == 1
            }

            exam_assignments = self._convert_to_exam_assignments(assigned_vars, context)

            if not exam_assignments:
                return SolutionExtractionResult(
                    solution=None,
                    extraction_successful=False,
                    extraction_time_seconds=0.0,
                    errors=["No partial assignments found"],
                )

            # Build partial solution
            solution = self._build_solution_object(exam_assignments, context)
            solution.status = SolutionStatus.INCOMPLETE

            # Calculate quality metrics for partial solution
            quality_metrics = self._calculate_solution_quality(solution, context)

            return SolutionExtractionResult(
                solution=solution,
                extraction_successful=True,
                extraction_time_seconds=0.0,
                quality_metrics=quality_metrics,
                warnings=["This is a partial solution"],
            )

        except Exception as e:
            logger.error(f"Error extracting partial solution: {e}")
            return SolutionExtractionResult(
                solution=None,
                extraction_successful=False,
                extraction_time_seconds=0.0,
                errors=[f"Partial extraction failed: {str(e)}"],
            )

    def get_solver_statistics(self, context: ExtractionContext) -> Dict[str, Any]:
        """Get detailed solver statistics"""
        try:
            stats: Dict[str, Any] = {
                "solver_status": str(context.solver_status),
                "solve_time_seconds": context.solve_time_seconds,
                # access solver fields defensively
                "wall_time": getattr(context.solver, "wall_time", None),
                "num_branches": getattr(context.solver, "num_branches", None),
                "num_conflicts": getattr(context.solver, "num_conflicts", None),
            }

            return stats

        except Exception as e:
            logger.error(f"Error getting solver statistics: {e}")
            return {"error": str(e)}

    def export_solution_for_ga(self, solution: TimetableSolution) -> Dict[str, Any]:
        """
        Export solution in format suitable for Genetic Algorithm initialization.

        Following research paper approach where CP-SAT solutions are used
        to seed GA population.
        """
        try:
            # prefer solution_id, fall back to id if present
            sol_id = getattr(solution, "solution_id", None) or getattr(
                solution, "id", None
            )
            ga_solution: Dict[str, Any] = {
                "solution_id": str(sol_id) if sol_id is not None else str(uuid4()),
                "assignments": [],
                "fitness_score": getattr(solution, "fitness_score", 0.0),
            }

            # Convert assignments to GA-compatible format
            for assignment in solution.assignments.values():
                if assignment.is_complete():
                    ga_assignment = {
                        "exam_id": str(assignment.exam_id),
                        "time_slot_id": str(assignment.time_slot_id),
                        "room_ids": [str(room_id) for room_id in assignment.room_ids],
                        "room_allocations": {
                            str(room_id): capacity
                            for room_id, capacity in assignment.room_allocations.items()
                        },
                    }
                    ga_solution["assignments"].append(ga_assignment)

            logger.info(
                f"Exported solution with {len(ga_solution['assignments'])} assignments for GA"
            )
            return ga_solution

        except Exception as e:
            logger.error(f"Error exporting solution for GA: {e}")
            return {"error": str(e)}

    def extract_infeasibility_analysis(
        self, context: ExtractionContext
    ) -> Dict[str, Any]:
        """
        Extract information about why problem is infeasible.

        Analyzes infeasible CP-SAT model to identify constraint conflicts.
        """
        analysis: Dict[str, Any] = {
            "is_infeasible": True,
            "conflicting_constraints": [],
            "recommendations": [],
            "relaxation_suggestions": [],
        }

        try:
            if context.solver_status == cp_model.INFEASIBLE:
                logger.warning("Problem is infeasible - analyzing conflicts")

                # Basic infeasibility analysis
                conflicts_list = cast(
                    List[str], analysis.setdefault("conflicting_constraints", [])
                )
                conflicts_list.append("Problem has no feasible solution")

                # Check common causes of infeasibility
                total_student_demand = sum(
                    exam.expected_students for exam in context.problem.exams.values()
                )
                total_room_capacity = sum(
                    room.exam_capacity * len(context.problem.time_slots)
                    for room in context.problem.rooms.values()
                )

                if total_student_demand > total_room_capacity:
                    recs = cast(List[str], analysis.setdefault("recommendations", []))
                    relax = cast(
                        List[str], analysis.setdefault("relaxation_suggestions", [])
                    )

                    recs.append(
                        f"Insufficient room capacity: {total_student_demand} students need "
                        f"{total_room_capacity} total capacity"
                    )
                    relax.append("Add more rooms or time slots")

        except Exception as e:
            conflict_list = cast(
                List[str], analysis.setdefault("conflicting_constraints", [])
            )
            conflict_list.append(f"Analysis failed: {str(e)}")
            logger.error(f"Error analyzing infeasibility: {e}")

        return analysis
