# scheduling_engine/core/constraint_registry.py

"""
Enhanced Constraint Registry for Exam Scheduling with Database Integration

Manages all constraint types, their definitions, and validation logic.
Enhanced to support database-driven constraint configuration and dynamic loading.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Type, Union, TYPE_CHECKING
from uuid import UUID
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime
import logging

# Only import real types for type checkers. Use aliases to avoid name collisions.
if TYPE_CHECKING:
    from app.services.data_retrieval import ConstraintData as _ConstraintDataType  # type: ignore
    from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSessionType  # type: ignore
    from .problem_model import ExamSchedulingProblem
    from .solution import TimetableSolution

# Runtime-safe placeholders. Use distinct runtime names to avoid redefinition issues.
RuntimeConstraintData: Optional[Any] = None
RuntimeAsyncSession: Optional[Any] = None
BACKEND_AVAILABLE = False

try:
    from app.services.data_retrieval import ConstraintData as _ConstraintDataRuntime  # type: ignore
    from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSessionRuntime  # type: ignore

    RuntimeConstraintData = _ConstraintDataRuntime
    RuntimeAsyncSession = _AsyncSessionRuntime
    BACKEND_AVAILABLE = True
except Exception:
    # Leave runtime placeholders as None when optional dependencies are absent.
    RuntimeConstraintData = None
    RuntimeAsyncSession = None

# Local project imports
from ..config import get_logger, ConstraintType  # type: ignore

logger = get_logger("core.constraint_registry")


class ConstraintCategory(Enum):
    STUDENT_CONSTRAINTS = "student_constraints"
    RESOURCE_CONSTRAINTS = "resource_constraints"
    TEMPORAL_CONSTRAINTS = "temporal_constraints"
    ACADEMIC_POLICIES = "academic_policies"
    OPTIMIZATION_CONSTRAINTS = "optimization_constraints"
    CONVENIENCE_CONSTRAINTS = "convenience_constraints"
    WORKLOAD_BALANCE = "workload_balance"


class ConstraintSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ConstraintViolation:
    constraint_id: UUID
    violation_id: UUID
    severity: ConstraintSeverity
    affected_exams: List[UUID]
    affected_resources: List[UUID]
    description: str
    penalty: float
    suggestions: List[str] = field(default_factory=list)
    constraint_code: Optional[str] = None
    database_rule_id: Optional[UUID] = None
    violation_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConstraintDefinition:
    constraint_id: str
    name: str
    description: str
    constraint_type: ConstraintType
    category: ConstraintCategory
    parameters: Dict[str, Any] = field(default_factory=dict)
    validation_rules: List[str] = field(default_factory=list)
    constraint_class: Optional[Type] = None
    database_rule_id: Optional[UUID] = None
    is_database_loaded: bool = False
    default_weight: float = 1.0
    is_configurable: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BaseConstraint(ABC):
    def __init__(
        self,
        constraint_id: Union[str, UUID],
        name: str,
        constraint_type: ConstraintType,
        category: ConstraintCategory,
        weight: float = 1.0,
        is_active: bool = True,
        parameters: Optional[Dict[str, Any]] = None,
        database_config: Optional[Dict[str, Any]] = None,
    ):
        self.id = (
            UUID(str(constraint_id))
            if isinstance(constraint_id, str)
            else constraint_id
        )
        self.constraint_id = str(constraint_id)
        self.name = name
        self.constraint_type = constraint_type
        self.category = category
        self.weight = weight
        self.is_active = is_active
        self.parameters = parameters or {}

        self.database_config = database_config or {}
        self.database_rule_id = self.database_config.get("rule_id")
        self.configuration_id = self.database_config.get("configuration_id")

        self._initialized = False

    def initialize(
        self,
        problem: ExamSchedulingProblem,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        if self._initialized:
            return
        try:
            merged_parameters: Dict[str, Any] = {}
            merged_parameters.update(self.parameters)
            if isinstance(self.database_config.get("custom_parameters"), dict):
                merged_parameters.update(self.database_config["custom_parameters"])
            if parameters:
                merged_parameters.update(parameters)

            self._initialize_implementation(problem, merged_parameters)
            self._initialized = True
            logger.debug(f"Initialized constraint {self.name}")
        except Exception as e:
            logger.error(f"Error initializing constraint {self.name}: {e}")
            raise

    @abstractmethod
    def _initialize_implementation(
        self,
        problem: ExamSchedulingProblem,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        raise NotImplementedError

    def evaluate(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> List[ConstraintViolation]:
        if not self._initialized:
            self.initialize(problem)
        try:
            violations = self._evaluate_implementation(problem, solution)
            for violation in violations:
                violation.constraint_code = self.constraint_id
                violation.database_rule_id = self.database_rule_id
                if self.configuration_id:
                    violation.violation_metadata["configuration_id"] = str(
                        self.configuration_id
                    )
            return violations
        except Exception as e:
            logger.error(f"Error evaluating constraint {self.name}: {e}")
            return []

    @abstractmethod
    def _evaluate_implementation(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> List[ConstraintViolation]:
        raise NotImplementedError

    def get_penalty(self, violation: ConstraintViolation) -> float:
        base_penalty = violation.penalty
        weight_multiplier = self.weight
        db_weight = self.database_config.get("weight")
        if db_weight is not None:
            try:
                weight_multiplier = float(db_weight)
            except Exception:
                logger.debug(
                    "Invalid weight in database_config, using constraint weight"
                )
        return base_penalty * weight_multiplier

    def is_satisfied(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> bool:
        violations = self.evaluate(problem, solution)
        return len(violations) == 0

    def get_definition(self) -> ConstraintDefinition:
        return ConstraintDefinition(
            constraint_id=self.constraint_id,
            name=self.name,
            description=f"Constraint: {self.name}",
            constraint_type=self.constraint_type,
            category=self.category,
            parameters=self.parameters,
            constraint_class=type(self),
            database_rule_id=self.database_rule_id,
            is_database_loaded=bool(self.database_rule_id),
            default_weight=self.weight,
            is_configurable=True,
        )


class LegacyConstraintAdapter(BaseConstraint):
    def __init__(
        self,
        legacy_constraint_instance: Any,
        constraint_code: str,
        database_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            constraint_id=constraint_code,
            name=getattr(legacy_constraint_instance, "name", constraint_code),
            constraint_type=getattr(
                legacy_constraint_instance, "constraint_type", ConstraintType.SOFT
            ),
            category=getattr(
                legacy_constraint_instance,
                "category",
                ConstraintCategory.OPTIMIZATION_CONSTRAINTS,
            ),
            database_config=database_config,
        )
        self.legacy_constraint = legacy_constraint_instance

    def _initialize_implementation(
        self,
        problem: ExamSchedulingProblem,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        if hasattr(self.legacy_constraint, "initialize"):
            try:
                self.legacy_constraint.initialize(problem, parameters or {})
            except TypeError:
                # fallback for legacy signatures
                self.legacy_constraint.initialize(problem)

    def _evaluate_implementation(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> List[ConstraintViolation]:
        if hasattr(self.legacy_constraint, "evaluate"):
            try:
                return self.legacy_constraint.evaluate(problem, solution)
            except TypeError:
                return self.legacy_constraint.evaluate(problem)
        return []


class ConstraintRegistry:
    def __init__(self, db_session: Optional[Any] = None):
        self._definitions: Dict[str, ConstraintDefinition] = {}
        self._active_constraints: Dict[UUID, BaseConstraint] = {}
        self._constraint_categories: Dict[ConstraintCategory, List[str]] = {}
        self._database_constraints: Dict[str, Dict[str, Any]] = {}

        # Database integration using runtime placeholders
        self.db_session = db_session
        self.constraint_data_service: Optional[Any] = None
        if (
            BACKEND_AVAILABLE
            and db_session is not None
            and RuntimeConstraintData is not None
        ):
            try:
                # avoid assuming constructor signature
                constructor = RuntimeConstraintData
                try:
                    self.constraint_data_service = constructor(db_session)
                except TypeError:
                    self.constraint_data_service = constructor()
            except Exception as e:
                logger.error(f"Failed to initialize ConstraintData service: {e}")
                self.constraint_data_service = None

        self._register_builtin_constraints()
        logger.info("Enhanced ConstraintRegistry initialized")

    async def load_database_constraints(self) -> None:
        if not BACKEND_AVAILABLE or not self.constraint_data_service:
            logger.warning("Database constraint loading not available")
            return
        try:
            get_active = getattr(
                self.constraint_data_service, "get_active_constraint_rules", None
            )
            if not get_active:
                logger.warning(
                    "ConstraintData service missing 'get_active_constraint_rules'"
                )
                return
            db_constraints = await get_active()
            logger.info(f"Loading {len(db_constraints)} constraint rules from database")
            for db_constraint in db_constraints:
                await self._register_database_constraint(db_constraint)
            logger.info(
                f"Successfully loaded {len(self._database_constraints)} database constraints"
            )
        except Exception as e:
            logger.error(f"Error loading database constraints: {e}")

    async def _register_database_constraint(
        self, db_constraint: Dict[str, Any]
    ) -> None:
        try:
            constraint_code = (db_constraint.get("code") or "").upper()
            if not constraint_code:
                logger.warning("Database constraint missing code, skipping")
                return

            self._database_constraints[constraint_code] = db_constraint

            db_id = db_constraint.get("id")
            database_rule_id: Optional[UUID] = None
            if db_id:
                try:
                    database_rule_id = UUID(db_id)
                except Exception:
                    database_rule_id = None

            definition = ConstraintDefinition(
                constraint_id=constraint_code,
                name=db_constraint.get("name", constraint_code),
                description=db_constraint.get("description", ""),
                constraint_type=self._map_constraint_type(
                    db_constraint.get("constraint_type", "soft")
                ),
                category=self._map_constraint_category(constraint_code),
                parameters=db_constraint.get("constraint_definition", {}) or {},
                database_rule_id=database_rule_id,
                is_database_loaded=True,
                default_weight=float(db_constraint.get("default_weight", 1.0)),
                is_configurable=bool(db_constraint.get("is_configurable", True)),
            )

            definition.constraint_class = self._get_constraint_class_for_code(
                constraint_code
            )
            self._register_constraint_definition(definition)
            logger.debug(f"Registered database constraint: {constraint_code}")
        except Exception as e:
            logger.error(f"Error registering database constraint: {e}")

    def _get_constraint_class_for_code(
        self, constraint_code: str
    ) -> Optional[Type[BaseConstraint]]:
        try:
            from ..constraints.hard_constraints import HARD_CONSTRAINT_REGISTRY  # type: ignore
            from ..constraints.soft_constraints import SOFT_CONSTRAINT_REGISTRY  # type: ignore

            cls = HARD_CONSTRAINT_REGISTRY.get(constraint_code)
            if cls:
                return cls
            cls = SOFT_CONSTRAINT_REGISTRY.get(constraint_code)
            if cls:
                return cls
            return None
        except ImportError:
            logger.warning(f"Could not import constraint modules for {constraint_code}")
            return None

    def _map_constraint_type(self, db_type: Optional[str]) -> ConstraintType:
        mapping = {
            "hard": ConstraintType.HARD,
            "soft": ConstraintType.SOFT,
            "HARD": ConstraintType.HARD,
            "SOFT": ConstraintType.SOFT,
        }
        return mapping.get(db_type or "", ConstraintType.SOFT)

    def _map_constraint_category(self, constraint_code: str) -> ConstraintCategory:
        category_mapping = {
            "NO_STUDENT_CONFLICT": ConstraintCategory.STUDENT_CONSTRAINTS,
            "ROOM_CAPACITY": ConstraintCategory.RESOURCE_CONSTRAINTS,
            "TIME_AVAILABILITY": ConstraintCategory.TEMPORAL_CONSTRAINTS,
            "CARRYOVER_PRIORITY": ConstraintCategory.ACADEMIC_POLICIES,
            "EXAM_DISTRIBUTION": ConstraintCategory.OPTIMIZATION_CONSTRAINTS,
            "ROOM_UTILIZATION": ConstraintCategory.RESOURCE_CONSTRAINTS,
            "INVIGILATOR_BALANCE": ConstraintCategory.OPTIMIZATION_CONSTRAINTS,
            "STUDENT_TRAVEL": ConstraintCategory.CONVENIENCE_CONSTRAINTS,
        }
        return category_mapping.get(
            constraint_code.upper(), ConstraintCategory.OPTIMIZATION_CONSTRAINTS
        )

    async def create_constraint_set_from_configuration(
        self, configuration_id: UUID
    ) -> List[BaseConstraint]:
        if not BACKEND_AVAILABLE or not self.constraint_data_service:
            logger.warning("Database configuration loading not available")
            return self.create_default_constraint_set()
        try:
            get_config = getattr(
                self.constraint_data_service, "get_configuration_constraints", None
            )
            if not get_config:
                logger.warning(
                    "ConstraintData service missing 'get_configuration_constraints'"
                )
                return self.create_default_constraint_set()
            config_constraints = await get_config(configuration_id)
            constraints: List[BaseConstraint] = []
            for config_constraint in config_constraints:
                if not config_constraint.get("is_enabled", True):
                    continue
                constraint_code = (
                    config_constraint.get("constraint_code") or ""
                ).upper()
                if not constraint_code:
                    logger.warning("Configuration constraint missing code, skipping")
                    continue
                constraint = await self.create_constraint_instance(
                    constraint_code,
                    weight=config_constraint.get("weight"),
                    database_config=config_constraint,
                )
                if constraint:
                    constraints.append(constraint)
                else:
                    logger.warning(
                        f"Could not create constraint instance for {constraint_code}"
                    )
            logger.info(
                f"Created {len(constraints)} constraints from configuration {configuration_id}"
            )
            return constraints
        except Exception as e:
            logger.error(f"Error creating constraint set from configuration: {e}")
            return self.create_default_constraint_set()

    async def create_constraint_instance(
        self,
        constraint_code: str,
        weight: Optional[float] = None,
        parameters: Optional[Dict[str, Any]] = None,
        database_config: Optional[Dict[str, Any]] = None,
    ) -> Optional[BaseConstraint]:
        try:
            definition = self.get_constraint_definition(constraint_code.upper())
            if not definition or not definition.constraint_class:
                logger.error(f"No constraint definition found for: {constraint_code}")
                return None

            config_context: Dict[str, Any] = {}
            if database_config:
                config_context.update(database_config)
            db_conf = self._database_constraints.get(constraint_code.upper())
            if isinstance(db_conf, dict):
                config_context.update(db_conf)

            final_weight = weight
            if final_weight is None and database_config:
                final_weight = database_config.get("weight")
            if final_weight is None:
                final_weight = definition.default_weight

            cls = definition.constraint_class
            if isinstance(cls, type) and issubclass(cls, BaseConstraint):
                constraint = cls(
                    constraint_id=constraint_code,
                    name=definition.name,
                    constraint_type=definition.constraint_type,
                    category=definition.category,
                    weight=final_weight,
                    parameters=parameters,
                    database_config=config_context,
                )
            else:
                legacy_instance = cls() if isinstance(cls, type) else cls
                constraint = LegacyConstraintAdapter(
                    legacy_constraint_instance=legacy_instance,
                    constraint_code=constraint_code,
                    database_config=config_context,
                )

            logger.debug(f"Created constraint instance: {constraint_code}")
            return constraint
        except Exception as e:
            logger.error(f"Error creating constraint instance {constraint_code}: {e}")
            return None

    def _register_constraint_definition(self, definition: ConstraintDefinition) -> None:
        self._definitions[definition.constraint_id] = definition
        if definition.category not in self._constraint_categories:
            self._constraint_categories[definition.category] = []
        if (
            definition.constraint_id
            not in self._constraint_categories[definition.category]
        ):
            self._constraint_categories[definition.category].append(
                definition.constraint_id
            )

    def get_constraint_definition(self, code: str) -> Optional[ConstraintDefinition]:
        return self._definitions.get(code.upper())

    def get_all_definitions(self) -> Dict[str, ConstraintDefinition]:
        return self._definitions.copy()

    def get_definitions_by_category(
        self, category: ConstraintCategory
    ) -> List[ConstraintDefinition]:
        codes = self._constraint_categories.get(category, [])
        return [self._definitions[c] for c in codes if c in self._definitions]

    def get_definitions_by_type(
        self, constraint_type: ConstraintType
    ) -> List[ConstraintDefinition]:
        return [
            d
            for d in self._definitions.values()
            if d.constraint_type == constraint_type
        ]

    def add_active_constraint(self, constraint: BaseConstraint) -> None:
        self._active_constraints[constraint.id] = constraint
        logger.debug(f"Added active constraint: {constraint.name}")

    def remove_active_constraint(self, constraint_id: UUID) -> bool:
        if constraint_id in self._active_constraints:
            constraint = self._active_constraints.pop(constraint_id)
            logger.debug(f"Removed active constraint: {constraint.name}")
            return True
        return False

    def get_active_constraints(
        self, constraint_type: Optional[ConstraintType] = None
    ) -> List[BaseConstraint]:
        constraints = list(self._active_constraints.values())
        if constraint_type:
            constraints = [
                c for c in constraints if c.constraint_type == constraint_type
            ]
        return [c for c in constraints if c.is_active]

    async def evaluate_all_constraints(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> Dict[str, List[ConstraintViolation]]:
        results: Dict[str, List[ConstraintViolation]] = {}
        for constraint in self.get_active_constraints():
            try:
                violations = constraint.evaluate(problem, solution)
                results[constraint.name] = violations
                if violations:
                    logger.debug(
                        f"Constraint {constraint.name} has {len(violations)} violations"
                    )
            except Exception as e:
                logger.error(f"Error evaluating constraint {constraint.name}: {e}")
                results[constraint.name] = []
        return results

    async def calculate_total_penalty(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> float:
        total_penalty = 0.0
        violation_results = await self.evaluate_all_constraints(problem, solution)
        for constraint_name, violations in violation_results.items():
            constraint = next(
                (
                    c
                    for c in self._active_constraints.values()
                    if c.name == constraint_name
                ),
                None,
            )
            if not constraint:
                continue
            for violation in violations:
                penalty = constraint.get_penalty(violation)
                total_penalty += penalty
        return total_penalty

    def create_default_constraint_set(self) -> List[BaseConstraint]:
        default_constraints: List[BaseConstraint] = []
        hard_definitions = self.get_definitions_by_type(ConstraintType.HARD)
        for definition in hard_definitions:
            if not definition.constraint_class:
                continue
            try:
                cls = definition.constraint_class
                if isinstance(cls, type) and issubclass(cls, BaseConstraint):
                    constraint = cls(
                        constraint_id=definition.constraint_id,
                        name=definition.name,
                        constraint_type=definition.constraint_type,
                        category=definition.category,
                        weight=definition.default_weight,
                    )
                    default_constraints.append(constraint)
                else:
                    legacy_instance = cls() if isinstance(cls, type) else cls
                    wrapped = LegacyConstraintAdapter(
                        legacy_constraint_instance=legacy_instance,
                        constraint_code=definition.constraint_id,
                    )
                    default_constraints.append(wrapped)
            except Exception as e:
                logger.error(
                    f"Error creating default constraint {definition.constraint_id}: {e}"
                )

        important_soft_constraints = ["EXAM_DISTRIBUTION", "ROOM_UTILIZATION"]
        for code in important_soft_constraints:
            definition_opt = self.get_constraint_definition(code)
            if not definition_opt or not definition_opt.constraint_class:
                continue
            try:
                cls = definition_opt.constraint_class
                if isinstance(cls, type) and issubclass(cls, BaseConstraint):
                    constraint = cls(
                        constraint_id=definition_opt.constraint_id,
                        name=definition_opt.name,
                        constraint_type=definition_opt.constraint_type,
                        category=definition_opt.category,
                        weight=definition_opt.default_weight,
                    )
                    default_constraints.append(constraint)
                else:
                    legacy_instance = cls() if isinstance(cls, type) else cls
                    wrapped = LegacyConstraintAdapter(
                        legacy_constraint_instance=legacy_instance,
                        constraint_code=definition_opt.constraint_id,
                    )
                    default_constraints.append(wrapped)
            except Exception as e:
                logger.error(f"Error creating default soft constraint {code}: {e}")

        logger.info(
            f"Created default constraint set with {len(default_constraints)} constraints"
        )
        return default_constraints

    async def validate_constraint_configuration(
        self, config: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        errors: List[str] = []
        warnings: List[str] = []
        for constraint_config in config.get("constraints", []):
            code = (constraint_config.get("code") or "").upper()
            if not code:
                errors.append("Constraint configuration missing code")
                continue
            definition = self.get_constraint_definition(code)
            if not definition:
                errors.append(f"Unknown constraint code: {code}")
                continue
            if definition.is_configurable:
                parameters = constraint_config.get("parameters", {})
                validation_errors = self._validate_constraint_parameters(
                    code, parameters, definition
                )
                errors.extend(validation_errors)
            weight = constraint_config.get("weight")
            if weight is not None and (
                not isinstance(weight, (int, float)) or weight < 0
            ):
                errors.append(f"Invalid weight for constraint {code}: {weight}")
        return {"errors": errors, "warnings": warnings}

    def _validate_constraint_parameters(
        self,
        constraint_code: str,
        parameters: Dict[str, Any],
        definition: ConstraintDefinition,
    ) -> List[str]:
        errors: List[str] = []
        param_schema = definition.parameters
        for param_name, param_value in parameters.items():
            if not param_schema:
                continue
            # extend validation as needed
        return errors

    def _register_builtin_constraints(self) -> None:
        try:
            from ..constraints.hard_constraints import (  # type: ignore
                NoStudentConflictConstraint,
                RoomCapacityConstraint,
                TimeAvailabilityConstraint,
                CarryoverPriorityConstraint,
            )
            from ..constraints.soft_constraints import (  # type: ignore
                ExamDistributionConstraint,
                RoomUtilizationConstraint,
                InvigilatorBalanceConstraint,
                StudentTravelConstraint,
            )

            hard_constraint_definitions = [
                ConstraintDefinition(
                    constraint_id="NO_STUDENT_CONFLICT",
                    name="No Student Conflicts",
                    description="Prevent students from having multiple exams at the same time",
                    constraint_type=ConstraintType.HARD,
                    category=ConstraintCategory.STUDENT_CONSTRAINTS,
                    constraint_class=NoStudentConflictConstraint,
                    default_weight=1.0,
                    is_configurable=True,
                ),
                ConstraintDefinition(
                    constraint_id="ROOM_CAPACITY",
                    name="Room Capacity",
                    description="Ensure room capacity is not exceeded",
                    constraint_type=ConstraintType.HARD,
                    category=ConstraintCategory.RESOURCE_CONSTRAINTS,
                    constraint_class=RoomCapacityConstraint,
                    default_weight=1.0,
                    is_configurable=True,
                    parameters={
                        "capacity_buffer_percent": {
                            "type": "float",
                            "default": 0.0,
                            "min": 0.0,
                            "max": 50.0,
                        }
                    },
                ),
                ConstraintDefinition(
                    constraint_id="TIME_AVAILABILITY",
                    name="Time Availability",
                    description="Ensure exams are scheduled in available time slots",
                    constraint_type=ConstraintType.HARD,
                    category=ConstraintCategory.TEMPORAL_CONSTRAINTS,
                    constraint_class=TimeAvailabilityConstraint,
                    default_weight=1.0,
                    is_configurable=True,
                    parameters={
                        "allow_weekend_exams": {"type": "bool", "default": False},
                        "earliest_exam_time": {"type": "string", "default": "08:00"},
                        "latest_exam_time": {"type": "string", "default": "18:00"},
                    },
                ),
                ConstraintDefinition(
                    constraint_id="CARRYOVER_PRIORITY",
                    name="Carryover Priority",
                    description="Give priority scheduling to carryover exams",
                    constraint_type=ConstraintType.HARD,
                    category=ConstraintCategory.ACADEMIC_POLICIES,
                    constraint_class=CarryoverPriorityConstraint,
                    default_weight=1.0,
                    is_configurable=True,
                    parameters={
                        "priority_levels": {
                            "type": "int",
                            "default": 3,
                            "min": 1,
                            "max": 10,
                        }
                    },
                ),
            ]

            soft_constraint_definitions = [
                ConstraintDefinition(
                    constraint_id="EXAM_DISTRIBUTION",
                    name="Exam Distribution",
                    description="Distribute exams evenly across time slots",
                    constraint_type=ConstraintType.SOFT,
                    category=ConstraintCategory.OPTIMIZATION_CONSTRAINTS,
                    constraint_class=ExamDistributionConstraint,
                    default_weight=0.7,
                    is_configurable=True,
                    parameters={
                        "minimum_gap_hours": {
                            "type": "int",
                            "default": 24,
                            "min": 12,
                            "max": 72,
                        },
                        "preferred_gap_hours": {
                            "type": "int",
                            "default": 48,
                            "min": 24,
                            "max": 120,
                        },
                    },
                ),
                ConstraintDefinition(
                    constraint_id="ROOM_UTILIZATION",
                    name="Room Utilization",
                    description="Maximize room utilization efficiency",
                    constraint_type=ConstraintType.SOFT,
                    category=ConstraintCategory.RESOURCE_CONSTRAINTS,
                    constraint_class=RoomUtilizationConstraint,
                    default_weight=0.6,
                    is_configurable=True,
                    parameters={
                        "target_utilization_rate": {
                            "type": "float",
                            "default": 0.85,
                            "min": 0.5,
                            "max": 1.0,
                        }
                    },
                ),
                ConstraintDefinition(
                    constraint_id="INVIGILATOR_BALANCE",
                    name="Invigilator Balance",
                    description="Balance invigilator workload",
                    constraint_type=ConstraintType.SOFT,
                    category=ConstraintCategory.OPTIMIZATION_CONSTRAINTS,
                    constraint_class=InvigilatorBalanceConstraint,
                    default_weight=0.5,
                    is_configurable=True,
                    parameters={
                        "balance_method": {
                            "type": "string",
                            "default": "variance_minimization",
                        }
                    },
                ),
                ConstraintDefinition(
                    constraint_id="STUDENT_TRAVEL",
                    name="Minimize Student Travel",
                    description="Minimize travel distance between consecutive exams for students",
                    constraint_type=ConstraintType.SOFT,
                    category=ConstraintCategory.CONVENIENCE_CONSTRAINTS,
                    constraint_class=StudentTravelConstraint,
                    default_weight=0.4,
                    is_configurable=True,
                    parameters={
                        "max_reasonable_travel_time": {
                            "type": "int",
                            "default": 15,
                            "min": 5,
                            "max": 30,
                        }
                    },
                ),
            ]

            for definition in hard_constraint_definitions + soft_constraint_definitions:
                self._register_constraint_definition(definition)

            logger.info(
                f"Registered {len(hard_constraint_definitions)} hard and {len(soft_constraint_definitions)} soft constraint definitions"
            )
        except ImportError as e:
            logger.error(f"Could not import constraint classes: {e}")

    async def refresh_database_constraints(self) -> None:
        if BACKEND_AVAILABLE and self.constraint_data_service:
            logger.info("Refreshing constraint definitions from database")
            old_db_constraints = [
                code
                for code, defn in list(self._definitions.items())
                if defn.is_database_loaded
            ]
            for code in old_db_constraints:
                del self._definitions[code]
            await self.load_database_constraints()
        else:
            logger.warning("Database refresh not available")

    def get_constraint_satisfaction_rate(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> Dict[str, float]:
        rates: Dict[str, float] = {}
        for constraint in self.get_active_constraints():
            try:
                violations = constraint.evaluate(problem, solution)
                rates[constraint.name] = 1.0 if len(violations) == 0 else 0.0
            except Exception as e:
                logger.error(
                    f"Error calculating satisfaction rate for {constraint.name}: {e}"
                )
                rates[constraint.name] = 0.0
        return rates

    # NEW METHODS ADDED FOR PROBLEM MODEL INTEGRATION
    async def load_from_database(self, configuration_id: Optional[UUID] = None) -> None:
        """Load constraint definitions from database"""
        await self.load_database_constraints()
        logger.info("Loaded constraint definitions from database")

    async def get_active_constraints_for_configuration(
        self, configuration_id: UUID
    ) -> List[BaseConstraint]:
        """Get active constraints for a specific configuration"""
        return await self.create_constraint_set_from_configuration(configuration_id)

    async def validate_constraint_configuration_by_id(
        self, configuration_id: UUID
    ) -> Dict[str, Any]:
        """Validate constraint configuration by ID"""
        if not BACKEND_AVAILABLE or not self.constraint_data_service:
            return {
                "valid": False,
                "errors": ["Database not available"],
                "warnings": [],
            }

        try:
            # Get configuration from database
            get_config = getattr(
                self.constraint_data_service, "get_configuration_by_id", None
            )
            if not get_config:
                return {
                    "valid": False,
                    "errors": ["Method not available"],
                    "warnings": [],
                }

            config = await get_config(configuration_id)
            if not config:
                return {
                    "valid": False,
                    "errors": ["Configuration not found"],
                    "warnings": [],
                }

            # Validate the configuration
            result = await self.validate_constraint_configuration(config)
            return {
                "valid": len(result["errors"]) == 0,
                "errors": result["errors"],
                "warnings": result["warnings"],
            }
        except Exception as e:
            logger.error(f"Error validating configuration: {e}")
            return {"valid": False, "errors": [str(e)], "warnings": []}

    def get_constraint_statistics(self) -> Dict[str, Any]:
        """Get statistics about registered constraints"""
        return {
            "total_definitions": len(self._definitions),
            "database_constraints": len(self._database_constraints),
            "active_constraints": len(self._active_constraints),
            "categories": {
                category.value: len(definitions)
                for category, definitions in self._constraint_categories.items()
            },
        }

    async def refresh_from_database(self) -> None:
        """Refresh constraint definitions from database"""
        await self.refresh_database_constraints()
