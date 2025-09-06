# scheduling_engine/constraints/constraint_manager.py

"""
Comprehensive Constraint Manager

This module provides a unified interface for managing all constraints in the
exam scheduling system, with database integration and dynamic configuration support.
"""

from typing import Dict, List, Any, Optional, Type, Union, cast
from uuid import UUID
import logging
from collections import defaultdict
from dataclasses import dataclass
import time

from sqlalchemy.ext.asyncio import AsyncSession
from app.services.data_retrieval.constraint_data import ConstraintData

BACKEND_AVAILABLE = True
SQLAlchemyAsyncSession = AsyncSession


from .enhanced_base_constraint import EnhancedBaseConstraint
from .hard_constraints import (
    HARD_CONSTRAINT_REGISTRY,
    get_essential_hard_constraints,
    validate_hard_constraint_set,
)
from .soft_constraints import (
    SOFT_CONSTRAINT_REGISTRY,
    get_optimization_focused_constraints,
    validate_soft_constraint_set,
)
from ..core.constraint_registry import (
    ConstraintType,
    ConstraintCategory,
)
from ..core.problem_model import ExamSchedulingProblem
from ..core.solution import TimetableSolution

logger = logging.getLogger(__name__)


@dataclass
class ConstraintSetSummary:
    """Summary of a constraint set"""

    total_constraints: int
    hard_constraints: int
    soft_constraints: int
    database_driven: int
    active_constraints: int
    total_weight: float
    categories: Dict[str, int]
    validation_status: Dict[str, Any]


class ConstraintManager:
    """
    Comprehensive constraint manager with database integration.

    This manager provides:
    - Dynamic constraint loading from database
    - Constraint set validation and optimization
    - Parameter management and overrides
    - Constraint lifecycle management
    - Performance monitoring and caching
    """

    def __init__(self, db_session: Optional[SQLAlchemyAsyncSession] = None):
        self.db_session = db_session
        self.constraint_data_service: Optional[ConstraintData] = None

        if BACKEND_AVAILABLE and db_session and ConstraintData is not None:
            try:
                self.constraint_data_service = ConstraintData(db_session)
            except Exception as e:
                logger.warning(f"Could not initialize constraint data service: {e}")

        # Active constraint instances
        self.active_constraints: List[EnhancedBaseConstraint] = []
        self.constraint_by_id: Dict[str, EnhancedBaseConstraint] = {}

        # Configuration tracking
        self.current_configuration_id: Optional[UUID] = None
        self.configuration_metadata: Dict[str, Any] = {}

        # Performance tracking
        self.evaluation_counts: Dict[str, int] = defaultdict(int)
        self.evaluation_times: Dict[str, float] = defaultdict(float)
        self.constraint_registry_cache: Dict[str, Type[EnhancedBaseConstraint]] = {}

        # Initialize registry cache
        self._initialize_registry_cache()

    def _initialize_registry_cache(self) -> None:
        """Initialize the constraint registry cache"""
        self.constraint_registry_cache.update(HARD_CONSTRAINT_REGISTRY)
        self.constraint_registry_cache.update(SOFT_CONSTRAINT_REGISTRY)

        logger.info(
            f"Initialized constraint registry with {len(self.constraint_registry_cache)} constraints"
        )

    async def load_configuration(
        self, configuration_id: Optional[UUID] = None
    ) -> ConstraintSetSummary:
        """
        Load constraint configuration from database or create default set.

        Args:
            configuration_id: Optional configuration ID to load

        Returns:
            Summary of the loaded constraint set
        """
        try:
            self.current_configuration_id = configuration_id

            if configuration_id and self.constraint_data_service:
                # Load from database
                constraints = await self._load_database_configuration(configuration_id)
                self.configuration_metadata = await self._load_configuration_metadata(
                    configuration_id
                )
            else:
                # Create default constraint set
                constraints = self._create_default_constraint_set()
                self.configuration_metadata = {"source": "default"}

            # Update active constraints
            self.active_constraints = constraints
            self.constraint_by_id = {c.constraint_id: c for c in constraints}

            # Generate summary
            summary = self._generate_constraint_summary()

            logger.info(
                f"Loaded constraint configuration: {summary.total_constraints} constraints "
                f"({summary.hard_constraints} hard, {summary.soft_constraints} soft)"
            )

            return summary

        except Exception as e:
            logger.error(f"Error loading constraint configuration: {e}")
            # Fallback to default set
            return await self.load_configuration(None)

    async def _load_database_configuration(
        self, configuration_id: UUID
    ) -> List[EnhancedBaseConstraint]:
        """Load constraints from database configuration"""
        if not self.constraint_data_service:
            raise RuntimeError("Database service not available")

        constraints = []

        try:
            # Get configuration constraints
            config_constraints = (
                await self.constraint_data_service.get_configuration_constraints(
                    configuration_id
                )
            )

            for config_constraint in config_constraints:
                if not config_constraint.get("is_enabled", True):
                    continue

                constraint_code = config_constraint.get("constraint_code")
                if not constraint_code:
                    logger.warning("Configuration constraint missing constraint_code")
                    continue

                # Get constraint class
                constraint_class = self.constraint_registry_cache.get(
                    constraint_code.upper()
                )
                if not constraint_class:
                    logger.warning(f"Unknown constraint code: {constraint_code}")
                    continue

                # Create database config
                database_config = {
                    "id": config_constraint.get("id"),
                    "configuration_id": str(configuration_id),
                    "configuration_name": config_constraint.get("configuration_name"),
                    "constraint_code": constraint_code,
                    "constraint_name": config_constraint.get("constraint_name"),
                    "constraint_type": config_constraint.get("constraint_type"),
                    "category_name": config_constraint.get("category_name"),
                    "weight": config_constraint.get("weight", 1.0),
                    "custom_parameters": config_constraint.get("custom_parameters", {}),
                    "is_enabled": config_constraint.get("is_enabled", True),
                    "rule": {
                        "id": config_constraint.get("constraint_id"),
                        "name": config_constraint.get("constraint_name"),
                        "constraint_type": config_constraint.get("constraint_type"),
                        "default_weight": config_constraint.get("weight", 1.0),
                    },
                    "config": {
                        "configuration_id": str(configuration_id),
                        "weight": config_constraint.get("weight", 1.0),
                        "custom_parameters": config_constraint.get(
                            "custom_parameters", {}
                        ),
                        "is_enabled": config_constraint.get("is_enabled", True),
                    },
                }

                # Create constraint instance
                try:
                    # Get constraint info from registry for required parameters
                    constraint_info = self._get_constraint_info(constraint_code)

                    constraint = constraint_class(
                        constraint_id=constraint_code,
                        name=constraint_info.get("name", constraint_code),
                        constraint_type=constraint_info.get(
                            "constraint_type", ConstraintType.SOFT
                        ),
                        category=constraint_info.get(
                            "category", ConstraintCategory.OPTIMIZATION_CONSTRAINTS
                        ),
                        database_config=database_config,
                    )
                    constraint.update_from_database_config(database_config)
                    constraints.append(constraint)

                    logger.debug(f"Created database constraint: {constraint_code}")

                except Exception as e:
                    logger.error(f"Error creating constraint {constraint_code}: {e}")
                    continue

            return constraints

        except Exception as e:
            logger.error(f"Error loading database configuration: {e}")
            raise

    def _get_constraint_info(self, constraint_code: str) -> Dict[str, Any]:
        """Get constraint information for creating instances"""
        # This would typically come from a constraint registry
        # For now, return default values based on common patterns
        constraint_code_upper = constraint_code.upper()

        # Hard constraints
        if constraint_code_upper in HARD_CONSTRAINT_REGISTRY:
            return {
                "constraint_type": ConstraintType.HARD,
                "category": (
                    ConstraintCategory.STUDENT_CONSTRAINTS
                    if "STUDENT" in constraint_code_upper
                    else (
                        ConstraintCategory.RESOURCE_CONSTRAINTS
                        if "ROOM" in constraint_code_upper
                        else ConstraintCategory.TEMPORAL_CONSTRAINTS
                    )
                ),
                "name": constraint_code_upper.replace("_", " ").title(),
            }

        # Soft constraints
        return {
            "constraint_type": ConstraintType.SOFT,
            "category": ConstraintCategory.OPTIMIZATION_CONSTRAINTS,
            "name": constraint_code_upper.replace("_", " ").title(),
        }

    async def _load_configuration_metadata(
        self, configuration_id: UUID
    ) -> Dict[str, Any]:
        """Load configuration metadata from database"""
        if not self.constraint_data_service:
            return {"source": "database", "configuration_id": str(configuration_id)}

        try:
            # This would load configuration metadata if available
            # For now, return basic info
            return {
                "source": "database",
                "configuration_id": str(configuration_id),
                "loaded_at": str(UUID()),  # Timestamp placeholder
            }
        except Exception as e:
            logger.error(f"Error loading configuration metadata: {e}")
            return {
                "source": "database_error",
                "configuration_id": str(configuration_id),
            }

    def _create_default_constraint_set(self) -> List[EnhancedBaseConstraint]:
        """Create default constraint set with balanced weights"""
        constraints = []

        # Essential hard constraints
        essential_hard = get_essential_hard_constraints()
        for constraint_code in essential_hard:
            constraint_class = self.constraint_registry_cache.get(constraint_code)
            if constraint_class:
                try:
                    constraint_info = self._get_constraint_info(constraint_code)
                    constraint = constraint_class(
                        constraint_id=constraint_code,
                        name=constraint_info["name"],
                        constraint_type=constraint_info["constraint_type"],
                        category=constraint_info["category"],
                    )
                    constraints.append(constraint)
                except Exception as e:
                    logger.error(
                        f"Error creating default hard constraint {constraint_code}: {e}"
                    )

        # Important soft constraints with balanced weights
        optimization_constraints = get_optimization_focused_constraints()
        for constraint_code, priority in optimization_constraints:
            constraint_class = self.constraint_registry_cache.get(constraint_code)
            if constraint_class:
                try:
                    # Weight decreases with priority (lower priority = lower weight)
                    weight = 1.0 - (priority - 1) * 0.1
                    constraint_info = self._get_constraint_info(constraint_code)
                    constraint = constraint_class(
                        constraint_id=constraint_code,
                        name=constraint_info["name"],
                        constraint_type=constraint_info["constraint_type"],
                        category=constraint_info["category"],
                        weight=weight,
                    )
                    constraints.append(constraint)
                except Exception as e:
                    logger.error(
                        f"Error creating default soft constraint {constraint_code}: {e}"
                    )

        logger.info(
            f"Created default constraint set with {len(constraints)} constraints"
        )
        return constraints

    def get_constraints_by_type(
        self, constraint_type: ConstraintType
    ) -> List[EnhancedBaseConstraint]:
        """Get all constraints of a specific type"""
        return [
            constraint
            for constraint in self.active_constraints
            if constraint.constraint_type == constraint_type and constraint.is_active
        ]

    def get_constraints_by_category(
        self, category: ConstraintCategory
    ) -> List[EnhancedBaseConstraint]:
        """Get all constraints in a specific category"""
        return [
            constraint
            for constraint in self.active_constraints
            if constraint.category == category and constraint.is_active
        ]

    def get_constraint_by_id(
        self, constraint_id: str
    ) -> Optional[EnhancedBaseConstraint]:
        """Get constraint by ID"""
        return self.constraint_by_id.get(constraint_id.upper())

    def add_constraint(self, constraint: EnhancedBaseConstraint) -> bool:
        """Add a constraint to the active set"""
        try:
            if constraint.constraint_id in self.constraint_by_id:
                logger.warning(
                    f"Constraint {constraint.constraint_id} already exists, replacing"
                )
                self.remove_constraint(constraint.constraint_id)

            self.active_constraints.append(constraint)
            self.constraint_by_id[constraint.constraint_id] = constraint

            logger.info(f"Added constraint: {constraint.constraint_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding constraint {constraint.constraint_id}: {e}")
            return False

    def remove_constraint(self, constraint_id: str) -> bool:
        """Remove a constraint from the active set"""
        try:
            constraint_id_upper = constraint_id.upper()

            if constraint_id_upper not in self.constraint_by_id:
                logger.warning(f"Constraint {constraint_id} not found")
                return False

            # Remove from both structures
            constraint = self.constraint_by_id[constraint_id_upper]
            self.active_constraints.remove(constraint)
            del self.constraint_by_id[constraint_id_upper]

            logger.info(f"Removed constraint: {constraint_id}")
            return True

        except Exception as e:
            logger.error(f"Error removing constraint {constraint_id}: {e}")
            return False

    def update_constraint_weight(self, constraint_id: str, new_weight: float) -> bool:
        """Update the weight of a specific constraint"""
        try:
            constraint = self.get_constraint_by_id(constraint_id)
            if not constraint:
                logger.error(f"Constraint {constraint_id} not found")
                return False

            if new_weight < 0:
                logger.error("Constraint weight cannot be negative")
                return False

            old_weight = constraint.weight
            constraint.weight = new_weight
            constraint.reset()  # Clear any caches

            logger.info(f"Updated {constraint_id} weight: {old_weight} -> {new_weight}")
            return True

        except Exception as e:
            logger.error(f"Error updating constraint weight: {e}")
            return False

    def update_constraint_parameters(
        self, constraint_id: str, parameters: Dict[str, Any]
    ) -> bool:
        """Update parameters for a specific constraint"""
        try:
            constraint = self.get_constraint_by_id(constraint_id)
            if not constraint:
                logger.error(f"Constraint {constraint_id} not found")
                return False

            constraint.update_parameters(parameters)

            logger.info(
                f"Updated {constraint_id} parameters: {list(parameters.keys())}"
            )
            return True

        except Exception as e:
            logger.error(f"Error updating constraint parameters: {e}")
            return False

    def validate_constraint_set(self) -> Dict[str, Any]:
        """Validate the current constraint set"""
        hard_codes = [
            c.constraint_id for c in self.get_constraints_by_type(ConstraintType.HARD)
        ]
        soft_codes = [
            c.constraint_id for c in self.get_constraints_by_type(ConstraintType.SOFT)
        ]

        hard_validation = validate_hard_constraint_set(hard_codes)
        soft_validation = validate_soft_constraint_set(soft_codes)

        # Validate individual constraints
        constraint_errors = []
        for constraint in self.active_constraints:
            errors = constraint.validate_parameters(constraint.parameters)
            if errors:
                constraint_errors.extend(
                    [f"{constraint.constraint_id}: {error}" for error in errors]
                )

        overall_valid = (
            hard_validation["valid"]
            and soft_validation["valid"]
            and len(constraint_errors) == 0
        )

        return {
            "overall_valid": overall_valid,
            "hard_constraint_validation": hard_validation,
            "soft_constraint_validation": soft_validation,
            "individual_constraint_errors": constraint_errors,
            "total_constraints": len(self.active_constraints),
            "active_constraints": len(
                [c for c in self.active_constraints if c.is_active]
            ),
        }

    def evaluate_all_constraints(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> Dict[str, Any]:
        """
        Evaluate all active constraints against a solution.

        Returns comprehensive evaluation results with performance tracking.
        """
        start_time = time.time()

        results = {
            "total_violations": 0,
            "total_penalty": 0.0,
            "constraint_results": {},
            "hard_constraint_violations": 0,
            "soft_constraint_violations": 0,
            "evaluation_time": 0.0,
        }

        try:
            for constraint in self.active_constraints:
                if not constraint.is_active:
                    continue

                constraint_start = time.time()

                try:
                    violations = constraint.evaluate(problem, solution)
                    constraint_penalty = sum(v.penalty for v in violations)
                    weighted_penalty = constraint_penalty * constraint.weight

                    # Update statistics
                    results["total_violations"] = cast(
                        int, results["total_violations"]
                    ) + len(violations)
                    results["total_penalty"] = (
                        cast(float, results["total_penalty"]) + weighted_penalty
                    )

                    if constraint.constraint_type == ConstraintType.HARD:
                        results["hard_constraint_violations"] = cast(
                            int, results["hard_constraint_violations"]
                        ) + len(violations)
                    else:
                        results["soft_constraint_violations"] = cast(
                            int, results["soft_constraint_violations"]
                        ) + len(violations)

                    # Store individual results
                    constraint_results = cast(
                        Dict[str, Any], results["constraint_results"]
                    )
                    constraint_results[constraint.constraint_id] = {
                        "violations": len(violations),
                        "penalty": constraint_penalty,
                        "weighted_penalty": weighted_penalty,
                        "is_satisfied": len(violations) == 0,
                        "constraint_type": constraint.constraint_type.value,
                        "evaluation_time": time.time() - constraint_start,
                    }

                    # Update performance stats
                    eval_key = f"{constraint.constraint_id}_evaluations"
                    self.evaluation_counts[eval_key] = (
                        self.evaluation_counts.get(eval_key, 0) + 1
                    )

                except Exception as e:
                    logger.error(
                        f"Error evaluating constraint {constraint.constraint_id}: {e}"
                    )
                    constraint_results = cast(
                        Dict[str, Any], results["constraint_results"]
                    )
                    constraint_results[constraint.constraint_id] = {
                        "error": str(e),
                        "violations": 0,
                        "penalty": 0.0,
                        "weighted_penalty": 0.0,
                        "is_satisfied": False,
                    }

            results["evaluation_time"] = time.time() - start_time
            results["is_feasible"] = (
                cast(int, results["hard_constraint_violations"]) == 0
            )

            # Update global stats
            self.evaluation_counts["total_evaluations"] = (
                self.evaluation_counts.get("total_evaluations", 0) + 1
            )
            self.evaluation_times["total_evaluation_time"] = self.evaluation_times.get(
                "total_evaluation_time", 0.0
            ) + cast(float, results["evaluation_time"])

            return results

        except Exception as e:
            logger.error(f"Error in constraint evaluation: {e}")
            results["error"] = str(e)
            results["evaluation_time"] = time.time() - start_time
            return results

    def _generate_constraint_summary(self) -> ConstraintSetSummary:
        """Generate summary of current constraint set"""
        hard_constraints = self.get_constraints_by_type(ConstraintType.HARD)
        soft_constraints = self.get_constraints_by_type(ConstraintType.SOFT)

        # Count by category
        categories: Dict[str, int] = defaultdict(int)
        for constraint in self.active_constraints:
            if hasattr(constraint.category, "value"):
                categories[constraint.category.value] += 1
            else:
                categories[str(constraint.category)] += 1

        # Database-driven constraints
        database_driven = len(
            [
                c
                for c in self.active_constraints
                if c.database_config and c.database_config.get("configuration_id")
            ]
        )

        # Validation status
        validation = self.validate_constraint_set()

        # Total weight
        total_weight = sum(c.weight for c in self.active_constraints if c.is_active)

        return ConstraintSetSummary(
            total_constraints=len(self.active_constraints),
            hard_constraints=len(hard_constraints),
            soft_constraints=len(soft_constraints),
            database_driven=database_driven,
            active_constraints=len([c for c in self.active_constraints if c.is_active]),
            total_weight=total_weight,
            categories=dict(categories),
            validation_status=validation,
        )

    def get_performance_statistics(self) -> Dict[str, Any]:
        """Get performance statistics for constraint evaluation"""
        total_evals = self.evaluation_counts.get("total_evaluations", 0)
        total_time = self.evaluation_times.get("total_evaluation_time", 0.0)

        avg_time = total_time / max(total_evals, 1) if total_evals > 0 else 0.0

        return {
            "total_evaluations": total_evals,
            "total_evaluation_time": total_time,
            "average_evaluation_time": avg_time,
            "constraint_specific_stats": {
                k: v
                for k, v in self.evaluation_counts.items()
                if k not in ["total_evaluations"]
            },
            "active_constraints": len(self.active_constraints),
            "current_configuration": (
                str(self.current_configuration_id)
                if self.current_configuration_id
                else "default"
            ),
        }

    def reset_all_constraints(self) -> None:
        """Reset all constraints and clear caches"""
        for constraint in self.active_constraints:
            constraint.reset()

        self.evaluation_counts.clear()
        self.evaluation_times.clear()
        logger.info("Reset all constraints and cleared caches")

    async def refresh_configuration(self) -> ConstraintSetSummary:
        """Refresh the current configuration from database"""
        if self.current_configuration_id:
            return await self.load_configuration(self.current_configuration_id)
        else:
            return await self.load_configuration(None)

    def export_configuration(self) -> Dict[str, Any]:
        """Export current constraint configuration"""
        return {
            "configuration_id": (
                str(self.current_configuration_id)
                if self.current_configuration_id
                else None
            ),
            "metadata": self.configuration_metadata,
            "constraints": [
                {
                    "constraint_id": c.constraint_id,
                    "name": c.name,
                    "type": c.constraint_type.value,
                    "category": (
                        c.category.value
                        if hasattr(c.category, "value")
                        else str(c.category)
                    ),
                    "weight": c.weight,
                    "is_active": c.is_active,
                    "parameters": c.parameters,
                    "has_database_config": bool(c.database_config),
                }
                for c in self.active_constraints
            ],
            "summary": self._generate_constraint_summary().__dict__,
            "performance_stats": self.get_performance_statistics(),
        }
