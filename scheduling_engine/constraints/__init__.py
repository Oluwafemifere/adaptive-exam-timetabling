# scheduling_engine/constraints/__init__.py

"""
Enhanced Constraints Module with Database Integration

This module contains all constraint implementations for the exam scheduling system,
organized into hard constraints (mandatory) and soft constraints (optimization objectives).
Enhanced with database integration for dynamic constraint management.

The constraints are used by both CP-SAT and GA components to:
1. Validate solution feasibility (hard constraints)
2. Calculate optimization objectives (soft constraints)
3. Guide search strategies and variable selection
4. Provide solution quality metrics
5. Support database-driven configuration and parameter management

Enhanced Architecture:
- Hard constraints must be satisfied for feasible solutions
- Soft constraints contribute to objective function for optimization
- Constraints can be loaded from database dynamically
- Database configurations override default parameters
- Constraint sets can be defined via database configurations
- Each constraint supports pluggable parameter modification
"""

from typing import Dict, List, Any, Optional, Type
from uuid import UUID
import logging

# Enhanced imports with database integration
from . import hard_constraints
from . import soft_constraints

# Import specific constraint classes for convenience
from .hard_constraints import (
    NoStudentConflictConstraint,
    RoomCapacityConstraint,
    TimeAvailabilityConstraint,
    CarryoverPriorityConstraint,
)

from .soft_constraints import (
    ExamDistributionConstraint,
    RoomUtilizationConstraint,
    InvigilatorBalanceConstraint,
    StudentTravelConstraint,
)

# Import enhanced constraint registry
from ..core.constraint_registry import (
    ConstraintRegistry,
    BaseConstraint,
    ConstraintDefinition,
    ConstraintType,
)

try:
    # Check if backend is available by trying to import a module
    import app.services.data_retrieval

    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False

logger = logging.getLogger(__name__)

# Export all constraint classes
__all__ = [
    # Modules
    "hard_constraints",
    "soft_constraints",
    # Hard constraints
    "NoStudentConflictConstraint",
    "RoomCapacityConstraint",
    "TimeAvailabilityConstraint",
    "CarryoverPriorityConstraint",
    # Soft constraints
    "ExamDistributionConstraint",
    "RoomUtilizationConstraint",
    "InvigilatorBalanceConstraint",
    "StudentTravelConstraint",
    # Enhanced registry components
    "ConstraintRegistry",
    "BaseConstraint",
    "ConstraintDefinition",
    "create_enhanced_constraint_registry",
    "load_constraint_set_from_database",
    "get_constraint_factory",
]


# Enhanced constraint registry combining built-in and database constraints
def create_enhanced_constraint_registry(db_session=None) -> ConstraintRegistry:
    """
    Create enhanced constraint registry with optional database integration

    Args:
        db_session: Optional database session for dynamic constraint loading

    Returns:
        Enhanced ConstraintRegistry instance
    """
    registry = ConstraintRegistry(db_session=db_session)
    return registry


async def load_constraint_set_from_database(
    configuration_id: UUID, db_session, fallback_to_defaults: bool = True
) -> List[BaseConstraint]:
    """
    Load constraint set from database configuration with fallback

    Args:
        configuration_id: Database configuration ID
        db_session: Database session
        fallback_to_defaults: Whether to fallback to defaults if loading fails

    Returns:
        List of configured constraint instances
    """
    try:
        registry = create_enhanced_constraint_registry(db_session)

        # Load database constraints first
        if BACKEND_AVAILABLE:
            await registry.load_database_constraints()

        # Create constraint set from configuration
        constraints = await registry.create_constraint_set_from_configuration(
            configuration_id
        )

        if not constraints and fallback_to_defaults:
            logger.warning(
                f"No constraints loaded from configuration {configuration_id}, using defaults"
            )
            constraints = registry.create_default_constraint_set()

        logger.info(
            f"Loaded {len(constraints)} constraints from configuration {configuration_id}"
        )
        return constraints

    except Exception as e:
        logger.error(f"Error loading constraint set from database: {e}")

        if fallback_to_defaults:
            registry = create_enhanced_constraint_registry()
            return registry.create_default_constraint_set()
        else:
            raise


class ConstraintFactory:
    """
    Factory class for creating pluggable constraints with database support
    """

    def __init__(self, db_session=None):
        self.registry = create_enhanced_constraint_registry(db_session)
        self.db_session = db_session

    async def create_constraint_from_code(
        self,
        constraint_code: str,
        weight: Optional[float] = None,
        parameters: Optional[Dict[str, Any]] = None,
        configuration_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[BaseConstraint]:
        """
        Create constraint instance from database code with configuration support

        Args:
            constraint_code: Database constraint rule code
            weight: Optional custom weight
            parameters: Optional parameter overrides
            configuration_context: Database configuration context

        Returns:
            Configured constraint instance or None
        """
        try:
            # Load from database if available
            if BACKEND_AVAILABLE and self.db_session:
                await self.registry.load_database_constraints()

            return await self.registry.create_constraint_instance(
                constraint_code,
                weight=weight,
                parameters=parameters,
                database_config=configuration_context,
            )

        except Exception as e:
            logger.error(f"Error creating constraint from code {constraint_code}: {e}")
            return None

    async def create_constraint_set_for_session(
        self, session_id: UUID, configuration_id: Optional[UUID] = None
    ) -> List[BaseConstraint]:
        """
        Create complete constraint set for a scheduling session

        Args:
            session_id: Academic session ID
            configuration_id: Optional configuration ID for custom constraints

        Returns:
            Complete set of configured constraints
        """
        try:
            if configuration_id:
                # Use specific configuration
                return await load_constraint_set_from_database(
                    configuration_id, self.db_session
                )
            else:
                # Use default constraint set
                if BACKEND_AVAILABLE and self.db_session:
                    await self.registry.load_database_constraints()

                return self.registry.create_default_constraint_set()

        except Exception as e:
            logger.error(f"Error creating constraint set for session {session_id}: {e}")
            # Always fallback to built-in defaults
            return self.registry.create_default_constraint_set()

    async def refresh_database_constraints(self) -> None:
        """Refresh constraint definitions from database"""
        if BACKEND_AVAILABLE and self.db_session:
            await self.registry.refresh_database_constraints()

    def get_available_constraints(self) -> Dict[str, ConstraintDefinition]:
        """Get all available constraint definitions"""
        return self.registry.get_all_definitions()

    async def validate_constraint_configuration(
        self, config: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Validate constraint configuration against schemas"""
        return await self.registry.validate_constraint_configuration(config)


# Global factory instance for convenient access
def get_constraint_factory(db_session=None) -> ConstraintFactory:
    """Get constraint factory instance"""
    return ConstraintFactory(db_session)


# Enhanced legacy compatibility functions with database support
def get_constraint_class(constraint_id: str) -> Optional[Type[BaseConstraint]]:
    """
    Legacy function: Get constraint class by identifier
    Enhanced to search both local and database constraints
    """
    registry = create_enhanced_constraint_registry()
    definition = registry.get_constraint_definition(constraint_id.upper())
    return definition.constraint_class if definition else None


def get_all_constraint_classes() -> Dict[str, Type[BaseConstraint]]:
    """
    Legacy function: Get all available constraint classes
    Enhanced to include database-loaded constraints
    """
    registry = create_enhanced_constraint_registry()
    return {
        code: defn.constraint_class
        for code, defn in registry.get_all_definitions().items()
        if defn.constraint_class is not None
    }


def get_hard_constraint_classes() -> Dict[str, Type[BaseConstraint]]:
    """Legacy function: Get only hard constraint classes"""
    registry = create_enhanced_constraint_registry()
    return {
        defn.constraint_id: defn.constraint_class
        for defn in registry.get_definitions_by_type(ConstraintType.HARD)
        if defn.constraint_class is not None
    }


def get_soft_constraint_classes() -> Dict[str, Type[BaseConstraint]]:
    """Legacy function: Get only soft constraint classes"""
    registry = create_enhanced_constraint_registry()
    return {
        defn.constraint_id: defn.constraint_class
        for defn in registry.get_definitions_by_type(ConstraintType.SOFT)
        if defn.constraint_class is not None
    }


async def create_constraint_instance(
    constraint_id: str, db_session=None, **kwargs
) -> Optional[BaseConstraint]:
    """
    Enhanced legacy function: Create instance of constraint by identifier with database support
    """
    registry = create_enhanced_constraint_registry(db_session)

    if BACKEND_AVAILABLE and db_session:
        await registry.load_database_constraints()

    return await registry.create_constraint_instance(constraint_id, **kwargs)


async def validate_constraint_set(
    constraint_ids: List[str], db_session=None
) -> Dict[str, Any]:
    """
    Enhanced constraint set validation with database support
    """
    registry = create_enhanced_constraint_registry(db_session)

    if BACKEND_AVAILABLE and db_session:
        await registry.load_database_constraints()

    # Initialize validation result with proper typing
    validation_result: Dict[str, Any] = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "missing_essential": [],
        "incompatible_pairs": [],
        "hard_constraints": [],
        "soft_constraints": [],
        "database_constraints": [],
    }

    # Enhanced validation with database constraint support
    for constraint_id in constraint_ids:
        definition = registry.get_constraint_definition(constraint_id.upper())

        if not definition:
            validation_result["errors"].append(f"Unknown constraint: {constraint_id}")
            validation_result["valid"] = False
        else:
            # Categorize constraint
            if definition.constraint_type == ConstraintType.HARD:
                validation_result["hard_constraints"].append(constraint_id)
            else:
                validation_result["soft_constraints"].append(constraint_id)

            # Track database-loaded constraints
            if definition.database_rule_id:
                validation_result["database_constraints"].append(constraint_id)

    # Check for essential hard constraints
    essential_constraints = ["NO_STUDENT_CONFLICT", "ROOM_CAPACITY"]
    for essential in essential_constraints:
        if essential not in [c.upper() for c in constraint_ids]:
            validation_result["missing_essential"].append(essential)
            validation_result["warnings"].append(
                f"Missing essential constraint: {essential}"
            )

    return validation_result


# Enhanced compatibility with existing constraint registries
ALL_CONSTRAINT_REGISTRY = {}


def _initialize_legacy_registry():
    """Initialize legacy registry for backward compatibility"""
    global ALL_CONSTRAINT_REGISTRY

    # Combine hard and soft constraint registries
    ALL_CONSTRAINT_REGISTRY.update(hard_constraints.HARD_CONSTRAINT_REGISTRY)
    ALL_CONSTRAINT_REGISTRY.update(soft_constraints.SOFT_CONSTRAINT_REGISTRY)

    logger.info(
        f"Initialized legacy constraint registry with {len(ALL_CONSTRAINT_REGISTRY)} constraints"
    )


# Initialize on module load
_initialize_legacy_registry()
