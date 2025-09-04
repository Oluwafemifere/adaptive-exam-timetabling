# backend/app/services/scheduling/admin_configuration_manager.py

"""
Administrative Configuration Manager for exam scheduling system.

Handles admin interface for constraint and objective selection, manages
constraint configuration templates and validates constraint combinations.
"""

from typing import Dict, List, Optional, Any, Tuple, Union
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
import logging
import json
from collections import defaultdict

# Import data retrieval services
from app.services.data_retrieval import ConstraintData, UserData, AuditData

# Import models
from app.models.constraints import (
    ConstraintCategory,
    ConstraintRule,
    ConfigurationConstraint,
)
from app.models.users import SystemConfiguration
from app.models.audit_logs import AuditLog

logger = logging.getLogger(__name__)


class ConfigurationTemplate(Enum):
    """Predefined configuration templates"""

    STANDARD = "standard"
    EMERGENCY = "emergency"
    EXAM_WEEK = "exam_week"
    FLEXIBLE = "flexible"
    STRICT = "strict"


class ObjectiveFunction(Enum):
    """Available objective functions"""

    MINIMIZE_CONFLICTS = "minimize_conflicts"
    MAXIMIZE_ROOM_UTILIZATION = "maximize_room_utilization"
    MINIMIZE_STUDENT_TRAVEL = "minimize_student_travel"
    BALANCE_WORKLOAD = "balance_workload"
    MINIMIZE_TIME_GAPS = "minimize_time_gaps"
    MULTI_OBJECTIVE = "multi_objective"


@dataclass
class ConstraintConfiguration:
    """Represents a constraint configuration"""

    constraint_id: UUID
    constraint_code: str
    constraint_name: str
    constraint_type: str
    is_enabled: bool
    weight: float
    custom_parameters: Dict[str, Any] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class ConfigurationValidationResult:
    """Result of configuration validation"""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    compatibility_issues: List[Dict[str, Any]] = field(default_factory=list)
    estimated_performance_impact: float = 0.0


class AdminConfigurationManager:
    """
    Manages administrative configuration for exam scheduling including
    constraint selection, objective functions, and configuration templates.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        # Initialize data retrieval services
        self.constraint_data = ConstraintData(session)
        self.user_data = UserData(session)
        self.audit_data = AuditData(session)

        # Configuration cache
        self._constraint_cache: Dict[UUID, Dict[str, Any]] = {}
        self._template_cache: Dict[str, Dict[str, Any]] = {}
        self._compatibility_matrix: Dict[Tuple[str, str], float] = {}

    async def initialize(self) -> None:
        """Initialize configuration manager"""
        try:
            logger.info("Initializing Administrative Configuration Manager")

            # Load constraint data
            await self._load_constraint_cache()

            # Load predefined templates
            await self._load_configuration_templates()

            # Build constraint compatibility matrix
            await self._build_compatibility_matrix()

            logger.info("Administrative Configuration Manager initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing configuration manager: {e}")
            raise

    async def _load_constraint_cache(self) -> None:
        """Load constraint data into cache"""
        try:
            constraints = await self.constraint_data.get_all_constraint_rules()
            for constraint in constraints:
                constraint_id = UUID(constraint["id"])
                self._constraint_cache[constraint_id] = constraint

            logger.info(f"Loaded {len(self._constraint_cache)} constraints into cache")

        except Exception as e:
            logger.error(f"Error loading constraint cache: {e}")

    async def _load_configuration_templates(self) -> None:
        """Load predefined configuration templates"""
        try:
            # Standard template - balanced approach
            self._template_cache[ConfigurationTemplate.STANDARD.value] = {
                "name": "Standard Configuration",
                "description": "Balanced configuration for regular exam scheduling",
                "objective_function": ObjectiveFunction.MULTI_OBJECTIVE.value,
                "objective_weights": {
                    "conflicts": 1.0,
                    "utilization": 0.7,
                    "student_travel": 0.5,
                    "workload": 0.6,
                },
                "constraint_weights": {
                    "hard_constraints": 1.0,
                    "soft_constraints": 0.5,
                    "preferences": 0.2,
                },
                "algorithm_parameters": {
                    "cp_sat_time_limit": 300,
                    "ga_generations": 100,
                    "ga_population_size": 50,
                },
            }

            # Emergency template - speed over optimization
            self._template_cache[ConfigurationTemplate.EMERGENCY.value] = {
                "name": "Emergency Configuration",
                "description": "Fast configuration for urgent scheduling needs",
                "objective_function": ObjectiveFunction.MINIMIZE_CONFLICTS.value,
                "objective_weights": {
                    "conflicts": 1.0,
                    "utilization": 0.3,
                    "student_travel": 0.1,
                    "workload": 0.2,
                },
                "constraint_weights": {
                    "hard_constraints": 1.0,
                    "soft_constraints": 0.2,
                    "preferences": 0.0,
                },
                "algorithm_parameters": {
                    "cp_sat_time_limit": 60,
                    "ga_generations": 20,
                    "ga_population_size": 20,
                },
            }

            # Exam week template - high quality results
            self._template_cache[ConfigurationTemplate.EXAM_WEEK.value] = {
                "name": "Exam Week Configuration",
                "description": "High-quality configuration for final exam periods",
                "objective_function": ObjectiveFunction.MULTI_OBJECTIVE.value,
                "objective_weights": {
                    "conflicts": 1.0,
                    "utilization": 0.9,
                    "student_travel": 0.8,
                    "workload": 0.7,
                },
                "constraint_weights": {
                    "hard_constraints": 1.0,
                    "soft_constraints": 0.8,
                    "preferences": 0.5,
                },
                "algorithm_parameters": {
                    "cp_sat_time_limit": 600,
                    "ga_generations": 200,
                    "ga_population_size": 100,
                },
            }

            logger.info(f"Loaded {len(self._template_cache)} configuration templates")

        except Exception as e:
            logger.error(f"Error loading configuration templates: {e}")

    async def _build_compatibility_matrix(self) -> None:
        """Build constraint compatibility matrix"""
        try:
            constraints = await self.constraint_data.get_all_constraint_rules()

            # Build compatibility matrix based on constraint types and categories
            for i, constraint1 in enumerate(constraints):
                for j, constraint2 in enumerate(constraints):
                    if i != j:
                        compatibility_score = (
                            await self._calculate_constraint_compatibility(
                                constraint1, constraint2
                            )
                        )
                        key = (constraint1["code"], constraint2["code"])
                        self._compatibility_matrix[key] = compatibility_score

            logger.info(
                f"Built compatibility matrix with {len(self._compatibility_matrix)} entries"
            )

        except Exception as e:
            logger.error(f"Error building compatibility matrix: {e}")

    async def _calculate_constraint_compatibility(
        self, constraint1: Dict[str, Any], constraint2: Dict[str, Any]
    ) -> float:
        """Calculate compatibility score between two constraints"""
        try:
            # Same category constraints are generally compatible
            if constraint1.get("category_name") == constraint2.get("category_name"):
                return 0.8

            # Hard constraints generally compatible with each other
            if (
                constraint1.get("constraint_type") == "hard"
                and constraint2.get("constraint_type") == "hard"
            ):
                return 0.9

            # Check for known incompatibilities
            incompatible_pairs = [
                ("STRICT_TIME_LIMITS", "FLEXIBLE_SCHEDULING"),
                ("NO_WEEKEND_EXAMS", "MAXIMIZE_TIME_USAGE"),
                ("MORNING_ONLY_COURSES", "EVENING_SCHEDULING"),
            ]

            for code1, code2 in incompatible_pairs:
                if (
                    constraint1.get("code") == code1
                    and constraint2.get("code") == code2
                ) or (
                    constraint1.get("code") == code2
                    and constraint2.get("code") == code1
                ):
                    return 0.2

            # Default compatibility
            return 0.6

        except Exception as e:
            logger.error(f"Error calculating constraint compatibility: {e}")
            return 0.5

    async def get_available_constraint_categories(
        self, user_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get available constraint categories for admin interface"""
        try:
            categories = await self.constraint_data.get_all_constraint_categories()

            # Enrich with usage statistics
            enriched_categories = []
            for category in categories:
                category_usage = await self._get_category_usage_stats(
                    UUID(category["id"])
                )

                enriched_category = {
                    **category,
                    "usage_stats": category_usage,
                    "is_recommended": category_usage["usage_frequency"] > 0.5,
                }
                enriched_categories.append(enriched_category)

            # Log access
            await self._log_admin_action(
                user_id,
                "get_constraint_categories",
                {"categories_count": len(enriched_categories)},
            )

            return enriched_categories

        except Exception as e:
            logger.error(f"Error getting constraint categories: {e}")
            return []

    async def _get_category_usage_stats(self, category_id: UUID) -> Dict[str, Any]:
        """Get usage statistics for a constraint category"""
        try:
            # Get all configurations using constraints from this category
            configurations = await self.constraint_data.get_configuration_constraints()

            category_constraints = [
                c
                for c in configurations
                if c.get("category_name")
                and UUID(c.get("constraint_id", "00000000-0000-0000-0000-000000000000"))
                in self._constraint_cache
            ]

            total_configs = len(configurations)
            category_usage = len(category_constraints)

            return {
                "total_configurations": total_configs,
                "category_usage_count": category_usage,
                "usage_frequency": category_usage / max(total_configs, 1),
                "average_weight": (
                    sum(c.get("weight", 0.0) for c in category_constraints)
                    / max(len(category_constraints), 1)
                ),
            }

        except Exception as e:
            logger.error(f"Error getting category usage stats: {e}")
            return {
                "total_configurations": 0,
                "category_usage_count": 0,
                "usage_frequency": 0.0,
                "average_weight": 0.0,
            }

    async def create_configuration(
        self,
        user_id: UUID,
        configuration_name: str,
        configuration_description: str,
        objective_function: ObjectiveFunction,
        constraint_configurations: List[ConstraintConfiguration],
        template_base: Optional[ConfigurationTemplate] = None,
        custom_parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create new scheduling configuration"""
        try:
            logger.info(
                f"Creating configuration '{configuration_name}' by user {user_id}"
            )

            # Validate configuration
            validation_result = await self.validate_configuration_combination(
                constraint_configurations, objective_function
            )

            if not validation_result.is_valid:
                return {
                    "success": False,
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                }

            # Create system configuration
            config_data = {
                "name": configuration_name,
                "description": configuration_description,
                "created_by": user_id,
                "is_default": False,
            }

            # Insert configuration into database
            new_config = SystemConfiguration(**config_data)
            self.session.add(new_config)
            await self.session.flush()

            # Create constraint configuration records
            constraint_records = []
            for constraint_config in constraint_configurations:
                constraint_record = ConfigurationConstraint(
                    configuration_id=new_config.id,
                    constraint_id=constraint_config.constraint_id,
                    weight=constraint_config.weight,
                    is_enabled=constraint_config.is_enabled,
                    custom_parameters=constraint_config.custom_parameters,
                )
                constraint_records.append(constraint_record)
                self.session.add(constraint_record)

            await self.session.commit()

            # Log creation
            await self._log_admin_action(
                user_id,
                "create_configuration",
                {
                    "configuration_id": str(new_config.id),
                    "configuration_name": configuration_name,
                    "constraint_count": len(constraint_configurations),
                    "objective_function": objective_function.value,
                },
            )

            return {
                "success": True,
                "configuration_id": str(new_config.id),
                "configuration_name": configuration_name,
                "validation_warnings": validation_result.warnings,
                "estimated_performance_impact": validation_result.estimated_performance_impact,
            }

        except Exception as e:
            logger.error(f"Error creating configuration: {e}")
            await self.session.rollback()
            return {
                "success": False,
                "errors": [f"Failed to create configuration: {str(e)}"],
            }

    async def validate_configuration_combination(
        self,
        constraint_configurations: List[ConstraintConfiguration],
        objective_function: ObjectiveFunction,
    ) -> ConfigurationValidationResult:
        """Validate constraint configuration combination"""
        try:
            result = ConfigurationValidationResult(is_valid=True)

            # Check individual constraints
            for config in constraint_configurations:
                if config.constraint_id not in self._constraint_cache:
                    result.errors.append(f"Unknown constraint: {config.constraint_id}")
                    result.is_valid = False
                    continue

                constraint = self._constraint_cache[config.constraint_id]

                # Validate weight range
                if not (0.0 <= config.weight <= 2.0):
                    result.errors.append(
                        f"Invalid weight for {config.constraint_name}: {config.weight}"
                    )
                    result.is_valid = False

                # Validate constraint type compatibility
                if constraint["constraint_type"] == "hard" and config.weight < 0.8:
                    result.warnings.append(
                        f"Low weight for hard constraint: {config.constraint_name}"
                    )

            # Check constraint combinations
            await self._validate_constraint_combinations(
                constraint_configurations, result
            )

            # Check objective function compatibility
            await self._validate_objective_function_compatibility(
                constraint_configurations, objective_function, result
            )

            # Estimate performance impact
            result.estimated_performance_impact = len(constraint_configurations) * 0.1

            return result

        except Exception as e:
            logger.error(f"Error validating configuration combination: {e}")
            return ConfigurationValidationResult(
                is_valid=False, errors=[f"Validation failed: {str(e)}"]
            )

    async def _validate_constraint_combinations(
        self,
        constraint_configurations: List[ConstraintConfiguration],
        result: ConfigurationValidationResult,
    ) -> None:
        """Validate constraint combinations for conflicts"""
        try:
            constraint_codes = [
                config.constraint_code for config in constraint_configurations
            ]

            for i, config1 in enumerate(constraint_configurations):
                for j, config2 in enumerate(constraint_configurations):
                    if i >= j:
                        continue

                    compatibility_key = (
                        config1.constraint_code,
                        config2.constraint_code,
                    )
                    compatibility_score = self._compatibility_matrix.get(
                        compatibility_key, 0.6
                    )

                    if compatibility_score < 0.4:
                        result.compatibility_issues.append(
                            {
                                "constraint1": config1.constraint_name,
                                "constraint2": config2.constraint_name,
                                "compatibility_score": compatibility_score,
                                "issue": "Low compatibility detected",
                            }
                        )
                        result.warnings.append(
                            f"Potential conflict between {config1.constraint_name} and {config2.constraint_name}"
                        )

        except Exception as e:
            logger.error(f"Error validating constraint combinations: {e}")

    async def _validate_objective_function_compatibility(
        self,
        constraint_configurations: List[ConstraintConfiguration],
        objective_function: ObjectiveFunction,
        result: ConfigurationValidationResult,
    ) -> None:
        """Validate objective function compatibility with constraints"""
        try:
            hard_constraints = [
                c for c in constraint_configurations if c.constraint_type == "hard"
            ]
            soft_constraints = [
                c for c in constraint_configurations if c.constraint_type == "soft"
            ]

            if (
                objective_function == ObjectiveFunction.MINIMIZE_CONFLICTS
                and not hard_constraints
            ):
                result.warnings.append(
                    "MINIMIZE_CONFLICTS objective with no hard constraints may be ineffective"
                )

            if (
                objective_function == ObjectiveFunction.MULTI_OBJECTIVE
                and len(soft_constraints) < 2
            ):
                result.warnings.append(
                    "MULTI_OBJECTIVE works best with multiple soft constraints"
                )

        except Exception as e:
            logger.error(f"Error validating objective function compatibility: {e}")

    async def get_configuration_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get available configuration templates"""
        return self._template_cache.copy()

    async def apply_configuration_template(
        self, template: ConfigurationTemplate, user_id: UUID, configuration_name: str
    ) -> Dict[str, Any]:
        """Apply a predefined configuration template"""
        try:
            if template.value not in self._template_cache:
                return {
                    "success": False,
                    "errors": [f"Template {template.value} not found"],
                }

            template_data = self._template_cache[template.value]

            # Create basic constraint configurations from template
            constraint_configurations = []

            # Add some default constraints based on template
            available_rules = await self.constraint_data.get_active_constraint_rules()

            for rule in available_rules[:3]:  # Just take first 3 for demo
                config = ConstraintConfiguration(
                    constraint_id=UUID(rule["id"]),
                    constraint_code=rule["code"],
                    constraint_name=rule["name"],
                    constraint_type=rule["constraint_type"],
                    is_enabled=True,
                    weight=rule.get("default_weight", 1.0),
                )
                constraint_configurations.append(config)

            # Apply template
            objective_function = ObjectiveFunction(template_data["objective_function"])

            return await self.create_configuration(
                user_id=user_id,
                configuration_name=configuration_name,
                configuration_description=template_data["description"],
                objective_function=objective_function,
                constraint_configurations=constraint_configurations,
                template_base=template,
            )

        except Exception as e:
            logger.error(f"Error applying configuration template: {e}")
            return {"success": False, "errors": [f"Failed to apply template: {str(e)}"]}

    async def _log_admin_action(
        self, user_id: UUID, action: str, details: Dict[str, Any]
    ) -> None:
        """Log administrative action"""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                entity_type="admin_configuration",
                new_values=details,
                notes=f"Admin configuration action: {action}",
            )
            self.session.add(audit_log)
            await self.session.commit()

        except Exception as e:
            logger.error(f"Error logging admin action: {e}")

    async def clear_cache(self) -> None:
        """Clear configuration caches"""
        try:
            self._constraint_cache.clear()
            self._template_cache.clear()
            self._compatibility_matrix.clear()

            # Reload caches
            await self._load_constraint_cache()
            await self._load_configuration_templates()
            await self._build_compatibility_matrix()

            logger.info("Configuration caches cleared and reloaded")

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
