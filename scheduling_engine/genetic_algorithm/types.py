"""
Types Module - Shared data structures to break circular import dependencies.

Contains all shared type definitions, dataclasses, and interfaces that were
causing circular imports between chromosome.py, operators.py, fitness.py, and population.py.
"""

import numpy as np
from typing import Dict, List, Set, Tuple, Optional, Any, TYPE_CHECKING
from uuid import UUID
from dataclasses import dataclass, field
import logging

if TYPE_CHECKING:
    from .deap_setup import get_deap_fitness_max

logger = logging.getLogger(__name__)


@dataclass
class SchedulingPreferences:
    """High-level scheduling preferences encoded in chromosome."""

    exam_priorities: Dict[UUID, float] = field(
        default_factory=dict
    )  # Exam scheduling priority [0,1]
    room_preferences: Dict[UUID, Dict[UUID, float]] = field(
        default_factory=dict
    )  # exam_id -> room_id -> preference [0,1]
    time_preferences: Dict[UUID, Dict[UUID, float]] = field(
        default_factory=dict
    )  # exam_id -> slot_id -> preference [0,1]
    invigilator_preferences: Dict[UUID, float] = field(
        default_factory=dict
    )  # invigilator_id -> utilization preference [0,1]

    def to_array(self) -> np.ndarray:
        """Convert preferences to flat numpy array for DEAP operations."""
        array_parts = []

        # Exam priorities
        array_parts.extend(list(self.exam_priorities.values()))

        # Room preferences (flattened)
        for exam_prefs in self.room_preferences.values():
            array_parts.extend(list(exam_prefs.values()))

        # Time preferences (flattened)
        for exam_prefs in self.time_preferences.values():
            array_parts.extend(list(exam_prefs.values()))

        # Invigilator preferences
        array_parts.extend(list(self.invigilator_preferences.values()))

        return np.array(array_parts, dtype=np.float32)

    @classmethod
    def from_array(
        cls, array: np.ndarray, structure_info: Dict
    ) -> "SchedulingPreferences":
        """Reconstruct preferences from flat array using structure information."""
        idx = 0

        # Exam priorities
        exam_priorities = {}
        for exam_id in structure_info["exam_ids"]:
            exam_priorities[exam_id] = float(array[idx])
            idx += 1

        # Room preferences
        room_preferences = {}
        for exam_id in structure_info["exam_ids"]:
            room_preferences[exam_id] = {}
            for room_id in structure_info["room_ids"]:
                room_preferences[exam_id][room_id] = float(array[idx])
                idx += 1

        # Time preferences
        time_preferences = {}
        for exam_id in structure_info["exam_ids"]:
            time_preferences[exam_id] = {}
            for slot_id in structure_info["slot_ids"]:
                time_preferences[exam_id][slot_id] = float(array[idx])
                idx += 1

        # Invigilator preferences
        invigilator_preferences = {}
        for inv_id in structure_info["invigilator_ids"]:
            invigilator_preferences[inv_id] = float(array[idx])
            idx += 1

        return cls(
            exam_priorities=exam_priorities,
            room_preferences=room_preferences,
            time_preferences=time_preferences,
            invigilator_preferences=invigilator_preferences,
        )


@dataclass
class PruningDecisions:
    """Constraint-aware decisions made by GA about which variables to prune."""

    pruned_x_vars: Set[Tuple[UUID, UUID]] = field(
        default_factory=set
    )  # (exam_id, slot_id) pairs to prune
    pruned_y_vars: Set[Tuple[UUID, UUID, UUID]] = field(
        default_factory=set
    )  # (exam_id, room_id, slot_id) to prune
    pruned_u_vars: Set[Tuple[UUID, UUID, UUID, UUID]] = field(
        default_factory=set
    )  # (inv_id, exam_id, room_id, slot_id) to prune
    constraint_relaxations: Dict[str, float] = field(
        default_factory=dict
    )  # constraint_id -> relaxation_factor

    # Constraint-critical variables that should NEVER be pruned (FIXED: Add missing attributes)
    critical_x_vars: Set[Tuple[UUID, UUID]] = field(
        default_factory=set
    )  # FIXED: Added critical_x_vars
    critical_y_vars: Set[Tuple[UUID, UUID, UUID]] = field(
        default_factory=set
    )  # FIXED: Added critical_y_vars
    critical_u_vars: Set[Tuple[UUID, UUID, UUID, UUID]] = field(
        default_factory=set
    )  # FIXED: Added critical_u_vars
    criticalxvars: Set[Tuple[UUID, UUID]] = field(
        default_factory=set
    )  # BACKWARD COMPATIBILITY: Keep old attribute name
    criticalyvars: Set[Tuple[UUID, UUID, UUID]] = field(
        default_factory=set
    )  # BACKWARD COMPATIBILITY
    criticaluvars: Set[Tuple[UUID, UUID, UUID, UUID]] = field(
        default_factory=set
    )  # BACKWARD COMPATIBILITY

    def __post_init__(self):
        """FIXED: Ensure backward compatibility by syncing critical variables."""
        # Sync new attributes with old ones for backward compatibility
        if self.critical_x_vars and not self.criticalxvars:
            self.criticalxvars = self.critical_x_vars.copy()
        elif self.criticalxvars and not self.critical_x_vars:
            self.critical_x_vars = self.criticalxvars.copy()

        if self.critical_y_vars and not self.criticalyvars:
            self.criticalyvars = self.critical_y_vars.copy()
        elif self.criticalyvars and not self.critical_y_vars:
            self.critical_y_vars = self.criticalyvars.copy()

        if self.critical_u_vars and not self.criticaluvars:
            self.criticaluvars = self.critical_u_vars.copy()
        elif self.criticaluvars and not self.critical_u_vars:
            self.critical_u_vars = self.criticaluvars.copy()

    def get_total_pruned(self) -> int:
        """Get total number of variables pruned."""
        return (
            len(self.pruned_x_vars) + len(self.pruned_y_vars) + len(self.pruned_u_vars)
        )

    def is_safe_to_prune(self, var_type: str, var_key: Tuple) -> bool:
        """Check if a variable is safe to prune (not constraint-critical)."""
        if var_type == "x" and var_key in self.critical_x_vars:
            return False
        elif var_type == "y" and var_key in self.critical_y_vars:
            return False
        elif var_type == "u" and var_key in self.critical_u_vars:
            return False
        return True


@dataclass
class FitnessComponents:
    """Individual components that make up the total fitness."""

    quality_score: float = 0.0  # Objective value quality (normalized)
    speed_score: float = 0.0  # CP-SAT solving speed (normalized)
    feasibility_score: float = 0.0  # Constraint satisfaction rate
    diversity_bonus: float = 0.0  # Population diversity contribution
    age_penalty: float = 0.0  # Age-based penalty for stagnation
    pruning_efficiency: float = 0.0  # Variable pruning effectiveness
    constraint_priority_score: float = 0.0  # Critical constraint satisfaction
    search_hint_quality: float = 0.0  # Quality of generated search hints

    def total_fitness(self, weights: Optional[Dict[str, float]] = None) -> float:
        """Calculate total weighted fitness."""
        if weights is None:
            weights = {
                "quality": 0.5,
                "speed": 0.15,
                "feasibility": 0.2,
                "constraint_priority": 0.1,  # High weight for critical constraints
                "diversity": 0.03,
                "age": 0.02,
                "pruning": 0.02,
                "search_hints": 0.03,
            }

        total = (
            weights.get("quality", 0.5) * self.quality_score
            + weights.get("speed", 0.15) * self.speed_score
            + weights.get("feasibility", 0.2) * self.feasibility_score
            + weights.get("constraint_priority", 0.1) * self.constraint_priority_score
            + weights.get("diversity", 0.03) * self.diversity_bonus
            - weights.get("age", 0.02) * self.age_penalty
            + weights.get("pruning", 0.02) * self.pruning_efficiency
            + weights.get("search_hints", 0.03) * self.search_hint_quality
        )
        return max(0.0, total)  # Ensure non-negative fitness


@dataclass
class PopulationStatistics:
    """Statistics about the current population with constraint awareness."""

    generation: int
    size: int
    best_fitness: float
    average_fitness: float
    worst_fitness: float
    fitness_variance: float
    average_diversity: float
    constraint_violations: int
    critical_constraint_violations: int
    feasibility_rate: float
    convergence_metric: float
    constraint_satisfaction_rate: float
    pruning_efficiency: float


@dataclass
class GAConfiguration:
    """Configuration parameters for constraint-aware GA."""

    population_size: int = 50
    max_generations: int = 100
    cpsat_time_limit: int = 30
    pruning_aggressiveness: float = 0.2
    constraint_pressure: float = 0.3
    min_feasible_ratio: float = 0.3
    critical_constraint_weight: float = 0.3
    crossover_prob: float = 0.8
    mutation_prob: float = 0.2
    adaptive_operators: bool = True
    feasibility_pressure_adaptation: bool = True
    early_stopping_generations: int = 20
    diversity_threshold: float = 0.1


@dataclass
class EvolutionReport:
    """Comprehensive report of GA evolution process."""

    success: bool
    generations_run: int
    best_fitness: float
    final_constraint_violations: int
    final_critical_violations: int
    variables_pruned: int
    constraint_satisfaction_rate: float
    convergence_generation: Optional[int]
    total_time: float
    solver_hints_generated: int
    feasible_solutions_found: int
    population_statistics: List[PopulationStatistics]

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics from the evolution."""
        return {
            "success": self.success,
            "generations": self.generations_run,
            "best_fitness": self.best_fitness,
            "constraint_satisfaction": self.constraint_satisfaction_rate,
            "variables_pruned": self.variables_pruned,
            "solver_hints": self.solver_hints_generated,
            "feasible_solutions": self.feasible_solutions_found,
            "total_time_seconds": self.total_time,
            "converged_at_generation": self.convergence_generation,
        }


# Forward declarations to avoid circular imports
class DEAPIndividual:
    """Forward declaration - actual implementation in chromosome_safe.py"""

    pass


class DEAPPopulation:
    """Forward declaration - actual implementation in population_safe.py"""

    pass


class ChromosomeEncoder:
    """Forward declaration - actual implementation in chromosome_safe.py"""

    pass


# Utility functions
def safe_copy_dict(d: Dict) -> Dict:
    """Safely copy a dictionary to avoid recursion issues."""
    if not d:
        return {}
    try:
        return {k: v for k, v in d.items()}
    except Exception:
        return {}


def safe_copy_set(s: Set) -> Set:
    """Safely copy a set to avoid recursion issues."""
    if not s:
        return set()
    try:
        return set(s)
    except Exception:
        return set()


def safe_fitness_value(individual) -> float:
    """Safely extract fitness value from individual."""
    if individual is None:
        return float("-inf")

    fitness = getattr(individual, "fitness", None)
    if fitness is None:
        return float("-inf")

    values = getattr(fitness, "values", None)
    if not values:
        return float("-inf")

    try:
        return float(values[0])
    except (IndexError, TypeError, ValueError):
        return float("-inf")


def validate_uuid_dict(d: Dict[UUID, Any], name: str) -> bool:
    """Validate that dictionary has UUID keys."""
    if not isinstance(d, dict):
        logger.error(f"{name} must be a dictionary")
        return False

    for key in d.keys():
        if not isinstance(key, UUID):
            logger.error(f"{name} keys must be UUIDs, got {type(key)}")
            return False
    return True


def normalize_preferences(preferences: Dict[UUID, float]) -> Dict[UUID, float]:
    """Normalize preference values to [0, 1] range."""
    if not preferences:
        return preferences

    values = list(preferences.values())
    if not values:
        return preferences

    min_val = min(values)
    max_val = max(values)

    if max_val == min_val:
        return {k: 0.5 for k in preferences.keys()}

    return {k: (v - min_val) / (max_val - min_val) for k, v in preferences.items()}


def calculate_preference_diversity(
    prefs1: Dict[UUID, float], prefs2: Dict[UUID, float]
) -> float:
    """Calculate diversity between two preference dictionaries."""
    if not prefs1 or not prefs2:
        return 1.0

    common_keys = set(prefs1.keys()) & set(prefs2.keys())
    if not common_keys:
        return 1.0

    differences = [abs(prefs1[k] - prefs2[k]) for k in common_keys]
    return sum(differences) / len(differences) if differences else 0.0


def merge_preferences_weighted(
    prefs1: Dict[UUID, float], prefs2: Dict[UUID, float], weight1: float = 0.5
) -> Dict[UUID, float]:
    """Merge two preference dictionaries with weighting."""
    weight2 = 1.0 - weight1
    all_keys = set(prefs1.keys()) | set(prefs2.keys())

    merged = {}
    for key in all_keys:
        val1 = prefs1.get(key, 0.5)  # Default to neutral preference
        val2 = prefs2.get(key, 0.5)
        merged[key] = weight1 * val1 + weight2 * val2

    return merged


# Constants for constraint awareness
CRITICAL_CONSTRAINT_PENALTY = 10.0
REGULAR_CONSTRAINT_PENALTY = 1.0
MIN_FEASIBLE_POPULATION_RATIO = 0.2
MAX_CONSTRAINT_VIOLATIONS_PER_INDIVIDUAL = 50
MAX_PRUNING_RATIO = 0.8  # Don't prune more than 80% of variables
