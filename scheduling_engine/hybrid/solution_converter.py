# scheduling_engine/hybrid/solution_converter.py

"""
Solution Converter for transforming between different solution representations.
Handles conversion between CP-SAT solutions, GA chromosomes, and internal solution formats
while preserving constraint satisfaction and optimization objectives.
"""

from typing import Dict, List, Optional, Any, Set, Tuple, Union, TYPE_CHECKING
from uuid import UUID, uuid4
from datetime import datetime, date, time as dt_time
import time
import json
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import copy

from ..config import get_logger, SchedulingEngineConfig
from ..core.problem_model import ExamSchedulingProblem, Exam, Room, TimeSlot
from ..core.solution import TimetableSolution, ExamAssignment, SolutionStatus
from ..core.metrics import SolutionMetrics, QualityScore

if TYPE_CHECKING:
    from ..cp_sat.model_builder import CPSATModelBuilder
    from ..genetic_algorithm.chromosome import VariableSelectorChromosome
    from ..genetic_algorithm.population import Population

logger = get_logger("hybrid.solution_converter")


class ConversionFormat(Enum):
    """Different solution representation formats"""

    INTERNAL = "internal"  # Internal TimetableSolution format
    CP_SAT = "cp_sat"  # CP-SAT solver format
    GENETIC = "genetic"  # Genetic algorithm chromosome format
    DATABASE = "database"  # Database record format
    EXPORT = "export"  # Export-friendly format


class ConversionDirection(Enum):
    """Direction of conversion"""

    TO_INTERNAL = "to_internal"
    FROM_INTERNAL = "from_internal"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class ConversionResult:
    """Result of a conversion operation"""

    success: bool
    converted_object: Any = None
    original_format: Optional[ConversionFormat] = None
    target_format: Optional[ConversionFormat] = None
    conversion_time: float = 0.0
    data_integrity_score: float = 1.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CPSATSolutionData:
    """Structure for CP-SAT solution data"""

    status: str
    objective_value: float
    variable_assignments: Dict[str, Any] = field(default_factory=dict)
    constraint_violations: List[str] = field(default_factory=list)
    solve_time: float = 0.0
    branch_count: int = 0


@dataclass
class GeneticSolutionData:
    """Structure for genetic algorithm solution data"""

    chromosome_id: UUID
    fitness: float
    objective_value: float
    generation: int
    variable_priorities: Dict[str, float] = field(default_factory=dict)
    tree_representation: Dict[str, Any] = field(default_factory=dict)
    evolution_history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DatabaseSolutionData:
    """Structure for database-compatible solution data"""

    job_id: UUID
    version_number: int
    exam_assignments: List[Dict[str, Any]] = field(default_factory=list)
    room_assignments: List[Dict[str, Any]] = field(default_factory=list)
    invigilator_assignments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    quality_metrics: Dict[str, float] = field(default_factory=dict)


class SolutionConverter:
    """
    Converts between different solution representations used in the hybrid system.

    Supports conversion between:
    - CP-SAT solver solutions
    - Genetic algorithm chromosomes
    - Internal timetable solutions
    - Database storage formats
    - Export formats
    """

    def __init__(self, config: SchedulingEngineConfig):
        self.config = config
        self.metrics = SolutionMetrics()

        # Conversion statistics
        self.conversion_stats: Dict[str, int] = defaultdict(int)
        self.conversion_times: Dict[str, List[float]] = defaultdict(list)

        # Validation settings
        self.validate_conversions = True
        self.preserve_metadata = True

        logger.info("Solution converter initialized")

    # ==================== Main Conversion Interface ====================

    async def convert_solution(
        self,
        source_object: Any,
        source_format: ConversionFormat,
        target_format: ConversionFormat,
        problem: ExamSchedulingProblem,
        context: Optional[Dict[str, Any]] = None,
    ) -> ConversionResult:
        """
        Main conversion method that handles all format transformations.

        Args:
            source_object: Object to convert
            source_format: Format of source object
            target_format: Format to convert to
            problem: Problem instance for context
            context: Additional conversion context

        Returns:
            Conversion result with converted object
        """
        start_time = time.time()
        logger.info(
            f"Converting solution from {source_format.value} to {target_format.value}"
        )

        try:
            # Route to appropriate conversion method
            if (
                source_format == ConversionFormat.CP_SAT
                and target_format == ConversionFormat.INTERNAL
            ):
                result = await self._cpsat_to_internal(source_object, problem, context)

            elif (
                source_format == ConversionFormat.INTERNAL
                and target_format == ConversionFormat.CP_SAT
            ):
                result = await self._internal_to_cpsat(source_object, problem, context)

            elif (
                source_format == ConversionFormat.GENETIC
                and target_format == ConversionFormat.INTERNAL
            ):
                result = await self._genetic_to_internal(
                    source_object, problem, context
                )

            elif (
                source_format == ConversionFormat.INTERNAL
                and target_format == ConversionFormat.GENETIC
            ):
                result = await self._internal_to_genetic(
                    source_object, problem, context
                )

            elif (
                source_format == ConversionFormat.INTERNAL
                and target_format == ConversionFormat.DATABASE
            ):
                result = await self._internal_to_database(
                    source_object, problem, context
                )

            elif (
                source_format == ConversionFormat.DATABASE
                and target_format == ConversionFormat.INTERNAL
            ):
                result = await self._database_to_internal(
                    source_object, problem, context
                )

            elif (
                source_format == ConversionFormat.INTERNAL
                and target_format == ConversionFormat.EXPORT
            ):
                result = await self._internal_to_export(source_object, problem, context)

            else:
                # For unsupported direct conversions, use internal format as intermediate
                if source_format != ConversionFormat.INTERNAL:
                    intermediate_result = await self.convert_solution(
                        source_object,
                        source_format,
                        ConversionFormat.INTERNAL,
                        problem,
                        context,
                    )
                    if not intermediate_result.success:
                        return intermediate_result

                    return await self.convert_solution(
                        intermediate_result.converted_object,
                        ConversionFormat.INTERNAL,
                        target_format,
                        problem,
                        context,
                    )
                else:
                    raise ValueError(
                        f"Unsupported conversion: {source_format.value} to {target_format.value}"
                    )

            # Set common result properties
            result.original_format = source_format
            result.target_format = target_format
            result.conversion_time = time.time() - start_time

            # Update statistics
            self.conversion_stats[
                f"{source_format.value}_to_{target_format.value}"
            ] += 1
            self.conversion_times[
                f"{source_format.value}_to_{target_format.value}"
            ].append(result.conversion_time)

            # Validate conversion if enabled
            if self.validate_conversions and result.success:
                validation_result = await self._validate_conversion_integrity(
                    source_object,
                    result.converted_object,
                    source_format,
                    target_format,
                    problem,
                )
                result.data_integrity_score = validation_result["integrity_score"]
                result.warnings.extend(validation_result["warnings"])

            logger.info(f"Conversion completed in {result.conversion_time:.3f}s")
            return result

        except Exception as e:
            logger.error(f"Error during conversion: {e}")
            return ConversionResult(
                success=False,
                original_format=source_format,
                target_format=target_format,
                conversion_time=time.time() - start_time,
                errors=[str(e)],
            )

    # ==================== CP-SAT Conversions ====================

    async def _cpsat_to_internal(
        self,
        cpsat_solution: Dict[str, Any],
        problem: ExamSchedulingProblem,
        context: Optional[Dict[str, Any]] = None,
    ) -> ConversionResult:
        """Convert CP-SAT solution to internal TimetableSolution format"""
        try:
            # Extract solution data
            status = cpsat_solution.get("status", "UNKNOWN")
            objective_value = cpsat_solution.get("objective_value", float("inf"))
            variable_assignments = cpsat_solution.get("variable_assignments", {})

            # Create internal solution
            solution = TimetableSolution(problem=problem)

            # Parse variable assignments and create exam assignments
            assignments = {}

            # CP-SAT variables are typically named like "exam_X_room_Y_timeslot_Z"
            for var_name, value in variable_assignments.items():
                if value and var_name.startswith("exam_"):
                    parts = var_name.split("_")
                    if len(parts) >= 6:  # exam_X_room_Y_timeslot_Z
                        try:
                            exam_id = UUID(parts[1])
                            room_id = UUID(parts[3])
                            timeslot_id = UUID(parts[5])

                            if exam_id not in assignments:
                                exam = problem.exams.get(exam_id)
                                if exam:
                                    # Create basic assignment
                                    assignment = ExamAssignment(exam_id=exam_id)
                                    assignment.time_slot_id = timeslot_id
                                    assignments[exam_id] = assignment

                            # Add room to assignment
                            if exam_id in assignments:
                                if room_id not in assignments[exam_id].room_ids:
                                    assignments[exam_id].room_ids.append(room_id)

                        except (ValueError, IndexError) as e:
                            logger.warning(f"Could not parse variable {var_name}: {e}")

            # Update solution with assignments
            for exam_id, assignment in assignments.items():
                solution.assignments[exam_id] = assignment

            # Set solution status based on CP-SAT status
            if status == "OPTIMAL":
                solution.status = SolutionStatus.OPTIMAL
            elif status == "FEASIBLE":
                solution.status = SolutionStatus.FEASIBLE
            else:
                solution.status = SolutionStatus.INFEASIBLE

            # Set objective value
            solution.objective_value = objective_value

            return ConversionResult(
                success=True,
                converted_object=solution,
                metadata={
                    "assignments_created": len(assignments),
                    "cp_sat_status": status,
                    "variable_count": len(variable_assignments),
                },
            )

        except Exception as e:
            logger.error(f"Error converting CP-SAT solution to internal format: {e}")
            return ConversionResult(success=False, errors=[str(e)])

    async def _internal_to_cpsat(
        self,
        internal_solution: TimetableSolution,
        problem: ExamSchedulingProblem,
        context: Optional[Dict[str, Any]] = None,
    ) -> ConversionResult:
        """Convert internal TimetableSolution to CP-SAT format"""
        try:
            # Extract variable assignments from internal solution
            variable_assignments = {}

            for exam_id, assignment in internal_solution.assignments.items():
                if assignment.is_complete():
                    # Create CP-SAT variable assignments
                    for room_id in assignment.room_ids:
                        var_name = f"exam_{exam_id}_room_{room_id}_timeslot_{assignment.time_slot_id}"
                        variable_assignments[var_name] = 1  # Binary variable set to 1

            # Convert status
            cp_sat_status = "UNKNOWN"
            if internal_solution.status == SolutionStatus.OPTIMAL:
                cp_sat_status = "OPTIMAL"
            elif internal_solution.status == SolutionStatus.FEASIBLE:
                cp_sat_status = "FEASIBLE"
            elif internal_solution.status == SolutionStatus.INFEASIBLE:
                cp_sat_status = "INFEASIBLE"

            cpsat_solution = CPSATSolutionData(
                status=cp_sat_status,
                objective_value=internal_solution.objective_value,
                variable_assignments=variable_assignments,
                solve_time=0.0,  # Not applicable for converted solution
                branch_count=0,  # Not applicable for converted solution
            )

            return ConversionResult(
                success=True,
                converted_object=cpsat_solution,
                metadata={
                    "variable_assignments": len(variable_assignments),
                    "exam_assignments": len(internal_solution.assignments),
                    "conversion_direction": "internal_to_cpsat",
                },
            )

        except Exception as e:
            logger.error(f"Error converting internal solution to CP-SAT format: {e}")
            return ConversionResult(success=False, errors=[str(e)])

        # ==================== Genetic Algorithm Conversions ====================

    async def _genetic_to_internal(
        self,
        genetic_data: "VariableSelectorChromosome",
        problem: ExamSchedulingProblem,
        context: Optional[Dict[str, Any]] = None,
    ) -> ConversionResult:
        """Convert genetic algorithm chromosome to internal solution"""
        try:
            from ortools.sat.python import cp_model
            from typing import Dict, Callable, Any, List
            from uuid import UUID
            from ..cp_sat.solver_manager import CPSATSolverManager
            from ..cp_sat.model_builder import (
                CPSATModelBuilder,
            )  # ensure available at runtime

            solver = CPSATSolverManager(self.config.cp_sat)
            model_builder = CPSATModelBuilder(self.config.cp_sat)

            # Expect build_model to return both model and variables; handle both signatures
            built = model_builder.build_model(problem)
            if isinstance(built, cp_model.CpModel):
                model: cp_model.CpModel = built
                variables: Dict[UUID, cp_model.IntVar] = getattr(
                    model_builder, "variables", {}
                )
                if not isinstance(variables, dict):
                    variables = {}
            else:
                # assume tuple-like
                model, variables = built  # type: ignore[misc]
                # help the type checker
                model = model  # type: ignore[assignment]
                variables = variables  # type: ignore[assignment]

            # Variable ordering from chromosome
            variable_ordering: List[UUID] = genetic_data.get_variable_ordering(problem)

            # Wrap ordering into a callable the solver expects
            def variable_selector(vars_dict: Dict[UUID, Any]) -> List[Any]:
                ordered = []
                for vid in variable_ordering:
                    v = vars_dict.get(vid)
                    if v is not None:
                        ordered.append(v)
                return ordered

            variables_str = {str(k): v for k, v in variables.items()}
            solve_result: Dict[str, Any] = solver.solve_with_time_limit(
                model=model,
                problem=problem,
                variables=variables_str,  # Use converted dict
                time_limit_seconds=30,
                variable_selector=variable_selector,
            )

            status = solve_result.get("status")
            if status in ("OPTIMAL", "FEASIBLE"):
                cpsat_conversion = await self._cpsat_to_internal(
                    solve_result, problem, context
                )
                if cpsat_conversion.success:
                    solution = cpsat_conversion.converted_object
                    return ConversionResult(
                        success=True,
                        converted_object=solution,
                        metadata={
                            "chromosome_fitness": getattr(
                                genetic_data, "fitness", None
                            ),
                            "solve_status": status,
                            "conversion_via": "cp_sat",
                        },
                    )

            return ConversionResult(
                success=False,
                errors=[
                    f"Genetic solution could not produce feasible timetable: {status}"
                ],
            )

        except Exception as e:
            logger.error(f"Error converting genetic solution to internal format: {e}")
            return ConversionResult(success=False, errors=[str(e)])

    async def _internal_to_genetic(
        self,
        internal_solution: TimetableSolution,
        problem: ExamSchedulingProblem,
        context: Optional[Dict[str, Any]] = None,
    ) -> ConversionResult:
        """Convert internal solution to genetic algorithm representation"""
        try:
            from ..genetic_algorithm.chromosome import VariableSelectorChromosome

            # Extract variable ordering patterns from solution
            variable_priorities = await self._extract_variable_priorities(
                internal_solution, problem
            )

            # Create chromosome based on solution patterns
            chromosome = VariableSelectorChromosome.create_random(problem)
            chromosome.fitness = internal_solution.fitness_score
            chromosome.objective_value = internal_solution.objective_value

            return ConversionResult(
                success=True,
                converted_object=chromosome,
                metadata={
                    "variable_priorities": len(variable_priorities),
                    "chromosome_fitness": chromosome.fitness,
                    "conversion_direction": "internal_to_genetic",
                },
            )

        except Exception as e:
            logger.error(f"Error converting internal solution to genetic format: {e}")
            return ConversionResult(success=False, errors=[str(e)])

    # ==================== Database Conversions ====================

    async def _internal_to_database(
        self,
        internal_solution: TimetableSolution,
        problem: ExamSchedulingProblem,
        context: Optional[Dict[str, Any]] = None,
    ) -> ConversionResult:
        """Convert internal solution to database-compatible format"""
        try:
            job_id = context.get("job_id", uuid4()) if context else uuid4()
            version_number = context.get("version_number", 1) if context else 1

            # Create exam assignment records
            exam_assignments = []
            for exam_id, assignment in internal_solution.assignments.items():
                if assignment.is_complete():
                    exam_record = {
                        "exam_id": str(exam_id),
                        "time_slot_id": str(assignment.time_slot_id),
                        "assigned_date": (
                            assignment.assigned_date.isoformat()
                            if assignment.assigned_date
                            else None
                        ),
                    }
                    exam_assignments.append(exam_record)

            # Create room assignment records
            room_assignments = []
            for exam_id, assignment in internal_solution.assignments.items():
                if assignment.is_complete():
                    for room_id in assignment.room_ids:
                        room_record = {
                            "exam_id": str(exam_id),
                            "room_id": str(room_id),
                        }
                        room_assignments.append(room_record)

            # Calculate quality metrics
            quality_score = self.metrics.evaluate_solution_quality(
                problem, internal_solution
            )
            quality_metrics = (
                {
                    "overall_score": quality_score.total_score,
                    "constraint_satisfaction": quality_score.constraint_satisfaction_score,
                    "objective_quality": quality_score.objective_value_score,
                    "room_utilization": quality_score.resource_utilization_score,
                    "student_satisfaction": quality_score.student_satisfaction_score,
                }
                if quality_score
                else {}
            )

            database_solution = DatabaseSolutionData(
                job_id=job_id,
                version_number=version_number,
                exam_assignments=exam_assignments,
                room_assignments=room_assignments,
                metadata={
                    "solution_id": str(internal_solution.id),
                    "created_at": internal_solution.created_at.isoformat(),
                    "last_modified": internal_solution.last_modified.isoformat(),
                    "status": internal_solution.status.value,
                    "total_assignments": len(internal_solution.assignments),
                },
                quality_metrics=quality_metrics,
            )

            return ConversionResult(
                success=True,
                converted_object=database_solution,
                metadata={
                    "exam_assignments": len(exam_assignments),
                    "room_assignments": len(room_assignments),
                },
            )

        except Exception as e:
            logger.error(f"Error converting internal solution to database format: {e}")
            return ConversionResult(success=False, errors=[str(e)])

    async def _database_to_internal(
        self,
        database_solution: DatabaseSolutionData,
        problem: ExamSchedulingProblem,
        context: Optional[Dict[str, Any]] = None,
    ) -> ConversionResult:
        """Convert database solution format to internal TimetableSolution"""
        try:
            # Create internal solution
            solution = TimetableSolution(problem=problem)

            # Reconstruct exam assignments
            for exam_assignment in database_solution.exam_assignments:
                exam_id = UUID(exam_assignment["exam_id"])

                # Create assignment
                assignment = ExamAssignment(exam_id=exam_id)

                # Set time slot if available
                if exam_assignment.get("time_slot_id"):
                    assignment.time_slot_id = UUID(exam_assignment["time_slot_id"])

                # Set assigned date if available
                if exam_assignment.get("assigned_date"):
                    assignment.assigned_date = datetime.fromisoformat(
                        exam_assignment["assigned_date"]
                    ).date()

                solution.assignments[exam_id] = assignment

            # Reconstruct room assignments
            for room_assignment in database_solution.room_assignments:
                exam_id = UUID(room_assignment["exam_id"])
                room_id = UUID(room_assignment["room_id"])

                if exam_id in solution.assignments:
                    if room_id not in solution.assignments[exam_id].room_ids:
                        solution.assignments[exam_id].room_ids.append(room_id)

            # Set solution status
            status_str = database_solution.metadata.get("status", "feasible")
            try:
                solution.status = SolutionStatus[status_str.upper()]
            except KeyError:
                solution.status = SolutionStatus.FEASIBLE

            return ConversionResult(
                success=True,
                converted_object=solution,
                metadata={
                    "assignments_reconstructed": len(solution.assignments),
                    "total_rooms": len(database_solution.room_assignments),
                },
            )

        except Exception as e:
            logger.error(f"Error converting database solution to internal format: {e}")
            return ConversionResult(success=False, errors=[str(e)])

    # ==================== Export Conversions ====================

    async def _internal_to_export(
        self,
        internal_solution: TimetableSolution,
        problem: ExamSchedulingProblem,
        context: Optional[Dict[str, Any]] = None,
    ) -> ConversionResult:
        """Convert internal solution to export-friendly format"""
        try:
            export_format = context.get("export_format", "json") if context else "json"
            timetable: List[Dict[str, Any]] = []
            # Create export structure
            export_data = {
                "metadata": {
                    "solution_id": str(internal_solution.id),
                    "session_id": str(problem.session_id),
                    "created_at": internal_solution.created_at.isoformat(),
                    "last_modified": internal_solution.last_modified.isoformat(),
                    "status": internal_solution.status.value,
                    "objective_value": internal_solution.objective_value,
                    "total_exams": len(internal_solution.assignments),
                },
                "timetable": timetable,
                "statistics": {
                    "rooms_used": len(
                        set(
                            room_id
                            for assignment in internal_solution.assignments.values()
                            for room_id in assignment.room_ids
                        )
                    ),
                    "time_slots_used": len(
                        set(
                            assignment.time_slot_id
                            for assignment in internal_solution.assignments.values()
                            if assignment.time_slot_id
                        )
                    ),
                },
            }

            # Create timetable entries
            for exam_id, assignment in internal_solution.assignments.items():
                if not assignment.is_complete():
                    continue

                exam = problem.exams.get(exam_id)
                if not exam:
                    continue

                # Get room details
                room_details: List[Dict[str, Any]] = []
                for room_id in assignment.room_ids:
                    room = problem.rooms.get(room_id)
                    if room:
                        room_details.append(
                            {
                                "room_id": str(room_id),
                                "room_code": room.code,
                                "room_name": room.name,
                                "capacity": room.exam_capacity,
                            }
                        )

                # Get time slot details
                time_slot_info = {}
                if assignment.time_slot_id:
                    time_slot = problem.time_slots.get(assignment.time_slot_id)
                    if time_slot:
                        time_slot_info = {
                            "time_slot_id": str(assignment.time_slot_id),
                            "name": time_slot.name,
                            "start_time": str(time_slot.start_time),
                            "end_time": str(time_slot.end_time),
                            "duration": time_slot.duration_minutes,
                        }

                # Create timetable entry
                timetable_entry = {
                    "exam_id": str(exam_id),
                    "course_code": exam.course_code,
                    "course_title": exam.course_title,
                    "exam_date": (
                        assignment.assigned_date.isoformat()
                        if assignment.assigned_date
                        else None
                    ),
                    "time_slot": time_slot_info,
                    "rooms": room_details,
                    "expected_students": exam.expected_students,
                    "duration_minutes": exam.duration_minutes,
                    "is_practical": exam.is_practical,
                    "requires_special_arrangements": exam.requires_special_arrangements,
                    "status": "scheduled",
                }

                timetable.append(timetable_entry)

            # Sort timetable by date and time
            timetable.sort(
                key=lambda x: (
                    x["exam_date"] or "9999-12-31",
                    x["time_slot"].get("start_time", "") or "23:59",
                )
            )

            return ConversionResult(
                success=True,
                converted_object=export_data,
                metadata={
                    "export_format": export_format,
                    "timetable_entries": len(export_data["timetable"]),
                    "export_timestamp": datetime.now().isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"Error converting internal solution to export format: {e}")
            return ConversionResult(success=False, errors=[str(e)])

    # ==================== Utility Methods ====================

    async def _extract_variable_priorities(
        self, solution: TimetableSolution, problem: ExamSchedulingProblem
    ) -> Dict[str, float]:
        """Extract variable priority patterns from a solution"""
        try:
            priorities = {}

            # Analyze assignment patterns to infer priorities
            for exam_id, assignment in solution.assignments.items():
                exam = problem.exams.get(exam_id)
                if not exam:
                    continue

                # Extract GP-style terminals for this exam
                terminals = problem.extract_gp_terminals(exam_id)

                # Create priority based on assignment quality
                priority = self._calculate_assignment_priority(
                    assignment, exam, terminals
                )
                priorities[str(exam_id)] = priority

            return priorities

        except Exception as e:
            logger.error(f"Error extracting variable priorities: {e}")
            return {}

    def _calculate_assignment_priority(
        self, assignment: ExamAssignment, exam: Exam, terminals: Dict[str, Any]
    ) -> float:
        """Calculate priority for an exam assignment based on various factors"""
        try:
            priority = 0.0

            # Weight (from GP terminal set)
            weight = terminals.get("W", 1.0)
            priority += weight * 0.3

            # Processing time influence
            processing_time = terminals.get("PT", exam.duration_minutes)
            priority += processing_time / 180.0 * 0.2  # Normalize by 3 hours

            # Earliness preference
            earliest_start = terminals.get("ES", 0)
            priority += (
                1.0 - earliest_start / 24.0
            ) * 0.2  # Earlier is higher priority

            return min(priority, 1.0)  # Cap at 1.0

        except Exception as e:
            logger.error(f"Error calculating assignment priority: {e}")
            return 0.5  # Default medium priority

    async def _validate_conversion_integrity(
        self,
        source_object: Any,
        converted_object: Any,
        source_format: ConversionFormat,
        target_format: ConversionFormat,
        problem: ExamSchedulingProblem,
    ) -> Dict[str, Any]:
        """Validate that conversion preserved essential data integrity"""
        try:
            integrity_score = 1.0
            warnings = []

            # Format-specific validation
            if (
                source_format == ConversionFormat.INTERNAL
                and target_format == ConversionFormat.DATABASE
            ):
                # Check that all exam assignments were preserved
                source_exams = len(source_object.assignments)
                if hasattr(converted_object, "exam_assignments"):
                    target_exams = len(converted_object.exam_assignments)

                    if source_exams != target_exams:
                        integrity_score *= 0.8
                        warnings.append(
                            f"Assignment count mismatch: {source_exams} -> {target_exams}"
                        )

            elif (
                source_format == ConversionFormat.CP_SAT
                and target_format == ConversionFormat.INTERNAL
            ):
                # Check objective value preservation
                if hasattr(source_object, "get") and callable(source_object.get):
                    source_obj = source_object.get("objective_value", 0)
                else:
                    source_obj = getattr(source_object, "objective_value", 0)

                target_obj = converted_object.objective_value

                if abs(source_obj - target_obj) > 0.001:
                    integrity_score *= 0.9
                    warnings.append(
                        f"Objective value changed: {source_obj} -> {target_obj}"
                    )

            return {
                "integrity_score": integrity_score,
                "warnings": warnings,
                "validation_passed": integrity_score >= 0.9,
            }

        except Exception as e:
            logger.error(f"Error validating conversion integrity: {e}")
            return {
                "integrity_score": 0.5,
                "warnings": [f"Validation error: {e}"],
                "validation_passed": False,
            }

    # ==================== Batch Conversion Methods ====================

    async def convert_solution_batch(
        self,
        solutions: List[Tuple[Any, ConversionFormat]],
        target_format: ConversionFormat,
        problem: ExamSchedulingProblem,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ConversionResult]:
        """Convert multiple solutions in batch"""
        results = []

        for source_solution, source_format in solutions:
            result = await self.convert_solution(
                source_solution, source_format, target_format, problem, context
            )
            results.append(result)

        logger.info(
            f"Batch converted {len(solutions)} solutions to {target_format.value}"
        )
        return results

    async def validate_solution_consistency(
        self,
        solution1: TimetableSolution,
        solution2: TimetableSolution,
        tolerance: float = 0.01,
    ) -> Dict[str, Any]:
        """Validate consistency between two solutions"""
        try:
            differences: List[str] = []

            # Check assignment differences
            all_exams = set(solution1.assignments.keys()) | set(
                solution2.assignments.keys()
            )

            for exam_id in all_exams:
                assign1 = solution1.assignments.get(exam_id)
                assign2 = solution2.assignments.get(exam_id)

                if not assign1 and assign2:
                    differences.append(f"Exam {exam_id} missing in solution 1")
                elif assign1 and not assign2:
                    differences.append(f"Exam {exam_id} missing in solution 2")
                elif assign1 and assign2:
                    if assign1.time_slot_id != assign2.time_slot_id:
                        differences.append(f"Exam {exam_id} time slot difference")
                    if set(assign1.room_ids) != set(assign2.room_ids):
                        differences.append(f"Exam {exam_id} room assignment difference")

            # Check objective value difference
            obj_diff = abs(solution1.objective_value - solution2.objective_value)
            objective_consistent = obj_diff <= tolerance

            return {
                "is_consistent": len(differences) == 0 and objective_consistent,
                "differences": differences,
                "objective_difference": obj_diff,
                "objective_consistent": objective_consistent,
                "similarity_score": 1.0 - (len(differences) / max(len(all_exams), 1)),
            }

        except Exception as e:
            logger.error(f"Error validating solution consistency: {e}")
            return {
                "is_consistent": False,
                "differences": [f"Validation error: {e}"],
                "similarity_score": 0.0,
            }

    def get_conversion_statistics(self) -> Dict[str, Any]:
        """Get conversion performance statistics"""
        stats = {
            "total_conversions": sum(self.conversion_stats.values()),
            "conversions_by_type": dict(self.conversion_stats),
            "average_times": {},
        }

        # Calculate average conversion times
        average_times = {}
        for conversion_type, times in self.conversion_times.items():
            if times:
                average_times[conversion_type] = {
                    "mean": sum(times) / len(times),
                    "min": min(times),
                    "max": max(times),
                    "count": len(times),
                }
        stats["average_times"] = average_times

        return stats

    def reset_statistics(self) -> None:
        """Reset conversion statistics"""
        self.conversion_stats.clear()
        self.conversion_times.clear()
        logger.info("Conversion statistics reset")


# Factory function
def create_solution_converter(config: SchedulingEngineConfig) -> SolutionConverter:
    """Create and configure a solution converter instance"""
    return SolutionConverter(config)
