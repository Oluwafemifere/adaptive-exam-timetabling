# scheduling_engine/genetic_algorithm/ga_model.py
"""
Defines the core DEAP model for the genetic algorithm pre-filter.

This module is responsible for setting up the genetic algorithm's fundamental
components using the DEAP library. It defines the structure of individuals
(chromosomes), the fitness evaluation function based on constraint penalties,
and the genetic operators (selection, crossover, mutation).

The design prioritizes speed and simplicity, focusing only on hard constraint
violations to quickly guide the search toward feasible regions of the solution space.
"""

import random
from typing import List, Dict, Any, Tuple

from deap import base, creator, tools
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# 1. Setup Fitness and Individual Structures at the module level.
#    Fitness aims to be maximized (target is 1.0).
creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.FitnessMax)


def penalty_fitness(
    individual: List[int], problem_spec: Dict[str, Any]
) -> Tuple[float,]:
    """
    Calculates the fitness of an individual based on a penalty system.
    MODIFIED to include more constraint-aware penalties and optimized loops.
    """
    schedule = individual_to_schedule(individual, problem_spec)
    total_penalty = 0.0
    weights = problem_spec.get("penalty_weights", {})

    # Penalty weights with defaults
    student_conflict_weight = weights.get("student_conflict", 1000.0)
    room_capacity_weight = weights.get("room_over_capacity", 100.0)
    invigilator_shortage_weight = weights.get("invigilator_shortage", 500.0)
    max_exams_per_day_weight = weights.get("max_exams_per_day", 750.0)

    # --- START OF OPTIMIZATION: MERGED STUDENT-RELATED PENALTIES ---
    student_conflict_penalty = 0
    max_exams_per_day_penalty = 0
    ga_params = problem_spec.get("ga_params", {})
    slot_to_day_map = ga_params.get("slot_to_day_map", {})
    max_exams_per_day = ga_params.get("max_exams_per_day", 2)

    for student_id, exam_ids in problem_spec.get("student_exam_map", {}).items():
        # Get the scheduled slots for this student's exams
        slots_for_student = [schedule.get(eid) for eid in exam_ids if eid in schedule]
        if not slots_for_student:
            continue

        # 1. Student Conflict Penalty calculation
        slot_counts = defaultdict(int)
        for slot in slots_for_student:
            if slot is not None:
                slot_counts[slot] += 1
        for count in slot_counts.values():
            if count > 1:
                student_conflict_penalty += count - 1

        # 2. Max Exams Per Student Per Day Penalty calculation
        if slot_to_day_map:
            student_day_counts = defaultdict(int)
            for slot_id in slots_for_student:
                if slot_id and slot_id in slot_to_day_map:
                    day_id = slot_to_day_map[slot_id]
                    student_day_counts[day_id] += 1
            for day_count in student_day_counts.values():
                if day_count > max_exams_per_day:
                    max_exams_per_day_penalty += day_count - max_exams_per_day

    total_penalty += student_conflict_weight * student_conflict_penalty
    total_penalty += max_exams_per_day_weight * max_exams_per_day_penalty
    # --- END OF OPTIMIZATION ---

    # 3. Room Capacity Penalty (existing)
    slot_demand = defaultdict(int)
    for exam_id, slot_id in schedule.items():
        exam_size = problem_spec["exam_info"][exam_id]["size"]
        slot_demand[slot_id] += exam_size

    for slot_id, demand in slot_demand.items():
        total_capacity_in_slot = problem_spec["slot_capacity_map"].get(slot_id, 0)
        if demand > total_capacity_in_slot:
            total_penalty += room_capacity_weight * (demand - total_capacity_in_slot)

    # 4. Invigilator Shortage Heuristic Penalty (existing)
    invigilator_shortage_penalty = 0
    num_invigilators = len(problem_spec.get("invigilator_info", {}))
    if num_invigilators > 0:
        exams_per_slot = defaultdict(int)
        for slot_id in schedule.values():
            exams_per_slot[slot_id] += 1

        for num_exams in exams_per_slot.values():
            if num_exams > num_invigilators:  # Simple heuristic
                invigilator_shortage_penalty += num_exams - num_invigilators
        total_penalty += invigilator_shortage_weight * invigilator_shortage_penalty

    return (1.0 / (1.0 + total_penalty),)


def mut_random_reassign(
    individual: List[int], indpb: float, timeslot_indices: List[int]
) -> Tuple[List[int],]:
    """
    Custom mutation operator that reassigns a gene to a new random timeslot.

    Args:
        individual: The individual to be mutated.
        indpb: The independent probability for each attribute to be mutated.
        timeslot_indices: A list of valid timeslot indices to choose from.

    Returns:
        A tuple containing the mutated individual.
    """
    for i in range(len(individual)):
        if random.random() < indpb:
            individual[i] = random.choice(timeslot_indices)
    return (individual,)


def create_toolbox(
    problem_spec: Dict[str, Any], ga_params: Dict[str, Any]
) -> base.Toolbox:
    """
    Creates and configures a DEAP toolbox for the GA pre-filter.

    Args:
        problem_spec: Dictionary with problem data (exam_ids, timeslot_ids, etc.).
        ga_params: Dictionary with GA hyperparameters (cx_prob, mut_prob, etc.).

    Returns:
        A fully configured DEAP toolbox instance.
    """
    # Initialize Toolbox
    toolbox = base.Toolbox()
    num_exams = len(problem_spec["exam_ids"])
    timeslot_indices = list(range(len(problem_spec["timeslot_ids"])))

    # Register Genetic Operators and Population Initializers
    # Attribute generator: a random timeslot index for each gene (exam).
    toolbox.register("attr_timeslot", random.choice, timeslot_indices)

    # Individual and population initializers.
    toolbox.register(
        "individual",
        tools.initRepeat,
        creator.Individual,
        toolbox.attr_timeslot,
        n=num_exams,
    )
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    # Evaluation (fitness) function.
    toolbox.register("evaluate", penalty_fitness, problem_spec=problem_spec)

    # Core genetic operators.
    # Rationale for choices:
    # - cxTwoPoint: Simple, effective crossover for position-based encodings.
    # - selTournament: Reduces premature convergence compared to simpler methods.
    toolbox.register("mate", tools.cxTwoPoint)
    toolbox.register(
        "mutate",
        mut_random_reassign,
        indpb=ga_params.get("mut_indpb", 0.02),
        timeslot_indices=timeslot_indices,
    )
    toolbox.register(
        "select", tools.selTournament, tournsize=ga_params.get("tournsize", 3)
    )

    return toolbox


def individual_to_schedule(
    individual: List[int], problem_spec: Dict[str, Any]
) -> Dict[Any, Any]:
    """
    Converts a GA individual (list of timeslot indices) to a more readable
    schedule dictionary mapping exam_id to timeslot_id.

    Args:
        individual: The GA individual (chromosome).
        problem_spec: Dictionary containing mappings from indices to IDs.

    Returns:
        A dictionary representing the exam schedule.
    """
    exam_ids = problem_spec["exam_ids"]
    timeslot_ids = problem_spec["timeslot_ids"]
    schedule = {
        exam_ids[i]: timeslot_ids[individual[i]] for i in range(len(individual))
    }
    return schedule
