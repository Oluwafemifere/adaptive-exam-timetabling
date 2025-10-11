# scheduling_engine/cp_sat/solver_manager.py

"""
REVISED - Orchestrates a two-phase decomposition solve process with SLOT-BY-SLOT packing.
This manager first solves the timetabling problem (Phase 1), then iterates through
each timeslot, solving a small, independent packing problem (Phase 2).
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Tuple, cast
from datetime import date, datetime
from collections import defaultdict
from uuid import UUID

from ortools.sat.python import cp_model
from ortools.sat import sat_parameters_pb2

from scheduling_engine.core.solution import (
    SolutionStatus,
    TimetableSolution,
    ExamAssignment,
    AssignmentStatus,
)
from scheduling_engine.cp_sat.solution_extractor import SolutionExtractor
from scheduling_engine.data_flow_tracker import track_data_flow
from scheduling_engine.cp_sat.model_builder import CPSATModelBuilder
from scheduling_engine.constraints.constraint_manager import CPSATConstraintManager

from backend.app.utils.celery_task_utils import task_progress_tracker
from scheduling_engine.genetic_algorithm.ga_processor import GAResult


logger = logging.getLogger(__name__)


class CeleryProgressCallback(cp_model.CpSolverSolutionCallback):
    """A CP-SAT callback to send solver progress to the Celery task."""

    # ... (no changes to this class)

    def __init__(
        self,
        task_context: Any,
        loop: asyncio.AbstractEventLoop,
        phase_name: str,
        progress_window: tuple[int, int],
    ):
        """
        Initializes the callback.

        Args:
            task_context: The Celery task instance (self).
            loop: The asyncio event loop from the Celery task's thread.
            phase_name: The name of the current solving phase.
            progress_window: The (start, end) progress percentage for this phase.
        """
        super().__init__()
        self.task_context = task_context
        self.loop = loop
        self.phase_name = phase_name
        self.start_progress, self.end_progress = progress_window
        self.solution_count = 0
        self.last_objective = float("inf")
        self.start_time = datetime.now()
        logger.info(
            f"CeleryProgressCallback initialized for phase '{self.phase_name}'."
        )

    def OnSolutionCallback(self):
        """Called by the solver each time a new, better solution is found."""
        if not self.task_context or not hasattr(self.task_context, "update_progress"):
            return

        current_objective = self.ObjectiveValue()
        # Only send updates for improving solutions to avoid spamming the logs
        if current_objective >= self.last_objective:
            return

        self.solution_count += 1
        self.last_objective = current_objective
        elapsed_time = (datetime.now() - self.start_time).total_seconds()

        message = (
            f"Solver found solution #{self.solution_count} after {elapsed_time:.1f}s. "
            f"Objective: {current_objective:,.0f}"
        )
        logger.info(f"[{self.phase_name.upper()}] {message}")

        # Keep the progress bar at the start of the phase, but update the message
        current_progress = self.start_progress

        # Schedule the async update_progress call on the main event loop.
        # This is the correct way to call async code from a synchronous callback.
        if self.loop and self.loop.is_running():
            coro = self.task_context.update_progress(
                progress=current_progress,
                phase=self.phase_name,
                message=message,
            )
            asyncio.run_coroutine_threadsafe(coro, self.loop)


class CPSATSolverManager:
    """Solver manager that orchestrates the build and solve process for the CP-SAT model."""

    def __init__(self, problem):
        self.problem = problem
        self.model: Optional[cp_model.CpModel] = None
        self.shared_vars = None
        self.solver = cp_model.CpSolver()
        self.ga_result: Optional[GAResult] = None
        self.task_context: Optional[Any] = None

        self.loop: Optional[asyncio.AbstractEventLoop] = None
        logger.info("Initialized CPSATSolverManager for Two-Phase Decomposition.")

    @track_data_flow("solve_model_decomposed", include_stats=True)
    async def solve(self) -> Tuple[int, TimetableSolution]:
        """Orchestrates the full two-phase solve process with start-time-group packing."""
        self.loop = asyncio.get_running_loop()
        logger.info("=============================================")
        logger.info("===   STARTING TWO-PHASE DECOMPOSED SOLVE   ===")
        logger.info("=============================================")

        # --- PHASE 1: Timetabling (Assign Exams to Slots) ---
        logger.info("\n--- STARTING PHASE 1: TIMETABLING ---")
        builder = CPSATModelBuilder(problem=self.problem)
        builder.task_context = self.task_context
        if builder.encoder and builder.encoder.ga_result:
            self.ga_result = builder.encoder.ga_result
        phase1_model, phase1_vars = await builder.build_phase1()

        status, exam_slot_map = await self._solve_phase1(phase1_model, phase1_vars)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            logger.error("Phase 1 FAILED. Aborting.")
            final_solution = TimetableSolution(self.problem)
            final_solution.status = SolutionStatus.INFEASIBLE
            return cast(int, status), final_solution
        logger.info(
            f"Phase 1 successful. Found start times for {len(exam_slot_map)} exams."
        )

        # --- START OF FIX: Group exams by START TIME for Phase 2 subproblems ---
        logger.info("\n--- STARTING PHASE 2: GROUP-BY-START-TIME PACKING ---")
        final_solution = TimetableSolution(self.problem)
        self._populate_solution_from_phase1(exam_slot_map, final_solution)

        # Group exams by their start slot ID
        exams_by_start_slot = defaultdict(list)
        for exam_id, (start_slot_id, _) in exam_slot_map.items():
            exams_by_start_slot[start_slot_id].append(exam_id)

        all_phase2_statuses = []
        total_groups = len(exams_by_start_slot)

        for i, (start_slot_id, exam_ids_in_group) in enumerate(
            exams_by_start_slot.items()
        ):
            logger.info(
                f"\n--- Solving packing for Start-Time Group {i+1}/{total_groups} (Slot: {start_slot_id}) ---"
            )

            # Collect the phase 1 results for only the exams in this group
            group_phase1_results = {
                exam_id: exam_slot_map[exam_id] for exam_id in exam_ids_in_group
            }

            # Build a new model for this specific group of exams
            phase2_builder = CPSATModelBuilder(problem=self.problem)
            phase2_builder.task_context = self.task_context
            phase2_model, phase2_vars = await phase2_builder.build_phase2_full_model(
                group_phase1_results
            )

            # Solve this single group's packing subproblem
            self.model = phase2_model
            phase2_status = await self._solve_phase2_full(phase2_model, phase2_vars)
            all_phase2_statuses.append(phase2_status)

            if phase2_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                # Extract the solution for this group and update the final_solution object
                extractor = SolutionExtractor(self.problem, phase2_vars, self.solver)
                extractor.task_context = self.task_context
                await extractor.extract_full_solution(
                    final_solution, group_phase1_results
                )
            else:
                logger.error(
                    f"Phase 2 FAILED for start-group {start_slot_id}. Assignments for these exams will be incomplete."
                )

        # --- END OF FIX ---

        logger.info("\n--- ASSEMBLING FINAL SOLUTION ---")
        logger.info("Updating final solution statistics and status...")
        final_solution.update_statistics()
        final_solution.status = (
            SolutionStatus.FEASIBLE
            if final_solution.is_feasible()
            else SolutionStatus.INFEASIBLE
        )
        final_status = (
            max(all_phase2_statuses) if all_phase2_statuses else cp_model.UNKNOWN
        )
        if cp_model.INFEASIBLE in all_phase2_statuses:
            final_status = cp_model.INFEASIBLE
            final_solution.status = SolutionStatus.INFEASIBLE

        logger.info(
            f"Final solution status determined as: {final_solution.status.value}"
        )
        final_solution.log_detected_conflicts()
        logger.info("\n✅ Two-phase decomposition solve complete.")
        return cast(int, final_status), final_solution

    @task_progress_tracker(
        start_progress=35,
        end_progress=55,
        phase="solving_phase_1",
        message="Solving for optimal exam times...",
    )
    async def _solve_phase1(
        self, model, shared_vars
    ) -> Tuple[int, Dict[UUID, Tuple[UUID, date]]]:
        """Solves the Phase 1 model and extracts the exam-to-slot mapping."""
        logger.info("--- Calling CP-SAT solver for Phase 1 ---")
        self._configure_solver_parameters()
        self.model = model  # Set the current model for the solver manager

        if self.ga_result and self.ga_result.search_hints:
            logger.info(
                f"Applying {len(self.ga_result.search_hints)} search hints from GA..."
            )
            x_vars = shared_vars.x_vars
            hints_applied = 0
            for exam_id, slot_id in self.ga_result.search_hints.items():
                hint_var = x_vars.get((exam_id, slot_id))
                assert self.model
                if hint_var:
                    self.model.AddHint(hint_var, 1)
                    hints_applied += 1
            logger.info(f"Successfully applied {hints_applied} hints to the model.")

        assert self.loop
        progress_callback = CeleryProgressCallback(
            task_context=self.task_context,
            loop=self.loop,
            phase_name="solving_phase_1",
            progress_window=(35, 55),
        )
        assert self.model
        status = cast(int, self.solver.Solve(self.model, progress_callback))
        status_name = self.solver.StatusName()
        logger.info(f"Phase 1 solver finished with status: {status_name}")
        logger.info(f"  - Objective value: {self.solver.ObjectiveValue()}")
        logger.info(f"  - Wall time: {self.solver.WallTime()}s")

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            logger.info("Extracting Phase 1 solution (exam-to-slot map)...")
            extractor = SolutionExtractor(self.problem, shared_vars, self.solver)
            return status, extractor.extract_phase1_solution()

        logger.warning("Phase 1 solution could not be found.")
        return status, {}

    @task_progress_tracker(
        start_progress=65,
        end_progress=80,
        phase="solving_phase_2",
        message="Assigning rooms and invigilators...",
    )
    async def _solve_phase2_full(self, model, shared_vars) -> int:
        """Solves a Phase 2 packing model (now for a single slot)."""
        logger.info("--- Calling CP-SAT solver for a Phase 2 subproblem ---")
        # Use a shorter time limit for subproblems
        time_limit = getattr(self.problem, "subproblem_time_limit_seconds", 60.0)
        self._configure_solver_parameters(time_limit_override=time_limit)

        assert self.loop
        progress_callback = CeleryProgressCallback(
            task_context=self.task_context,
            loop=self.loop,
            phase_name="solving_phase_2",
            progress_window=(65, 80),
        )
        status = cast(int, self.solver.Solve(model, progress_callback))
        status_name = self.solver.StatusName()
        logger.info(f"Phase 2 subproblem solver finished with status: {status_name}")
        logger.info(f"  - Objective value: {self.solver.ObjectiveValue()}")
        logger.info(f"  - Wall time: {self.solver.WallTime()}s")
        return status

    def _populate_solution_from_phase1(
        self, exam_slot_map: Dict, solution: TimetableSolution
    ) -> None:
        """Populates a solution object with time assignments from Phase 1."""
        logger.info("Pre-populating final solution with time assignments from Phase 1.")
        for exam_id, (slot_id, day_date) in exam_slot_map.items():
            asm = ExamAssignment(
                exam_id=exam_id,
                time_slot_id=slot_id,
                assigned_date=day_date,
                status=AssignmentStatus.UNASSIGNED,
            )
            solution.assignments[exam_id] = asm
        logger.info(f"Populated {len(exam_slot_map)} time assignments.")

    def _configure_solver_parameters(
        self, time_limit_override: Optional[float] = None, log_progress: bool = True
    ) -> None:
        """Configures solver parameters."""
        logger.info("Configuring solver parameters...")
        params = self.solver.parameters
        params.enumerate_all_solutions = False
        params.log_search_progress = log_progress

        time_limit = time_limit_override or getattr(
            self.problem, "solver_time_limit_seconds", 300.0
        )
        params.max_time_in_seconds = float(time_limit)

        num_workers = getattr(self.problem, "solver_num_workers", 0)
        if num_workers > 0:
            params.num_workers = int(num_workers)
        else:
            logger.info("solver_num_workers not set, allowing OR-Tools to auto-detect.")

        params.cp_model_presolve = True
        params.cp_model_probing_level = 2
        params.search_branching = sat_parameters_pb2.SatParameters.PORTFOLIO_SEARCH
        params.linearization_level = 2
        params.use_lns = True

        if log_progress:
            logger.info(
                f"Solver configured: TimeLimit={params.max_time_in_seconds}s, Workers={params.num_workers}, LogProgress={log_progress}"
            )
