# scheduling_engine/genetic_algorithm/ga_model.py
"""
Defines the core components for the PyGAD-based genetic algorithm pre-filter.

This module is responsible for the fitness evaluation function, a constraint-aware
mutation operator, and a feasible individual initializer, all designed to work
with the PyGAD library.

This version is TRULY CONSTRAINT-AWARE, using a fitness function that heavily
penalizes hard constraints and operators that cannot create infeasible individuals
regarding exam durations.
"""

import math
import random
from typing import List, Dict, Any, Tuple
import logging
from collections import defaultdict
import numpy as np

# Configure logger for detailed output
logger = logging.getLogger(__name__)


def calculate_fitness_pygad(
    solution: np.ndarray, problem_spec: Dict[str, Any]
) -> float:
    """
    MODIFIED for PyGAD: Calculates a single fitness value.
    This version includes a DURATION-AWARE and BIN-PACKING-HEURISTIC capacity check.
    Fitness is calculated as: - ( (hard_violations * 1000) + soft_penalty )
    The goal is to maximize this value (i.e., bring it closer to 0).

    FIXED: The 'max_exams_per_day' check is now correctly treated as a hard violation
    to align with the CP-SAT solver's hard constraints, preventing the GA from
    proposing inherently infeasible solutions.
    """
    individual = list(map(int, solution))
    individual_id = id(individual)
    logger.debug(f"FEVAL id={id(individual)} first5genes={individual[:5]}")

    schedule = individual_to_schedule(individual, problem_spec)
    hard_violations = 0.0
    soft_penalty = 0.0

    # Hard Constraint 0: Completeness
    scheduled_exam_count = len(schedule)
    total_exam_count = len(problem_spec["exam_ids"])
    if scheduled_exam_count < total_exam_count:
        violation_count = total_exam_count - scheduled_exam_count
        hard_violations += violation_count * 1000

    # Combined Student Conflict, Capacity, and Duration check
    student_occupied_slots = defaultdict(list)
    slot_demand = defaultdict(int)
    exams_in_slot = defaultdict(list)
    exam_durations = problem_spec["exam_durations_in_slots"]
    day_to_slots_map = problem_spec["day_to_slots_map"]
    slot_to_day_map = problem_spec["ga_params"].get("slot_to_day_map", {})
    day_slot_indices = {
        day_id: {slot: i for i, slot in enumerate(slots)}
        for day_id, slots in day_to_slots_map.items()
    }
    duration_violation_count = 0
    for exam_id, start_slot_id in schedule.items():
        exam_info = problem_spec["exam_info"][exam_id]
        exam_size = exam_info["size"]
        students = problem_spec["student_exam_map"].get(exam_id, [])
        duration = exam_durations.get(exam_id, 1)
        day_id = slot_to_day_map.get(start_slot_id)

        if not day_id:
            hard_violations += 100
            continue

        day_slots = day_to_slots_map.get(day_id, [])
        start_index = day_slot_indices.get(day_id, {}).get(start_slot_id)

        if start_index is None or start_index + duration > len(day_slots):
            hard_violations += 100
            duration_violation_count += 1
            continue

        occupied_slots_for_exam = []
        for i in range(duration):
            occupied_slot_id = day_slots[start_index + i]
            occupied_slots_for_exam.append(occupied_slot_id)
            slot_demand[occupied_slot_id] += exam_size
            exams_in_slot[occupied_slot_id].append(exam_size)

        for student_id in students:
            student_occupied_slots[student_id].extend(occupied_slots_for_exam)

    # 1. Student Conflicts (Duration-Aware)
    student_conflict_violations = 0
    for student_id, slots in student_occupied_slots.items():
        if len(set(slots)) < len(slots):
            conflict_count = len(slots) - len(set(slots))
            student_conflict_violations += conflict_count
    hard_violations += student_conflict_violations

    # 2. Capacity Heuristics
    for slot_id, demand in slot_demand.items():
        total_capacity = problem_spec["slot_capacity_map"].get(slot_id, 0)
        if demand > total_capacity:
            hard_violations += math.ceil((demand - total_capacity) / 100)

    all_room_capacities = sorted(
        [r["capacity"] for r in problem_spec["room_info"].values()], reverse=True
    )
    num_rooms = len(all_room_capacities)
    for slot_id, exam_sizes in exams_in_slot.items():
        if not exam_sizes or num_rooms == 0:
            continue
        sorted_exams = sorted(exam_sizes, reverse=True)
        if len(sorted_exams) > num_rooms:
            hard_violations += (len(sorted_exams) - num_rooms) * 10
            continue
        if sorted_exams[0] > all_room_capacities[0]:
            hard_violations += 10
        for k in range(1, min(len(sorted_exams), num_rooms) + 1):
            if sum(sorted_exams[:k]) > sum(all_room_capacities[:k]):
                hard_violations += 5
                break

    # 3. Max Exams Per Day (as a Hard Violation)
    student_exam_start_slots = defaultdict(list)
    for exam_id, start_slot_id in schedule.items():
        students = problem_spec["student_exam_map"].get(exam_id, [])
        for student_id in students:
            student_exam_start_slots[student_id].append(start_slot_id)

    student_day_counts = defaultdict(lambda: defaultdict(int))
    for student_id, slots in student_exam_start_slots.items():
        for slot_id in slots:
            day_id = slot_to_day_map.get(slot_id)
            if day_id:
                student_day_counts[student_id][day_id] += 1

    max_exams_per_day = problem_spec["ga_params"].get("max_exams_per_day", 2)
    for student_id, day_counts in student_day_counts.items():
        for day, count in day_counts.items():
            if count > max_exams_per_day:
                # Add a significant penalty for each exam over the limit.
                hard_violations += (count - max_exams_per_day) * 50

    total_soft_penalty = 0
    soft_penalty = total_soft_penalty

    # Final fitness value (higher is better)
    final_fitness = -((hard_violations * 1000) + soft_penalty)
    logger.debug(
        f"[Fitness Eval ID: {individual_id}] Complete. H-Violations: {hard_violations}, S-Penalty: {soft_penalty}, Final Fitness: {final_fitness}"
    )
    return final_fitness


def mutate_feasible_reassign_pygad(
    offspring: np.ndarray, ga_instance, problem_spec: Dict[str, Any]
) -> np.ndarray:
    """
    NEW for PyGAD: Constraint-aware mutation.
    An exam (gene) is only ever mutated to another FEASIBLE start slot.
    """
    exam_ids = problem_spec["exam_ids"]
    feasible_slots_per_exam = problem_spec["feasible_slots_per_exam"]
    mutation_prob = ga_instance.mutation_probability

    for chromosome_idx in range(offspring.shape[0]):
        for gene_idx in range(offspring.shape[1]):
            if random.random() < mutation_prob:
                exam_id = exam_ids[gene_idx]
                if feasible_slots_per_exam.get(exam_id):
                    new_slot_index = random.choice(feasible_slots_per_exam[exam_id])
                    offspring[chromosome_idx, gene_idx] = new_slot_index
    return offspring


def create_feasible_individual_pygad(problem_spec: Dict[str, Any]) -> List[int]:
    """
    NEW for PyGAD: Constraint-aware individual initializer.
    Creates a single individual where each exam is assigned a random feasible start slot.
    """
    exam_ids = problem_spec["exam_ids"]
    feasible_slots = problem_spec["feasible_slots_per_exam"]
    genes = []
    for exam_id in exam_ids:
        if feasible_slots.get(exam_id):
            chosen_slot = random.choice(feasible_slots[exam_id])
            genes.append(chosen_slot)
        else:
            logger.error(
                f"FATAL: In create_feasible_individual, Exam {exam_id} has NO feasible start slots."
            )
            genes.append(-1)  # Placeholder that will be heavily penalized
    return genes


def individual_to_schedule(
    individual: List[int], problem_spec: Dict[str, Any]
) -> Dict[Any, Any]:
    """
    Converts a GA individual (list of timeslot indices) to a schedule dictionary.
    This helper function is compatible with both deap and PyGAD.
    """
    logger.debug(f"Converting individual {id(individual)} to schedule format...")
    exam_ids = problem_spec["exam_ids"]
    index_to_timeslot_id = problem_spec["index_to_timeslot_id"]

    schedule = {
        exam_ids[i]: index_to_timeslot_id[individual[i]]
        for i in range(len(individual))
        if individual[i] in index_to_timeslot_id
    }
    logger.debug(f"Conversion complete. Schedule contains {len(schedule)} assignments.")
    return schedule
