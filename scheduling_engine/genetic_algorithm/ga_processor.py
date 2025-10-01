# scheduling_engine/genetic_algorithm/ga_processor.py
"""
Orchestrates the Genetic Algorithm pre-filtering process.

This module provides the GAProcessor class, which manages the entire GA
lifecycle from population initialization to result extraction. It uses the
DEAP model defined in `ga_model` to run the evolutionary algorithm.

After the evolution completes, it post-processes the top-performing
individuals to generate:
1. `viable_y_vars`: A pruned set of (exam, room, slot) assignments.
2. `viable_u_vars`: A pruned set of (invigilator, exam, room, slot) assignments.
3. `search_hints`: High-confidence exam-to-slot assignments for the CP-SAT solver.
"""

import time
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Any, Set, Tuple, Optional
import logging
import platform  # MODIFIED: Import platform to check OS

# --- START OF MODIFICATION: ADD MULTIPROCESSING FOR PARALLELIZATION ---
import multiprocessing

# --- END OF MODIFICATION ---

from deap import algorithms, tools
import numpy as np

from .ga_model import create_toolbox, individual_to_schedule

logger = logging.getLogger(__name__)


@dataclass
class GAInput:
    """Data contract for inputs to the GAProcessor."""

    exam_ids: List[Any]
    timeslot_ids: List[Any]
    room_info: Dict[Any, Dict]  # room_id -> {id, capacity, features}
    exam_info: Dict[Any, Dict]  # exam_id -> {id, size, required_features}
    invigilator_info: Dict[Any, Dict]  # invigilator_id -> {id, availability_by_slot}
    student_exam_map: Dict[Any, List[Any]]  # student_id -> [exam_ids]
    ga_params: Dict[str, Any]


@dataclass
class GAResult:
    """Data contract for outputs from the GAProcessor."""

    viable_y_vars: Set[Tuple] = field(default_factory=set)
    viable_u_vars: Set[Tuple] = field(default_factory=set)
    search_hints: Dict[Any, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)


class GAProcessor:
    """Orchestrates the GA run and post-processes results."""

    def __init__(self, ga_input: GAInput):
        self.ga_input = ga_input
        self.ga_params = ga_input.ga_params
        self.problem_spec = self._build_problem_spec(ga_input)

        # Set seed for reproducibility
        seed = self.ga_params.get("seed")
        if seed is not None:
            random.seed(seed)

    def _build_problem_spec(self, ga_input: GAInput) -> Dict[str, Any]:
        """Consolidates GA input into a single spec dict for the fitness function."""
        # Pre-calculate total room capacity per timeslot for faster penalty checks
        slot_capacity_map = defaultdict(int)
        for room in ga_input.room_info.values():
            # Assuming all rooms are available in all slots for this simplified GA
            for slot_id in ga_input.timeslot_ids:
                slot_capacity_map[slot_id] += room.get("capacity", 0)

        return {
            "exam_ids": ga_input.exam_ids,
            "timeslot_ids": ga_input.timeslot_ids,
            "exam_info": ga_input.exam_info,
            "room_info": ga_input.room_info,
            "invigilator_info": ga_input.invigilator_info,
            "student_exam_map": ga_input.student_exam_map,
            "slot_capacity_map": slot_capacity_map,
            "ga_params": self.ga_params,  # Pass GA params through
        }

    def run(self) -> GAResult:
        """
        Executes the full GA lifecycle and returns the processed results.
        MODIFIED to conditionally use multiprocessing to avoid spawn errors on Windows.
        """
        start_time = time.time()
        logger.info("Starting GA pre-filtering process...")

        # 1. Setup DEAP
        toolbox = create_toolbox(self.problem_spec, self.ga_params)
        pop_size = self.ga_params.get("pop_size", 200)
        population = toolbox.population(n=pop_size)
        hof = tools.HallOfFame(10)  # Store the top 10 individuals

        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", lambda x: np.mean([val[0] for val in x]))
        stats.register("min", lambda x: np.min([val[0] for val in x]))
        stats.register("max", lambda x: np.max([val[0] for val in x]))

        # 2. Run Evolutionary Algorithm
        generations = self.ga_params.get("generations", 150)
        cx_prob = self.ga_params.get("cx_prob", 0.6)
        mut_prob = self.ga_params.get("mut_prob", 0.2)

        # --- START OF FIX: Conditionally use multiprocessing ---
        # On Windows, using multiprocessing.Pool inside a Celery worker can
        # lead to ModuleNotFoundError. We fall back to sequential execution.
        if platform.system() == "Windows":
            logger.warning(
                "Running on Windows: GA evaluation will run sequentially to avoid spawn errors."
            )
            # Run sequentially (this is DEAP's default if no map is registered)
            final_pop, logbook = algorithms.eaSimple(
                population,
                toolbox,
                cxpb=cx_prob,
                mutpb=mut_prob,
                ngen=generations,
                stats=stats,
                halloffame=hof,
                verbose=False,
            )
        else:
            logger.info("Using multiprocessing for parallel GA evaluation.")
            # Use a multiprocessing pool for parallel evaluation on other OS
            with multiprocessing.Pool() as pool:
                toolbox.register("map", pool.map)
                # The algorithm MUST be called within the 'with' block
                final_pop, logbook = algorithms.eaSimple(
                    population,
                    toolbox,
                    cxpb=cx_prob,
                    mutpb=mut_prob,
                    ngen=generations,
                    stats=stats,
                    halloffame=hof,
                    verbose=False,
                )
        # --- END OF FIX ---

        run_duration = time.time() - start_time
        best_fitness = hof[0].fitness.values[0] if hof else 0.0
        logger.info(
            f"GA run finished in {run_duration:.2f}s. Best fitness: {best_fitness:.4f}"
        )

        # 3. Post-process top individuals
        top_n_pct = self.ga_params.get("top_n_pct", 0.1)  # Default to top 10%
        num_to_select = max(1, int(pop_size * top_n_pct))
        top_individuals = tools.selBest(final_pop, k=num_to_select)

        viable_y_vars, viable_u_vars = self._build_viable_sets(top_individuals)
        search_hints = self._generate_search_hints(top_individuals)

        # 4. Compile and return results
        result = GAResult(
            viable_y_vars=viable_y_vars,
            viable_u_vars=viable_u_vars,
            search_hints=search_hints,
            stats={
                "runtime_seconds": run_duration,
                "best_fitness": best_fitness,
                "generations_run": generations,
                "viable_y_vars_count": len(viable_y_vars),
                "viable_u_vars_count": len(viable_u_vars),
                "search_hints_count": len(search_hints),
            },
        )
        return result

    def _build_viable_sets(
        self, top_individuals: List[Any]
    ) -> Tuple[Set[Tuple], Set[Tuple]]:
        """
        Generates viable Y and U variables from the top individuals.
        MODIFIED to include a safety net ensuring all exams have at least one assignment.
        """
        viable_y = set()
        viable_u = set()

        # Sort rooms by capacity once to efficiently find suitable rooms
        sorted_rooms = sorted(
            self.problem_spec["room_info"].values(),
            key=lambda r: r["capacity"],
            reverse=True,
        )

        for ind in top_individuals:
            schedule = individual_to_schedule(ind, self.problem_spec)
            invig_usage = defaultdict(set)

            for exam_id, slot_id in schedule.items():
                exam_size = self.problem_spec["exam_info"][exam_id]["size"]
                # Find the smallest room that fits the exam to improve utilization
                chosen_room = None
                for room in reversed(sorted_rooms):  # Iterate from smallest to largest
                    if room["capacity"] >= exam_size:
                        chosen_room = room
                        break
                # If no room is large enough, pick the largest available one
                if not chosen_room:
                    chosen_room = sorted_rooms[0] if sorted_rooms else None

                if not chosen_room:
                    continue

                room_id = chosen_room["id"]
                viable_y.add((exam_id, room_id, slot_id))

                # Simple invigilator assignment heuristic
                chosen_invig = None
                available_invigs = list(self.problem_spec["invigilator_info"].keys())
                random.shuffle(available_invigs)  # Avoid bias
                for invig_id in available_invigs:
                    invig = self.problem_spec["invigilator_info"][invig_id]
                    if (
                        slot_id in invig["availability_by_slot"]
                        and slot_id not in invig_usage[invig_id]
                    ):
                        chosen_invig = invig
                        break

                if chosen_invig:
                    invig_id = chosen_invig["id"]
                    viable_u.add((invig_id, exam_id, room_id, slot_id))
                    invig_usage[invig_id].add(slot_id)

        # --- START OF FIX: SAFETY NET ---
        # 1. Ensure every exam has at least one viable Y-var.
        assigned_exams = {y[0] for y in viable_y}
        all_exams = set(self.problem_spec["exam_ids"])
        unassigned_exams = all_exams - assigned_exams

        if unassigned_exams:
            logger.warning(
                f"GA Safety Net: Found {len(unassigned_exams)} exams with no viable assignments. Creating fallbacks."
            )
            fallback_slot = self.problem_spec["timeslot_ids"][0]
            fallback_room = sorted_rooms[0] if sorted_rooms else None

            if fallback_room:
                for exam_id in unassigned_exams:
                    viable_y.add((exam_id, fallback_room["id"], fallback_slot))

        # 2. Ensure every viable Y-var has at least one viable U-var.
        y_without_u = {(y[0], y[1], y[2]) for y in viable_y} - {
            (u[1], u[2], u[3]) for u in viable_u
        }
        if y_without_u:
            logger.warning(
                f"GA Safety Net: Found {len(y_without_u)} Y-vars with no invigilator. Creating fallbacks."
            )
            fallback_invig_id = next(iter(self.problem_spec["invigilator_info"]), None)

            if fallback_invig_id:
                for exam_id, room_id, slot_id in y_without_u:
                    viable_u.add((fallback_invig_id, exam_id, room_id, slot_id))
        # --- END OF FIX ---

        return viable_y, viable_u

    def _generate_search_hints(self, top_individuals: List[Any]) -> Dict[Any, Any]:
        """
        Generates high-confidence search hints for the CP-SAT solver.
        """
        hints = {}
        hint_threshold = self.ga_params.get("hint_threshold", 0.9)
        num_individuals = len(top_individuals)
        if num_individuals == 0:
            return {}

        exam_slot_freq = defaultdict(lambda: defaultdict(int))
        for ind in top_individuals:
            schedule = individual_to_schedule(ind, self.problem_spec)
            for exam_id, slot_id in schedule.items():
                exam_slot_freq[exam_id][slot_id] += 1

        for exam_id, slot_counts in exam_slot_freq.items():
            for slot_id, count in slot_counts.items():
                confidence = count / num_individuals
                if confidence >= hint_threshold:
                    # CP-SAT hints are exam -> slot. If multiple slots are high-confidence,
                    # we pick the most frequent one.
                    current_hint_confidence = hints.get(exam_id, {}).get(
                        "confidence", 0
                    )
                    if confidence > current_hint_confidence:
                        hints[exam_id] = {"slot_id": slot_id, "confidence": confidence}

        # Flatten hints to the required format: {exam_id: slot_id}
        flat_hints = {exam_id: data["slot_id"] for exam_id, data in hints.items()}
        return flat_hints
