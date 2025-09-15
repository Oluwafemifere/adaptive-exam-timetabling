# # scheduling_engine/hybrid/adaptive_controller.py

# """
# Adaptive Controller for Hybrid Optimization.
# Dynamically adjusts optimization parameters based on problem characteristics,
# solution quality progression, and resource constraints. Implements adaptive
# parameter tuning from the research paper for improved performance.
# """

# from typing import Dict, List, Optional, Any, Tuple
# from uuid import UUID, uuid4
# from datetime import datetime
# import time
# from dataclasses import dataclass, field
# from enum import Enum
# from collections import deque, defaultdict
# import numpy as np

# from ..config import get_logger, SchedulingEngineConfig
# from ..core.problem_model import ExamSchedulingProblem, ProblemComplexity
# from ..core.metrics import SolutionMetrics
# from ..genetic_algorithm.population import Population

# logger = get_logger("hybrid.adaptive_controller")


# class AdaptationTrigger(Enum):
#     """Triggers for parameter adaptation"""

#     CONVERGENCE_PLATEAU = "convergence_plateau"
#     POOR_DIVERSITY = "poor_diversity"
#     TIME_PRESSURE = "time_pressure"
#     INFEASIBILITY_THRESHOLD = "infeasibility_threshold"
#     QUALITY_STAGNATION = "quality_stagration"
#     RESOURCE_CONSTRAINTS = "resource_constraints"


# class AdaptationStrategy(Enum):
#     """Available adaptation strategies"""

#     CONSERVATIVE = "conservative"  # Small adjustments
#     AGGRESSIVE = "aggressive"  # Large adjustments
#     INTELLIGENT = "intelligent"  # Context-aware adjustments
#     EMERGENCY = "emergency"  # Crisis mode adaptations


# @dataclass
# class PerformanceWindow:
#     """Sliding window for tracking optimization performance"""

#     max_size: int = 10
#     objective_values: deque = field(default_factory=lambda: deque(maxlen=10))
#     fitness_scores: deque = field(default_factory=lambda: deque(maxlen=10))
#     diversity_scores: deque = field(default_factory=lambda: deque(maxlen=10))
#     timestamps: deque = field(default_factory=lambda: deque(maxlen=10))

#     def add_measurement(
#         self, objective_value: float, fitness_score: float, diversity_score: float
#     ) -> None:
#         """Add new measurement to the window"""
#         current_time = time.time()
#         self.objective_values.append(objective_value)
#         self.fitness_scores.append(fitness_score)
#         self.diversity_scores.append(diversity_score)
#         self.timestamps.append(current_time)

#     def get_improvement_rate(self) -> float:
#         """Calculate objective improvement rate over the window"""
#         if len(self.objective_values) < 2:
#             return 0.0

#         recent_values = list(self.objective_values)[-5:]  # Last 5 measurements
#         if len(recent_values) < 2:
#             return 0.0

#         # Calculate average improvement per measurement
#         improvements = [
#             recent_values[i - 1] - recent_values[i]
#             for i in range(1, len(recent_values))
#             if recent_values[i - 1] > recent_values[i]  # Only count improvements
#         ]

#         return sum(improvements) / len(improvements) if improvements else 0.0

#     def is_converged(self, threshold: float = 0.001) -> bool:
#         """Check if optimization has converged"""
#         if len(self.objective_values) < self.max_size:
#             return False

#         recent_values = list(self.objective_values)
#         variance = np.var(recent_values) if recent_values else float("inf")
#         return bool(variance < threshold)  # Convert numpy.bool to Python bool


# @dataclass
# class AdaptationEvent:
#     """Record of a parameter adaptation event"""

#     event_id: UUID
#     timestamp: datetime
#     trigger: AdaptationTrigger
#     strategy: AdaptationStrategy
#     parameter_changes: Dict[str, Dict[str, Any]]
#     rationale: str
#     expected_impact: Dict[str, float]
#     actual_impact: Optional[Dict[str, float]] = None


# class AdaptiveController:
#     """
#     Adaptive parameter controller for hybrid optimization.

#     Monitors optimization progress and dynamically adjusts parameters
#     based on problem characteristics, solution quality, and resource constraints.
#     Implements adaptive strategies from the research paper.
#     """

#     def __init__(self, config: SchedulingEngineConfig):
#         self.config = config
#         self.metrics = SolutionMetrics()

#         # Performance tracking
#         self.performance_window = PerformanceWindow()
#         self.adaptation_history: List[AdaptationEvent] = []

#         # Problem analysis cache
#         self.problem_complexity: Optional[ProblemComplexity] = None
#         self.baseline_parameters: Dict[str, Any] = {}
#         self.current_parameters: Dict[str, Any] = {}

#         # Adaptation thresholds and configuration
#         self.adaptation_config = self._initialize_adaptation_config()

#         # Statistics
#         self.adaptation_count = 0
#         self.successful_adaptations = 0

#         logger.info("Adaptive controller initialized")

#     def _initialize_adaptation_config(self) -> Dict[str, Any]:
#         """Initialize adaptive configuration parameters"""
#         return {
#             "convergence_threshold": 0.001,
#             "diversity_threshold": 0.1,
#             "stagnation_generations": 10,
#             "time_pressure_threshold": 0.8,  # 80% of time budget
#             "quality_improvement_threshold": 0.05,
#             # Parameter adjustment ranges
#             "mutation_rate_range": (0.05, 0.3),
#             "crossover_rate_range": (0.6, 0.95),
#             "population_size_range": (50, 500),
#             "cp_sat_time_factor_range": (0.5, 2.0),
#             # Adaptation strategies
#             "conservative_factor": 0.1,
#             "aggressive_factor": 0.3,
#             "intelligent_factor": 0.2,
#             "emergency_factor": 0.5,
#         }

#     async def initialize_for_problem(self, problem: ExamSchedulingProblem) -> None:
#         """Initialize controller for specific problem instance"""
#         logger.info(
#             f"Initializing adaptive controller for problem with {len(problem.exams)} exams"
#         )

#         # Analyze problem complexity
#         self.problem_complexity = await self._analyze_problem_complexity(problem)

#         # Store baseline parameters
#         self.baseline_parameters = {
#             "mutation_rate": self.config.genetic_algorithm.mutation_rate,
#             "crossover_rate": self.config.genetic_algorithm.crossover_rate,
#             "population_size": self.config.genetic_algorithm.population_size,
#             "cp_sat_time_limit": self.config.cp_sat.time_limit_seconds,
#             "num_generations": self.config.genetic_algorithm.num_generations,
#         }

#         # Set initial parameters based on problem complexity
#         self.current_parameters = await self._calculate_initial_parameters(problem)

#         # Clear performance tracking
#         self.performance_window = PerformanceWindow()
#         self.adaptation_history.clear()

#         logger.info(
#             f"Adaptive controller initialized for complexity level: {self.problem_complexity.level}"
#         )

#     async def _analyze_problem_complexity(
#         self, problem: ExamSchedulingProblem
#     ) -> ProblemComplexity:
#         """Analyze problem complexity to guide parameter selection"""
#         try:
#             # Basic size metrics
#             num_exams = len(problem.exams)
#             num_rooms = len(problem.rooms)
#             num_time_slots = len(problem.time_slots)

#             # Calculate constraint density
#             hard_constraints = len(problem.get_hard_constraints())
#             soft_constraints = len(problem.get_soft_constraints())
#             total_constraints = hard_constraints + soft_constraints

#             # Student-course interaction complexity
#             total_registrations = sum(
#                 exam.expected_students for exam in problem.exams.values()
#             )
#             avg_registrations_per_exam = total_registrations / max(num_exams, 1)

#             # Resource contention analysis
#             avg_students_per_exam = sum(
#                 exam.expected_students for exam in problem.exams.values()
#             ) / max(num_exams, 1)

#             total_capacity = sum(room.exam_capacity for room in problem.rooms.values())
#             capacity_utilization = (avg_students_per_exam * num_exams) / max(
#                 total_capacity, 1
#             )

#             # Faculty distribution analysis
#             faculty_distribution = self._analyze_faculty_distribution(problem)

#             # Calculate overall complexity score
#             complexity_score = self._calculate_complexity_score(
#                 num_exams,
#                 num_rooms,
#                 num_time_slots,
#                 total_constraints,
#                 avg_registrations_per_exam,
#                 capacity_utilization,
#                 faculty_distribution,
#             )

#             return ProblemComplexity(
#                 exams=num_exams,
#                 rooms=num_rooms,
#                 time_slots=num_time_slots,
#                 constraints=total_constraints,
#                 registrations=total_registrations,
#                 complexity_score=complexity_score,
#                 level=self._classify_complexity_level(complexity_score),
#                 faculty_balance=faculty_distribution["balance_score"],
#                 resource_contention=capacity_utilization,
#             )

#         except Exception as e:
#             logger.error(f"Error analyzing problem complexity: {e}")
#             # Return default complexity
#             return ProblemComplexity(
#                 exams=len(problem.exams),
#                 rooms=len(problem.rooms),
#                 time_slots=len(problem.time_slots),
#                 constraints=0,
#                 registrations=0,
#                 complexity_score=1.0,
#                 level="medium",
#             )

#     def _analyze_faculty_distribution(
#         self, problem: ExamSchedulingProblem
#     ) -> Dict[str, Any]:
#         """Analyze distribution of exams across faculties"""
#         faculty_exam_counts: Dict[Optional[UUID], int] = defaultdict(int)

#         for exam in problem.exams.values():
#             faculty_id = exam.faculty_id
#             faculty_exam_counts[faculty_id] += 1

#         if not faculty_exam_counts:
#             return {"balance_score": 0.5, "num_faculties": 0, "max_faculty_size": 0}

#         counts = list(faculty_exam_counts.values())
#         mean_count = float(np.mean(counts))
#         std_count = float(np.std(counts))

#         balance_score = 1.0 - (std_count / mean_count) if mean_count > 0 else 0.5

#         return {
#             "balance_score": max(0.0, min(1.0, balance_score)),
#             "num_faculties": len(faculty_exam_counts),
#             "max_faculty_size": int(max(counts)),
#             "min_faculty_size": int(min(counts)),
#             "avg_faculty_size": mean_count,
#         }

#     def _calculate_complexity_score(
#         self,
#         num_exams: int,
#         num_rooms: int,
#         num_time_slots: int,
#         total_constraints: int,
#         avg_registrations: float,
#         capacity_utilization: float,
#         faculty_distribution: Dict[str, Any],
#     ) -> float:
#         """Calculate normalized complexity score (0-1)"""
#         try:
#             # Size complexity (0-0.3)
#             size_complexity = min(0.3, float(num_exams * num_rooms) / 10000.0)

#             # Constraint complexity (0-0.25)
#             constraint_density = total_constraints / max(num_exams, 1)
#             constraint_complexity = min(0.25, float(constraint_density) / 10.0)

#             # Registration complexity (0-0.25)
#             registration_complexity = min(0.25, float(avg_registrations) / 50.0)

#             # Resource complexity (0-0.2)
#             resource_complexity = min(0.2, float(capacity_utilization))

#             # Balance penalty (0-0.1 reduction)
#             balance_penalty = (1.0 - float(faculty_distribution["balance_score"])) * 0.1

#             total_complexity = (
#                 size_complexity
#                 + constraint_complexity
#                 + registration_complexity
#                 + resource_complexity
#                 - balance_penalty
#             )

#             return max(0.0, min(1.0, float(total_complexity)))

#         except Exception as e:
#             logger.warning(f"Error calculating complexity score: {e}")
#             return 0.5

#     def _classify_complexity_level(self, complexity_score: float) -> str:
#         """Classify problem complexity level"""
#         if complexity_score < 0.3:
#             return "low"
#         elif complexity_score < 0.6:
#             return "medium"
#         elif complexity_score < 0.8:
#             return "high"
#         else:
#             return "extreme"

#     async def _calculate_initial_parameters(
#         self, problem: ExamSchedulingProblem
#     ) -> Dict[str, Any]:
#         """Calculate initial parameters based on problem analysis"""
#         if not self.problem_complexity:
#             return self.baseline_parameters.copy()

#         # Start with baseline parameters
#         params = self.baseline_parameters.copy()

#         # Adjust based on problem complexity
#         complexity_level = self.problem_complexity.level

#         if complexity_level == "low":
#             # Simple problems: favor exploitation
#             params["mutation_rate"] *= 0.8
#             params["crossover_rate"] *= 1.1
#             params["population_size"] = max(50, int(params["population_size"] * 0.7))

#         elif complexity_level == "high":
#             # Complex problems: favor exploration
#             params["mutation_rate"] *= 1.3
#             params["crossover_rate"] *= 0.9
#             params["population_size"] = min(500, int(params["population_size"] * 1.5))
#             params["cp_sat_time_limit"] = min(
#                 600, int(params["cp_sat_time_limit"] * 1.5)
#             )

#         elif complexity_level == "extreme":
#             # Extreme problems: aggressive exploration
#             params["mutation_rate"] *= 1.5
#             params["population_size"] = min(1000, int(params["population_size"] * 2.0))
#             params["cp_sat_time_limit"] = min(
#                 900, int(params["cp_sat_time_limit"] * 2.0)
#             )
#             params["num_generations"] = min(200, int(params["num_generations"] * 1.5))

#         # Adjust for faculty balance
#         if self.problem_complexity.faculty_balance < 0.5:
#             # Poor faculty balance - increase diversity mechanisms
#             params["mutation_rate"] *= 1.2

#         # Adjust for resource contention
#         if self.problem_complexity.resource_contention > 0.8:
#             # High resource contention - focus on feasibility
#             params["cp_sat_time_limit"] = min(
#                 1200, int(params["cp_sat_time_limit"] * 2.0)
#             )

#         logger.info(f"Initial parameters calculated for {complexity_level} complexity")
#         return params

#     def update_performance_metrics(
#         self,
#         generation: int,
#         best_objective: float,
#         average_fitness: float,
#         population_diversity: float,
#         convergence_rate: float,
#     ) -> None:
#         """Update performance tracking with current generation metrics"""
#         self.performance_window.add_measurement(
#             best_objective, average_fitness, population_diversity
#         )

#         # Store additional metrics for analysis
#         if not hasattr(self, "generation_metrics"):
#             self.generation_metrics: Dict[str, List[Any]] = defaultdict(list)

#         self.generation_metrics["generation"].append(generation)
#         self.generation_metrics["convergence_rate"].append(float(convergence_rate))

#         logger.debug(f"Performance updated for generation {generation}")

#     async def should_adapt_parameters(
#         self, current_generation: int
#     ) -> Tuple[bool, List[AdaptationTrigger]]:
#         """Determine if parameters should be adapted and why"""
#         triggers = []

#         # Check convergence plateau
#         if self.performance_window.is_converged(threshold=0.001):
#             triggers.append(AdaptationTrigger.CONVERGENCE_PLATEAU)

#         # Check poor diversity
#         if (
#             len(self.performance_window.diversity_scores) > 0
#             and self.performance_window.diversity_scores[-1] < 0.1
#         ):
#             triggers.append(AdaptationTrigger.POOR_DIVERSITY)

#         # Check quality stagnation
#         improvement_rate = self.performance_window.get_improvement_rate()
#         if improvement_rate < 0.01 and current_generation > 10:
#             triggers.append(AdaptationTrigger.QUALITY_STAGNATION)

#         # Check time pressure (if we have time budget info)
#         if hasattr(self, "time_budget") and hasattr(self, "start_time"):
#             elapsed_ratio = (time.time() - self.start_time) / self.time_budget
#             if elapsed_ratio > self.adaptation_config["time_pressure_threshold"]:
#                 triggers.append(AdaptationTrigger.TIME_PRESSURE)

#         # Check resource constraints
#         if (
#             self.problem_complexity
#             and self.problem_complexity.resource_contention > 0.9
#         ):
#             triggers.append(AdaptationTrigger.RESOURCE_CONSTRAINTS)

#         should_adapt = len(triggers) > 0

#         if should_adapt:
#             logger.info(f"Adaptation triggered by: {[t.value for t in triggers]}")

#         return should_adapt, triggers

#     async def adapt_parameters(
#         self,
#         triggers: List[AdaptationTrigger],
#         current_generation: int,
#         population: Population,
#         time_budget_remaining: float,
#     ) -> Dict[str, Any]:
#         """
#         Adapt optimization parameters based on current state and triggers.

#         Returns:
#             Updated parameter set for the optimization algorithm
#         """
#         logger.info(f"Adapting parameters for triggers: {[t.value for t in triggers]}")

#         # Determine adaptation strategy
#         strategy = self._select_adaptation_strategy(
#             triggers, current_generation, time_budget_remaining
#         )

#         # Calculate parameter adjustments
#         parameter_changes = await self._calculate_parameter_adjustments(
#             triggers, strategy, population, time_budget_remaining
#         )

#         # Apply changes to current parameters
#         new_parameters = self.current_parameters.copy()
#         rationale_parts = []

#         for param_name, change_info in parameter_changes.items():
#             old_value = new_parameters.get(param_name)
#             new_value = change_info["new_value"]
#             new_parameters[param_name] = new_value

#             rationale_parts.append(
#                 f"{param_name}: {old_value} → {new_value} ({change_info['reason']})"
#             )

#         # Create adaptation event record
#         adaptation_event = AdaptationEvent(
#             event_id=uuid4(),
#             timestamp=datetime.now(),
#             trigger=triggers[0] if triggers else AdaptationTrigger.QUALITY_STAGNATION,
#             strategy=strategy,
#             parameter_changes=parameter_changes,
#             rationale="; ".join(rationale_parts),
#             expected_impact=self._estimate_adaptation_impact(parameter_changes),
#         )

#         self.adaptation_history.append(adaptation_event)
#         self.adaptation_count += 1
#         self.current_parameters = new_parameters

#         logger.info(f"Parameters adapted using {strategy.value} strategy")
#         logger.debug(f"Adaptation rationale: {adaptation_event.rationale}")

#         return new_parameters

#     def _select_adaptation_strategy(
#         self,
#         triggers: List[AdaptationTrigger],
#         current_generation: int,
#         time_budget_remaining: float,
#     ) -> AdaptationStrategy:
#         """Select appropriate adaptation strategy based on context"""

#         # Emergency strategy for critical situations
#         if AdaptationTrigger.TIME_PRESSURE in triggers and time_budget_remaining < 0.2:
#             return AdaptationStrategy.EMERGENCY

#         # Aggressive strategy for early generations or severe stagnation
#         if (
#             current_generation < 20
#             or AdaptationTrigger.POOR_DIVERSITY in triggers
#             or len(triggers) >= 3
#         ):
#             return AdaptationStrategy.AGGRESSIVE

#         # Conservative strategy for fine-tuning
#         if current_generation > 80 or AdaptationTrigger.CONVERGENCE_PLATEAU in triggers:
#             return AdaptationStrategy.CONSERVATIVE

#         # Default to intelligent strategy
#         return AdaptationStrategy.INTELLIGENT

#     async def _calculate_parameter_adjustments(
#         self,
#         triggers: List[AdaptationTrigger],
#         strategy: AdaptationStrategy,
#         population: Population,
#         time_budget_remaining: float,
#     ) -> Dict[str, Dict[str, Any]]:
#         """Calculate specific parameter adjustments based on triggers and strategy"""
#         adjustments = {}

#         # Get strategy adjustment factor
#         strategy_factors = {
#             AdaptationStrategy.CONSERVATIVE: self.adaptation_config[
#                 "conservative_factor"
#             ],
#             AdaptationStrategy.AGGRESSIVE: self.adaptation_config["aggressive_factor"],
#             AdaptationStrategy.INTELLIGENT: self.adaptation_config[
#                 "intelligent_factor"
#             ],
#             AdaptationStrategy.EMERGENCY: self.adaptation_config["emergency_factor"],
#         }

#         adjustment_factor = strategy_factors[strategy]

#         # Mutation rate adjustments
#         if AdaptationTrigger.CONVERGENCE_PLATEAU in triggers:
#             # Increase mutation for more exploration
#             current_mutation = self.current_parameters.get("mutation_rate", 0.1)
#             new_mutation = min(
#                 self.adaptation_config["mutation_rate_range"][1],
#                 current_mutation * (1 + adjustment_factor),
#             )
#             adjustments["mutation_rate"] = {
#                 "new_value": new_mutation,
#                 "reason": "increase exploration due to convergence",
#             }

#         elif AdaptationTrigger.POOR_DIVERSITY in triggers:
#             # Significantly increase mutation for diversity
#             current_mutation = self.current_parameters.get("mutation_rate", 0.1)
#             new_mutation = min(
#                 self.adaptation_config["mutation_rate_range"][1],
#                 current_mutation * (1 + 2 * adjustment_factor),
#             )
#             adjustments["mutation_rate"] = {
#                 "new_value": new_mutation,
#                 "reason": "boost diversity",
#             }

#         # Crossover rate adjustments
#         if AdaptationTrigger.QUALITY_STAGNATION in triggers:
#             # Adjust crossover rate inversely to mutation
#             current_crossover = self.current_parameters.get("crossover_rate", 0.8)

#             if "mutation_rate" in adjustments:
#                 # If mutation increased, slightly decrease crossover
#                 new_crossover = max(
#                     self.adaptation_config["crossover_rate_range"][0],
#                     current_crossover * (1 - adjustment_factor * 0.5),
#                 )
#             else:
#                 # Increase crossover for better solution mixing
#                 new_crossover = min(
#                     self.adaptation_config["crossover_rate_range"][1],
#                     current_crossover * (1 + adjustment_factor * 0.5),
#                 )

#             adjustments["crossover_rate"] = {
#                 "new_value": new_crossover,
#                 "reason": "balance exploration/exploitation",
#             }

#         # Population size adjustments (for next run)
#         if AdaptationTrigger.RESOURCE_CONSTRAINTS in triggers:
#             # Reduce population size under resource pressure
#             current_pop_size = self.current_parameters.get("population_size", 200)
#             new_pop_size = max(
#                 self.adaptation_config["population_size_range"][0],
#                 int(current_pop_size * (1 - adjustment_factor)),
#             )
#             adjustments["population_size"] = {
#                 "new_value": new_pop_size,
#                 "reason": "reduce resource usage",
#             }

#         # Time budget adjustments
#         if AdaptationTrigger.TIME_PRESSURE in triggers:
#             # Reduce CP-SAT time limit to leave more time for GA
#             current_time_limit = self.current_parameters.get("cp_sat_time_limit", 300)
#             new_time_limit = max(
#                 60,  # Minimum time limit
#                 int(current_time_limit * (1 - adjustment_factor)),
#             )
#             adjustments["cp_sat_time_limit"] = {
#                 "new_value": new_time_limit,
#                 "reason": "prioritize GA phase under time pressure",
#             }

#         return adjustments

#     def _estimate_adaptation_impact(
#         self, parameter_changes: Dict[str, Dict[str, Any]]
#     ) -> Dict[str, float]:
#         """Estimate expected impact of parameter changes"""
#         impact = {
#             "exploration_boost": 0.0,
#             "convergence_speed": 0.0,
#             "solution_quality": 0.0,
#             "resource_efficiency": 0.0,
#         }

#         # Analyze each parameter change
#         for param_name, change_info in parameter_changes.items():
#             if param_name == "mutation_rate":
#                 # Higher mutation = more exploration
#                 impact["exploration_boost"] += 0.3
#                 impact["convergence_speed"] -= 0.1  # May slow convergence

#             elif param_name == "crossover_rate":
#                 # Higher crossover = better solution mixing
#                 impact["solution_quality"] += 0.2

#             elif param_name == "population_size":
#                 # Larger population = better search, more resources
#                 if (
#                     change_info["new_value"]
#                     > self.baseline_parameters["population_size"]
#                 ):
#                     impact["solution_quality"] += 0.3
#                     impact["resource_efficiency"] -= 0.3
#                 else:
#                     impact["resource_efficiency"] += 0.2
#                     impact["solution_quality"] -= 0.1

#             elif param_name == "cp_sat_time_limit":
#                 # More CP-SAT time = better initial solutions
#                 if (
#                     change_info["new_value"]
#                     > self.baseline_parameters["cp_sat_time_limit"]
#                 ):
#                     impact["solution_quality"] += 0.1
#                     impact["resource_efficiency"] -= 0.1

#         return impact

#     def record_adaptation_outcome(
#         self, adaptation_event_id: UUID, actual_impact: Dict[str, float]
#     ) -> None:
#         """Record the actual impact of an adaptation for learning"""
#         for event in self.adaptation_history:
#             if event.event_id == adaptation_event_id:
#                 event.actual_impact = actual_impact

#                 # Determine if adaptation was successful
#                 expected = event.expected_impact
#                 success_threshold = 0.7  # 70% of expected impact

#                 success_score = 0.0
#                 for metric, expected_value in expected.items():
#                     actual_value = actual_impact.get(metric, 0.0)
#                     if expected_value != 0:
#                         success_score += min(actual_value / expected_value, 1.0)

#                 success_score /= len(expected)

#                 if success_score >= success_threshold:
#                     self.successful_adaptations += 1
#                     logger.info(f"Successful adaptation: {event.rationale}")
#                 else:
#                     logger.warning(
#                         f"Adaptation underperformed: expected {expected}, got {actual_impact}"
#                     )

#                 break

#     def get_adaptive_cp_sat_parameters(self) -> Dict[str, Any]:
#         """Get adapted parameters for CP-SAT phase"""
#         return {
#             "time_limit_seconds": self.current_parameters.get("cp_sat_time_limit"),
#             "num_search_workers": self._get_optimal_worker_count(),
#             "emphasis": self._get_solver_emphasis(),
#             "search_branching": self._get_search_branching_strategy(),
#         }

#     def get_adaptive_ga_parameters(self) -> Dict[str, Any]:
#         """Get adapted parameters for GA phase"""
#         return {
#             "population_size": self.current_parameters.get("population_size"),
#             "mutation_rate": self.current_parameters.get("mutation_rate"),
#             "crossover_rate": self.current_parameters.get("crossover_rate"),
#             "max_generations": self.current_parameters.get("num_generations"),
#         }

#     def _get_optimal_worker_count(self) -> int:
#         """Determine optimal number of workers for CP-SAT based on problem complexity"""
#         if not self.problem_complexity:
#             return 4

#         if self.problem_complexity.level == "low":
#             return 2
#         elif self.problem_complexity.level == "medium":
#             return 4
#         elif self.problem_complexity.level == "high":
#             return 6
#         else:  # extreme
#             return 8

#     def _get_solver_emphasis(self) -> str:
#         """Determine CP-SAT solver emphasis based on problem characteristics"""
#         if not self.problem_complexity:
#             return "balanced"

#         if self.problem_complexity.resource_contention > 0.8:
#             return "feasibility"
#         elif self.problem_complexity.level in ["high", "extreme"]:
#             return "optimality"
#         else:
#             return "balanced"

#     def _get_search_branching_strategy(self) -> str:
#         """Determine CP-SAT search branching strategy"""
#         if not self.problem_complexity:
#             return "automatic"

#         if self.problem_complexity.faculty_balance < 0.5:
#             return "portfolio"  # Multiple strategies in parallel
#         else:
#             return "automatic"

#     def get_adaptation_report(self) -> Dict[str, Any]:
#         """Generate comprehensive adaptation report"""
#         return {
#             "controller_id": str(uuid4()),
#             "problem_complexity": (
#                 {
#                     "level": self.problem_complexity.level,
#                     "score": self.problem_complexity.complexity_score,
#                     "exams": self.problem_complexity.exams,
#                     "faculty_balance": self.problem_complexity.faculty_balance,
#                     "resource_contention": self.problem_complexity.resource_contention,
#                 }
#                 if self.problem_complexity
#                 else None
#             ),
#             "adaptation_statistics": {
#                 "total_adaptations": self.adaptation_count,
#                 "successful_adaptations": self.successful_adaptations,
#                 "success_rate": (
#                     self.successful_adaptations / max(self.adaptation_count, 1)
#                 ),
#             },
#             "current_parameters": self.current_parameters.copy(),
#             "baseline_parameters": self.baseline_parameters.copy(),
#             "parameter_drift": {
#                 param: (
#                     abs(
#                         self.current_parameters.get(param, 0)
#                         - self.baseline_parameters.get(param, 0)
#                     )
#                 )
#                 for param in self.baseline_parameters.keys()
#             },
#             "adaptation_history": [
#                 {
#                     "event_id": str(event.event_id),
#                     "timestamp": event.timestamp.isoformat(),
#                     "trigger": event.trigger.value,
#                     "strategy": event.strategy.value,
#                     "rationale": event.rationale,
#                     "impact_achieved": (event.actual_impact is not None),
#                 }
#                 for event in self.adaptation_history
#             ],
#             "performance_window": {
#                 "window_size": len(self.performance_window.objective_values),
#                 "current_improvement_rate": self.performance_window.get_improvement_rate(),
#                 "is_converged": self.performance_window.is_converged(),
#                 "latest_diversity": (
#                     list(self.performance_window.diversity_scores)[-1]
#                     if self.performance_window.diversity_scores
#                     else None
#                 ),
#             },
#         }

#     def reset_for_new_problem(self) -> None:
#         """Reset controller state for new problem instance"""
#         logger.info("Resetting adaptive controller for new problem")

#         self.problem_complexity = None
#         self.performance_window = PerformanceWindow()
#         self.adaptation_history.clear()
#         self.adaptation_count = 0
#         self.successful_adaptations = 0
#         self.current_parameters = self.baseline_parameters.copy()

#         if hasattr(self, "generation_metrics"):
#             self.generation_metrics.clear()

#     def set_time_budget(self, start_time: float, total_budget_seconds: float) -> None:
#         """Set time budget for adaptive decisions"""
#         self.start_time = start_time
#         self.time_budget = total_budget_seconds

#     def get_faculty_specific_parameters(self, faculty_id: UUID) -> Dict[str, Any]:
#         """Get parameters adapted for specific faculty characteristics"""
#         # This would be enhanced with faculty-specific analysis
#         base_params = self.current_parameters.copy()

#         # Placeholder for faculty-specific adaptations
#         # Real implementation would analyze faculty-specific complexity

#         return base_params

#     def should_enable_parallel_optimization(self) -> bool:
#         """Determine if parallel optimization should be enabled"""
#         if not self.problem_complexity:
#             return False

#         # Enable for complex problems with good faculty balance
#         return (
#             self.problem_complexity.level in ["high", "extreme"]
#             and self.problem_complexity.faculty_balance > 0.6
#             and self.problem_complexity.exams > 100
#         )

#     def get_partition_specific_config(
#         self, partition_info: Dict[str, Any]
#     ) -> Dict[str, Any]:
#         """Get configuration adapted for specific partition characteristics"""
#         base_config = self.current_parameters.copy()

#         # Adjust based on partition size
#         partition_size = partition_info.get("exam_count", 0)
#         if partition_size < 20:
#             # Small partition - reduce population size
#             base_config["population_size"] = max(
#                 20, base_config.get("population_size", 100) // 2
#             )
#             base_config["num_generations"] = max(
#                 10, base_config.get("num_generations", 50) // 2
#             )
#         elif partition_size > 200:
#             # Large partition - increase resources
#             base_config["population_size"] = min(
#                 500, base_config.get("population_size", 100) * 2
#             )
#             base_config["cp_sat_time_limit"] = min(
#                 1800, base_config.get("cp_sat_time_limit", 300) * 2
#             )

#         # Adjust based on partition dependencies
#         dependency_count = partition_info.get("dependency_count", 0)
#         if dependency_count > 5:
#             # High dependencies - favor feasibility
#             base_config["cp_sat_time_limit"] = min(
#                 900, int(base_config.get("cp_sat_time_limit", 300) * 1.5)
#             )

#         return base_config


# # Factory function
# def create_adaptive_controller(
#     config: Optional[SchedulingEngineConfig] = None,
# ) -> AdaptiveController:
#     """Create and configure an adaptive controller instance"""
#     return AdaptiveController(config or SchedulingEngineConfig())
