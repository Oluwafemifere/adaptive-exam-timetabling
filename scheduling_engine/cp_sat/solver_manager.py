# scheduling_engine/cp_sat/solver_manager.py

"""
REFACTORED - Orchestrates the two-phase decomposition solve process.
This manager first solves the timetabling problem (Phase 1), then solves a
single, large packing problem for all rooms and invigilators (Phase 2).
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Tuple, cast
from datetime import date, datetime
from collections import defaultdict
from uuid import UUID

from ortools.sat.python import cp_model

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

# --- START OF MODIFICATION ---
from backend.app.utils.celery_task_utils import task_progress_tracker

# --- END OF MODIFICATION ---


logger = logging.getLogger(__name__)


class CeleryProgressCallback(cp_model.CpSolverSolutionCallback):
    """A CP-SAT callback to send solver progress to the Celery task."""

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

        self.task_context: Optional[Any] = None

        self.loop: Optional[asyncio.AbstractEventLoop] = None
        logger.info("Initialized CPSATSolverManager for Two-Phase Decomposition.")

    @track_data_flow("solve_model_decomposed", include_stats=True)
    async def solve(self) -> Tuple[int, TimetableSolution]:
        """Orchestrates the full two-phase solve process."""
        self.loop = asyncio.get_running_loop()
        logger.info("=============================================")
        logger.info("===   STARTING TWO-PHASE DECOMPOSED SOLVE   ===")
        logger.info("=============================================")

        # --- PHASE 1: Timetabling (Assign Exams to Slots) ---
        logger.info("\n--- STARTING PHASE 1: TIMETABLING ---")
        builder = CPSATModelBuilder(problem=self.problem)
        builder.task_context = self.task_context  # Propagate context
        phase1_model, phase1_vars = await builder.build_phase1()

        status, exam_slot_map = await self._solve_phase1(phase1_model, phase1_vars)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            logger.error(
                "Phase 1 FAILED to find a feasible solution. Problem is likely infeasible or too constrained. Aborting."
            )
            final_solution = TimetableSolution(self.problem)
            final_solution.status = SolutionStatus.INFEASIBLE
            return cast(int, status), final_solution
        logger.info(
            f"Phase 1 successful. Found start times for {len(exam_slot_map)} exams."
        )

        # --- PHASE 2: Full Packing (Assign All Rooms & Invigilators) ---
        logger.info("\n--- STARTING PHASE 2: FULL PACKING & ASSIGNMENT ---")
        phase2_builder = CPSATModelBuilder(problem=self.problem)
        phase2_builder.task_context = self.task_context  # Propagate context
        phase2_model, phase2_vars = await phase2_builder.build_phase2_full_model(
            exam_slot_map
        )

        phase2_status = await self._solve_phase2_full(phase2_model, phase2_vars)

        # --- FINAL SOLUTION EXTRACTION & ASSEMBLY ---
        logger.info("\n--- ASSEMBLING FINAL SOLUTION ---")
        final_solution = TimetableSolution(self.problem)
        if phase2_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            logger.info(
                "Phase 2 solved successfully. Extracting final room and invigilator assignments."
            )
            extractor = SolutionExtractor(self.problem, phase2_vars, self.solver)
            extractor.task_context = self.task_context  # Propagate context
            await extractor.extract_full_solution(final_solution, exam_slot_map)
        else:
            logger.error(
                "Phase 2 FAILED to find a feasible packing. The final solution will only contain time assignments from Phase 1."
            )
            # Populate with just Phase 1 data for a partial solution
            self._populate_solution_from_phase1(exam_slot_map, final_solution)

        logger.info("Updating final solution statistics and status...")
        final_solution.update_statistics()
        final_solution.status = (
            SolutionStatus.FEASIBLE
            if final_solution.is_feasible()
            else SolutionStatus.INFEASIBLE
        )
        logger.info(
            f"Final solution status determined as: {final_solution.status.value}"
        )

        logger.info("\n✅ Two-phase decomposition solve complete.")
        return cast(int, phase2_status), final_solution

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
        # --- START OF MODIFICATION ---
        assert self.loop
        progress_callback = CeleryProgressCallback(
            task_context=self.task_context,
            loop=self.loop,
            phase_name="solving_phase_1",
            progress_window=(35, 55),
        )
        status = cast(int, self.solver.Solve(model, progress_callback))
        # --- END OF MODIFICATION ---
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
        """Solves the single, large Phase 2 packing model."""
        logger.info("--- Calling CP-SAT solver for Full Phase 2 ---")
        time_limit = getattr(self.problem, "solver_time_limit_seconds", 300.0)
        self._configure_solver_parameters(time_limit_override=time_limit)
        # --- START OF MODIFICATION ---
        assert self.loop
        progress_callback = CeleryProgressCallback(
            task_context=self.task_context,
            loop=self.loop,
            phase_name="solving_phase_2",
            progress_window=(65, 80),
        )
        status = cast(int, self.solver.Solve(model, progress_callback))
        # --- END OF MODIFICATION ---
        status_name = self.solver.StatusName()
        logger.info(f"Full Phase 2 solver finished with status: {status_name}")
        logger.info(f"  - Objective value: {self.solver.ObjectiveValue()}")
        logger.info(f"  - Wall time: {self.solver.WallTime()}s")
        return status

    def _populate_solution_from_phase1(
        self, exam_slot_map: Dict, solution: TimetableSolution
    ) -> None:
        """Populates a solution object with only time assignments from Phase 1."""
        logger.info(
            "Populating final solution with partial data from Phase 1 due to Phase 2 failure."
        )
        for exam_id, (slot_id, day_date) in exam_slot_map.items():
            asm = ExamAssignment(
                exam_id=exam_id,
                time_slot_id=slot_id,
                assigned_date=day_date,
                status=AssignmentStatus.UNASSIGNED,  # Not fully assigned
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

        num_workers = getattr(self.problem, "solver_num_workers", 24)
        if num_workers:
            params.num_workers = int(num_workers)
        else:
            # Let OR-Tools decide the optimal number of workers
            logger.info("solver_num_workers not set, allowing OR-Tools to auto-detect.")

        if log_progress:
            logger.info(
                f"Solver configured: TimeLimit={params.max_time_in_seconds}s, Workers={params.num_workers}, LogProgress={log_progress}"
            )
