"""
DEAP Setup Module - Centralized DEAP initialization to prevent conflicts.

This module handles all DEAP creator initialization in one place to prevent
the "class already exists" errors that occur when multiple modules try to
create the same DEAP classes.
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Global flag to prevent multiple DEAP initializations
DEAP_INITIALIZED = False
DEAP_AVAILABLE = False

# Declare module-level variables to satisfy type checker
creator: Any = None
base: Any = None
tools: Any = None
algorithms: Any = None

try:
    from deap import base, creator, tools, algorithms

    DEAP_AVAILABLE = True
    logger.info("DEAP framework available")
except ImportError:
    DEAP_AVAILABLE = False
    logger.warning("DEAP framework not available. Install with: pip install deap")


def initialize_deap_creators() -> bool:
    """
    Initialize all DEAP creator classes once and only once.

    Returns:
        True if initialization successful, False otherwise
    """
    global DEAP_INITIALIZED

    if DEAP_INITIALIZED:
        logger.debug("DEAP creators already initialized")
        return True

    if not DEAP_AVAILABLE:
        logger.error("Cannot initialize DEAP creators - DEAP not available")
        return False

    try:
        # Create fitness classes - check if already exist first
        if not hasattr(creator, "FitnessMax"):
            creator.create("FitnessMax", base.Fitness, weights=(1.0,))

        if not hasattr(creator, "FitnessMultiMax"):
            creator.create(
                "FitnessMultiMax", base.Fitness, weights=(1.0, 1.0, 1.0, 1.0)
            )

        if not hasattr(creator, "FitnessMin"):
            creator.create("FitnessMin", base.Fitness, weights=(-1.0,))

        # Create individual classes
        if not hasattr(creator, "Individual"):
            # Safe access to FitnessMax with fallback
            fitness_class = getattr(creator, "FitnessMax", base.Fitness)
            creator.create("Individual", list, fitness=fitness_class)

        if not hasattr(creator, "MultiObjectiveIndividual"):
            # Safe access to FitnessMultiMax with fallback
            fitness_multi_class = getattr(creator, "FitnessMultiMax", base.Fitness)
            creator.create(
                "MultiObjectiveIndividual", list, fitness=fitness_multi_class
            )

        DEAP_INITIALIZED = True
        logger.info("DEAP creators initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize DEAP creators: {e}")
        return False


def get_deap_fitness_max() -> Optional[Any]:
    """Get FitnessMax class, initializing if needed."""
    if not DEAP_INITIALIZED:
        initialize_deap_creators()
    return getattr(creator, "FitnessMax", None) if DEAP_AVAILABLE else None


def get_deap_fitness_multi() -> Optional[Any]:
    """Get FitnessMultiMax class, initializing if needed."""
    if not DEAP_INITIALIZED:
        initialize_deap_creators()
    return getattr(creator, "FitnessMultiMax", None) if DEAP_AVAILABLE else None


def get_deap_individual() -> Optional[Any]:
    """Get Individual class, initializing if needed."""
    if not DEAP_INITIALIZED:
        initialize_deap_creators()
    return getattr(creator, "Individual", None) if DEAP_AVAILABLE else None


def get_deap_multi_objective_individual() -> Optional[Any]:
    """Get MultiObjectiveIndividual class, initializing if needed."""
    if not DEAP_INITIALIZED:
        initialize_deap_creators()
    return (
        getattr(creator, "MultiObjectiveIndividual", None) if DEAP_AVAILABLE else None
    )


def is_deap_available() -> bool:
    """Check if DEAP is available and initialized."""
    return DEAP_AVAILABLE and DEAP_INITIALIZED


def reset_deap_creators() -> None:
    """Reset DEAP creators for testing purposes."""
    global DEAP_INITIALIZED
    DEAP_INITIALIZED = False

    if DEAP_AVAILABLE and creator is not None:
        # Clear existing creators
        for attr_name in [
            "FitnessMax",
            "FitnessMultiMax",
            "FitnessMin",
            "Individual",
            "MultiObjectiveIndividual",
        ]:
            if hasattr(creator, attr_name):
                delattr(creator, attr_name)


# Auto-initialize on import
if DEAP_AVAILABLE:
    initialize_deap_creators()
