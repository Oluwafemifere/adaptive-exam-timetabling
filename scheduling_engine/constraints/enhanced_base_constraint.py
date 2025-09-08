# scheduling_engine/constraints/enhanced_base_constraint.py

"""
Enhanced Base Constraint with Database Integration

This module provides the base class that all constraints inherit from, supporting
database-driven configuration and dynamic parameter management.
"""

from typing import Dict, List, Set, Any, Optional, Tuple
from uuid import UUID, uuid4
from abc import ABC, abstractmethod
import logging
from dataclasses import dataclass

from ..core.constraint_registry import (
    BaseConstraint,
)
from ..core.constraint_types import (
    ConstraintType,
    ConstraintCategory,
    ConstraintViolation,
    ConstraintSeverity,
    ConstraintDefinition,
)
from ..core.problem_model import ExamSchedulingProblem
from ..core.solution import TimetableSolution

logger = logging.getLogger(__name__)


class EnhancedBaseConstraint(BaseConstraint):
    """
    Enhanced base constraint class with comprehensive database integration.

    This class provides:
    - Database parameter management
    - Configuration validation
    - Standardized evaluation interface
    - Parameter merging and overrides
    - Constraint lifecycle management
    """

    def __init__(
        self,
        constraint_id: str,
        name: str,
        constraint_type: ConstraintType,
        category: ConstraintCategory,
        weight: float = 1.0,
        parameters: Optional[Dict[str, Any]] = None,
        database_config: Optional[Dict[str, Any]] = None,
        **kwargs,  # Add this to capture any extra arguments
    ):
        # Remove constraint_id from kwargs if present to avoid duplication
        kwargs.pop("constraint_id", None)

        super().__init__(
            constraint_id=constraint_id,
            name=name,
            constraint_type=constraint_type,
            category=category,
            weight=weight,
            parameters=parameters,
            database_config=database_config,
            **kwargs,  # Pass remaining kwargs to parent
        )

        # Enhanced state tracking
        self._evaluation_cache: Dict[str, Any] = {}
        self._parameter_validation_cache: List[str] = []
        self._last_problem_hash: Optional[str] = None
        self._is_initialized: bool = False  # Added missing attribute

        # Apply any additional configuration from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """
        Get parameter value with database override support and type safety.

        Priority order:
        1. Database custom parameters
        2. Database rule default parameters
        3. Instance parameters
        4. Default value
        """
        # Check database custom parameters first
        if self.database_config:
            custom_params = self.database_config.get("custom_parameters", {})
            if key in custom_params:
                return custom_params[key]

        # Check instance parameters
        if key in self.parameters:
            return self.parameters[key]

        # Check database rule defaults
        if self.database_config:
            rule_params = self.database_config.get("rule_parameters", {})
            if key in rule_params:
                return rule_params[key]

        return default

    def set_parameter(self, key: str, value: Any) -> None:
        """Set parameter value with validation"""
        # Validate parameter if validator exists
        validation_errors = self.validate_single_parameter(key, value)
        if validation_errors:
            raise ValueError(f"Invalid parameter {key}: {validation_errors}")

        self.parameters[key] = value

        # Clear validation cache since parameters changed
        self._parameter_validation_cache.clear()
        self._evaluation_cache.clear()

    def update_parameters(self, new_parameters: Dict[str, Any]) -> None:
        """Update multiple parameters with validation"""
        # Validate all parameters first
        all_params = self.parameters.copy()
        all_params.update(new_parameters)

        validation_errors = self.validate_parameters(all_params)
        if validation_errors:
            raise ValueError(f"Parameter validation failed: {validation_errors}")

        # If validation passes, update parameters
        self.parameters.update(new_parameters)
        self._parameter_validation_cache.clear()
        self._evaluation_cache.clear()

    def update_from_database_config(self, db_config: Dict[str, Any]) -> None:
        """Update constraint configuration from database with enhanced validation"""
        try:
            # Store the database config
            self.database_config = db_config.copy()

            # Extract rule information
            rule = db_config.get("rule", {})
            config = db_config.get("config", {})

            # Update constraint properties from database rule
            if "name" in rule:
                self.name = rule["name"]

            if "description" in rule:
                self.description = rule["description"]

            if "constraint_type" in rule:
                constraint_type_str = rule["constraint_type"].upper()
                if constraint_type_str in ["HARD", "SOFT"]:
                    self.constraint_type = (
                        ConstraintType.HARD
                        if constraint_type_str == "HARD"
                        else ConstraintType.SOFT
                    )

            if "default_weight" in rule:
                self.weight = float(rule["default_weight"])

            # Override with configuration-specific settings
            if "weight" in config:
                self.weight = float(config["weight"])

            # Update custom parameters
            custom_params = config.get("custom_parameters", {})
            if custom_params:
                # Validate before updating
                test_params = self.parameters.copy()
                test_params.update(custom_params)

                validation_errors = self.validate_parameters(test_params)
                if validation_errors:
                    logger.warning(
                        f"Database parameters for {self.constraint_id} failed validation: "
                        f"{validation_errors}"
                    )
                else:
                    self.parameters.update(custom_params)

            # Update activation status
            if "is_enabled" in config:
                self.is_active = bool(config["is_enabled"])
            elif "is_active" in rule:
                self.is_active = bool(rule["is_active"])

            # Store additional database context
            self.database_rule_id = rule.get("id")
            self.configuration_id = config.get("configuration_id")

            # Clear caches
            self._parameter_validation_cache.clear()
            self._evaluation_cache.clear()

            logger.debug(
                f"Updated constraint {self.constraint_id} from database: "
                f"weight={self.weight}, active={self.is_active}"
            )

        except Exception as e:
            logger.error(
                f"Error updating {self.constraint_id} from database config: {e}"
            )
            raise

    def evaluate(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """
        Enhanced evaluation with caching and comprehensive error handling.
        """
        if not self.is_active:
            return []

        try:
            # Check if we can use cached results
            problem_hash = self._calculate_problem_hash(problem, solution)

            if (
                self._last_problem_hash == problem_hash
                and "violations" in self._evaluation_cache
            ):
                return self._evaluation_cache["violations"]

            # Initialize if needed
            if not self._is_initialized:
                self.initialize(problem)
                self._is_initialized = True  # Mark as initialized

            # Perform evaluation
            violations = self._evaluate_implementation(problem, solution)

            # Enhance violations with database context
            for violation in violations:
                violation.constraint_code = self.constraint_id
                violation.database_rule_id = self.database_rule_id
                if self.configuration_id:
                    violation.violation_metadata["configuration_id"] = str(
                        self.configuration_id
                    )

            # Cache results
            self._evaluation_cache["violations"] = violations
            self._last_problem_hash = problem_hash

            return violations

        except Exception as e:
            logger.error(f"Error evaluating constraint {self.constraint_id}: {e}")
            return []

    @abstractmethod
    def _evaluate_implementation(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """
        Implementation-specific evaluation logic.

        Subclasses must implement this method to define their constraint logic.
        """
        pass

    def validate_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """
        Validate constraint parameters with enhanced checks.

        Returns list of validation error messages.
        """
        errors = []

        # Check basic parameter validity
        if self.weight < 0:
            errors.append("Constraint weight cannot be negative")

        if self.constraint_type == ConstraintType.HARD and self.weight != 1.0:
            logger.warning(
                f"Hard constraint {self.constraint_id} has non-standard weight: {self.weight}"
            )

        # Validate parameter types and ranges
        for key, value in parameters.items():
            param_errors = self.validate_single_parameter(key, value)
            errors.extend(param_errors)

        return errors

    def validate_single_parameter(self, key: str, value: Any) -> List[str]:
        """
        Validate a single parameter.

        Subclasses can override this for parameter-specific validation.
        """
        errors = []

        # Basic type checking for common parameters
        if key.endswith("_penalty") or key.endswith("_weight"):
            if not isinstance(value, (int, float)) or value < 0:
                errors.append(f"{key} must be a non-negative number")

        elif key.endswith("_threshold") or key.endswith("_limit"):
            if not isinstance(value, (int, float)) or value < 0:
                errors.append(f"{key} must be a non-negative number")

        elif key.endswith("_enabled") or key.startswith("enable_"):
            if not isinstance(value, bool):
                errors.append(f"{key} must be a boolean")

        return errors

    def get_constraint_info(self) -> Dict[str, Any]:
        """Get comprehensive constraint information"""
        return {
            "constraint_id": self.constraint_id,
            "name": self.name,
            "type": (
                self.constraint_type.value
                if hasattr(self.constraint_type, "value")
                else str(self.constraint_type)
            ),
            "category": (
                self.category.value
                if hasattr(self.category, "value")
                else str(self.category)
            ),
            "weight": self.weight,
            "is_active": self.is_active,
            "parameters": self.parameters.copy(),
            "database_config": self.database_config.copy(),
            "is_initialized": self._is_initialized,
            "database_rule_id": (
                str(self.database_rule_id) if self.database_rule_id else None
            ),
            "configuration_id": (
                str(self.configuration_id) if self.configuration_id else None
            ),
            "has_database_config": bool(self.database_config),
        }

    def get_evaluation_summary(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> Dict[str, Any]:
        """Get summary of constraint evaluation results"""
        violations = self.evaluate(problem, solution)

        total_penalty = sum(v.penalty for v in violations)
        severity_counts = {
            "critical": len(
                [v for v in violations if v.severity == ConstraintSeverity.CRITICAL]
            ),
            "high": len(
                [v for v in violations if v.severity == ConstraintSeverity.HIGH]
            ),
            "medium": len(
                [v for v in violations if v.severity == ConstraintSeverity.MEDIUM]
            ),
            "low": len([v for v in violations if v.severity == ConstraintSeverity.LOW]),
        }

        return {
            "constraint_id": self.constraint_id,
            "is_satisfied": len(violations) == 0,
            "violation_count": len(violations),
            "total_penalty": total_penalty,
            "weighted_penalty": total_penalty * self.weight,
            "severity_breakdown": severity_counts,
            "constraint_type": self.constraint_type.value,
            "is_active": self.is_active,
        }

    def reset(self) -> None:
        """Reset constraint state and clear caches"""
        self._evaluation_cache.clear()
        self._parameter_validation_cache.clear()
        self._last_problem_hash = None
        self._is_initialized = False  # Reset initialization state

    def _calculate_problem_hash(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> str:
        """Calculate a hash representing the current problem and solution state"""
        try:
            # Simple hash based on key identifiers
            # In a real implementation, this would be more sophisticated
            problem_elements = [
                len(problem.exams),
                len(problem.rooms),
                len(problem.time_slots),
                str(solution.id),
                (
                    str(solution.last_modified)
                    if hasattr(solution, "last_modified")
                    else ""
                ),
            ]

            return str(
                hash(tuple(str(e) for e in problem_elements))
            )  # Convert to string

        except Exception:
            # If hashing fails, return a random value to disable caching
            return str(uuid4())

    @abstractmethod
    def clone(
        self,
        new_weight: Optional[float] = None,
        new_parameters: Optional[Dict[str, Any]] = None,
    ) -> "EnhancedBaseConstraint":
        """
        Create a copy of this constraint with optional modifications.

        Subclasses must implement this method.
        """
        pass

    def __str__(self) -> str:
        """String representation of the constraint"""
        return (
            f"{self.__class__.__name__}("
            f"id={self.constraint_id}, "
            f"type={self.constraint_type.value}, "
            f"weight={self.weight}, "
            f"active={self.is_active})"
        )

    def __repr__(self) -> str:
        """Detailed representation of the constraint"""
        return (
            f"{self.__class__.__name__}("
            f"constraint_id='{self.constraint_id}', "
            f"name='{self.name}', "
            f"constraint_type={self.constraint_type}, "
            f"category={self.category}, "
            f"weight={self.weight}, "
            f"is_active={self.is_active}, "
            f"parameters={self.parameters}, "
            f"database_config={bool(self.database_config)})"
        )
