# scheduling_engine/hybrid/incremental_optimizer.py

"""
Incremental Optimizer for handling manual edits and solution refinement.
Implements incremental optimization strategies for real-time timetable editing
and local search improvements while maintaining solution feasibility.
"""

from typing import Dict, List, Optional, Any, Set, Tuple, DefaultDict
from uuid import UUID, uuid4
from datetime import datetime
import time
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from ..config import get_logger, SchedulingEngineConfig
from ..core.problem_model import ExamSchedulingProblem
from ..core.solution import TimetableSolution
from ..core.metrics import SolutionMetrics
from ..core.constraint_registry import ConstraintRegistry
from ..core.constraint_types import (
    ConstraintViolation,
)
from ..cp_sat.model_builder import CPSATModelBuilder
from ..cp_sat.solver_manager import CPSATSolverManager
from ..genetic_algorithm.chromosome import VariableSelectorChromosome
from ..genetic_algorithm.operators.mutation import (
    MutationOperatorFactory,
    MutationConfig,
)

logger = get_logger("hybrid.incremental_optimizer")


class EditType(Enum):
    """Types of manual edits to timetable"""

    TIME_CHANGE = "time_change"
    ROOM_CHANGE = "room_change"
    DATE_CHANGE = "date_change"
    CAPACITY_CHANGE = "capacity_change"
    INVIGILATOR_CHANGE = "invigilator_change"
    EXAM_CANCELLATION = "exam_cancellation"
    EXAM_ADDITION = "exam_addition"


class OptimizationScope(Enum):
    """Scope of incremental optimization"""

    LOCAL = "local"  # Only affected exams/timeslots
    REGIONAL = "regional"  # Affected faculty/department
    GLOBAL = "global"  # Entire timetable


class RepairStrategy(Enum):
    """Strategies for repairing infeasible solutions"""

    CP_SAT_REPAIR = "cp_sat_repair"  # Use CP-SAT to repair constraints
    LOCAL_SEARCH = "local_search"  # Local heuristic repair
    GENETIC_REPAIR = "genetic_repair"  # Use GA operators for repair
    BACKTRACK = "backtrack"  # Revert to previous valid state
    HYBRID_REPAIR = "hybrid_repair"  # Combination of methods


@dataclass
class EditRequest:
    """Manual edit request structure"""

    edit_id: UUID
    edit_type: EditType
    exam_id: UUID
    old_values: Dict[str, Any]
    new_values: Dict[str, Any]
    user_id: UUID
    timestamp: datetime
    reason: Optional[str] = None
    priority: int = 1  # 1=low, 5=high

    def __post_init__(self):
        if self.edit_id is None:
            self.edit_id = uuid4()
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class EditResult:
    """Result of applying an edit"""

    edit_id: UUID
    success: bool
    applied_changes: Dict[str, Any] = field(default_factory=dict)
    constraint_violations: List[ConstraintViolation] = field(default_factory=list)
    repair_actions: List[str] = field(default_factory=list)
    affected_exams: Set[UUID] = field(default_factory=set)
    quality_impact: Dict[str, float] = field(default_factory=dict)
    optimization_time: float = 0.0
    fallback_used: bool = False
    error_message: Optional[str] = None


@dataclass
class IncrementalOptimizationResult:
    """Result of incremental optimization process"""

    optimization_id: UUID
    original_solution: TimetableSolution
    optimized_solution: TimetableSolution
    edit_results: List[EditResult] = field(default_factory=list)
    total_edits_applied: int = 0
    total_optimization_time: float = 0.0
    quality_improvement: float = 0.0
    feasibility_maintained: bool = True
    performance_metrics: Dict[str, Any] = field(default_factory=dict)


class IncrementalOptimizer:
    """
    Handles incremental optimization for manual edits and solution refinement.

    Implements repair strategies and local optimization to maintain solution
    quality while accommodating real-time changes to the timetable.
    """

    def __init__(self, config: SchedulingEngineConfig):
        self.config = config
        self.constraint_registry = ConstraintRegistry()
        self.metrics = SolutionMetrics()

        # CP-SAT components for repair operations
        self.cp_sat_builder = CPSATModelBuilder(config.cp_sat)
        self.cp_sat_solver = CPSATSolverManager(config.cp_sat)

        # GA components for local optimization - use factory to create concrete mutation operator
        mutation_config = MutationConfig(
            mutation_rate=config.genetic_algorithm.mutation_rate,
            # Provide default values for missing attributes
            priority_mutation_strength=0.5,
            assignment_mutation_rate=0.1,
            adaptive_mutation=False,
            constraint_guided_mutation=False,
            repair_mutations=False,
            diversity_preservation=False,
        )
        self.mutation_operator = MutationOperatorFactory.create_operator(
            "priority", mutation_config
        )

        # State tracking
        self.current_solution: Optional[TimetableSolution] = None
        self.problem: Optional[ExamSchedulingProblem] = None
        self.edit_history: List[EditRequest] = []
        self.solution_snapshots: List[Tuple[datetime, TimetableSolution]] = []

        # Configuration
        self.max_repair_attempts = 3
        self.max_snapshots = 10
        self.repair_time_limit = 30  # seconds
        self.local_search_radius = 5  # number of related exams to consider

        logger.info("Incremental optimizer initialized")

    def set_current_solution(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> None:
        """Set the current solution for incremental optimization"""
        self.problem = problem
        self.current_solution = solution.copy()

        # Create initial snapshot
        self._create_solution_snapshot()

        logger.info(
            f"Current solution set with {len(solution.assignments)} assignments"
        )

    async def apply_edit(self, edit_request: EditRequest) -> EditResult:
        """
        Apply a single edit to the current solution with repair if needed.

        Args:
            edit_request: The edit to apply

        Returns:
            Result of the edit application including any repairs
        """
        logger.info(
            f"Applying edit {edit_request.edit_type.value} to exam {edit_request.exam_id}"
        )

        start_time = time.time()
        self.edit_history.append(edit_request)

        try:
            if self.current_solution is None:
                return EditResult(
                    edit_id=edit_request.edit_id,
                    success=False,
                    error_message="No current solution set",
                    optimization_time=time.time() - start_time,
                )

            # Create working copy of current solution
            working_solution = self.current_solution.copy()

            # Apply the edit
            edit_result = await self._apply_edit_to_solution(
                working_solution, edit_request
            )

            if edit_result.success:
                # Validate the edited solution
                validation_result = await self._validate_edited_solution(
                    working_solution, edit_request
                )

                if validation_result["is_feasible"]:
                    # Solution is feasible - update current solution
                    self.current_solution = working_solution
                    self._create_solution_snapshot()

                    edit_result.quality_impact = self._calculate_quality_impact(
                        edit_request, validation_result
                    )

                else:
                    # Solution is infeasible - attempt repair
                    logger.warning(
                        "Edit created infeasible solution, attempting repair"
                    )

                    repair_result = await self._repair_solution(
                        working_solution, edit_request, validation_result["violations"]
                    )

                    if repair_result["success"]:
                        self.current_solution = repair_result["solution"]
                        self._create_solution_snapshot()
                        edit_result.repair_actions = repair_result["actions"]
                        edit_result.affected_exams.update(
                            repair_result["affected_exams"]
                        )
                    else:
                        # Repair failed - revert to fallback
                        edit_result.success = False
                        edit_result.fallback_used = True
                        edit_result.error_message = repair_result.get("error")
                        await self._handle_repair_failure(edit_request, repair_result)

            edit_result.optimization_time = time.time() - start_time
            logger.info(f"Edit completed in {edit_result.optimization_time:.2f}s")

            return edit_result

        except Exception as e:
            logger.error(f"Error applying edit: {e}")
            return EditResult(
                edit_id=edit_request.edit_id,
                success=False,
                error_message=str(e),
                optimization_time=time.time() - start_time,
            )

    async def _apply_edit_to_solution(
        self, solution: TimetableSolution, edit_request: EditRequest
    ) -> EditResult:
        """Apply the edit to the solution structure"""
        result = EditResult(edit_id=edit_request.edit_id, success=True)

        try:
            exam_id = edit_request.exam_id

            # Find current assignment for the exam
            if exam_id not in solution.assignments:
                result.success = False
                result.error_message = f"No assignment found for exam {exam_id}"
                return result

            current_assignment = solution.assignments[exam_id]

            # Apply changes based on edit type
            if edit_request.edit_type == EditType.TIME_CHANGE:
                old_time_slot = current_assignment.time_slot_id
                new_time_slot = edit_request.new_values.get("time_slot_id")

                if new_time_slot:
                    current_assignment.time_slot_id = UUID(new_time_slot)
                    result.applied_changes["time_slot_id"] = {
                        "old": str(old_time_slot),
                        "new": str(new_time_slot),
                    }

            elif edit_request.edit_type == EditType.ROOM_CHANGE:
                old_rooms = current_assignment.room_ids.copy()
                new_rooms = edit_request.new_values.get("room_ids", [])

                current_assignment.room_ids = [UUID(rid) for rid in new_rooms]
                result.applied_changes["room_ids"] = {
                    "old": [str(rid) for rid in old_rooms],
                    "new": new_rooms,
                }

            elif edit_request.edit_type == EditType.DATE_CHANGE:
                old_date = current_assignment.assigned_date
                new_date = edit_request.new_values.get("assigned_date")

                if new_date:
                    current_assignment.assigned_date = new_date
                    result.applied_changes["assigned_date"] = {
                        "old": str(old_date),
                        "new": str(new_date),
                    }

            elif edit_request.edit_type == EditType.CAPACITY_CHANGE:
                old_capacity = current_assignment.get_total_capacity()
                new_capacity = edit_request.new_values.get("expected_students")

                if new_capacity is not None:
                    # Reallocate capacity across rooms
                    room_count = len(current_assignment.room_ids)
                    if room_count > 0:
                        capacity_per_room = new_capacity // room_count
                        remainder = new_capacity % room_count

                        for i, room_id in enumerate(current_assignment.room_ids):
                            allocation = capacity_per_room + (1 if i < remainder else 0)
                            current_assignment.room_allocations[room_id] = allocation

                    result.applied_changes["allocated_capacity"] = {
                        "old": old_capacity,
                        "new": new_capacity,
                    }

            elif edit_request.edit_type == EditType.INVIGILATOR_CHANGE:
                # Invigilator handling would be implemented here
                pass

            # Track affected exam
            result.affected_exams.add(exam_id)

            # Update solution timestamp
            solution.last_modified = datetime.now()

            return result

        except Exception as e:
            logger.error(f"Error applying edit to solution: {e}")
            result.success = False
            result.error_message = str(e)
            return result

    async def _validate_edited_solution(
        self, solution: TimetableSolution, edit_request: EditRequest
    ) -> Dict[str, Any]:
        """Validate solution after edit application"""
        try:
            # Use constraint registry to validate
            if self.problem is None:
                return {
                    "is_feasible": False,
                    "violations": [],
                    "error": "No problem set",
                }

            # This is a placeholder - actual implementation would validate constraints
            # For now, check basic feasibility
            is_feasible = solution.is_feasible()
            violations: List[ConstraintViolation] = []

            return {
                "is_feasible": is_feasible,
                "violations": violations,
                "hard_violations": [],
                "soft_violations": [],
                "quality_score": (
                    self.metrics.evaluate_solution_quality(self.problem, solution)
                    if is_feasible
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"Error validating edited solution: {e}")
            return {"is_feasible": False, "violations": [], "error": str(e)}

    async def _repair_solution(
        self,
        solution: TimetableSolution,
        edit_request: EditRequest,
        violations: List[ConstraintViolation],
        strategy: RepairStrategy = RepairStrategy.HYBRID_REPAIR,
    ) -> Dict[str, Any]:
        """
        Repair an infeasible solution using specified strategy.

        Args:
            solution: The infeasible solution to repair
            edit_request: The edit that caused infeasibility
            violations: List of constraint violations
            strategy: Repair strategy to use

        Returns:
            Repair result with success status and repaired solution
        """
        logger.info(
            f"Repairing solution with {len(violations)} violations using {strategy.value}"
        )

        repair_start = time.time()

        try:
            if strategy == RepairStrategy.CP_SAT_REPAIR:
                return await self._cp_sat_repair(solution, edit_request, violations)

            elif strategy == RepairStrategy.LOCAL_SEARCH:
                return await self._local_search_repair(
                    solution, edit_request, violations
                )

            elif strategy == RepairStrategy.GENETIC_REPAIR:
                return await self._genetic_repair(solution, edit_request, violations)

            elif strategy == RepairStrategy.BACKTRACK:
                return await self._backtrack_repair(solution, edit_request)

            elif strategy == RepairStrategy.HYBRID_REPAIR:
                # Try multiple strategies in order
                for repair_strategy in [
                    RepairStrategy.LOCAL_SEARCH,
                    RepairStrategy.CP_SAT_REPAIR,
                    RepairStrategy.GENETIC_REPAIR,
                ]:
                    result = await self._repair_solution(
                        solution.copy(), edit_request, violations, repair_strategy
                    )

                    if result["success"]:
                        result["actions"].append(
                            f"Successful repair with {repair_strategy.value}"
                        )
                        return result

                # All strategies failed - backtrack
                logger.warning("All repair strategies failed, reverting to backtrack")
                return await self._backtrack_repair(solution, edit_request)

            else:
                raise ValueError(f"Unknown repair strategy: {strategy}")

        except Exception as e:
            logger.error(f"Error during solution repair: {e}")
            return {
                "success": False,
                "error": str(e),
                "actions": [f"Repair failed: {e}"],
                "optimization_time": time.time() - repair_start,
            }

    async def _cp_sat_repair(
        self,
        solution: TimetableSolution,
        edit_request: EditRequest,
        violations: List[ConstraintViolation],
    ) -> Dict[str, Any]:
        """Repair solution using CP-SAT local solve around the edited area"""
        try:
            if self.problem is None:
                return {
                    "success": False,
                    "error": "No problem instance available",
                    "actions": ["CP-SAT repair failed: no problem"],
                }

            # Identify affected region
            affected_exams = self._identify_affected_region(
                solution, edit_request, violations
            )

            # Create sub-problem for the affected region
            sub_problem = self._create_sub_problem(affected_exams)

            # Build CP-SAT model for sub-problem
            model = self.cp_sat_builder.build_model(sub_problem)

            # Add constraints to fix unaffected assignments
            self._add_fixed_assignment_constraints(model, solution, affected_exams)

            # Solve with limited time
            # Note: This would need proper variable mapping which is complex
            # For now, return not implemented
            return {
                "success": False,
                "error": "CP-SAT repair not fully implemented",
                "actions": ["CP-SAT repair attempted but not implemented"],
            }

        except Exception as e:
            logger.error(f"Error in CP-SAT repair: {e}")
            return {
                "success": False,
                "error": str(e),
                "actions": [f"CP-SAT repair error: {e}"],
            }

    async def _local_search_repair(
        self,
        solution: TimetableSolution,
        edit_request: EditRequest,
        violations: List[ConstraintViolation],
    ) -> Dict[str, Any]:
        """Repair solution using local search heuristics"""
        try:
            actions = []
            affected_exams = set([edit_request.exam_id])
            repaired_solution = solution.copy()

            # Simple repair: try to find alternative time slots for conflicted exams
            for violation in violations:
                # Try to resolve each violation by rescheduling exams
                exam_id = edit_request.exam_id
                alternative_slot = await self._find_alternative_timeslot(
                    repaired_solution, exam_id, []
                )

                if alternative_slot and exam_id in repaired_solution.assignments:
                    repaired_solution.assignments[exam_id].time_slot_id = (
                        alternative_slot
                    )
                    actions.append(f"Rescheduled exam {exam_id} to alternative slot")
                    affected_exams.add(exam_id)

            # Validate repaired solution
            final_validation = await self._validate_edited_solution(
                repaired_solution, edit_request
            )

            success = final_validation["is_feasible"]

            return {
                "success": success,
                "solution": repaired_solution,
                "actions": actions,
                "affected_exams": affected_exams,
                "repair_method": "local_search",
            }

        except Exception as e:
            logger.error(f"Error in local search repair: {e}")
            return {
                "success": False,
                "error": str(e),
                "actions": [f"Local search repair error: {e}"],
            }

    async def _genetic_repair(
        self,
        solution: TimetableSolution,
        edit_request: EditRequest,
        violations: List[ConstraintViolation],
    ) -> Dict[str, Any]:
        """Repair solution using genetic algorithm operators"""
        try:
            # Convert solution to chromosome representation
            chromosome = self._solution_to_chromosome(solution)

            # Apply targeted mutations to repair violations
            repair_attempts = 0
            max_attempts = 10

            while repair_attempts < max_attempts:
                # Apply constraint-guided mutation
                mutated_chromosome = await self._constraint_guided_mutation(
                    chromosome, violations
                )

                # Convert back to solution
                candidate_solution = self._chromosome_to_solution(mutated_chromosome)

                # Check if violations are resolved
                validation_result = await self._validate_edited_solution(
                    candidate_solution, edit_request
                )

                if validation_result["is_feasible"]:
                    return {
                        "success": True,
                        "solution": candidate_solution,
                        "actions": [
                            f"Genetic repair in {repair_attempts + 1} attempts"
                        ],
                        "affected_exams": {edit_request.exam_id},
                        "repair_method": "genetic",
                    }

                chromosome = mutated_chromosome
                repair_attempts += 1

            # Genetic repair failed
            return {
                "success": False,
                "error": f"Genetic repair failed after {max_attempts} attempts",
                "actions": [f"Genetic repair attempted {max_attempts} times"],
            }

        except Exception as e:
            logger.error(f"Error in genetic repair: {e}")
            return {
                "success": False,
                "error": str(e),
                "actions": [f"Genetic repair error: {e}"],
            }

    async def _backtrack_repair(
        self, solution: TimetableSolution, edit_request: EditRequest
    ) -> Dict[str, Any]:
        """Repair by reverting to previous valid solution"""
        try:
            if len(self.solution_snapshots) < 2:
                return {
                    "success": False,
                    "error": "No previous solution available for backtrack",
                    "actions": ["Backtrack attempted but no snapshots available"],
                }

            # Get most recent valid snapshot (excluding current)
            previous_snapshot = self.solution_snapshots[-2]
            previous_solution = previous_snapshot[1].copy()

            return {
                "success": True,
                "solution": previous_solution,
                "actions": [f"Reverted to solution from {previous_snapshot[0]}"],
                "affected_exams": set(),
                "repair_method": "backtrack",
            }

        except Exception as e:
            logger.error(f"Error in backtrack repair: {e}")
            return {
                "success": False,
                "error": str(e),
                "actions": [f"Backtrack repair error: {e}"],
            }

    async def _find_alternative_timeslot(
        self, solution: TimetableSolution, exam_id: UUID, avoid_exams: List[UUID]
    ) -> Optional[UUID]:
        """Find alternative time slot for an exam"""
        if not self.problem:
            return None

        # Get all available time slots
        available_slots = list(self.problem.time_slots.keys())

        if exam_id not in solution.assignments:
            return None

        current_assignment = solution.assignments[exam_id]
        current_slot = current_assignment.time_slot_id

        # Try to find a slot that doesn't create conflicts
        for slot_id in available_slots:
            if slot_id == current_slot:
                continue

            # Simple conflict check - would need proper implementation
            has_conflict = False
            for other_exam_id, other_assignment in solution.assignments.items():
                if other_assignment.time_slot_id == slot_id:
                    # Check if this would create a conflict
                    has_conflict = True
                    break

            if not has_conflict:
                return slot_id

        return None

    def _identify_affected_region(
        self,
        solution: TimetableSolution,
        edit_request: EditRequest,
        violations: List[ConstraintViolation],
    ) -> Set[UUID]:
        """Identify region of exams affected by edit and violations"""
        affected = set([edit_request.exam_id])

        # Add exams mentioned in violations
        for violation in violations:
            # Extract affected exams from violation - implementation specific
            # For now, just add the edited exam
            affected.add(edit_request.exam_id)

        return affected

    def _create_sub_problem(self, exam_ids: Set[UUID]) -> ExamSchedulingProblem:
        """Create sub-problem containing only specified exams"""
        if not self.problem:
            raise ValueError("No problem instance available")

        # Create a copy of the problem with only the specified exams
        # This is a simplified implementation
        sub_problem = ExamSchedulingProblem(
            session_id=self.problem.session_id,
            session_name=self.problem.session_name,
            exam_period_start=self.problem.exam_period_start,
            exam_period_end=self.problem.exam_period_end,
        )

        # Copy relevant exams
        for exam_id in exam_ids:
            if exam_id in self.problem.exams:
                sub_problem.exams[exam_id] = self.problem.exams[exam_id]

        # Copy all time slots and rooms (simplified)
        sub_problem.time_slots = self.problem.time_slots.copy()
        sub_problem.rooms = self.problem.rooms.copy()

        return sub_problem

    def _add_fixed_assignment_constraints(self, model, solution, affected_exams):
        """Add constraints to fix unaffected assignments - placeholder"""
        # This would be implemented to fix non-affected exams in place
        pass

    def _apply_repair_assignments(
        self, original_solution, repair_solution, affected_exams
    ):
        """Apply repaired assignments to solution - placeholder"""
        # This would apply the repairs from the sub-problem solution
        return original_solution

    async def optimize_locally(
        self,
        focus_exams: Set[UUID],
        optimization_scope: OptimizationScope = OptimizationScope.LOCAL,
        time_limit_seconds: int = 60,
    ) -> IncrementalOptimizationResult:
        """
        Perform local optimization around specified exams.

        Args:
            focus_exams: Set of exam IDs to focus optimization on
            optimization_scope: Scope of the optimization
            time_limit_seconds: Maximum time for optimization

        Returns:
            Result of the local optimization
        """
        logger.info(
            f"Starting local optimization for {len(focus_exams)} exams with {optimization_scope.value} scope"
        )

        start_time = time.time()

        if self.current_solution is None or self.problem is None:
            return IncrementalOptimizationResult(
                optimization_id=uuid4(),
                original_solution=TimetableSolution(ExamSchedulingProblem(uuid4(), "")),
                optimized_solution=TimetableSolution(
                    ExamSchedulingProblem(uuid4(), "")
                ),
                total_optimization_time=time.time() - start_time,
                quality_improvement=0.0,
                feasibility_maintained=False,
            )

        original_solution = self.current_solution.copy()

        try:
            # Determine optimization region based on scope
            optimization_region = await self._determine_optimization_region(
                focus_exams, optimization_scope
            )

            # Create sub-problem
            sub_problem = self._create_sub_problem(optimization_region)

            # Apply local genetic optimization
            optimized_solution = await self._apply_local_genetic_optimization(
                self.current_solution, sub_problem, time_limit_seconds
            )

            # Calculate quality improvement
            original_quality = self.metrics.evaluate_solution_quality(
                self.problem, original_solution
            )
            optimized_quality = self.metrics.evaluate_solution_quality(
                self.problem, optimized_solution
            )

            quality_improvement = 0.0
            if hasattr(original_quality, "overall_score") and hasattr(
                optimized_quality, "overall_score"
            ):
                quality_improvement = (
                    optimized_quality.overall_score - original_quality.overall_score
                )

            # Update current solution if improvement found
            if quality_improvement > 0:
                self.current_solution = optimized_solution
                self._create_solution_snapshot()

            return IncrementalOptimizationResult(
                optimization_id=uuid4(),
                original_solution=original_solution,
                optimized_solution=optimized_solution,
                total_optimization_time=time.time() - start_time,
                quality_improvement=quality_improvement,
                performance_metrics={
                    "optimization_scope": optimization_scope.value,
                    "region_size": len(optimization_region),
                    "improvement_found": quality_improvement > 0,
                },
            )

        except Exception as e:
            logger.error(f"Error in local optimization: {e}")
            return IncrementalOptimizationResult(
                optimization_id=uuid4(),
                original_solution=original_solution,
                optimized_solution=original_solution,  # No change
                total_optimization_time=time.time() - start_time,
                quality_improvement=0.0,
                feasibility_maintained=True,
            )

    async def _apply_local_genetic_optimization(
        self,
        solution: TimetableSolution,
        sub_problem: ExamSchedulingProblem,
        time_limit: int,
    ) -> TimetableSolution:
        """Apply genetic optimization to sub-problem region"""
        try:
            # This is a simplified version - just return the original solution
            # A full implementation would use genetic algorithms for local optimization
            return solution.copy()

        except Exception as e:
            logger.error(f"Error in local genetic optimization: {e}")
            return solution

    def _create_solution_snapshot(self) -> None:
        """Create a snapshot of current solution for backtracking"""
        if self.current_solution:
            snapshot = (datetime.now(), self.current_solution.copy())
            self.solution_snapshots.append(snapshot)

            # Maintain maximum number of snapshots
            if len(self.solution_snapshots) > self.max_snapshots:
                self.solution_snapshots.pop(0)

            logger.debug(
                f"Solution snapshot created (total: {len(self.solution_snapshots)})"
            )

    def _calculate_quality_impact(
        self, edit_request: EditRequest, validation_result: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate quality impact of an edit"""
        quality_score = validation_result.get("quality_score")
        if not quality_score:
            return {}

        return {
            "objective_change": 0.0,  # Would be calculated based on before/after
            "constraint_score_change": 0.0,
            "room_utilization_change": 0.0,
            "student_satisfaction_change": 0.0,
        }

    async def _handle_repair_failure(
        self, edit_request: EditRequest, repair_result: Dict[str, Any]
    ) -> None:
        """Handle case where solution repair failed"""
        logger.error(
            f"Repair failed for edit {edit_request.edit_id}: {repair_result.get('error')}"
        )

    def get_edit_statistics(self) -> Dict[str, Any]:
        """Get statistics about edit operations"""
        edit_types: DefaultDict[str, int] = defaultdict(int)

        for edit in self.edit_history:
            edit_types[edit.edit_type.value] += 1

        return {
            "total_edits": len(self.edit_history),
            "edit_types": dict(edit_types),
            "snapshots_available": len(self.solution_snapshots),
            "average_edit_complexity": (
                sum(len(edit.new_values) for edit in self.edit_history)
                / len(self.edit_history)
                if self.edit_history
                else 0
            ),
        }

    def _solution_to_chromosome(
        self, solution: TimetableSolution
    ) -> VariableSelectorChromosome:
        """Convert solution to chromosome representation for genetic operations"""
        # Create a random chromosome as placeholder
        if self.problem:
            return VariableSelectorChromosome.create_random(
                self.problem, max_tree_depth=5
            )
        else:
            return VariableSelectorChromosome()

    def _chromosome_to_solution(
        self, chromosome: VariableSelectorChromosome
    ) -> TimetableSolution:
        """Convert chromosome back to solution representation"""
        # This would reconstruct solution using the variable selector
        # For now, return current solution
        return (
            self.current_solution.copy()
            if self.current_solution
            else TimetableSolution(ExamSchedulingProblem(uuid4(), ""))
        )

    async def _constraint_guided_mutation(
        self,
        chromosome: VariableSelectorChromosome,
        violations: List[ConstraintViolation],
    ) -> VariableSelectorChromosome:
        """Apply mutation guided by constraint violations"""
        # Use mutation operator with constraint awareness
        if self.problem:
            return self.mutation_operator.mutate(chromosome, self.problem)
        return chromosome

    async def _determine_optimization_region(
        self, focus_exams: Set[UUID], scope: OptimizationScope
    ) -> Set[UUID]:
        """Determine which exams to include in local optimization"""
        region = focus_exams.copy()

        if scope == OptimizationScope.LOCAL:
            # Just the focus exams
            return region

        elif scope == OptimizationScope.REGIONAL:
            # Add exams from same departments/faculties
            if self.problem:
                for exam_id in focus_exams:
                    exam = self.problem.exams.get(exam_id)
                    if exam and exam.department_id:
                        # Add exams from same department
                        for other_exam_id, other_exam in self.problem.exams.items():
                            if other_exam.department_id == exam.department_id:
                                region.add(other_exam_id)

        elif scope == OptimizationScope.GLOBAL:
            # Include all exams
            if self.problem:
                region = set(self.problem.exams.keys())

        return region


# Factory function
def create_incremental_optimizer(
    config: SchedulingEngineConfig,
) -> IncrementalOptimizer:
    """Create and configure an incremental optimizer instance"""
    return IncrementalOptimizer(config)
