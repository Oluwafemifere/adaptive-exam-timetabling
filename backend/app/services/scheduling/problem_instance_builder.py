# backend/app/services/scheduling/problem_instance_builder.py
"""
Problem instance builder that converts database data into CP-SAT and GA
data structures for optimization algorithms.
"""
import logging
from typing import Dict, List, Any, Tuple, cast
from dataclasses import dataclass, field
from collections import defaultdict
import random

from .enhanced_engine_connector import ProblemInstance

logger = logging.getLogger(__name__)


@dataclass
class CPSATVariables:
    """Container for CP-SAT decision variables"""

    # exam_assignments[exam_id][room_id][timeslot_id] = BoolVar
    exam_assignments: Dict[str, Dict[str, Dict[str, Any]]] = field(default_factory=dict)

    # staff_assignments[staff_id][exam_id][timeslot_id] = BoolVar
    staff_assignments: Dict[str, Dict[str, Dict[str, Any]]] = field(
        default_factory=dict
    )

    # Helper lookup variables
    exam_scheduled: Dict[str, Any] = field(default_factory=dict)  # exam_id -> BoolVar
    room_occupied: Dict[str, Dict[str, Any]] = field(
        default_factory=dict
    )  # room_id -> {timeslot_id -> BoolVar}


@dataclass
class CPSATModel:
    """Complete CP-SAT model with variables and constraints"""

    model: Any  # cp_model.CpModel
    variables: CPSATVariables
    objective_vars: List[Any] = field(default_factory=list)
    constraint_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GAChromosome:
    """Genetic Algorithm chromosome representation"""

    # exam_assignments[exam_id] = {"room_id": str, "timeslot_id": str, "staff_ids": List[str]}
    exam_assignments: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    fitness_score: float = 0.0
    constraint_violations: Dict[str, int] = field(default_factory=dict)

    def copy(self) -> "GAChromosome":
        """Create a deep copy of the chromosome"""
        new_chromosome = GAChromosome()
        new_chromosome.exam_assignments = {
            exam_id: assignment.copy()
            for exam_id, assignment in self.exam_assignments.items()
        }
        new_chromosome.fitness_score = self.fitness_score
        new_chromosome.constraint_violations = self.constraint_violations.copy()
        return new_chromosome


class ProblemInstanceBuilder:
    """
    Builds CP-SAT and GA problem representations from ProblemInstance.
    Handles conversion between different algorithm representations.
    """

    def __init__(self, connector):
        self.connector = connector

    async def build_cpsat_model(
        self, problem_instance: ProblemInstance, constraints_config: Dict[str, Any]
    ) -> CPSATModel:
        """
        Build complete CP-SAT model from problem instance.
        """
        try:
            from ortools.sat.python import cp_model

            logger.info("Building CP-SAT model...")

            # Initialize model and variables
            model = cp_model.CpModel()
            variables = CPSATVariables()

            # Create decision variables
            await self._create_cpsat_variables(model, variables, problem_instance)

            # Add hard constraints
            await self._add_hard_constraints(
                model, variables, problem_instance, constraints_config
            )

            # Add soft constraints as objectives
            objective_vars = await self._add_soft_constraints(
                model, variables, problem_instance, constraints_config
            )

            # Set up objective function
            if objective_vars:
                model.Maximize(sum(objective_vars))

            constraint_info = {
                "num_variables": len(variables.exam_assignments),
                "num_hard_constraints": model.Proto().constraints.__len__(),
                "num_objective_terms": len(objective_vars),
            }

            logger.info(
                f"CP-SAT model built: {constraint_info['num_variables']} variables, "
                f"{constraint_info['num_hard_constraints']} constraints"
            )

            return CPSATModel(
                model=model,
                variables=variables,
                objective_vars=objective_vars,
                constraint_info=constraint_info,
            )

        except Exception as e:
            logger.error(f"Failed to build CP-SAT model: {e}")
            raise

    async def _create_cpsat_variables(
        self, model: Any, variables: CPSATVariables, problem_instance: ProblemInstance
    ) -> None:
        """Create all CP-SAT decision variables"""

        # Provide explicit casts so mypy knows these are mappings
        exams = cast(Dict[str, Dict[str, Any]], problem_instance.exams)
        room_compatibility = cast(
            Dict[str, List[str]], problem_instance.room_compatibility
        )
        time_constraints = cast(Dict[str, List[str]], problem_instance.time_constraints)
        rooms = cast(Dict[str, Dict[str, Any]], problem_instance.rooms)
        time_slots = cast(Dict[str, Dict[str, Any]], problem_instance.time_slots)
        staff_constraints = cast(Dict[str, Any], problem_instance.staff_constraints)

        # Create exam assignment variables: exam -> room -> timeslot -> BoolVar
        for exam_id, exam_data in exams.items():
            # ensure type stays Dict[str, Dict[str, Any]]
            variables.exam_assignments[exam_id] = cast(Dict[str, Dict[str, Any]], {})
            compatible_rooms = room_compatibility.get(exam_id, [])
            available_slots = time_constraints.get(exam_id, [])

            for room_id in compatible_rooms:
                variables.exam_assignments[exam_id][room_id] = cast(Dict[str, Any], {})
                for timeslot_id in available_slots:
                    var_name = f"exam_{exam_id}_room_{room_id}_slot_{timeslot_id}"
                    variables.exam_assignments[exam_id][room_id][timeslot_id] = (
                        model.NewBoolVar(var_name)
                    )

        # Create helper variables for easier constraint formulation
        for exam_id in exams:
            variables.exam_scheduled[exam_id] = model.NewBoolVar(
                f"exam_scheduled_{exam_id}"
            )

        # Create room occupancy variables
        for room_id in rooms:
            variables.room_occupied[room_id] = cast(Dict[str, Any], {})
            for timeslot_id in time_slots:
                variables.room_occupied[room_id][timeslot_id] = model.NewBoolVar(
                    f"room_{room_id}_occupied_{timeslot_id}"
                )

        # Create staff assignment variables
        raw_individual_constraints = staff_constraints.get("individual_constraints", {})
        if not isinstance(raw_individual_constraints, dict):
            raw_individual_constraints = {}
        individual_constraints = cast(Dict[str, Any], raw_individual_constraints)

        for staff_id in individual_constraints:
            variables.staff_assignments[staff_id] = cast(Dict[str, Dict[str, Any]], {})
            for exam_id in exams:
                variables.staff_assignments[staff_id][exam_id] = cast(
                    Dict[str, Any], {}
                )
                available_slots = time_constraints.get(exam_id, [])
                unavailable_slots = individual_constraints[staff_id].get(
                    "unavailable_slots", []
                )

                for timeslot_id in available_slots:
                    if timeslot_id not in unavailable_slots:
                        var_name = f"staff_{staff_id}_exam_{exam_id}_slot_{timeslot_id}"
                        variables.staff_assignments[staff_id][exam_id][timeslot_id] = (
                            model.NewBoolVar(var_name)
                        )

    async def _add_hard_constraints(
        self,
        model: Any,
        variables: CPSATVariables,
        problem_instance: ProblemInstance,
        constraints_config: Dict[str, Any],
    ) -> None:
        """Add hard constraints to CP-SAT model"""

        # Typed local aliases
        exams = cast(Dict[str, Dict[str, Any]], problem_instance.exams)
        rooms = cast(Dict[str, Dict[str, Any]], problem_instance.rooms)
        time_slots = cast(Dict[str, Dict[str, Any]], problem_instance.time_slots)
        room_compatibility = cast(
            Dict[str, List[str]], problem_instance.room_compatibility
        )
        raw_individual_constraints = problem_instance.staff_constraints.get(
            "individual_constraints", {}
        )
        if not isinstance(raw_individual_constraints, dict):
            raw_individual_constraints = {}
        individual_constraints = cast(Dict[str, Any], raw_individual_constraints)
        conflict_matrix = cast(List[Tuple[str, str]], problem_instance.conflict_matrix)

        # Constraint 1: Each exam must be assigned exactly once
        for exam_id in exams:
            exam_assignment_vars: List[Any] = []
            if exam_id in variables.exam_assignments:
                # tell mypy this is a mapping room_id -> (timeslot_id -> var)
                room_map = cast(
                    Dict[str, Dict[str, Any]], variables.exam_assignments[exam_id]
                )
                for room_assignments in room_map.values():
                    timeslot_map = cast(Dict[str, Any], room_assignments)
                    for var in timeslot_map.values():
                        exam_assignment_vars.append(var)

                if exam_assignment_vars:
                    model.Add(sum(exam_assignment_vars) == 1)

        # Constraint 2: No student conflicts (exams with same students can't be at same time)
        conflict_list = cast(List[Tuple[str, str]], conflict_matrix)
        time_slots_map = cast(Dict[str, Dict[str, Any]], time_slots)

        for exam1_id, exam2_id in conflict_list:
            if (
                exam1_id in variables.exam_assignments
                and exam2_id in variables.exam_assignments
            ):
                for timeslot_id in time_slots_map.keys():
                    # Get all variables for exam1 in this timeslot
                    exam1_vars: List[Any] = []
                    room_map1 = cast(
                        Dict[str, Dict[str, Any]], variables.exam_assignments[exam1_id]
                    )
                    for room_assignments in room_map1.values():
                        timeslot_map = cast(Dict[str, Any], room_assignments)
                        if timeslot_id in timeslot_map:
                            exam1_vars.append(timeslot_map[timeslot_id])

                    # Get all variables for exam2 in this timeslot
                    exam2_vars: List[Any] = []
                    room_map2 = cast(
                        Dict[str, Dict[str, Any]], variables.exam_assignments[exam2_id]
                    )
                    for room_assignments in room_map2.values():
                        timeslot_map = cast(Dict[str, Any], room_assignments)
                        if timeslot_id in timeslot_map:
                            exam2_vars.append(timeslot_map[timeslot_id])

                    if exam1_vars and exam2_vars:
                        model.Add(sum(exam1_vars + exam2_vars) <= 1)

        # Constraint 3: Room capacity must not be exceeded
        for room_id, room_data in rooms.items():
            room_capacity = room_data.get("exam_capacity", room_data.get("capacity", 0))

            for timeslot_id in time_slots:
                capacity_usage = []

                for exam_id, exam_data in exams.items():
                    if (
                        exam_id in variables.exam_assignments
                        and room_id in variables.exam_assignments[exam_id]
                        and timeslot_id in variables.exam_assignments[exam_id][room_id]
                    ):

                        expected_students = exam_data.get("expected_students", 0)
                        var = variables.exam_assignments[exam_id][room_id][timeslot_id]
                        capacity_usage.append(var * expected_students)

                if capacity_usage:
                    model.Add(sum(capacity_usage) <= room_capacity)

        # Constraint 4: Staff availability and limits
        for staff_id, staff_data in individual_constraints.items():
            max_daily = staff_data.get("max_daily_sessions", 2)
            max_consecutive = staff_data.get("max_consecutive_sessions", 2)

            if staff_id in variables.staff_assignments:
                # Daily limit constraint
                daily_assignments = []
                for exam_assignments in variables.staff_assignments[staff_id].values():
                    for var in exam_assignments.values():
                        daily_assignments.append(var)

                if daily_assignments:
                    model.Add(sum(daily_assignments) <= max_daily)

                # Consecutive sessions constraint (simplified)
                sorted_timeslots = sorted(time_slots.keys())
                for i in range(len(sorted_timeslots) - max_consecutive):
                    consecutive_vars = []
                    for j in range(max_consecutive + 1):
                        timeslot_id = sorted_timeslots[i + j]
                        for exam_assignments in variables.staff_assignments[
                            staff_id
                        ].values():
                            if timeslot_id in exam_assignments:
                                consecutive_vars.append(exam_assignments[timeslot_id])

                    if consecutive_vars:
                        model.Add(sum(consecutive_vars) <= max_consecutive)

        # Link exam scheduling with staff assignments
        for exam_id in exams:
            if exam_id in variables.exam_scheduled:
                # At least one staff member must be assigned to each scheduled exam
                staff_assigned_to_exam = []
                for staff_id in variables.staff_assignments:
                    if exam_id in variables.staff_assignments[staff_id]:
                        for var in variables.staff_assignments[staff_id][
                            exam_id
                        ].values():
                            staff_assigned_to_exam.append(var)

                if staff_assigned_to_exam:
                    model.Add(
                        sum(staff_assigned_to_exam) >= variables.exam_scheduled[exam_id]
                    )

    async def _add_soft_constraints(
        self,
        model: Any,
        variables: CPSATVariables,
        problem_instance: ProblemInstance,
        constraints_config: Dict[str, Any],
    ) -> List[Any]:
        """Add soft constraints as objective terms"""
        objective_vars = []

        # Local typed aliases
        exams = cast(Dict[str, Dict[str, Any]], problem_instance.exams)
        rooms = cast(Dict[str, Dict[str, Any]], problem_instance.rooms)
        time_slots = cast(Dict[str, Dict[str, Any]], problem_instance.time_slots)
        time_constraints = cast(Dict[str, List[str]], problem_instance.time_constraints)
        staff_constraints = cast(Dict[str, Any], problem_instance.staff_constraints)

        soft_constraints = constraints_config.get("soft_constraints", {})

        # Room utilization optimization
        if "room_utilization" in soft_constraints:
            weight = int(soft_constraints["room_utilization"].get("weight", 100))

            for room_id, room_data in rooms.items():
                room_capacity = room_data.get(
                    "exam_capacity", room_data.get("capacity", 1)
                )

                for timeslot_id in time_slots:
                    utilization_var = model.NewIntVar(
                        0, room_capacity, f"util_{room_id}_{timeslot_id}"
                    )

                    # Calculate actual utilization
                    capacity_usage = []
                    for exam_id, exam_data in exams.items():
                        if (
                            exam_id in variables.exam_assignments
                            and room_id in variables.exam_assignments[exam_id]
                            and timeslot_id
                            in variables.exam_assignments[exam_id][room_id]
                        ):

                            expected_students = exam_data.get("expected_students", 0)
                            var = variables.exam_assignments[exam_id][room_id][
                                timeslot_id
                            ]
                            capacity_usage.append(var * expected_students)

                    if capacity_usage:
                        model.Add(utilization_var == sum(capacity_usage))
                        # Reward high utilization (prefer 70-90% utilization)
                        target_util = int(room_capacity * 0.8)
                        deviation_var = model.NewIntVar(
                            0, room_capacity, f"dev_{room_id}_{timeslot_id}"
                        )
                        model.AddAbsEquality(
                            deviation_var, utilization_var - target_util
                        )

                        # Minimize deviation from target utilization
                        objective_vars.append(weight * (room_capacity - deviation_var))

        # Time preference optimization
        if "time_preferences" in soft_constraints:
            weight = int(soft_constraints["time_preferences"].get("weight", 50))

            # Prefer morning slots for certain exam types
            morning_bonus = {}
            for timeslot_id, timeslot_data in time_slots.items():
                if timeslot_data.get("time_category") == "morning":
                    morning_bonus[timeslot_id] = 2
                elif timeslot_data.get("time_category") == "afternoon":
                    morning_bonus[timeslot_id] = 1
                else:
                    morning_bonus[timeslot_id] = 0

            for exam_id, exam_data in exams.items():
                course_level = exam_data.get("course_level", 100)
                if course_level >= 400:  # Graduate courses prefer morning
                    if exam_id in variables.exam_assignments:
                        for room_id in variables.exam_assignments[exam_id]:
                            for timeslot_id, var in variables.exam_assignments[exam_id][
                                room_id
                            ].items():
                                bonus = morning_bonus.get(timeslot_id, 0)
                                if bonus > 0:
                                    objective_vars.append(weight * bonus * var)

        # Staff workload balancing
        if "staff_balance" in soft_constraints:
            weight = int(soft_constraints["staff_balance"].get("weight", 25))

            # Try to balance workload across staff members
            staff_workload_vars = {}
            raw_individual_constraints = staff_constraints.get(
                "individual_constraints", {}
            )
            if not isinstance(raw_individual_constraints, dict):
                raw_individual_constraints = {}
            individual_constraints = cast(Dict[str, Any], raw_individual_constraints)

            for staff_id in individual_constraints:
                if staff_id in variables.staff_assignments:
                    workload_var = model.NewIntVar(0, 10, f"workload_{staff_id}")

                    # Calculate total assignments for this staff member
                    assignments = []
                    for exam_assignments in variables.staff_assignments[
                        staff_id
                    ].values():
                        for var in exam_assignments.values():
                            assignments.append(var)

                    if assignments:
                        model.Add(workload_var == sum(assignments))
                        staff_workload_vars[staff_id] = workload_var

            # Minimize variance in workload (simplified as minimizing max workload)
            if staff_workload_vars:
                max_workload_var = model.NewIntVar(0, 10, "max_workload")
                for workload_var in staff_workload_vars.values():
                    model.Add(max_workload_var >= workload_var)

                # Minimize maximum workload to balance assignments
                objective_vars.append(-weight * max_workload_var)

        return objective_vars

    async def build_ga_population(
        self,
        problem_instance: ProblemInstance,
        initial_solution: Dict[str, Any],
        population_size: int = 50,
    ) -> List[GAChromosome]:
        """Build initial GA population from CP-SAT solution"""

        population = []

        # Create first chromosome from CP-SAT solution
        base_chromosome = await self._cpsat_solution_to_chromosome(
            initial_solution, problem_instance
        )
        base_chromosome.fitness_score = await self._evaluate_chromosome_fitness(
            base_chromosome, problem_instance
        )
        population.append(base_chromosome)

        # Generate variations of the base solution
        for i in range(population_size - 1):
            variant = base_chromosome.copy()

            # Apply random mutations to create diversity
            mutation_count = random.randint(
                1, max(1, len(variant.exam_assignments) // 10)
            )
            for _ in range(mutation_count):
                await self._mutate_chromosome(variant, problem_instance)

            # Repair any constraint violations
            await self._repair_chromosome(variant, problem_instance)

            # Evaluate fitness
            variant.fitness_score = await self._evaluate_chromosome_fitness(
                variant, problem_instance
            )

            population.append(variant)

        logger.info(f"Built GA population with {len(population)} chromosomes")
        return population

    async def _cpsat_solution_to_chromosome(
        self, cpsat_solution: Dict[str, Any], problem_instance: ProblemInstance
    ) -> GAChromosome:
        """Convert CP-SAT solution to GA chromosome"""

        # typed alias
        exams = cast(Dict[str, Dict[str, Any]], problem_instance.exams)

        chromosome = GAChromosome()
        assignments = cpsat_solution.get("assignments", {})

        for exam_id, assignment in assignments.items():
            if exam_id in exams:
                chromosome.exam_assignments[exam_id] = {
                    "room_id": assignment.get("room_id"),
                    "timeslot_id": assignment.get("timeslot_id"),
                    "staff_ids": assignment.get("staff_ids", []),
                }

        return chromosome

    async def _evaluate_chromosome_fitness(
        self, chromosome: GAChromosome, problem_instance: ProblemInstance
    ) -> float:
        """Evaluate fitness score for GA chromosome"""

        # Local typed aliases
        exams = cast(Dict[str, Dict[str, Any]], problem_instance.exams)
        rooms = cast(Dict[str, Dict[str, Any]], problem_instance.rooms)
        time_constraints = cast(Dict[str, List[str]], problem_instance.time_constraints)
        room_compatibility = cast(
            Dict[str, List[str]], problem_instance.room_compatibility
        )
        conflict_matrix = cast(List[Tuple[str, str]], problem_instance.conflict_matrix)

        fitness = 0.0
        violations: Dict[str, int] = defaultdict(int)

        # Check hard constraints
        # 1. Student conflicts
        conflict_penalty = 0
        assigned_timeslots = defaultdict(list)

        for exam_id, assignment in chromosome.exam_assignments.items():
            timeslot_id = assignment.get("timeslot_id")
            if timeslot_id:
                assigned_timeslots[timeslot_id].append(exam_id)

        for timeslot_id, exam_ids in assigned_timeslots.items():
            for i in range(len(exam_ids)):
                for j in range(i + 1, len(exam_ids)):
                    exam1, exam2 = exam_ids[i], exam_ids[j]
                    if (exam1, exam2) in conflict_matrix or (
                        exam2,
                        exam1,
                    ) in conflict_matrix:
                        conflict_penalty += 1000  # Heavy penalty
                        violations["student_conflicts"] += 1

        fitness -= conflict_penalty

        # 2. Room capacity violations
        capacity_penalty = 0
        room_usage: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for exam_id, assignment in chromosome.exam_assignments.items():
            room_id = assignment.get("room_id")
            timeslot_id = assignment.get("timeslot_id")
            if room_id and timeslot_id and exam_id in exams:
                expected_students = exams[exam_id].get("expected_students", 0)
                room_usage[room_id][timeslot_id] += expected_students

        for room_id, timeslots in room_usage.items():
            if room_id in rooms:
                room_capacity = rooms[room_id].get(
                    "exam_capacity", rooms[room_id].get("capacity", 0)
                )

                for timeslot_id, usage in timeslots.items():
                    if usage > room_capacity:
                        capacity_penalty += (usage - room_capacity) * 100
                        violations["capacity_violations"] += 1

        fitness -= capacity_penalty

        # Soft constraint rewards
        # 1. Room utilization efficiency
        utilization_bonus = 0
        for room_id, timeslots in room_usage.items():
            if room_id in rooms:
                room_capacity = rooms[room_id].get(
                    "exam_capacity", rooms[room_id].get("capacity", 1)
                )

                for timeslot_id, usage in timeslots.items():
                    if usage > 0:
                        utilization_rate = usage / room_capacity
                        if 0.7 <= utilization_rate <= 0.9:  # Sweet spot
                            utilization_bonus += 50
                        elif utilization_rate <= 1.0:
                            utilization_bonus += 20

        fitness += utilization_bonus

        # 2. Assignment completeness
        total_exams = len(exams)
        assigned_exams = len(
            [
                a
                for a in chromosome.exam_assignments.values()
                if a.get("room_id") and a.get("timeslot_id")
            ]
        )
        assignment_rate = assigned_exams / max(1, total_exams)
        fitness += assignment_rate * 1000  # High reward for completeness

        chromosome.constraint_violations = dict(violations)
        return fitness

    async def _mutate_chromosome(
        self, chromosome: GAChromosome, problem_instance: ProblemInstance
    ) -> None:
        """Apply random mutation to chromosome"""

        if not chromosome.exam_assignments:
            return

        # typed aliases
        room_compatibility = cast(
            Dict[str, List[str]], problem_instance.room_compatibility
        )
        time_constraints = cast(Dict[str, List[str]], problem_instance.time_constraints)

        # Select random exam to mutate
        exam_id = random.choice(list(chromosome.exam_assignments.keys()))

        # Get alternative options
        compatible_rooms = room_compatibility.get(exam_id, [])
        available_timeslots = time_constraints.get(exam_id, [])

        if compatible_rooms and available_timeslots:
            # Random reassignment
            new_room = random.choice(compatible_rooms)
            new_timeslot = random.choice(available_timeslots)

            chromosome.exam_assignments[exam_id]["room_id"] = new_room
            chromosome.exam_assignments[exam_id]["timeslot_id"] = new_timeslot

    async def _repair_chromosome(
        self, chromosome: GAChromosome, problem_instance: ProblemInstance
    ) -> None:
        """Repair constraint violations in chromosome"""

        # typed aliases
        time_constraints = cast(Dict[str, List[str]], problem_instance.time_constraints)
        room_compatibility = cast(
            Dict[str, List[str]], problem_instance.room_compatibility
        )
        conflict_matrix = cast(List[Tuple[str, str]], problem_instance.conflict_matrix)

        # Simple repair: try to fix student conflicts by rescheduling
        assigned_timeslots = defaultdict(list)

        for exam_id, assignment in chromosome.exam_assignments.items():
            timeslot_id = assignment.get("timeslot_id")
            if timeslot_id:
                assigned_timeslots[timeslot_id].append(exam_id)

        # Find and resolve conflicts
        for timeslot_id, exam_ids in assigned_timeslots.items():
            conflicts = []
            for i in range(len(exam_ids)):
                for j in range(i + 1, len(exam_ids)):
                    exam1, exam2 = exam_ids[i], exam_ids[j]
                    if (exam1, exam2) in conflict_matrix or (
                        exam2,
                        exam1,
                    ) in conflict_matrix:
                        conflicts.append((exam1, exam2))

            # Resolve conflicts by moving one exam to a different time
            for exam1, exam2 in conflicts:
                # Try to reschedule exam2
                available_slots = time_constraints.get(exam2, [])
                alternative_slots = [s for s in available_slots if s != timeslot_id]

                if alternative_slots:
                    new_slot = random.choice(alternative_slots)
                    compatible_rooms = room_compatibility.get(exam2, [])

                    if compatible_rooms:
                        new_room = random.choice(compatible_rooms)
                        chromosome.exam_assignments[exam2]["room_id"] = new_room
                        chromosome.exam_assignments[exam2]["timeslot_id"] = new_slot

    async def get_solution_from_chromosome(
        self, chromosome: GAChromosome, problem_instance: ProblemInstance
    ) -> Dict[str, Any]:
        """Convert GA chromosome back to solution format"""

        exams = cast(Dict[str, Dict[str, Any]], problem_instance.exams)

        solution = {
            "assignments": chromosome.exam_assignments.copy(),
            "metadata": {
                "fitness_score": chromosome.fitness_score,
                "constraint_violations": chromosome.constraint_violations,
                "assignment_rate": len(
                    [
                        a
                        for a in chromosome.exam_assignments.values()
                        if a.get("room_id") and a.get("timeslot_id")
                    ]
                )
                / max(1, len(exams)),
                "total_exams": len(exams),
                "assigned_exams": len(
                    [
                        a
                        for a in chromosome.exam_assignments.values()
                        if a.get("room_id") and a.get("timeslot_id")
                    ]
                ),
            },
        }

        return solution
