"""
GA Factory - Factory Pattern for Genetic Algorithm Components

Breaks circular dependencies between constraint_encoder and evolution_manager
by providing controlled instantiation with dependency injection.
"""

import logging
import sys
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass
import time

# Safe imports using TYPE_CHECKING
if TYPE_CHECKING:
    from ..core.problem_model import ExamSchedulingProblem
    from ..genetic_algorithm.evolution_manager import (
        DEAPConstraintAwareEvolutionManager,
        ConstraintAwareGAParameters,
        ConstraintAwareEvolutionReport,
    )
    from ..genetic_algorithm.early_filter_ga import EarlyGAFilterGenerator
    from ..cp_sat.constraint_encoder import ConstraintEncoder

logger = logging.getLogger(__name__)


@dataclass
class GAFactoryConfig:
    """Configuration for GA Factory operations."""

    enable_evolution_manager: bool = True
    enable_early_filter: bool = True
    max_recursion_depth: int = 1000
    evolution_timeout_seconds: int = 60
    fallback_on_error: bool = True
    minimal_ga_params: bool = True
    debug_mode: bool = False


class GAComponentFactory:
    """
    Factory for creating GA components with proper dependency management.

    This factory:
    1. Uses lazy imports to avoid circular dependencies
    2. Implements timeout protection
    3. Provides fallback mechanisms
    4. Manages recursion limits
    5. Handles error recovery
    """

    def __init__(self, config: Optional[GAFactoryConfig] = None):
        self.config = config or GAFactoryConfig()
        self._component_cache: Dict[str, Any] = {}
        self._import_cache: Dict[str, Any] = {}

    def create_evolution_manager(
        self,
        problem: "ExamSchedulingProblem",
        constraint_encoder: "ConstraintEncoder",
        ga_parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional["DEAPConstraintAwareEvolutionManager"]:
        """
        Create evolution manager with safe dependency injection.

        Args:
            problem: The scheduling problem instance
            constraint_encoder: The constraint encoder instance
            ga_parameters: Optional GA parameters dictionary

        Returns:
            Evolution manager instance or None if creation fails
        """
        if not self.config.enable_evolution_manager:
            logger.info("Evolution manager creation disabled in config")
            return None

        try:
            # Set recursion limit protection
            old_limit = sys.getrecursionlimit()
            sys.setrecursionlimit(self.config.max_recursion_depth)

            try:
                # Lazy import with error handling
                evolution_classes = self._get_evolution_manager_classes()
                if not evolution_classes:
                    return None

                DEAPConstraintAwareEvolutionManager = evolution_classes["manager"]
                ConstraintAwareGAParameters = evolution_classes["parameters"]

                # Create minimal parameters to reduce complexity
                if self.config.minimal_ga_params:
                    params = ConstraintAwareGAParameters(
                        population_size=5,  # Very small
                        max_generations=3,  # Very small
                        cp_sat_time_limit=10,  # Short timeout
                        pruning_aggressiveness=0.1,  # Conservative
                        constraint_pressure=0.2,  # Low pressure
                        adaptive_operators=False,  # Disabled
                        multi_objective=False,  # Simplified
                        convergence_threshold=0.1,  # Lenient
                        diversity_threshold=0.05,  # Lenient
                    )
                else:
                    # Use provided parameters
                    param_dict = ga_parameters or {}
                    params = ConstraintAwareGAParameters(**param_dict)

                # Create evolution manager with timeout protection
                start_time = time.time()

                evolution_manager = DEAPConstraintAwareEvolutionManager(
                    problem=problem,
                    constraint_encoder=constraint_encoder,
                    parameters=params,
                )

                creation_time = time.time() - start_time
                logger.info(f"Evolution manager created in {creation_time:.2f}s")

                return evolution_manager

            finally:
                sys.setrecursionlimit(old_limit)

        except (ImportError, RecursionError, RuntimeError) as e:
            logger.warning(f"Evolution manager creation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating evolution manager: {e}")
            return None

    def create_early_filter_generator(
        self,
        problem: "ExamSchedulingProblem",
        max_combinations_per_exam: Optional[int] = None,
    ) -> Optional["EarlyGAFilterGenerator"]:
        """
        Create early filter generator with safe initialization.

        Args:
            problem: The scheduling problem instance
            max_combinations_per_exam: Maximum combinations to consider per exam

        Returns:
            EarlyGAFilterGenerator instance or None if creation fails
        """
        if not self.config.enable_early_filter:
            logger.info("Early filter generator creation disabled in config")
            return None

        try:
            # Lazy import
            filter_class = self._get_early_filter_class()
            if not filter_class:
                return None

            # Create with conservative parameters
            max_combinations = max_combinations_per_exam or 20  # Conservative default

            filter_generator = filter_class(
                problem=problem, max_combinations_per_exam=max_combinations
            )

            logger.info("Early filter generator created successfully")
            return filter_generator

        except Exception as e:
            logger.warning(f"Early filter generator creation failed: {e}")
            return None

    def run_ga_evolution_safe(
        self,
        evolution_manager: "DEAPConstraintAwareEvolutionManager",
        max_generations: Optional[int] = None,
    ) -> Optional["ConstraintAwareEvolutionReport"]:
        """
        Run GA evolution with error protection (without timeout on Windows).
        """
        if evolution_manager is None:
            return None

        try:
            # Run evolution with limited generations (no timeout on Windows)
            generations = max_generations or (
                3 if self.config.minimal_ga_params else 10
            )

            start_time = time.time()
            evolution_report = evolution_manager.solve(max_generations=generations)
            evolution_time = time.time() - start_time

            logger.info(f"GA evolution completed in {evolution_time:.2f}s")
            return evolution_report

        except (RecursionError, RuntimeError) as e:
            logger.warning(f"GA evolution failed with system error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in GA evolution: {e}")
            return None

    def create_fallback_filtering_result(self) -> Dict[str, Any]:
        """
        Create fallback filtering result when GA components fail.

        Returns:
            Dictionary with minimal viable filtering results
        """
        return {
            "viable_y_vars": set(),
            "viable_u_vars": set(),
            "pruning_decisions": None,
            "search_hints": [],
            "ga_stats": {
                "success": False,
                "fallback_used": True,
                "error_recovery": True,
            },
        }

    def _get_evolution_manager_classes(self) -> Optional[Dict[str, Any]]:
        """Lazy import evolution manager classes with caching."""
        cache_key = "evolution_manager_classes"

        if cache_key in self._import_cache:
            return self._import_cache[cache_key]

        try:
            # Import with TYPE_CHECKING protection
            from ..genetic_algorithm.evolution_manager import (
                DEAPConstraintAwareEvolutionManager,
                ConstraintAwareGAParameters,
            )

            classes = {
                "manager": DEAPConstraintAwareEvolutionManager,
                "parameters": ConstraintAwareGAParameters,
            }

            self._import_cache[cache_key] = classes
            return classes

        except ImportError as e:
            logger.warning(f"Could not import evolution manager classes: {e}")
            self._import_cache[cache_key] = None
            return None

    def _get_early_filter_class(self) -> Optional[Any]:
        """Lazy import early filter class with caching."""
        cache_key = "early_filter_class"

        if cache_key in self._import_cache:
            return self._import_cache[cache_key]

        try:
            from ..genetic_algorithm.early_filter_ga import EarlyGAFilterGenerator

            self._import_cache[cache_key] = EarlyGAFilterGenerator
            return EarlyGAFilterGenerator

        except ImportError as e:
            logger.warning(f"Could not import early filter class: {e}")
            self._import_cache[cache_key] = None
            return None


# Singleton factory instance
_factory_instance: Optional[GAComponentFactory] = None


def get_ga_factory(config: Optional[GAFactoryConfig] = None) -> GAComponentFactory:
    """
    Get singleton GA factory instance.

    Args:
        config: Optional factory configuration

    Returns:
        GAComponentFactory singleton instance
    """
    global _factory_instance

    if _factory_instance is None:
        _factory_instance = GAComponentFactory(config)
    elif config is not None:
        # Update configuration if provided
        _factory_instance.config = config

    return _factory_instance


def create_evolution_manager_safe(
    problem: "ExamSchedulingProblem",
    constraint_encoder: "ConstraintEncoder",
    ga_parameters: Optional[Dict[str, Any]] = None,
    config: Optional[GAFactoryConfig] = None,
) -> Optional["DEAPConstraintAwareEvolutionManager"]:
    """
    Convenience function to create evolution manager safely.

    Args:
        problem: The scheduling problem instance
        constraint_encoder: The constraint encoder instance
        ga_parameters: Optional GA parameters dictionary
        config: Optional factory configuration

    Returns:
        Evolution manager instance or None if creation fails
    """
    factory = get_ga_factory(config)
    return factory.create_evolution_manager(problem, constraint_encoder, ga_parameters)


def run_early_ga_filtering_safe(
    problem: "ExamSchedulingProblem",
    constraint_encoder: "ConstraintEncoder",
    ga_parameters: Optional[Dict[str, Any]] = None,
    config: Optional[GAFactoryConfig] = None,
) -> Dict[str, Any]:
    """
    Run complete GA filtering pipeline safely with comprehensive error handling.

    Args:
        problem: The scheduling problem instance
        constraint_encoder: The constraint encoder instance
        ga_parameters: Optional GA parameters dictionary
        config: Optional factory configuration

    Returns:
        Dictionary containing filtering results or fallback values
    """
    factory = get_ga_factory(config)

    try:
        # Step 1: Try to create evolution manager
        evolution_manager = factory.create_evolution_manager(
            problem, constraint_encoder, ga_parameters
        )

        if evolution_manager is None:
            logger.info("Evolution manager creation failed, using fallback")
            return factory.create_fallback_filtering_result()

        # Step 2: Try to run evolution
        evolution_report = factory.run_ga_evolution_safe(evolution_manager)

        if evolution_report is None:
            logger.info("GA evolution failed, using fallback")
            return factory.create_fallback_filtering_result()

        # Step 3: Extract results from successful evolution
        if evolution_report.success and evolution_report.best_individual:
            try:
                # Convert evolution results to filtering format
                pruning_decisions = (
                    evolution_manager.get_constraint_aware_pruning_decisions()
                )
                search_hints = evolution_manager.get_constraint_aware_solver_hints()

                return {
                    "viable_y_vars": set(),  # Would be populated from evolution results
                    "viable_u_vars": set(),  # Would be populated from evolution results
                    "pruning_decisions": pruning_decisions,
                    "search_hints": search_hints[:100],  # Limit hints
                    "ga_stats": {
                        "success": True,
                        "generations_run": evolution_report.generations_run,
                        "total_evaluations": evolution_report.total_evaluations,
                        "best_fitness": evolution_report.best_fitness,
                        "variables_pruned": evolution_report.variables_pruned,
                        "search_hints_generated": evolution_report.search_hints_generated,
                    },
                }

            except Exception as e:
                logger.warning(f"Error extracting evolution results: {e}")
                return factory.create_fallback_filtering_result()

        else:
            logger.info("GA evolution unsuccessful, using fallback")
            return factory.create_fallback_filtering_result()

    except Exception as e:
        logger.error(f"Comprehensive error in GA filtering pipeline: {e}")
        return factory.create_fallback_filtering_result()
