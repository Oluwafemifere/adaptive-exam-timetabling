# scheduling_engine/genetic_algorithm/ga_processor.py
"""
Orchestrates the Genetic Algorithm pre-filtering process using PyGAD.

This module provides the GAProcessor class, which manages the entire GA
lifecycle from population initialization to result extraction. It uses the
components defined in `ga_model` to run the evolutionary algorithm with PyGAD.

After the evolution completes, it post-processes the top-performing
individuals to generate pruned start time variables (X-vars) and search hints
for the CP-SAT solver.
"""

import time
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Any, Set, Tuple, Optional
import logging
import platform
import math
import pygad
import numpy as np

from .ga_model import (
    calculate_fitness_pygad,
    mutate_feasible_reassign_pygad,
    create_feasible_individual_pygad,
    individual_to_schedule,
)

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class GAInput:
    """Data contract for inputs to the GAProcessor."""

    exam_ids: List[Any]
    timeslot_ids: List[Any]
    room_info: Dict[Any, Dict]
    exam_info: Dict[Any, Dict]
    invigilator_info: Dict[Any, Dict]
    student_exam_map: Dict[Any, List[Any]]
    ga_params: Dict[str, Any]


@dataclass
class GAResult:
    """Data contract for outputs from the GAProcessor."""

    promising_x_vars: Set[Tuple] = field(
        default_factory=set
    )  # CHANGED: This is the new output
    search_hints: Dict[Any, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)


class GAProcessor:
    """Orchestrates the GA run with PyGAD and post-processes results."""

    def __init__(self, ga_input: GAInput):
        """Initializes the GAProcessor."""
        logger.info("Initializing GAProcessor with PyGAD backend...")
        self.ga_input = ga_input
        self.ga_params = ga_input.ga_params

        seed = self.ga_params.get("seed")
        if seed is not None:
            logger.info(f"Setting random seed to: {seed}")
            random.seed(seed)
            np.random.seed(seed)
        else:
            logger.info("No random seed provided.")

        logger.info("Building and validating problem specification...")
        self.problem_spec = self._build_problem_spec(ga_input)
        logger.info("Problem specification built successfully.")

    def _build_problem_spec(self, ga_input: GAInput) -> Dict[str, Any]:
        """
        Consolidates GA input and pre-calculates feasible start slots.
        This function is the first line of defense, ensuring the problem is
        theoretically solvable by the GA before it even begins.
        """
        logger.debug("--- Building Problem Specification ---")
        slot_capacity_map = defaultdict(int)
        for room_id, room in ga_input.room_info.items():
            for slot_id in ga_input.timeslot_ids:
                slot_capacity_map[slot_id] += room.get("capacity", 0)

        for eid, einfo in ga_input.exam_info.items():
            if "duration_minutes" not in einfo:
                einfo["duration_minutes"] = 180

        slot_duration = self.ga_params.get("slot_duration_minutes", 60)
        exam_durations_in_slots = {
            eid: math.ceil(einfo.get("duration_minutes", slot_duration) / slot_duration)
            for eid, einfo in ga_input.exam_info.items()
        }

        day_to_slots_map = defaultdict(list)
        slot_to_day_map = self.ga_params.get("slot_to_day_map", {})
        timeslot_ids_list = ga_input.timeslot_ids
        timeslot_id_to_index = {ts_id: i for i, ts_id in enumerate(timeslot_ids_list)}
        index_to_timeslot_id = {i: ts_id for i, ts_id in enumerate(timeslot_ids_list)}

        for slot_id in timeslot_ids_list:
            day_id = slot_to_day_map.get(slot_id)
            if day_id:
                day_to_slots_map[day_id].append(slot_id)

        for day_id, slots in day_to_slots_map.items():
            day_to_slots_map[day_id] = sorted(
                slots, key=lambda s: timeslot_id_to_index.get(s, float("inf"))
            )

        logger.info(
            "Calculating all theoretically feasible start slots for each exam..."
        )
        feasible_slots_per_exam = defaultdict(list)
        for exam_id in ga_input.exam_ids:
            duration = exam_durations_in_slots.get(exam_id, 1)
            for day_id, day_slots in day_to_slots_map.items():
                if not day_slots or len(day_slots) < duration:
                    continue
                for i in range(len(day_slots) - duration + 1):
                    start_slot_id = day_slots[i]
                    start_slot_index = timeslot_id_to_index[start_slot_id]
                    feasible_slots_per_exam[exam_id].append(start_slot_index)

        logger.info("--- CRITICAL: Performing upfront infeasibility check ---")
        unplaceable_exams = [
            eid for eid in ga_input.exam_ids if not feasible_slots_per_exam.get(eid)
        ]
        if unplaceable_exams:
            error_msg = f"CRITICAL GA PRE-CHECK FAILED: {len(unplaceable_exams)} exams have NO feasible start slots."
            logger.error(error_msg)
            raise ValueError(error_msg)
        else:
            logger.info("SUCCESS: All exams have at least one feasible start slot.")

        return {
            "exam_ids": ga_input.exam_ids,
            "timeslot_ids": timeslot_ids_list,
            "exam_info": ga_input.exam_info,
            "room_info": ga_input.room_info,
            "invigilator_info": ga_input.invigilator_info,
            "student_exam_map": ga_input.student_exam_map,
            "slot_capacity_map": slot_capacity_map,
            "ga_params": self.ga_params,
            "exam_durations_in_slots": exam_durations_in_slots,
            "day_to_slots_map": day_to_slots_map,
            "feasible_slots_per_exam": feasible_slots_per_exam,
            "timeslot_id_to_index": timeslot_id_to_index,
            "index_to_timeslot_id": index_to_timeslot_id,
        }

    def _create_initial_population(self, pop_size: int) -> np.ndarray:
        """Creates an initial population of feasible individuals."""
        logger.info(
            f"Step 2: Initializing population with {pop_size} feasible individuals..."
        )
        population = [
            create_feasible_individual_pygad(self.problem_spec) for _ in range(pop_size)
        ]
        return np.array(population)

    def run(self) -> GAResult:
        """Executes the full GA lifecycle using PyGAD and returns the processed results."""
        start_time = time.time()
        logger.info("=============================================")
        logger.info("===  Starting Constraint-Aware GA Process ===")
        logger.info("===          (Backend: PyGAD)           ===")
        logger.info("=============================================")

        # --- GA Parameters ---
        pop_size = self.ga_params.get("pop_size", 200)
        generations = self.ga_params.get("generations", 150)
        cx_prob = self.ga_params.get("cx_prob", 0.7)
        mut_prob = self.ga_params.get("mut_prob", 0.2)
        num_parents_mating = int(pop_size * 0.25)

        logger.info(
            f"GA Parameters: Population Size={pop_size}, Generations={generations}, Crossover P={cx_prob}, Mutation P={mut_prob}"
        )

        # --- Step 1 & 2: Create initial population and define fitness/mutation functions ---
        initial_population = self._create_initial_population(pop_size)

        def fitness_func_wrapper(ga_instance, solution, solution_idx):
            return calculate_fitness_pygad(solution, self.problem_spec)

        def mutation_func_wrapper(offspring, ga_instance):
            return mutate_feasible_reassign_pygad(
                offspring, ga_instance, self.problem_spec
            )

        # --- Step 3: Configure and run the PyGAD instance ---
        logger.info("Step 3: Configuring PyGAD instance...")
        ga_instance = pygad.GA(
            num_generations=generations,
            num_parents_mating=num_parents_mating,
            initial_population=initial_population,
            fitness_func=fitness_func_wrapper,
            parent_selection_type="sss",
            crossover_type="two_points",
            crossover_probability=cx_prob,
            mutation_type=mutation_func_wrapper,
            mutation_probability=mut_prob,
            allow_duplicate_genes=True,
            stop_criteria=[f"saturate_{int(generations * 0.2)}"],
        )

        logger.info(
            f"Step 4: Starting PyGAD evolution for {generations} generations..."
        )
        ga_instance.run()
        logger.info("GA evolution has completed.")

        run_duration = time.time() - start_time
        solution, solution_fitness, solution_idx = ga_instance.best_solution()
        best_fitness_val = solution_fitness

        # --- GA Run Summary ---
        logger.info("--- GA Run Summary ---")
        logger.info(f"Total execution time: {run_duration:.2f} seconds.")
        logger.info(f"Best Fitness achieved: {best_fitness_val}")

        # --- Post-processing ---
        logger.info("--- Post-processing Top Individuals ---")
        top_n_pct = self.ga_params.get("top_n_pct", 0.2)
        num_to_select = max(1, int(pop_size * top_n_pct))

        logger.info(
            f"Step 5: Selecting top {top_n_pct*100}% of final population ({num_to_select} individuals) for analysis."
        )

        final_population = getattr(ga_instance, "population", np.array([]))
        final_fitness = getattr(ga_instance, "last_generation_fitness", np.array([]))

        if final_fitness is None or len(final_fitness) == 0:
            logger.warning("Final fitness values are empty. Using best solution only.")
            sorted_indices = [solution_idx]
        else:
            sorted_indices = np.argsort(final_fitness)[::-1]

        top_individuals = [
            final_population[i]
            for i in sorted_indices[:num_to_select]
            if i < len(final_population)
        ]

        logger.info(
            "Step 6: Building promising start time variables (X-vars) from top individuals..."
        )
        promising_x_vars = self._build_promising_start_times(top_individuals)

        logger.info(
            "Step 7: Generating high-confidence search hints for the CP-SAT solver..."
        )
        search_hints = self._generate_search_hints(top_individuals)

        ga_result_stats = {
            "runtime_seconds": run_duration,
            "best_fitness": best_fitness_val,
            "generations_run": ga_instance.generations_completed,
            "promising_x_vars_count": len(promising_x_vars),
            "search_hints_count": len(search_hints),
        }

        logger.info("--- GA Process Finished ---")
        logger.info(f"Final Stats: {ga_result_stats}")

        return GAResult(
            promising_x_vars=promising_x_vars,
            search_hints=search_hints,
            stats=ga_result_stats,
        )

    def _build_promising_start_times(self, top_individuals: List[Any]) -> Set[Tuple]:
        """
        MODIFIED: Generates a set of promising start time assignments (exam_id, slot_id)
        by observing the start times assigned in the top-performing individuals.
        This guides the CP-solver without overly constraining room choices.
        """
        promising_x = set()
        for ind in top_individuals:
            schedule = individual_to_schedule(list(ind), self.problem_spec)
            for exam_id, slot_id in schedule.items():
                promising_x.add((exam_id, slot_id))

        logger.info(
            f"Generated {len(promising_x)} unique promising X_vars (exam, slot)."
        )

        self._apply_safety_net(promising_x)
        return promising_x

    def _apply_safety_net(self, promising_x: Set[Tuple]):
        """
        MODIFIED: This function is now an ALARM. If it triggers, it means the GA
        failed its primary mission of producing at least one start time for every exam.
        """
        assigned_exams = {x[0] for x in promising_x}
        all_exams = set(self.problem_spec["exam_ids"])
        unassigned_exams = all_exams - assigned_exams

        if unassigned_exams:
            logger.error(
                f"GA SAFETY NET ALARM: The GA process failed to produce assignments for "
                f"{len(unassigned_exams)} exams: {unassigned_exams}. The CP-SAT problem may be made infeasible."
            )
        else:
            logger.info(
                "Safety Net: OK. All exams have at least one viable start time from the GA."
            )

    def _generate_search_hints(self, top_individuals: List[Any]) -> Dict[Any, Any]:
        """Generates high-confidence search hints for the CP-SAT solver."""
        hints = {}
        # --- START OF FIX: Make hint_threshold configurable ---
        hint_threshold = self.ga_params.get("hint_threshold", 0.9)
        # --- END OF FIX ---
        num_individuals = len(top_individuals)

        if num_individuals == 0:
            logger.warning("Cannot generate hints: list of top individuals is empty.")
            return {}

        exam_slot_freq = defaultdict(lambda: defaultdict(int))
        for ind in top_individuals:
            schedule = individual_to_schedule(list(ind), self.problem_spec)
            for exam_id, slot_id in schedule.items():
                exam_slot_freq[exam_id][slot_id] += 1

        for exam_id, slot_counts in exam_slot_freq.items():
            if not slot_counts:
                continue
            best_slot, max_count = max(slot_counts.items(), key=lambda item: item[1])
            confidence = max_count / num_individuals
            if confidence >= hint_threshold:
                hints[exam_id] = best_slot
                logger.info(
                    f"  -> CREATING HINT for Exam {exam_id} -> Slot {best_slot} (Confidence: {confidence:.2f})"
                )

        logger.info(f"Generated a total of {len(hints)} search hints.")
        return hints
