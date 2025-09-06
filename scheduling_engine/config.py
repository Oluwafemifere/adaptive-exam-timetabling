# scheduling_engine/config.py

"""
Configuration module for the scheduling engine.
Based on the research paper's genetic-based constraint programming approach.
"""

from typing import Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field
import logging


class SolverPhase(Enum):
    """Solver phases in the hybrid approach"""

    CP_SAT = "cp_sat"
    GENETIC_ALGORITHM = "genetic_algorithm"
    HYBRID_COORDINATION = "hybrid_coordination"


class OptimizationObjective(Enum):
    """Optimization objectives"""

    MINIMIZE_CONFLICTS = "minimize_conflicts"
    MINIMIZE_TOTAL_WEIGHTED_TARDINESS = "minimize_twt"
    MAXIMIZE_ROOM_UTILIZATION = "maximize_room_utilization"
    MINIMIZE_STUDENT_TRAVEL = "minimize_student_travel"
    MULTI_OBJECTIVE = "multi_objective"


@dataclass
class CPSATConfig:
    """Configuration for CP-SAT solver phase"""

    time_limit_seconds: int = 300  # 5 minutes for feasibility
    num_workers: int = 4
    log_search_progress: bool = True
    use_hint_from_previous: bool = True
    enumerate_all_solutions: bool = False

    # Variable selection strategies
    default_domain_selection: str = "choosing_lowest_domain_value"
    domain_reduction: str = "selecting_min_value"


@dataclass
class GeneticAlgorithmConfig:
    """Configuration for Genetic Algorithm phase"""

    population_size: int = 200
    num_generations: int = 50
    tournament_size: int = 5
    crossover_rate: float = 0.9
    mutation_rate: float = 0.1
    max_tree_depth: int = 7

    # Pre-selection parameters
    use_pre_selection: bool = True
    pre_selection_instances: int = 10
    intermediate_population_size: int = 400  # 2 * population_size

    # Training parameters
    training_instances_per_generation: int = 5
    training_time_limit_seconds: int = 30


@dataclass
class HybridConfig:
    """Configuration for hybrid coordination"""

    enable_faculty_partitioning: bool = True
    min_partition_size: int = 5
    max_partition_size: int = 200
    dependency_threshold: float = 0.3

    # Phase coordination
    cp_sat_weight: float = 0.7
    ga_weight: float = 0.3
    adaptation_frequency: int = 10  # generations


@dataclass
class SchedulingEngineConfig:
    """Main configuration for the scheduling engine"""

    # Solver configurations
    cp_sat: CPSATConfig = field(default_factory=CPSATConfig)
    genetic_algorithm: GeneticAlgorithmConfig = field(
        default_factory=GeneticAlgorithmConfig
    )
    hybrid: HybridConfig = field(default_factory=HybridConfig)

    # Global settings
    optimization_objective: OptimizationObjective = (
        OptimizationObjective.MULTI_OBJECTIVE
    )
    enable_logging: bool = True
    log_level: str = "INFO"

    # Constraint weights (for multi-objective optimization)
    constraint_weights: Dict[str, float] | None = None

    # Performance settings
    enable_parallel_processing: bool = True
    max_memory_gb: int = 8

    def __post_init__(self):
        if self.constraint_weights is None:
            self.constraint_weights = {
                "hard_constraints": 1.0,
                "soft_constraints": 0.5,
                "room_utilization": 0.7,
                "student_conflicts": 1.0,
                "invigilator_balance": 0.6,
                "exam_distribution": 0.4,
            }


# Global configuration instance
config = SchedulingEngineConfig()

# Terminal set for GP (from research paper Table 1)
GP_TERMINAL_SET = [
    "ES",  # earliest start time or release time
    "PT",  # processing time
    "W",  # weight
    "DD",  # due date
    "WL",  # workload of the machine processing j
    "maxWL",  # maximum workload for all machines
    "NPREC",  # number of precedence jobs
    "NSUC",  # number of successors
    "WLPREC",  # workload of precedence jobs
    "WLSUC",  # workload of successors
]

# Function set for GP (from research paper)
GP_FUNCTION_SET = ["+", "-", "*", "%", "max", "min"]


def get_logger(name: str) -> logging.Logger:
    """Get configured logger for scheduling engine"""
    logger = logging.getLogger(f"scheduling_engine.{name}")
    if config.enable_logging:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, config.log_level))
    return logger


# Performance monitoring settings
PERFORMANCE_METRICS = {
    "solution_quality": ["objective_value", "constraint_violations", "feasibility"],
    "solver_performance": ["runtime", "memory_usage", "iterations", "branching_steps"],
    "ga_evolution": [
        "generation",
        "best_fitness",
        "population_diversity",
        "convergence_rate",
    ],
    "hybrid_coordination": [
        "phase_transitions",
        "solution_improvements",
        "coordination_overhead",
    ],
}
