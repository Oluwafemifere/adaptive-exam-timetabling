# scheduling_engine/genetic_algorithm/fitness.py

"""
Fitness Evaluator for Genetic Algorithm component of hybrid CP-SAT + GA scheduling engine.
Implements quality-based fitness evaluation as described in the research paper,
focusing on solution quality rather than computational effort.

Based on Nguyen et al. 2024 "Genetic-based Constraint Programming for Resource Constrained Job Scheduling"
"""

from typing import Dict, List, Optional, Any
from uuid import UUID
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics
import asyncio

from ..core.problem_model import ExamSchedulingProblem
from ..core.solution import TimetableSolution, SolutionStatus
from ..core.metrics import SolutionMetrics, QualityScore
from .chromosome import VariableSelectorChromosome
from ..cp_sat.solver_manager import CPSATSolverManager
from ..utils.logging import get_logger

logger = get_logger(__name__)


class FitnessObjective(Enum):
    """Fitness objectives for evaluation"""

    MINIMIZE_CONFLICTS = "minimize_conflicts"
    MAXIMIZE_ROOM_UTILIZATION = "maximize_room_utilization"
    MINIMIZE_STUDENT_TRAVEL = "minimize_student_travel"
    BALANCE_WORKLOAD = "balance_workload"
    MINIMIZE_TIME_GAPS = "minimize_time_gaps"
    MULTI_OBJECTIVE = "multi_objective"


class ConstraintViolationType(Enum):
    """Types of constraint violations"""

    STUDENT_CONFLICT = "student_conflict"
    ROOM_CAPACITY = "room_capacity"
    TIME_AVAILABILITY = "time_availability"
    STAFF_CONFLICT = "staff_conflict"
    CARRYOVER_PRIORITY = "carryover_priority"
    RESOURCE_CONSTRAINT = "resource_constraint"
    PRECEDENCE_VIOLATION = "precedence_violation"


@dataclass
class ConstraintViolation:
    """Represents a constraint violation"""

    violation_type: ConstraintViolationType
    severity: float  # 0.0 to 1.0
    affected_entities: List[UUID]
    description: str
    penalty_weight: float = 1.0


@dataclass
class FitnessComponent:
    """Individual component of fitness evaluation"""

    name: str
    value: float
    weight: float
    normalized_value: float
    contribution: float


@dataclass
class FitnessResult:
    """Result of fitness evaluation"""

    # Primary fitness metrics
    total_fitness: float
    quality_score: float
    efficiency_score: float

    # Constraint satisfaction
    constraint_violations: int
    violation_penalty: float
    feasibility_score: float

    # Solution metrics
    solution: Optional[TimetableSolution]
    evaluation_time: float
    solver_iterations: int

    # Detailed breakdown
    fitness_components: List[FitnessComponent] = field(default_factory=list)
    constraint_violation_details: List[ConstraintViolation] = field(
        default_factory=list
    )
    quality_metrics: Optional[QualityScore] = None

    # Performance indicators
    room_utilization: float = 0.0
    student_satisfaction: float = 0.0
    staff_workload_balance: float = 0.0
    time_distribution: float = 0.0


@dataclass
class FitnessConfig:
    """Configuration for fitness evaluator"""

    # Objective weights (from research paper - multi-objective approach)
    quality_weight: float = 1.0
    efficiency_weight: float = 0.3
    feasibility_weight: float = 2.0

    # Objective function weights
    conflict_weight: float = 1.0
    utilization_weight: float = 0.7
    travel_weight: float = 0.5
    workload_weight: float = 0.6
    gap_weight: float = 0.4

    # Constraint violation penalties
    hard_constraint_penalty: float = 1000.0
    soft_constraint_penalty: float = 100.0
    preference_penalty: float = 10.0

    # Normalization parameters
    max_conflicts_threshold: int = 100
    max_travel_distance: float = 1000.0
    max_time_gap_minutes: int = 240

    # CP-SAT solver parameters for fitness evaluation
    solver_time_limit: float = 30.0  # Quick evaluation time limit
    solver_threads: int = 1
    enable_solution_hinting: bool = True

    # Performance thresholds
    excellent_fitness_threshold: float = 0.1
    good_fitness_threshold: float = 0.3
    acceptable_fitness_threshold: float = 0.6


class FitnessEvaluator:
    """
    Evaluates fitness of chromosomes by converting variable selectors to CP-SAT guidance
    and measuring solution quality. Implements the research paper's approach of using
    solution quality rather than computational effort for fitness evaluation.
    """

    def __init__(
        self, problem: ExamSchedulingProblem, config: Optional[FitnessConfig] = None
    ):
        self.problem = problem
        self.config = config or FitnessConfig()

        # Initialize CP-SAT solver for fitness evaluation
        self.cp_solver = CPSATSolverManager()

        # Caching for efficiency
        self.fitness_cache: Dict[str, FitnessResult] = {}
        self.problem_statistics: Dict[str, Any] = {}

        # Performance tracking
        self.evaluation_count = 0
        self.total_evaluation_time = 0.0
        self.cache_hits = 0

        # Initialize problem statistics for normalization
        asyncio.create_task(self._initialize_problem_statistics())

    async def _initialize_problem_statistics(self) -> None:
        """Initialize problem statistics for fitness normalization"""
        try:
            logger.debug("Initializing problem statistics for fitness normalization")

            # Calculate problem complexity metrics
            self.problem_statistics = {
                "total_exams": len(self.problem.exams),
                "total_students": len(self.problem.students),
                "total_rooms": len(self.problem.rooms),
                "total_time_slots": len(self.problem.time_slots),
                "average_exam_size": (
                    statistics.mean(
                        [exam.expected_students for exam in self.problem.exams.values()]
                    )
                    if self.problem.exams
                    else 0
                ),
                "max_exam_size": (
                    max(
                        [exam.expected_students for exam in self.problem.exams.values()]
                    )
                    if self.problem.exams
                    else 0
                ),
                "total_room_capacity": (
                    sum([room.capacity for room in self.problem.rooms.values()])
                    if self.problem.rooms
                    else 0
                ),
                "exam_density": (
                    len(self.problem.exams)
                    / (len(self.problem.rooms) * len(self.problem.time_slots))
                    if self.problem.rooms and self.problem.time_slots
                    else 0
                ),
            }

            # Calculate student course load distribution
            student_loads = {}
            for exam_id, exam in self.problem.exams.items():
                students = self.problem.get_students_for_exam(exam_id)
                for student_id in students:
                    if student_id not in student_loads:
                        student_loads[student_id] = 0
                    student_loads[student_id] += 1

            if student_loads:
                self.problem_statistics.update(
                    {
                        "average_student_load": statistics.mean(student_loads.values()),
                        "max_student_load": max(student_loads.values()),
                        "student_load_variance": (
                            statistics.variance(student_loads.values())
                            if len(student_loads) > 1
                            else 0
                        ),
                    }
                )

            logger.debug(f"Problem statistics initialized: {self.problem_statistics}")

        except Exception as e:
            logger.error(f"Error initializing problem statistics: {e}")
            self.problem_statistics = {}

    async def evaluate(
        self,
        chromosome: VariableSelectorChromosome,
        training_instances: Optional[List[ExamSchedulingProblem]] = None,
    ) -> FitnessResult:
        """
        Main fitness evaluation method following research paper approach:
        1. Convert chromosome to variable selector for CP-SAT
        2. Solve problem with time limit
        3. Evaluate solution quality
        4. Return fitness based on quality metrics
        """
        try:
            import time

            evaluation_start = time.time()

            # Check cache first
            cache_key = self._get_cache_key(chromosome)
            if cache_key in self.fitness_cache:
                self.cache_hits += 1
                cached_result = self.fitness_cache[cache_key]
                logger.debug(f"Fitness cache hit for chromosome {cache_key[:8]}")
                return cached_result

            # Use primary problem or training instances
            evaluation_problems = training_instances or [self.problem]

            # Evaluate on all instances and aggregate results
            instance_results = []
            for instance in evaluation_problems:
                result = await self._evaluate_single_instance(chromosome, instance)
                instance_results.append(result)

            # Aggregate results across instances
            aggregated_result = await self._aggregate_instance_results(instance_results)

            # Update performance tracking
            evaluation_time = time.time() - evaluation_start
            self.evaluation_count += 1
            self.total_evaluation_time += evaluation_time
            aggregated_result.evaluation_time = evaluation_time

            # Cache result
            self.fitness_cache[cache_key] = aggregated_result

            logger.debug(
                f"Evaluated chromosome fitness: {aggregated_result.total_fitness:.4f} "
                f"(quality: {aggregated_result.quality_score:.3f}, "
                f"efficiency: {aggregated_result.efficiency_score:.3f}) "
                f"in {evaluation_time:.3f}s"
            )

            return aggregated_result

        except Exception as e:
            logger.error(f"Error evaluating chromosome fitness: {e}")
            return self._create_error_fitness_result(str(e))

    async def _evaluate_single_instance(
        self, chromosome: VariableSelectorChromosome, problem: ExamSchedulingProblem
    ) -> FitnessResult:
        """Evaluate chromosome on a single problem instance"""
        try:
            # Convert chromosome to CP-SAT variable selector
            variable_ordering = chromosome.get_variable_ordering(problem)

            # Solve problem using variable selector guidance
            solution = await self._solve_with_variable_ordering(
                problem, variable_ordering, time_limit=self.config.solver_time_limit
            )

            if solution is None or solution.status == SolutionStatus.INFEASIBLE:
                return self._create_infeasible_fitness_result()

            # Evaluate solution quality
            quality_metrics = await self._evaluate_solution_quality(solution, problem)

            # Calculate constraint violations
            violations = await self._evaluate_constraint_violations(solution, problem)

            # Calculate fitness components
            fitness_components = await self._calculate_fitness_components(
                solution, problem, quality_metrics, violations
            )

            # Aggregate into total fitness
            total_fitness = self._aggregate_fitness_components(fitness_components)

            return FitnessResult(
                total_fitness=total_fitness,
                quality_score=quality_metrics.total_score if quality_metrics else 0.0,
                efficiency_score=self._calculate_efficiency_score(solution, problem),
                constraint_violations=len(violations),
                violation_penalty=sum(
                    v.penalty_weight * v.severity for v in violations
                ),
                feasibility_score=1.0 - min(1.0, len(violations) / 10.0),  # Normalize
                solution=solution,
                evaluation_time=0.0,  # Will be set by caller
                solver_iterations=getattr(solution, "solver_iterations", 0),
                fitness_components=fitness_components,
                constraint_violation_details=violations,
                quality_metrics=quality_metrics,
                room_utilization=(
                    quality_metrics.resource_utilization_score
                    if quality_metrics
                    else 0.0
                ),
                student_satisfaction=(
                    quality_metrics.student_satisfaction_score
                    if quality_metrics
                    else 0.0
                ),
                staff_workload_balance=self._calculate_staff_workload_balance(
                    solution, problem
                ),
                time_distribution=self._calculate_time_distribution_score(
                    solution, problem
                ),
            )

        except Exception as e:
            logger.error(f"Error evaluating single instance: {e}")
            return self._create_error_fitness_result(str(e))

    async def _solve_with_variable_ordering(
        self,
        problem: ExamSchedulingProblem,
        variable_ordering: List[UUID],
        time_limit: float,
    ) -> Optional[TimetableSolution]:
        """Solve problem using variable ordering to guide CP-SAT search"""
        try:
            # Configure CP-SAT solver with variable ordering
            solver_config = {
                "time_limit_seconds": time_limit,
                "num_search_workers": self.config.solver_threads,
                "variable_ordering": variable_ordering,
                "solution_hinting": self.config.enable_solution_hinting,
            }

            # Solve using CP-SAT with variable ordering guidance
            # Note: Using asyncio.to_thread to run synchronous solver in a thread
            result = await asyncio.to_thread(
                lambda: self.cp_solver.solve(problem, **solver_config)  # type: ignore
            )

            return result  # type: ignore

        except Exception as e:
            logger.error(f"Error solving with variable ordering: {e}")
            return None

    async def _evaluate_solution_quality(
        self, solution: TimetableSolution, problem: ExamSchedulingProblem
    ) -> Optional[QualityScore]:
        """Evaluate comprehensive solution quality metrics"""
        try:
            metrics = SolutionMetrics()
            return metrics.evaluate_solution_quality(problem, solution)
        except Exception as e:
            logger.error(f"Error evaluating solution quality: {e}")
            return None

    async def _evaluate_constraint_violations(
        self, solution: TimetableSolution, problem: ExamSchedulingProblem
    ) -> List[ConstraintViolation]:
        """Evaluate constraint violations in solution"""
        try:
            violations = []

            # Check student conflicts
            student_conflicts = await self._check_student_conflicts(solution, problem)
            violations.extend(student_conflicts)

            # Check room capacity violations
            capacity_violations = await self._check_room_capacity_violations(
                solution, problem
            )
            violations.extend(capacity_violations)

            # Check time availability violations
            time_violations = await self._check_time_availability_violations(
                solution, problem
            )
            violations.extend(time_violations)

            return violations

        except Exception as e:
            logger.error(f"Error evaluating constraint violations: {e}")
            return []

    async def _check_student_conflicts(
        self, solution: TimetableSolution, problem: ExamSchedulingProblem
    ) -> List[ConstraintViolation]:
        """Check for student scheduling conflicts"""
        try:
            violations = []

            # Group assignments by time slot
            assignments_by_slot = defaultdict(list)
            for assignment in solution.assignments.values():
                if assignment.time_slot_id:
                    assignments_by_slot[assignment.time_slot_id].append(assignment)

            # Check each time slot for student conflicts
            for slot_id, assignments in assignments_by_slot.items():
                if len(assignments) < 2:
                    continue

                # Find students scheduled in multiple exams at same time
                student_exam_map = defaultdict(list)
                for assignment in assignments:
                    exam = problem.exams.get(assignment.exam_id)
                    if exam:
                        students = problem.get_students_for_exam(exam.id)
                        for student_id in students:
                            student_exam_map[student_id].append(assignment.exam_id)

                # Report conflicts
                for student_id, exam_ids in student_exam_map.items():
                    if len(exam_ids) > 1:
                        violation = ConstraintViolation(
                            violation_type=ConstraintViolationType.STUDENT_CONFLICT,
                            severity=1.0,  # Hard constraint
                            affected_entities=exam_ids,
                            description=f"Student {student_id} has conflicting exams: {exam_ids}",
                            penalty_weight=self.config.hard_constraint_penalty,
                        )
                        violations.append(violation)

            return violations

        except Exception as e:
            logger.error(f"Error checking student conflicts: {e}")
            return []

    async def _check_room_capacity_violations(
        self, solution: TimetableSolution, problem: ExamSchedulingProblem
    ) -> List[ConstraintViolation]:
        """Check for room capacity violations"""
        try:
            violations = []

            for assignment in solution.assignments.values():
                if not assignment.room_ids or not assignment.exam_id:
                    continue

                # Find exam details
                exam = problem.exams.get(assignment.exam_id)
                if not exam:
                    continue

                # Check each room in the assignment
                for room_id in assignment.room_ids:
                    room = problem.rooms.get(room_id)
                    if not room:
                        continue

                    # Check capacity violation
                    allocated = assignment.room_allocations.get(room_id, 0)
                    if allocated > room.exam_capacity:
                        overflow = allocated - room.exam_capacity
                        severity = min(1.0, overflow / room.exam_capacity)

                        violation = ConstraintViolation(
                            violation_type=ConstraintViolationType.ROOM_CAPACITY,
                            severity=severity,
                            affected_entities=[exam.id, room.id],
                            description=f"Exam {exam.course_code} ({allocated} students) exceeds room {room.code} capacity ({room.exam_capacity})",
                            penalty_weight=self.config.hard_constraint_penalty,
                        )
                        violations.append(violation)

            return violations

        except Exception as e:
            logger.error(f"Error checking room capacity violations: {e}")
            return []

    async def _check_time_availability_violations(
        self, solution: TimetableSolution, problem: ExamSchedulingProblem
    ) -> List[ConstraintViolation]:
        """Check for time availability violations"""
        try:
            violations = []

            for assignment in solution.assignments.values():
                if assignment.time_slot_id and assignment.exam_id:
                    # Check if exam is scheduled outside allowed time windows
                    exam = problem.exams.get(assignment.exam_id)
                    time_slot = problem.time_slots.get(assignment.time_slot_id)

                    if exam and exam.morning_only and time_slot:
                        # Check if time slot is in morning (assuming morning ends at 12:00)
                        if time_slot.start_time.hour >= 12:
                            violation = ConstraintViolation(
                                violation_type=ConstraintViolationType.TIME_AVAILABILITY,
                                severity=1.0,
                                affected_entities=[exam.id],
                                description=f"Morning-only exam {exam.course_code} scheduled in afternoon",
                                penalty_weight=self.config.hard_constraint_penalty,
                            )
                            violations.append(violation)

            return violations

        except Exception as e:
            logger.error(f"Error checking time availability violations: {e}")
            return []

    async def _calculate_fitness_components(
        self,
        solution: TimetableSolution,
        problem: ExamSchedulingProblem,
        quality_metrics: Optional[QualityScore],
        violations: List[ConstraintViolation],
    ) -> List[FitnessComponent]:
        """Calculate individual fitness components"""
        try:
            components = []

            # Quality component
            if quality_metrics:
                quality_value = (
                    1.0 - quality_metrics.total_score
                )  # Convert to minimization
                components.append(
                    FitnessComponent(
                        name="quality",
                        value=quality_value,
                        weight=self.config.quality_weight,
                        normalized_value=quality_value,
                        contribution=quality_value * self.config.quality_weight,
                    )
                )

            # Constraint violation component
            violation_penalty = sum(v.penalty_weight * v.severity for v in violations)
            normalized_penalty = min(1.0, violation_penalty / 1000.0)  # Normalize
            components.append(
                FitnessComponent(
                    name="violations",
                    value=violation_penalty,
                    weight=self.config.feasibility_weight,
                    normalized_value=normalized_penalty,
                    contribution=normalized_penalty * self.config.feasibility_weight,
                )
            )

            # Room utilization component
            utilization_score = self._calculate_room_utilization_fitness(
                solution, problem
            )
            components.append(
                FitnessComponent(
                    name="room_utilization",
                    value=utilization_score,
                    weight=self.config.utilization_weight,
                    normalized_value=utilization_score,
                    contribution=utilization_score * self.config.utilization_weight,
                )
            )

            # Student travel component
            travel_score = self._calculate_student_travel_fitness(solution, problem)
            components.append(
                FitnessComponent(
                    name="student_travel",
                    value=travel_score,
                    weight=self.config.travel_weight,
                    normalized_value=travel_score,
                    contribution=travel_score * self.config.travel_weight,
                )
            )

            # Time distribution component
            time_score = self._calculate_time_distribution_fitness(solution, problem)
            components.append(
                FitnessComponent(
                    name="time_distribution",
                    value=time_score,
                    weight=self.config.gap_weight,
                    normalized_value=time_score,
                    contribution=time_score * self.config.gap_weight,
                )
            )

            return components

        except Exception as e:
            logger.error(f"Error calculating fitness components: {e}")
            return []

    def _aggregate_fitness_components(
        self, components: List[FitnessComponent]
    ) -> float:
        """Aggregate fitness components into total fitness"""
        try:
            if not components:
                return float("inf")

            # Weighted sum of contributions
            total_fitness = sum(component.contribution for component in components)

            # Apply penalties and bonuses
            # Add small penalty for complexity to prefer simpler solutions when quality is equal
            complexity_penalty = len(components) * 0.01

            return total_fitness + complexity_penalty

        except Exception as e:
            logger.error(f"Error aggregating fitness components: {e}")
            return float("inf")

    def _calculate_room_utilization_fitness(
        self, solution: TimetableSolution, problem: ExamSchedulingProblem
    ) -> float:
        """Calculate room utilization fitness component"""
        try:
            total_capacity = sum(room.exam_capacity for room in problem.rooms.values())
            if total_capacity == 0:
                return 0.0

            used_capacity = 0
            for assignment in solution.assignments.values():
                if assignment.room_ids:
                    exam = problem.exams.get(assignment.exam_id)
                    if exam:
                        used_capacity += min(
                            exam.expected_students,
                            sum(assignment.room_allocations.values()),
                        )

            utilization_rate = used_capacity / total_capacity

            # Convert to fitness (lower is better, so invert high utilization)
            target_utilization = 0.8  # Target 80% utilization
            fitness = abs(utilization_rate - target_utilization)

            return fitness

        except Exception as e:
            logger.error(f"Error calculating room utilization fitness: {e}")
            return 1.0

    def _calculate_student_travel_fitness(
        self, solution: TimetableSolution, problem: ExamSchedulingProblem
    ) -> float:
        """Calculate student travel minimization fitness component"""
        try:
            # Simplified implementation - would need actual room locations for accurate calculation
            # For now, just return a baseline value
            return 0.5

        except Exception as e:
            logger.error(f"Error calculating student travel fitness: {e}")
            return 0.0

    def _calculate_time_distribution_fitness(
        self, solution: TimetableSolution, problem: ExamSchedulingProblem
    ) -> float:
        """Calculate time distribution fitness component"""
        try:
            # Count exams per time slot
            slot_usage: Dict[UUID, int] = defaultdict(int)
            for assignment in solution.assignments.values():
                if assignment.time_slot_id:
                    slot_usage[assignment.time_slot_id] += 1

            if not slot_usage:
                return 1.0

            # Calculate distribution variance (prefer even distribution)
            usage_counts = list(slot_usage.values())
            mean_usage = statistics.mean(usage_counts)
            variance = statistics.variance(usage_counts) if len(usage_counts) > 1 else 0

            # Normalize variance to [0, 1]
            max_possible_variance = mean_usage**2  # Worst case: all exams in one slot
            normalized_variance = min(1.0, variance / max(max_possible_variance, 1.0))

            return normalized_variance

        except Exception as e:
            logger.error(f"Error calculating time distribution fitness: {e}")
            return 0.0

    def _calculate_efficiency_score(
        self, solution: TimetableSolution, problem: ExamSchedulingProblem
    ) -> float:
        """Calculate efficiency score based on resource utilization"""
        try:
            # Simple efficiency metric based on assignments made
            total_possible_assignments = len(problem.exams)
            actual_assignments = len(
                [a for a in solution.assignments.values() if a.is_complete()]
            )

            if total_possible_assignments == 0:
                return 0.0

            efficiency = actual_assignments / total_possible_assignments
            return efficiency

        except Exception as e:
            logger.error(f"Error calculating efficiency score: {e}")
            return 0.0

    def _calculate_staff_workload_balance(
        self, solution: TimetableSolution, problem: ExamSchedulingProblem
    ) -> float:
        """Calculate staff workload balance score"""
        try:
            # This would calculate how evenly distributed staff workload is
            # Placeholder implementation
            return 0.5

        except Exception as e:
            logger.error(f"Error calculating staff workload balance: {e}")
            return 0.0

    def _calculate_time_distribution_score(
        self, solution: TimetableSolution, problem: ExamSchedulingProblem
    ) -> float:
        """Calculate time distribution quality score"""
        try:
            # Calculate how well exams are distributed across time slots
            return 1.0 - self._calculate_time_distribution_fitness(solution, problem)

        except Exception as e:
            logger.error(f"Error calculating time distribution score: {e}")
            return 0.0

    async def _aggregate_instance_results(
        self, results: List[FitnessResult]
    ) -> FitnessResult:
        """Aggregate fitness results across multiple instances"""
        try:
            if not results:
                return self._create_error_fitness_result("No results to aggregate")

            # Use weighted average based on instance importance
            total_fitness = statistics.mean([r.total_fitness for r in results])
            quality_score = statistics.mean([r.quality_score for r in results])
            efficiency_score = statistics.mean([r.efficiency_score for r in results])

            # Sum violations across instances
            total_violations = sum([r.constraint_violations for r in results])
            total_violation_penalty = sum([r.violation_penalty for r in results])

            # Use best solution among instances
            best_result = min(results, key=lambda r: r.total_fitness)

            return FitnessResult(
                total_fitness=total_fitness,
                quality_score=quality_score,
                efficiency_score=efficiency_score,
                constraint_violations=total_violations,
                violation_penalty=total_violation_penalty,
                feasibility_score=statistics.mean(
                    [r.feasibility_score for r in results]
                ),
                solution=best_result.solution,
                evaluation_time=sum([r.evaluation_time for r in results]),
                solver_iterations=sum([r.solver_iterations for r in results]),
                fitness_components=best_result.fitness_components,
                constraint_violation_details=best_result.constraint_violation_details,
                quality_metrics=best_result.quality_metrics,
                room_utilization=statistics.mean([r.room_utilization for r in results]),
                student_satisfaction=statistics.mean(
                    [r.student_satisfaction for r in results]
                ),
                staff_workload_balance=statistics.mean(
                    [r.staff_workload_balance for r in results]
                ),
                time_distribution=statistics.mean(
                    [r.time_distribution for r in results]
                ),
            )

        except Exception as e:
            logger.error(f"Error aggregating instance results: {e}")
            return self._create_error_fitness_result(str(e))

    def _get_cache_key(self, chromosome: VariableSelectorChromosome) -> str:
        """Generate cache key for chromosome"""
        try:
            # Create hash of chromosome structure and parameters
            return str(hash(str(chromosome.to_dict())))
        except Exception as e:
            logger.error(f"Error generating cache key: {e}")
            return str(hash(str(chromosome)))

    def _create_error_fitness_result(self, error_message: str) -> FitnessResult:
        """Create fitness result for error cases"""
        return FitnessResult(
            total_fitness=float("inf"),
            quality_score=0.0,
            efficiency_score=0.0,
            constraint_violations=1000,
            violation_penalty=self.config.hard_constraint_penalty,
            feasibility_score=0.0,
            solution=None,
            evaluation_time=0.0,
            solver_iterations=0,
            fitness_components=[],
            constraint_violation_details=[
                ConstraintViolation(
                    violation_type=ConstraintViolationType.RESOURCE_CONSTRAINT,
                    severity=1.0,
                    affected_entities=[],
                    description=f"Evaluation error: {error_message}",
                    penalty_weight=self.config.hard_constraint_penalty,
                )
            ],
        )

    def _create_infeasible_fitness_result(self) -> FitnessResult:
        """Create fitness result for infeasible solutions"""
        return FitnessResult(
            total_fitness=float("inf"),
            quality_score=0.0,
            efficiency_score=0.0,
            constraint_violations=1,
            violation_penalty=self.config.hard_constraint_penalty,
            feasibility_score=0.0,
            solution=None,
            evaluation_time=0.0,
            solver_iterations=0,
            fitness_components=[],
            constraint_violation_details=[
                ConstraintViolation(
                    violation_type=ConstraintViolationType.RESOURCE_CONSTRAINT,
                    severity=1.0,
                    affected_entities=[],
                    description="Solution is infeasible",
                    penalty_weight=self.config.hard_constraint_penalty,
                )
            ],
        )

    # Quick evaluation methods for pre-selection

    async def evaluate_quick(
        self,
        chromosome: VariableSelectorChromosome,
        small_instances: List[ExamSchedulingProblem],
    ) -> FitnessResult:
        """Quick evaluation using small instances (for pre-selection)"""
        try:
            # Use shorter time limit for quick evaluation
            original_time_limit = self.config.solver_time_limit
            self.config.solver_time_limit = 5.0  # 5 seconds for quick eval

            result = await self.evaluate(chromosome, small_instances)

            # Restore original time limit
            self.config.solver_time_limit = original_time_limit

            return result

        except Exception as e:
            logger.error(f"Error in quick evaluation: {e}")
            return self._create_error_fitness_result(str(e))

    # Performance and statistics methods

    def get_evaluation_statistics(self) -> Dict[str, Any]:
        """Get fitness evaluation statistics"""
        try:
            avg_eval_time = self.total_evaluation_time / max(self.evaluation_count, 1)

            cache_hit_rate = self.cache_hits / max(
                self.evaluation_count + self.cache_hits, 1
            )

            return {
                "total_evaluations": self.evaluation_count,
                "cache_hits": self.cache_hits,
                "cache_hit_rate": cache_hit_rate,
                "total_evaluation_time": self.total_evaluation_time,
                "average_evaluation_time": avg_eval_time,
                "cached_results": len(self.fitness_cache),
                "evaluations_per_second": self.evaluation_count
                / max(self.total_evaluation_time, 1),
            }

        except Exception as e:
            logger.error(f"Error getting evaluation statistics: {e}")
            return {}

    def clear_cache(self) -> None:
        """Clear fitness evaluation cache"""
        try:
            self.fitness_cache.clear()
            logger.info("Fitness evaluation cache cleared")
        except Exception as e:
            logger.error(f"Error clearing fitness cache: {e}")

    def update_config(self, new_config: FitnessConfig) -> None:
        """Update fitness evaluation configuration"""
        try:
            self.config = new_config
            self.clear_cache()  # Clear cache since config changed
            logger.info("Fitness evaluator configuration updated")
        except Exception as e:
            logger.error(f"Error updating fitness config: {e}")
