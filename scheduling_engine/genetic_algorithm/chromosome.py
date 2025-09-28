"""

Safe Chromosome Module - DEAP-Integrated chromosome with recursion-safe copying.

This module fixes the infinite recursion issues in DEAPIndividual.copy() and

implements constraint-aware chromosome operations without circular dependencies.

"""

import numpy as np

import logging

from typing import Dict, List, Set, Tuple, Optional, Any, Union, cast

from uuid import UUID

import random

# Safe imports to prevent circular dependencies

from .deap_setup import get_deap_fitness_max, is_deap_available

from .types import (
    SchedulingPreferences,
    PruningDecisions,
    safe_copy_dict,
    safe_copy_set,
    safe_fitness_value,
)

logger = logging.getLogger(__name__)


# Type definitions for DEAP fitness to help Pylance
class DEAPFitness:
    """Type stub for DEAP fitness objects to help with type checking."""

    values: Tuple[float, ...]
    valid: bool
    wvalues: property  # This is a property in DEAP that returns weighted values

    def __init__(self) -> None:
        self.values = ()
        self.valid = False


class DEAPIndividual(list):
    """
    FIXED: DEAP-based individual class with recursion-safe operations.

    Key fixes:
    - Safe copying without infinite recursion
    - Manual field copying instead of deep copy
    - Circular reference detection and breaking
    - GENE LENGTH VALIDATION added
    """

    def __init__(self, genes=None):
        if genes is not None:
            super().__init__(genes)
        else:
            super().__init__()

        # Initialize DEAP fitness safely with proper typing
        fitness_class = get_deap_fitness_max()
        if fitness_class:
            self.fitness = fitness_class()
            # Cast to our type stub for better type checking
            self.fitness = cast(DEAPFitness, self.fitness)
        else:
            # Fallback fitness implementation with proper attributes
            class FallbackFitness:
                def __init__(self):
                    self.values: Tuple[float, ...] = ()
                    self.valid = False

                @property
                def wvalues(self) -> Tuple[float, ...]:
                    return self.values

            self.fitness = FallbackFitness()

        # Chromosome-specific attributes
        self.preferences: Optional[SchedulingPreferences] = None
        self.pruning_decisions: Optional[PruningDecisions] = None
        self.age = 0
        self.generation_created = 0

        # Performance metrics
        self.cp_sat_solve_time = 0.0
        self.objective_value = float("inf")
        self.feasibility_score = 0.0
        self.constraint_violations = 0.0
        self.solver_hints: List[Any] = []

        # Constraint-aware tracking
        self.constraint_satisfaction_rate = 0.0
        self.critical_constraint_violations = 0
        self.pruning_efficiency = 0.0

    def copy(self):
        """
        FIXED: Create a safe copy without infinite recursion.

        Uses manual field copying and avoids deep copy operations
        that can cause recursion with complex nested objects.
        """
        # FIXED: Validate gene length during copy
        if len(self) == 0:
            logger.warning(
                "Attempting to copy individual with 0 genes, creating minimal valid individual"
            )
            # Create minimal valid individual instead of empty one
            minimal_genes = [0.5] * 16  # Default minimal gene length
            new_individual = DEAPIndividual(minimal_genes)
        else:
            # Create new individual with same genes (shallow copy of list)
            new_individual = DEAPIndividual(list(self))

        # Safe fitness copying with type-aware access
        try:
            if hasattr(self, "fitness") and getattr(self.fitness, "valid", False):
                fitness_values = getattr(self.fitness, "values", ())
                new_individual.fitness.values = fitness_values

        except Exception as e:
            logger.debug(f"Fitness copy failed, using defaults: {e}")
            new_individual.fitness.values = ()

        # Safe preferences copying - avoid deep copy recursion
        if self.preferences is not None:
            try:
                new_individual.preferences = SchedulingPreferences(
                    exam_priorities=safe_copy_dict(self.preferences.exam_priorities),
                    room_preferences={
                        k: safe_copy_dict(v)
                        for k, v in self.preferences.room_preferences.items()
                    },
                    time_preferences={
                        k: safe_copy_dict(v)
                        for k, v in self.preferences.time_preferences.items()
                    },
                    invigilator_preferences=safe_copy_dict(
                        self.preferences.invigilator_preferences
                    ),
                )
            except Exception as e:
                logger.debug(f"Preferences copy failed: {e}")
                new_individual.preferences = None

        # Safe pruning decisions copying
        if self.pruning_decisions is not None:
            try:
                new_individual.pruning_decisions = PruningDecisions(
                    pruned_x_vars=safe_copy_set(self.pruning_decisions.pruned_x_vars),
                    pruned_y_vars=safe_copy_set(self.pruning_decisions.pruned_y_vars),
                    pruned_u_vars=safe_copy_set(self.pruning_decisions.pruned_u_vars),
                    constraint_relaxations=safe_copy_dict(
                        self.pruning_decisions.constraint_relaxations
                    ),
                    critical_x_vars=safe_copy_set(
                        self.pruning_decisions.critical_x_vars
                    ),
                    critical_y_vars=safe_copy_set(
                        self.pruning_decisions.critical_y_vars
                    ),
                    critical_u_vars=safe_copy_set(
                        self.pruning_decisions.critical_u_vars
                    ),
                )
            except Exception as e:
                logger.debug(f"Pruning decisions copy failed: {e}")
                new_individual.pruning_decisions = None

        # Copy simple attributes safely (no deep copy needed)
        new_individual.age = 0  # Reset age for new individual
        new_individual.generation_created = self.generation_created
        new_individual.objective_value = self.objective_value
        new_individual.feasibility_score = self.feasibility_score
        new_individual.constraint_violations = self.constraint_violations
        new_individual.constraint_satisfaction_rate = self.constraint_satisfaction_rate
        new_individual.critical_constraint_violations = (
            self.critical_constraint_violations
        )
        new_individual.pruning_efficiency = self.pruning_efficiency
        new_individual.cp_sat_solve_time = self.cp_sat_solve_time

        # Safe solver hints copying
        try:
            if hasattr(self, "solver_hints") and self.solver_hints:
                # Shallow copy of hints to avoid recursion
                new_individual.solver_hints = [
                    list(hint) if isinstance(hint, (list, tuple)) else hint
                    for hint in self.solver_hints[:50]  # Limit to prevent memory issues
                ]
            else:
                new_individual.solver_hints = []
        except Exception as e:
            logger.debug(f"Solver hints copy failed: {e}")
            new_individual.solver_hints = []

        return new_individual

    def dominates(self, other) -> bool:
        """Check if this individual dominates another (Pareto dominance)."""
        # Use getattr for safe attribute access
        self_valid = getattr(self.fitness, "valid", False)
        other_valid = getattr(other.fitness, "valid", False)

        if not (self_valid and other_valid):
            return False

        self_values = getattr(self.fitness, "values", ())
        other_values = getattr(other.fitness, "values", ())

        # For single objective
        if len(self_values) == 1 and len(other_values) == 1:
            return self_values[0] > other_values[0]

        # For multi-objective (Pareto dominance)
        return all(s >= o for s, o in zip(self_values, other_values)) and any(
            s > o for s, o in zip(self_values, other_values)
        )

    def get_diversity_metric(self, other) -> float:
        """Calculate diversity metric between two individuals."""
        if len(self) != len(other):
            return 1.0

        # Euclidean distance in gene space
        try:
            diff = np.array(self) - np.array(other)
            return float(np.sqrt(np.sum(diff**2)) / len(self))
        except Exception:
            return 0.5  # Default diversity if calculation fails

    def violates_critical_constraints(self) -> bool:
        """Check if individual violates any critical constraints."""
        return self.critical_constraint_violations > 0

    def get_constraint_priority_score(self) -> float:
        """Calculate priority score based on constraint satisfaction."""
        if self.constraint_violations == 0:
            return 1.0

        # Higher weight for critical constraint violations
        critical_penalty = self.critical_constraint_violations * 10.0
        regular_penalty = (
            self.constraint_violations - self.critical_constraint_violations
        ) * 1.0
        total_penalty = critical_penalty + regular_penalty

        return max(0.0, 1.0 / (1.0 + total_penalty))


class ChromosomeEncoder:
    """Encodes problem instance into DEAP-compatible chromosome structure."""

    def __init__(self, problem, constraint_manager=None):
        self.problem = problem
        self.constraint_manager = constraint_manager
        self.structure_info = self._build_structure_info()

    def _build_structure_info(self) -> Dict:
        """Build structure information needed for chromosome encoding/decoding."""
        return {
            "exam_ids": list(self.problem.exams.keys()),
            "room_ids": list(self.problem.rooms.keys()),
            "slot_ids": list(self.problem.timeslots.keys()),
            "invigilator_ids": list(getattr(self.problem, "invigilators", {}).keys()),
            "num_exams": len(self.problem.exams),
            "num_rooms": len(self.problem.rooms),
            "num_slots": len(self.problem.timeslots),
            "num_invigilators": len(getattr(self.problem, "invigilators", {})),
        }

    def create_random_individual(self) -> DEAPIndividual:
        """FIXED: Create a random individual with valid structure and constraint awareness."""
        gene_length = self._calculate_gene_length()

        # CRITICAL FIX: Validate gene length
        if gene_length <= 0:
            logger.error(f"Invalid gene length calculated: {gene_length}")
            # Use minimal safe gene length
            gene_length = max(16, len(self.structure_info["exam_ids"]) * 4)
            logger.warning(f"Using fallback gene length: {gene_length}")

        genes = [random.uniform(0.0, 1.0) for _ in range(gene_length)]
        individual = DEAPIndividual(genes)

        # CRITICAL FIX: Validate individual length
        if len(individual) != gene_length:
            logger.error(
                f"Individual length mismatch: {len(individual)} != {gene_length}"
            )
            raise ValueError(
                f"Individual length mismatch: {len(individual)} != {gene_length}"
            )

        if len(individual) == 0:
            logger.error("Created individual with 0 genes - this should never happen")
            raise ValueError("Cannot create individual with 0 genes")

        # Create preferences and constraint-aware pruning decisions
        individual.preferences = self._genes_to_preferences(individual)
        individual.pruning_decisions = self._create_constraint_aware_pruning(individual)

        return individual

    def create_heuristic_individual(
        self, heuristic_type: str = "constraint_priority"
    ) -> DEAPIndividual:
        """Create individual using constraint-aware domain-specific heuristics."""
        if heuristic_type == "constraint_priority":
            return self._create_constraint_priority_individual()
        elif heuristic_type == "difficulty_first":
            return self._create_difficulty_first_individual()
        elif heuristic_type == "capacity_utilization":
            return self._create_capacity_utilization_individual()
        elif heuristic_type == "time_distribution":
            return self._create_time_distribution_individual()
        else:
            return self.create_random_individual()

    def _calculate_gene_length(self) -> int:
        """FIXED: Calculate the required gene length for the chromosome."""
        base_length = (
            self.structure_info["num_exams"]  # exam priorities
            + self.structure_info["num_exams"]
            * self.structure_info["num_rooms"]  # room prefs
            + self.structure_info["num_exams"]
            * self.structure_info["num_slots"]  # time prefs
            + self.structure_info["num_invigilators"]  # invigilator prefs
        )

        # CRITICAL FIX: Ensure minimum gene length
        min_length = 16  # Absolute minimum
        calculated_length = max(min_length, base_length)

        logger.debug(
            f"Calculated gene length: {calculated_length} (base: {base_length}, min: {min_length})"
        )
        return calculated_length

    def _genes_to_preferences(
        self, individual: DEAPIndividual
    ) -> SchedulingPreferences:
        """Convert gene array to scheduling preferences."""
        genes = list(individual)
        idx = 0

        # FIXED: Add length validation
        if len(genes) == 0:
            logger.warning("Empty gene array in _genes_to_preferences")
            return SchedulingPreferences({}, {}, {}, {})

        # Exam priorities
        exam_priorities = {}
        for exam_id in self.structure_info["exam_ids"]:
            exam_priorities[exam_id] = genes[idx] if idx < len(genes) else 0.5
            idx += 1

        # Room preferences
        room_preferences = {}
        for exam_id in self.structure_info["exam_ids"]:
            room_preferences[exam_id] = {}
            for room_id in self.structure_info["room_ids"]:
                room_preferences[exam_id][room_id] = (
                    genes[idx] if idx < len(genes) else 0.5
                )
                idx += 1

        # Time preferences
        time_preferences = {}
        for exam_id in self.structure_info["exam_ids"]:
            time_preferences[exam_id] = {}
            for slot_id in self.structure_info["slot_ids"]:
                time_preferences[exam_id][slot_id] = (
                    genes[idx] if idx < len(genes) else 0.5
                )
                idx += 1

        # Invigilator preferences
        invigilator_preferences = {}
        for inv_id in self.structure_info["invigilator_ids"]:
            invigilator_preferences[inv_id] = genes[idx] if idx < len(genes) else 0.5
            idx += 1

        return SchedulingPreferences(
            exam_priorities=exam_priorities,
            room_preferences=room_preferences,
            time_preferences=time_preferences,
            invigilator_preferences=invigilator_preferences,
        )

    def _create_constraint_aware_pruning(
        self, individual: DEAPIndividual
    ) -> PruningDecisions:
        """Create constraint-aware pruning decisions that preserve critical variables."""
        preferences = (
            individual.preferences
            if individual.preferences
            else self._genes_to_preferences(individual)
        )

        pruning_decisions = PruningDecisions()

        # Identify critical variables that must never be pruned
        self._identify_critical_variables(pruning_decisions)

        # Conservative pruning of low-preference combinations
        if (
            preferences
            and preferences.room_preferences
            and preferences.time_preferences
        ):
            for exam_id in preferences.room_preferences:
                exam_room_prefs = preferences.room_preferences[exam_id]
                exam_time_prefs = preferences.time_preferences.get(exam_id, {})

                for room_id, room_pref in exam_room_prefs.items():
                    for slot_id, time_pref in exam_time_prefs.items():
                        combined_pref = (room_pref + time_pref) / 2.0
                        var_key = (exam_id, room_id, slot_id)

                        # Very conservative pruning threshold for constraint safety
                        if (
                            combined_pref < 0.15
                            and pruning_decisions.is_safe_to_prune("y", var_key)
                            and self._can_prune_safely(var_key)
                        ):
                            pruning_decisions.pruned_y_vars.add(var_key)

        return pruning_decisions

    def _identify_critical_variables(self, pruning_decisions: PruningDecisions):
        """Identify variables that are critical for constraint satisfaction."""
        MIN_START_OPTIONS = 3
        MIN_ROOM_OPTIONS = 2

        # For each exam, ensure it has viable start options
        for exam_id in self.structure_info["exam_ids"]:
            viable_starts = []
            for slot_id in self.structure_info["slot_ids"]:
                # Check if this start time could work
                if self._has_feasible_rooms_for_slot(exam_id, slot_id):
                    viable_starts.append((exam_id, slot_id))

            # Mark top viable starts as critical
            for start_var in viable_starts[:MIN_START_OPTIONS]:
                pruning_decisions.critical_x_vars.add(start_var)

        # For each exam, ensure it has viable room options per time slot
        for exam_id in self.structure_info["exam_ids"]:
            for slot_id in self.structure_info["slot_ids"]:
                viable_rooms = []
                for room_id in self.structure_info["room_ids"]:
                    if self._is_feasible_assignment(exam_id, room_id, slot_id):
                        viable_rooms.append((exam_id, room_id, slot_id))

                # Mark viable room assignments as critical
                for room_var in viable_rooms[:MIN_ROOM_OPTIONS]:
                    pruning_decisions.critical_y_vars.add(room_var)

    def _has_feasible_rooms_for_slot(self, exam_id: UUID, slot_id: UUID) -> bool:
        """Check if exam has at least one feasible room for the given slot."""
        for room_id in self.structure_info["room_ids"]:
            if self._is_feasible_assignment(exam_id, room_id, slot_id):
                return True
        return False

    def _is_feasible_assignment(
        self, exam_id: UUID, room_id: UUID, slot_id: UUID
    ) -> bool:
        """Check if an exam-room-slot assignment is basically feasible."""
        exam = self.problem.exams.get(exam_id)
        room = self.problem.rooms.get(room_id)

        if not exam or not room:
            return False

        # Check capacity
        enrollment = getattr(exam, "expected_students", 0)
        capacity = getattr(room, "exam_capacity", getattr(room, "capacity", 0))

        if enrollment > capacity * 1.15:  # Allow 15% overbooking
            return False

        return True

    def _can_prune_safely(self, var_key: Tuple) -> bool:
        """Check if variable can be pruned without violating constraint requirements."""
        exam_id, room_id, slot_id = var_key

        # Count remaining feasible options for this exam
        remaining_options = 0
        for r_id in self.problem.rooms:
            for s_id in self.problem.timeslots:
                if r_id != room_id or s_id != slot_id:
                    if self._is_feasible_assignment(exam_id, r_id, s_id):
                        remaining_options += 1

        return remaining_options >= 10  # Conservative threshold

    # Heuristic individual creation methods
    def _create_constraint_priority_individual(self) -> DEAPIndividual:
        """Create individual that prioritizes constraint satisfaction."""
        gene_length = self._calculate_gene_length()
        genes = []

        # Exam priorities based on constraint criticality
        for exam_id in self.structure_info["exam_ids"]:
            exam = self.problem.exams[exam_id]
            enrollment = getattr(exam, "expected_students", 1)
            duration = getattr(exam, "duration_minutes", 180)
            conflict_count = self._estimate_exam_conflicts(exam_id)

            # Higher priority for more constrained exams
            criticality = min(1.0, (enrollment * duration * conflict_count) / 50000.0)
            priority = 0.3 + 0.7 * criticality
            genes.append(priority)

        # Room preferences based on constraint compatibility
        for exam_id in self.structure_info["exam_ids"]:
            exam = self.problem.exams[exam_id]
            enrollment = getattr(exam, "expected_students", 1)

            for room_id in self.structure_info["room_ids"]:
                room = self.problem.rooms[room_id]
                capacity = getattr(room, "exam_capacity", getattr(room, "capacity", 1))

                if capacity >= enrollment:
                    utilization = enrollment / capacity
                    preference = max(0.1, 1.0 - abs(0.8 - utilization))
                else:
                    preference = 0.05  # Very low for impossible assignments
                genes.append(preference)

        # Time preferences based on constraint conflicts
        for exam_id in self.structure_info["exam_ids"]:
            for slot_id in self.structure_info["slot_ids"]:
                conflict_potential = self._calculate_slot_conflict_potential(
                    exam_id, slot_id
                )
                preference = max(0.1, 1.0 - conflict_potential)
                genes.append(preference)

        # Balanced invigilator utilization
        for _ in self.structure_info["invigilator_ids"]:
            genes.append(0.5 + random.random() * 0.3)

        # FIXED: Ensure we have the right gene length
        while len(genes) < gene_length:
            genes.append(0.5)
        genes = genes[:gene_length]  # Trim if too long

        individual = DEAPIndividual(genes)
        individual.preferences = self._genes_to_preferences(individual)
        individual.pruning_decisions = self._create_constraint_aware_pruning(individual)

        return individual

    def _create_difficulty_first_individual(self) -> DEAPIndividual:
        """Create individual that prioritizes difficult exams first."""
        return self._create_constraint_priority_individual()  # Simplified for now

    def _create_capacity_utilization_individual(self) -> DEAPIndividual:
        """Create individual focused on optimal capacity utilization."""
        return self._create_constraint_priority_individual()  # Simplified for now

    def _create_time_distribution_individual(self) -> DEAPIndividual:
        """Create individual for balanced time distribution."""
        return self._create_constraint_priority_individual()  # Simplified for now

    def _estimate_exam_conflicts(self, exam_id: UUID) -> int:
        """Estimate number of conflicts for an exam."""
        return random.randint(1, 5)  # Placeholder

    def _calculate_slot_conflict_potential(self, exam_id: UUID, slot_id: UUID) -> float:
        """Calculate conflict potential for exam in specific slot."""
        return random.random() * 0.3  # Placeholder


class ChromosomeDecoder:
    """FIXED Decodes chromosomes to constraint-aware solver hints and pruning decisions."""

    def __init__(self, problem, constraint_encoder=None):
        self.problem = problem
        self.constraint_encoder = constraint_encoder

    def decode_to_search_hints(self, individual) -> List[Tuple]:
        """Generate constraint-aware search hints for CP-SAT solver."""
        if not individual.preferences:
            return []

        hints = []
        preferences = individual.preferences

        try:
            # Generate high-confidence Y variable hints
            for exam_id, exam_priority in preferences.exam_priorities.items():
                if exam_priority < 0.3:  # Skip low-priority exams
                    continue

                room_prefs = preferences.room_preferences.get(exam_id, {})
                time_prefs = preferences.time_preferences.get(exam_id, {})

                for room_id, room_pref in room_prefs.items():
                    if room_pref < 0.6:  # Only high-preference rooms
                        continue
                    for slot_id, time_pref in time_prefs.items():
                        if time_pref < 0.6:  # Only high-preference times
                            continue

                        var_key = (exam_id, room_id, slot_id)
                        confidence = min(0.95, exam_priority + room_pref + time_pref)
                        if confidence > 0.5:
                            hints.append((var_key, 1, confidence))

            # Sort hints by confidence and return top ones
            hints.sort(key=lambda x: x[2], reverse=True)
            logger.debug(f"Generated {len(hints)} search hints from individual")
            return hints[:100]  # Return top 100 hints

        except Exception as e:
            logger.error(f"Error decoding search hints: {e}")
            return []

    def decode_to_pruning_decisions(self, individual) -> PruningDecisions:
        """FIXED Generate constraint-aware variable pruning decisions."""
        try:
            preferences = (
                individual.preferences
                if individual.preferences
                else SchedulingPreferences()
            )

            # Create proper PruningDecisions object with all required attributes
            pruning_decisions = PruningDecisions()

            # FIXED: Populate critical variables to prevent attribute errors
            self._identify_critical_variables(pruning_decisions, preferences)

            # Add some pruning decisions based on preferences
            if preferences.room_preferences and preferences.time_preferences:
                for exam_id in preferences.room_preferences:
                    exam_room_prefs = preferences.room_preferences[exam_id]
                    exam_time_prefs = preferences.time_preferences.get(exam_id, {})

                    for room_id, room_pref in exam_room_prefs.items():
                        for slot_id, time_pref in exam_time_prefs.items():
                            combined_pref = (room_pref + time_pref) / 2.0
                            var_key = (exam_id, room_id, slot_id)

                            # Conservative pruning of low-preference combinations
                            if (
                                combined_pref < 0.15
                                and pruning_decisions.is_safe_to_prune("y", var_key)
                                and self._can_prune_safely(var_key)
                            ):
                                pruning_decisions.pruned_y_vars.add(var_key)

            logger.debug(
                f"Created pruning decisions: {pruning_decisions.get_total_pruned()} variables to prune"
            )
            return pruning_decisions

        except Exception as e:
            logger.error(f"Error in decode_to_pruning_decisions: {e}")
            # Return a minimal but valid PruningDecisions object
            return PruningDecisions()

    def _identify_critical_variables(
        self, pruning_decisions: PruningDecisions, preferences: SchedulingPreferences
    ):
        """FIXED Identify variables that are critical for constraint satisfaction."""
        MIN_START_OPTIONS = 3
        MIN_ROOM_OPTIONS = 2

        try:
            # Get structure info safely
            exam_ids = list(getattr(self.problem, "exams", {}).keys())[
                :10
            ]  # Limit for performance
            room_ids = list(getattr(self.problem, "rooms", {}).keys())[:10]
            slot_ids = list(getattr(self.problem, "timeslots", {}).keys())[:10]

            # For each exam, ensure it has viable start options
            for exam_id in exam_ids:
                viable_starts = []
                for slot_id in slot_ids:
                    if self._has_feasible_rooms_for_slot(exam_id, slot_id):
                        viable_starts.append((exam_id, slot_id))

                # Mark top viable starts as critical
                for start_var in viable_starts[:MIN_START_OPTIONS]:
                    pruning_decisions.critical_x_vars.add(start_var)
                    pruning_decisions.criticalxvars.add(
                        start_var
                    )  # Backward compatibility

            # For each exam, ensure it has viable room options per time slot
            for exam_id in exam_ids:
                for slot_id in slot_ids:
                    viable_rooms = []
                    for room_id in room_ids:
                        if self._is_feasible_assignment(exam_id, room_id, slot_id):
                            viable_rooms.append((exam_id, room_id, slot_id))

                    # Mark viable room assignments as critical
                    for room_var in viable_rooms[:MIN_ROOM_OPTIONS]:
                        pruning_decisions.critical_y_vars.add(room_var)
                        pruning_decisions.criticalyvars.add(
                            room_var
                        )  # Backward compatibility

            logger.debug(
                f"Identified {len(pruning_decisions.critical_x_vars)} critical X vars, "
                f"{len(pruning_decisions.critical_y_vars)} critical Y vars"
            )

        except Exception as e:
            logger.error(f"Error identifying critical variables: {e}")
            # Ensure we have empty sets at minimum
            if not hasattr(pruning_decisions, "critical_x_vars"):
                pruning_decisions.critical_x_vars = set()
                pruning_decisions.criticalxvars = set()
            if not hasattr(pruning_decisions, "critical_y_vars"):
                pruning_decisions.critical_y_vars = set()
                pruning_decisions.criticalyvars = set()
            if not hasattr(pruning_decisions, "critical_u_vars"):
                pruning_decisions.critical_u_vars = set()
                pruning_decisions.criticaluvars = set()

    def _has_feasible_rooms_for_slot(self, exam_id: UUID, slot_id: UUID) -> bool:
        """Check if exam has at least one feasible room for the given slot."""
        try:
            room_ids = list(getattr(self.problem, "rooms", {}).keys())
            for room_id in room_ids:
                if self._is_feasible_assignment(exam_id, room_id, slot_id):
                    return True
            return False
        except Exception:
            return True  # Conservative - assume feasible if we can't check

    def _is_feasible_assignment(
        self, exam_id: UUID, room_id: UUID, slot_id: UUID
    ) -> bool:
        """Check if an exam-room-slot assignment is basically feasible."""
        try:
            exam = getattr(self.problem, "exams", {}).get(exam_id)
            room = getattr(self.problem, "rooms", {}).get(room_id)

            if not exam or not room:
                return False

            # Check capacity
            enrollment = getattr(exam, "expected_students", 0)
            capacity = getattr(room, "exam_capacity", getattr(room, "capacity", 0))

            if enrollment > capacity * 1.15:  # Allow 15% overbooking
                return False

            return True
        except Exception:
            return True  # Conservative - assume feasible if we can't check

    def _can_prune_safely(self, var_key: Tuple) -> bool:
        """Check if variable can be pruned without violating constraint requirements."""
        try:
            exam_id, room_id, slot_id = var_key

            # Count remaining feasible options for this exam
            remaining_options = 0
            rooms = getattr(self.problem, "rooms", {})
            timeslots = getattr(self.problem, "timeslots", {})

            for r_id in rooms:
                for s_id in timeslots:
                    if r_id != room_id or s_id != slot_id:
                        if self._is_feasible_assignment(exam_id, r_id, s_id):
                            remaining_options += 1

            return remaining_options >= 10  # Conservative threshold
        except Exception:
            return False  # Conservative - don't prune if we can't check
