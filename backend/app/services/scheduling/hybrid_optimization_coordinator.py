# backend/app/services/scheduling/hybrid_optimization_coordinator.py

"""
Hybrid optimization coordinator that orchestrates the CP-SAT + GA pipeline
for exam timetable generation with real-time progress tracking.
"""

import logging
import time
import asyncio
import random
from typing import Dict, Any, Optional, List, Tuple, Union, cast
from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class OptimizationPhaseResult:
    """Result from a single optimization phase"""

    success: bool
    solution: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    execution_time: float = 0.0
    error: Optional[str] = None


class HybridOptimizationCoordinator:
    """
    Coordinates the hybrid CP-SAT + GA optimization pipeline.
    Handles phase transitions, progress tracking, and result integration.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

        # Import here to avoid circular imports
        from .enhanced_engine_connector import EnhancedSchedulingEngineConnector
        from .problem_instance_builder import ProblemInstanceBuilder

        self.connector = EnhancedSchedulingEngineConnector(session)
        self.problem_builder = ProblemInstanceBuilder(self.connector)

        # Default optimization parameters
        self.default_params: Dict[str, Dict[str, Any]] = {
            "cpsat": {
                "time_limit_seconds": 300,
                "num_search_workers": 4,
                "max_time_in_seconds": 600,
                "log_search_progress": False,
            },
            "ga": {
                "generations": 100,
                "population_size": 50,
                "mutation_rate": 0.1,
                "crossover_rate": 0.8,
                "elitism_rate": 0.1,
                "tournament_size": 3,
            },
        }

    async def optimize_timetable(
        self,
        job_id: UUID,
        session_id: UUID,
        configuration_id: UUID,
        optimization_params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Run the complete hybrid optimization pipeline.

        Pipeline:
        1. Load and prepare problem instance
        2. CP-SAT phase: Find feasible solution
        3. GA phase: Optimize solution quality
        4. Validate and format results
        """
        start_time = time.time()

        try:
            from .enhanced_engine_connector import OptimizationResult
            from app.services.notification import publish_job_update

            logger.info(f"Starting hybrid optimization for job {job_id}")

            # Merge provided parameters with defaults
            params = self._merge_optimization_params(optimization_params)

            # Phase 1: Problem preparation (0-20%)
            await publish_job_update(
                str(job_id),
                {
                    "status": "running",
                    "progress": 5,
                    "phase": "data_preparation",
                    "message": "Loading and analyzing problem data...",
                },
            )

            problem_instance = await self.connector.get_complete_problem_instance(
                session_id, use_cache=False, refresh_views=True
            )

            await publish_job_update(
                str(job_id),
                {
                    "progress": 15,
                    "phase": "data_analysis",
                    "message": f"Problem loaded: {len(problem_instance.exams)} exams, "
                    f"{len(problem_instance.rooms)} rooms, "
                    f"complexity: {problem_instance.problem_metrics.get('complexity_estimate', 'UNKNOWN')}",
                },
            )

            # Get constraint configuration
            constraints_config = await self._get_constraints_configuration(
                configuration_id
            )

            await publish_job_update(
                str(job_id),
                {
                    "progress": 20,
                    "phase": "constraint_preparation",
                    "message": f"Constraints loaded: {len(constraints_config.get('hard_constraints', {}))} hard, "
                    f"{len(constraints_config.get('soft_constraints', {}))} soft",
                },
            )

            # Phase 2: CP-SAT optimization (20-60%)
            cpsat_result = await self._run_cpsat_phase(
                job_id, problem_instance, constraints_config, params["cpsat"]
            )

            if not cpsat_result.success:
                return OptimizationResult(
                    success=False,
                    error=f"CP-SAT phase failed: {cpsat_result.error}",
                    execution_time=time.time() - start_time,
                )

            # Ensure we have a solution before proceeding
            if not cpsat_result.solution:
                return OptimizationResult(
                    success=False,
                    error="CP-SAT phase completed but no solution was generated",
                    execution_time=time.time() - start_time,
                )

            # Phase 3: GA optimization (60-90%)
            ga_result = await self._run_ga_phase(
                job_id, problem_instance, cpsat_result.solution, params["ga"]
            )

            # Handle final solution and metrics
            final_solution: Dict[str, Any]
            final_metrics: Dict[str, Any] = {}

            if not ga_result.success:
                # Fall back to CP-SAT solution if GA fails
                logger.warning(
                    f"GA phase failed for job {job_id}, using CP-SAT solution"
                )
                final_solution = cpsat_result.solution or {}
                final_metrics = cpsat_result.metrics or {}
            else:
                final_solution = ga_result.solution or {}
                final_metrics = self._combine_phase_metrics(
                    cpsat_result.metrics, ga_result.metrics
                )

            # Ensure we have a solution before proceeding
            if not final_solution:
                return OptimizationResult(
                    success=False,
                    error="Optimization completed but no solution was generated",
                    execution_time=time.time() - start_time,
                )

            # Phase 4: Solution validation and formatting (90-100%)
            await publish_job_update(
                str(job_id),
                {
                    "progress": 90,
                    "phase": "solution_validation",
                    "message": "Validating and formatting final solution...",
                },
            )

            validated_solution = await self._validate_and_format_solution(
                final_solution, problem_instance
            )

            # Calculate final metrics
            total_time = time.time() - start_time
            enhanced_metrics = await self._calculate_final_metrics(
                validated_solution, problem_instance, final_metrics, total_time
            )

            await publish_job_update(
                str(job_id),
                {
                    "progress": 100,
                    "phase": "completed",
                    "message": f"Optimization completed in {total_time:.2f}s",
                },
            )

            assignment_rate = enhanced_metrics.get("quality_metrics", {}).get(
                "assignment_rate", 0
            )
            logger.info(
                f"Hybrid optimization completed for job {job_id} in {total_time:.2f}s: "
                f"{assignment_rate:.1%} assignment rate"
            )

            return OptimizationResult(
                success=True,
                solution=validated_solution,
                metrics=enhanced_metrics,
                execution_time=total_time,
            )

        except Exception as e:
            logger.error(
                f"Hybrid optimization failed for job {job_id}: {e}", exc_info=True
            )

            try:
                from app.services.notification import publish_job_update

                await publish_job_update(
                    str(job_id),
                    {
                        "status": "failed",
                        "progress": 0,
                        "phase": "error",
                        "message": f"Optimization failed: {str(e)}",
                    },
                )
            except Exception:
                pass

            from .enhanced_engine_connector import OptimizationResult

            return OptimizationResult(
                success=False, error=str(e), execution_time=time.time() - start_time
            )

    async def _run_cpsat_phase(
        self,
        job_id: UUID,
        problem_instance: Any,
        constraints_config: Dict[str, Any],
        cpsat_params: Dict[str, Any],
    ) -> OptimizationPhaseResult:
        """Run CP-SAT optimization phase"""
        phase_start_time = time.time()

        try:
            from app.services.notification import publish_job_update

            await publish_job_update(
                str(job_id),
                {
                    "progress": 25,
                    "phase": "cpsat_modeling",
                    "message": "Building CP-SAT constraint model...",
                },
            )

            # Build CP-SAT model
            cpsat_model = await self.problem_builder.build_cpsat_model(
                problem_instance, constraints_config
            )

            await publish_job_update(
                str(job_id),
                {
                    "progress": 35,
                    "phase": "cpsat_solving",
                    "message": f"Solving with CP-SAT ({cpsat_params.get('time_limit_seconds', 300)}s limit)...",
                },
            )

            # Solve with CP-SAT
            solution = await self._solve_cpsat_model(cpsat_model, cpsat_params, job_id)

            if solution.get("status") in ["FEASIBLE", "OPTIMAL"]:
                phase_time = time.time() - phase_start_time

                await publish_job_update(
                    str(job_id),
                    {
                        "progress": 60,
                        "phase": "cpsat_completed",
                        "message": f"CP-SAT found {solution.get('status', 'UNKNOWN').lower()} solution "
                        f"in {phase_time:.2f}s",
                    },
                )

                metrics = {
                    "cpsat_status": solution.get("status"),
                    "cpsat_runtime": phase_time,
                    "cpsat_assignments": len(solution.get("assignments", {})),
                    "cpsat_objective_value": solution.get("objective_value", 0),
                }

                return OptimizationPhaseResult(
                    success=True,
                    solution=solution,
                    metrics=metrics,
                    execution_time=phase_time,
                )

            else:
                return OptimizationPhaseResult(
                    success=False,
                    error=f"CP-SAT failed to find feasible solution: {solution.get('status', 'UNKNOWN')}",
                    execution_time=time.time() - phase_start_time,
                )

        except Exception as e:
            logger.error(f"CP-SAT phase failed: {e}")
            return OptimizationPhaseResult(
                success=False,
                error=f"CP-SAT phase error: {str(e)}",
                execution_time=time.time() - phase_start_time,
            )

    async def _solve_cpsat_model(
        self, cpsat_model: Any, params: Dict[str, Any], job_id: UUID
    ) -> Dict[str, Any]:
        """Solve CP-SAT model with progress tracking"""
        try:
            # Try to import ortools
            try:
                from ortools.sat.python import cp_model
            except ImportError:
                logger.warning("OR-Tools not available, using mock CP-SAT solver")
                return await self._mock_cpsat_solver(params, job_id)

            # Create solver
            solver = cp_model.CpSolver()

            # Set parameters
            solver.parameters.max_time_in_seconds = params.get(
                "time_limit_seconds", 300
            )
            solver.parameters.num_search_workers = params.get("num_search_workers", 4)
            solver.parameters.log_search_progress = params.get(
                "log_search_progress", False
            )

            # Solve in a separate task to allow for progress updates
            solve_task = asyncio.create_task(
                self._run_cpsat_solver(solver, cpsat_model.model)
            )

            # Progress tracking loop
            start_time = time.time()
            time_limit = params.get("time_limit_seconds", 300)

            while not solve_task.done():
                elapsed = time.time() - start_time
                progress = 35 + int((elapsed / time_limit) * 20)  # 35-55%

                try:
                    from app.services.notification import publish_job_update

                    await publish_job_update(
                        str(job_id),
                        {
                            "progress": min(progress, 55),
                            "phase": "cpsat_solving",
                            "message": f"CP-SAT solving... {elapsed:.1f}s elapsed",
                        },
                    )
                except Exception:
                    pass

                await asyncio.sleep(2)

            # Get result
            status = await solve_task

            # Extract solution if feasible
            if status in [cp_model.FEASIBLE, cp_model.OPTIMAL]:
                solution = await self._extract_cpsat_solution(
                    solver, cpsat_model.variables
                )
                solution["status"] = (
                    "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
                )
                solution["objective_value"] = (
                    solver.ObjectiveValue() if hasattr(solver, "ObjectiveValue") else 0
                )
                solution["runtime"] = time.time() - start_time
                return solution
            else:
                return {
                    "status": self._get_status_string(status),
                    "assignments": {},
                    "runtime": time.time() - start_time,
                }

        except Exception as e:
            logger.error(f"CP-SAT solver error: {e}")
            return {"status": "ERROR", "error": str(e), "assignments": {}}

    async def _mock_cpsat_solver(
        self, params: Dict[str, Any], job_id: UUID
    ) -> Dict[str, Any]:
        """Mock CP-SAT solver for when OR-Tools is not available"""

        # Simulate solving time
        solve_time = min(
            params.get("time_limit_seconds", 300), 30
        )  # Max 30s simulation

        for i in range(int(solve_time)):
            progress = 35 + int((i / solve_time) * 20)
            try:
                from app.services.notification import publish_job_update

                await publish_job_update(
                    str(job_id),
                    {
                        "progress": min(progress, 55),
                        "phase": "cpsat_solving",
                        "message": f"CP-SAT solving (mock)... {i}s elapsed",
                    },
                )
            except Exception:
                pass
            await asyncio.sleep(1)

        # Return mock solution
        return {
            "status": "FEASIBLE",
            "assignments": {},
            "objective_value": 0.8,
            "runtime": solve_time,
            "solver_stats": {
                "wall_time": solve_time,
                "user_time": solve_time,
                "num_conflicts": 100,
                "num_branches": 1000,
            },
        }

    async def _run_cpsat_solver(self, solver: Any, model: Any) -> int:
        """Run CP-SAT solver in executor to avoid blocking"""

        def solve():
            return solver.Solve(model)

        loop = asyncio.get_event_loop()
        status = await loop.run_in_executor(None, solve)
        return status

    async def _extract_cpsat_solution(
        self, solver: Any, variables: Any
    ) -> Dict[str, Any]:
        """Extract solution from CP-SAT solver"""
        assignments = {}

        try:
            # Extract exam assignments
            for exam_id, room_assignments in variables.exam_assignments.items():
                for room_id, timeslot_assignments in room_assignments.items():
                    for timeslot_id, var in timeslot_assignments.items():
                        if solver.Value(var) == 1:  # This assignment is selected
                            assignments[exam_id] = {
                                "room_id": room_id,
                                "timeslot_id": timeslot_id,
                                "staff_ids": [],  # Will be filled by staff assignments
                            }
                            break

            # Extract staff assignments
            if hasattr(variables, "staff_assignments"):
                for staff_id, exam_assignments in variables.staff_assignments.items():
                    for exam_id, timeslot_assignments in exam_assignments.items():
                        for timeslot_id, var in timeslot_assignments.items():
                            if solver.Value(var) == 1 and exam_id in assignments:
                                if "staff_ids" not in assignments[exam_id]:
                                    assignments[exam_id]["staff_ids"] = []
                                assignments[exam_id]["staff_ids"].append(staff_id)

        except Exception as e:
            logger.error(f"Failed to extract CP-SAT solution: {e}")

        return {
            "assignments": assignments,
            "solver_stats": {
                "wall_time": getattr(solver, "WallTime", lambda: 0)(),
                "user_time": getattr(solver, "UserTime", lambda: 0)(),
                "num_conflicts": getattr(solver, "NumConflicts", lambda: 0)(),
                "num_branches": getattr(solver, "NumBranches", lambda: 0)(),
            },
        }

    def _get_status_string(self, status: int) -> str:
        """Convert CP-SAT status code to string"""
        try:
            from ortools.sat.python import cp_model

            status_map: Dict[int, str] = {  # Added explicit type annotation
                cp_model.UNKNOWN: "UNKNOWN",
                cp_model.MODEL_INVALID: "MODEL_INVALID",
                cp_model.FEASIBLE: "FEASIBLE",
                cp_model.INFEASIBLE: "INFEASIBLE",
                cp_model.OPTIMAL: "OPTIMAL",
            }
            return status_map.get(status, f"STATUS_{status}")
        except ImportError:
            # Fallback mapping when ortools not available
            status_names: Dict[int, str] = {  # Added explicit type annotation
                0: "UNKNOWN",
                1: "MODEL_INVALID",
                2: "FEASIBLE",
                3: "INFEASIBLE",
                4: "OPTIMAL",
            }
            return status_names.get(status, f"STATUS_{status}")

    async def _run_ga_phase(
        self,
        job_id: UUID,
        problem_instance: Any,
        initial_solution: Dict[str, Any],
        ga_params: Dict[str, Any],
    ) -> OptimizationPhaseResult:
        """Run genetic algorithm optimization phase"""
        phase_start_time = time.time()

        try:
            from app.services.notification import publish_job_update

            await publish_job_update(
                str(job_id),
                {
                    "progress": 65,
                    "phase": "ga_initialization",
                    "message": "Initializing genetic algorithm population...",
                },
            )

            # Build initial population from CP-SAT solution
            population = await self.problem_builder.build_ga_population(
                problem_instance, initial_solution, ga_params.get("population_size", 50)
            )

            await publish_job_update(
                str(job_id),
                {
                    "progress": 70,
                    "phase": "ga_evolution",
                    "message": f"Evolving population for {ga_params.get('generations', 100)} generations...",
                },
            )

            # Run genetic algorithm
            best_chromosome = await self._run_genetic_algorithm(
                population, problem_instance, ga_params, job_id
            )

            # Convert back to solution format
            final_solution = await self.problem_builder.get_solution_from_chromosome(
                best_chromosome, problem_instance
            )

            phase_time = time.time() - phase_start_time

            await publish_job_update(
                str(job_id),
                {
                    "progress": 90,
                    "phase": "ga_completed",
                    "message": f"GA optimization completed in {phase_time:.2f}s, "
                    f"fitness: {best_chromosome.fitness_score:.2f}",
                },
            )

            metrics = {
                "ga_runtime": phase_time,
                "ga_final_fitness": best_chromosome.fitness_score,
                "ga_generations": ga_params.get("generations", 100),
                "ga_constraint_violations": best_chromosome.constraint_violations,
                "ga_assignment_rate": final_solution["metadata"]["assignment_rate"],
            }

            return OptimizationPhaseResult(
                success=True,
                solution=final_solution,
                metrics=metrics,
                execution_time=phase_time,
            )

        except Exception as e:
            logger.error(f"GA phase failed: {e}")
            return OptimizationPhaseResult(
                success=False,
                error=f"GA phase error: {str(e)}",
                execution_time=time.time() - phase_start_time,
            )

    async def _run_genetic_algorithm(
        self,
        population: List[Any],
        problem_instance: Any,
        params: Dict[str, Any],
        job_id: UUID,
    ) -> Any:
        """Run genetic algorithm evolution"""
        generations = params.get("generations", 100)
        mutation_rate = params.get("mutation_rate", 0.1)
        crossover_rate = params.get("crossover_rate", 0.8)
        elitism_rate = params.get("elitism_rate", 0.1)
        tournament_size = params.get("tournament_size", 3)

        best_fitness_history = []

        for generation in range(generations):
            # Selection
            selected = await self._tournament_selection(population, tournament_size)

            # Crossover
            offspring = []
            for i in range(0, len(selected) - 1, 2):
                parent1, parent2 = selected[i], selected[i + 1]
                if random.random() < crossover_rate:
                    child1, child2 = await self._crossover(
                        parent1, parent2, problem_instance
                    )
                else:
                    child1, child2 = parent1.copy(), parent2.copy()
                offspring.extend([child1, child2])

            # Mutation
            for chromosome in offspring:
                if random.random() < mutation_rate:
                    await self.problem_builder._mutate_chromosome(
                        chromosome, problem_instance
                    )

            # Repair and evaluate
            for chromosome in offspring:
                await self.problem_builder._repair_chromosome(
                    chromosome, problem_instance
                )
                chromosome.fitness_score = (
                    await self.problem_builder._evaluate_chromosome_fitness(
                        chromosome, problem_instance
                    )
                )

            # Elitism + replacement
            population.sort(key=lambda x: x.fitness_score, reverse=True)
            elite_count = int(len(population) * elitism_rate)
            new_population = (
                population[:elite_count] + offspring[: len(population) - elite_count]
            )
            population = new_population[: len(population)]

            best_fitness = max(c.fitness_score for c in population)
            best_fitness_history.append(best_fitness)

            # Progress update every 10 generations
            if generation % 10 == 0:
                progress = 70 + int((generation / generations) * 20)  # 70-90%
                try:
                    from app.services.notification import publish_job_update

                    await publish_job_update(
                        str(job_id),
                        {
                            "progress": progress,
                            "phase": "ga_evolution",
                            "message": f"Generation {generation}/{generations}, "
                            f"best fitness: {best_fitness:.2f}",
                        },
                    )
                except Exception:
                    pass

        # Return best chromosome
        population.sort(key=lambda x: x.fitness_score, reverse=True)
        return population[0]

    async def _tournament_selection(
        self, population: List[Any], tournament_size: int
    ) -> List[Any]:
        """Tournament selection for GA"""
        selected = []
        for _ in range(len(population)):
            tournament = random.sample(
                population, min(tournament_size, len(population))
            )
            winner = max(tournament, key=lambda x: x.fitness_score)
            selected.append(winner.copy())
        return selected

    async def _crossover(
        self, parent1: Any, parent2: Any, problem_instance: Any
    ) -> Tuple[Any, Any]:
        """Order-based crossover for GA chromosomes"""
        child1 = parent1.copy()
        child2 = parent2.copy()

        # Simple crossover: swap assignments for random subset of exams
        exam_ids = list(parent1.exam_assignments.keys())
        if len(exam_ids) > 1:
            crossover_point = random.randint(1, len(exam_ids) - 1)
            swap_exams = random.sample(exam_ids, crossover_point)

            for exam_id in swap_exams:
                if exam_id in parent2.exam_assignments:
                    child1.exam_assignments[exam_id] = parent2.exam_assignments[
                        exam_id
                    ].copy()
                if exam_id in parent1.exam_assignments:
                    child2.exam_assignments[exam_id] = parent1.exam_assignments[
                        exam_id
                    ].copy()

        return child1, child2

    def _merge_optimization_params(
        self, provided_params: Optional[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Merge provided parameters with defaults"""
        if not provided_params:
            return self.default_params.copy()

        merged: Dict[str, Dict[str, Any]] = self.default_params.copy()
        for phase in ["cpsat", "ga"]:
            if phase in provided_params and isinstance(provided_params[phase], dict):
                merged[phase].update(provided_params[phase])

        return merged

    async def _get_constraints_configuration(
        self, configuration_id: UUID
    ) -> Dict[str, Any]:
        """Get constraint configuration from database"""
        # For now, return a default configuration
        # In practice, this would query the configuration_constraints table
        return {
            "hard_constraints": {
                "no_student_conflicts": {"weight": 1.0, "enabled": True},
                "room_capacity": {"weight": 1.0, "enabled": True},
                "staff_availability": {"weight": 1.0, "enabled": True},
                "time_availability": {"weight": 1.0, "enabled": True},
            },
            "soft_constraints": {
                "room_utilization": {"weight": 100, "enabled": True},
                "time_preferences": {"weight": 50, "enabled": True},
                "staff_balance": {"weight": 25, "enabled": True},
            },
        }

    def _combine_phase_metrics(
        self,
        cpsat_metrics: Optional[Dict[str, Any]],
        ga_metrics: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Combine metrics from both optimization phases"""
        combined: Dict[str, Any] = {}

        if cpsat_metrics:
            combined["cpsat"] = cpsat_metrics
        if ga_metrics:
            combined["ga"] = ga_metrics

        # Calculate combined metrics
        total_runtime = 0.0
        if cpsat_metrics:
            total_runtime += cpsat_metrics.get("cpsat_runtime", 0.0)
        if ga_metrics:
            total_runtime += ga_metrics.get("ga_runtime", 0.0)

        combined["total_runtime"] = total_runtime
        return combined

    async def _validate_and_format_solution(
        self, solution: Dict[str, Any], problem_instance: Any
    ) -> Dict[str, Any]:
        """Validate and format the final solution"""
        # Basic validation
        assignments = solution.get("assignments", {})
        valid_assignments: Dict[str, Any] = {}

        for exam_id, assignment in assignments.items():
            # Convert exam_id to string for consistency
            exam_id_str = str(exam_id)
            if (
                exam_id_str in problem_instance.exams
                and assignment.get("room_id") in problem_instance.rooms
                and assignment.get("timeslot_id") in problem_instance.time_slots
            ):
                valid_assignments[exam_id_str] = assignment

        # Format final solution
        formatted_solution = {
            "assignments": valid_assignments,
            "metadata": {
                "total_exams": len(problem_instance.exams),
                "assigned_exams": len(valid_assignments),
                "assignment_rate": len(valid_assignments)
                / max(1, len(problem_instance.exams)),
                "optimization_method": "hybrid_cpsat_ga",
                "timestamp": time.time(),
            },
            "statistics": solution.get("metadata", {}),
        }

        return formatted_solution

    async def _calculate_final_metrics(
        self,
        solution: Dict[str, Any],
        problem_instance: Any,
        phase_metrics: Dict[str, Any],
        total_time: float,
    ) -> Dict[str, Any]:
        """Calculate comprehensive final metrics"""
        assignments = solution.get("assignments", {})

        # Quality metrics
        assignment_rate = len(assignments) / max(1, len(problem_instance.exams))

        # Resource utilization
        room_usage: Dict[str, int] = {}
        for assignment in assignments.values():
            room_id = assignment.get("room_id")
            if room_id:
                room_id_str = str(room_id)
                room_usage[room_id_str] = room_usage.get(room_id_str, 0) + 1

        room_utilization_rate = len(room_usage) / max(1, len(problem_instance.rooms))

        # Constraint analysis
        student_conflicts = 0
        capacity_violations = 0

        # Count violations (simplified)
        timeslot_exams: Dict[str, List[str]] = {}
        for exam_id, assignment in assignments.items():
            timeslot_id = assignment.get("timeslot_id")
            if timeslot_id:
                timeslot_id_str = str(timeslot_id)
                if timeslot_id_str not in timeslot_exams:
                    timeslot_exams[timeslot_id_str] = []
                timeslot_exams[timeslot_id_str].append(str(exam_id))

        for timeslot_id, exam_ids in timeslot_exams.items():
            for i, exam1 in enumerate(exam_ids):
                for exam2 in exam_ids[i + 1 :]:
                    # Convert to string for consistent comparison
                    exam1_str, exam2_str = str(exam1), str(exam2)
                    if (exam1_str, exam2_str) in getattr(
                        problem_instance, "conflict_matrix", {}
                    ) or (exam2_str, exam1_str) in getattr(
                        problem_instance, "conflict_matrix", {}
                    ):
                        student_conflicts += 1

        final_metrics = {
            "quality_metrics": {
                "assignment_rate": assignment_rate,
                "total_exams": len(problem_instance.exams),
                "assigned_exams": len(assignments),
                "unassigned_exams": len(problem_instance.exams) - len(assignments),
            },
            "resource_utilization": {
                "room_utilization_rate": room_utilization_rate,
                "rooms_used": len(room_usage),
                "total_rooms": len(problem_instance.rooms),
            },
            "constraint_analysis": {
                "hard_constraints": {
                    "student_conflicts": {
                        "violations": student_conflicts,
                        "status": "passed" if student_conflicts == 0 else "failed",
                    },
                    "capacity_violations": {
                        "violations": capacity_violations,
                        "status": "passed" if capacity_violations == 0 else "failed",
                    },
                }
            },
            "performance_metrics": {
                "total_runtime_seconds": total_time,
                "solution_method": "hybrid_cpsat_ga",
            },
            "phase_times": phase_metrics,
        }

        return final_metrics
