# scheduling_engine/constraints/base_constraint.py - FIXED VERSION

"""
FIXED Base Constraint - Enhanced Validation and Fail-Fast Logic

CRITICAL FIXES:
- Added fail-fast validation for critical constraint modules
- Enhanced constraint counting with validation
- Better error handling and reporting
- Performance guards for constraint explosion
"""

from abc import ABC, abstractmethod
from types import MappingProxyType
import logging
from typing import Dict, Any, Optional, Set, List

logger = logging.getLogger(__name__)


class CPSATBaseConstraint(ABC):
    """
    FIXED base constraint with enhanced validation and fail-fast logic
    """

    # Explicit dependencies - override in subclasses
    dependencies: List[str] = []
    constraint_category: str = "CORE"
    enabled: bool = True

    # FIXED: Add critical constraint designation
    is_critical: bool = False  # Override in critical constraints
    min_expected_constraints: int = 0  # Override with expected minimum

    def __init__(self, constraint_id: str, problem, shared_variables, model):
        """Initialize constraint with enhanced validation and logging"""
        self.constraint_id = constraint_id
        self.problem = problem
        self.model = model
        self._constraint_count = 0
        self._constraints_added = False

        # Log initialization with better formatting
        logger.info(f"🔧 Initializing {constraint_id} ({self.constraint_category})")

        # Safely access shared variables with validation
        self._core_x = self._safe_variable_access(shared_variables, "x_vars")
        self._core_z = self._safe_variable_access(shared_variables, "z_vars")
        self._core_y = self._safe_variable_access(shared_variables, "y_vars")
        self._core_u = self._safe_variable_access(shared_variables, "u_vars")

        # Safe access to shared precomputed data
        self._shared_conflict_pairs = self._safe_data_access(
            shared_variables, "conflict_pairs", set()
        )
        self._shared_student_exams = self._safe_data_access(
            shared_variables, "student_exams", {}
        )
        self._shared_effective_capacities = self._safe_data_access(
            shared_variables, "effective_capacities", {}
        )
        self._shared_allowed_rooms = self._safe_data_access(
            shared_variables, "allowed_rooms", {}
        )

        # Module-specific variables
        self._local_vars: Dict[str, Any] = {}

        # FIXED: Enhanced logging with validation summary
        self._log_initialization_summary()

    def _safe_variable_access(self, shared_variables, attr_name):
        """Safely access variable dictionaries with validation"""
        try:
            variables = getattr(shared_variables, attr_name, {})
            if isinstance(variables, dict):
                return MappingProxyType(variables)
            else:
                logger.warning(
                    f"⚠️ {self.constraint_id}: {attr_name} is not a dict, got {type(variables)}"
                )
                return MappingProxyType({})
        except Exception as e:
            logger.error(f"❌ {self.constraint_id}: Failed to access {attr_name}: {e}")
            return MappingProxyType({})

    def _safe_data_access(self, shared_variables, attr_name, default_value):
        """Safely access precomputed data with fallback defaults"""
        try:
            return getattr(shared_variables, attr_name, default_value)
        except Exception as e:
            logger.warning(f"⚠️ {self.constraint_id}: Failed to access {attr_name}: {e}")
            return default_value

    def _log_initialization_summary(self):
        """Log comprehensive initialization summary"""
        logger.debug(f"📊 {self.constraint_id} initialization summary:")
        logger.debug(f" • x_vars: {len(self._core_x)}")
        logger.debug(f" • z_vars: {len(self._core_z)}")
        logger.debug(f" • y_vars: {len(self._core_y)}")
        logger.debug(f" • u_vars: {len(self._core_u)}")
        logger.debug(f" • conflict_pairs: {len(self._shared_conflict_pairs)}")
        logger.debug(f" • student_exams: {len(self._shared_student_exams)}")
        logger.info(f"✅ {self.constraint_id} initialization complete")

    @property
    def x(self) -> MappingProxyType:
        """Read-only access to start variables x[e,d,t]"""
        return self._core_x

    @property
    def z(self) -> MappingProxyType:
        """Read-only access to occupancy variables z[e,d,t]"""
        return self._core_z

    @property
    def y(self) -> MappingProxyType:
        """Read-only access to room assignment variables y[e,r,d,t]"""
        return self._core_y

    @property
    def u(self) -> MappingProxyType:
        """Read-only access to shared invigilator variables u[i,e,r,d,t]"""
        return self._core_u

    @property
    def conflict_pairs(self) -> Set:
        """Access to shared precomputed conflict pairs"""
        return self._shared_conflict_pairs

    @property
    def student_exams(self) -> Dict[str, Set[str]]:
        """Access to shared student-exam mapping"""
        return self._shared_student_exams

    @property
    def effective_capacities(self) -> Dict[str, int]:
        """Access to shared effective capacities"""
        return self._shared_effective_capacities

    @property
    def allowed_rooms(self) -> Dict[str, Set[str]]:
        """Access to shared allowed rooms mapping"""
        return self._shared_allowed_rooms

    def initialize_variables(self):
        """Initialize constraint-specific variables with comprehensive validation"""
        if hasattr(self, "_variables_initialized"):
            logger.debug(f"⚠️ {self.constraint_id}: Variables already initialized")
            return

        logger.info(f"🔧 {self.constraint_id}: Initializing variables...")

        # Validate essential data availability
        if not self._validate_essential_data():
            error_msg = f"{self.constraint_id}: Essential data validation failed"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        try:
            self._create_local_variables()
            self._variables_initialized = True
            logger.info(f"✅ {self.constraint_id}: Variable initialization complete")

            if self._local_vars:
                logger.debug(
                    f"📦 {self.constraint_id}: Created {len(self._local_vars)} local variables"
                )
        except Exception as e:
            logger.error(
                f"❌ {self.constraint_id}: Variable initialization failed: {e}"
            )
            raise

    def _validate_essential_data(self) -> bool:
        """FIXED: Enhanced essential data validation"""
        essential_checks = {
            "problem_exams": len(getattr(self.problem, "exams", {})) > 0,
            "problem_rooms": len(getattr(self.problem, "rooms", {})) > 0,
            "problem_time_slots": len(getattr(self.problem, "time_slots", {})) > 0,
            "shared_variables": len(self._core_x) > 0
            or len(self._core_z) > 0
            or len(self._core_y) > 0,
        }

        missing = [name for name, check in essential_checks.items() if not check]

        if missing:
            logger.error(f"❌ {self.constraint_id}: Missing essential data: {missing}")
            return False

        # FIXED: Additional category-specific validation
        if self.constraint_category == "INVIGILATOR":
            invigilators = getattr(self.problem, "invigilators", {})
            if not invigilators:
                logger.error(
                    f"❌ {self.constraint_id}: INVIGILATOR category requires invigilators but none found"
                )
                return False

        if self.constraint_category in ["STUDENT_CONFLICT", "MULTI_EXAM_CAPACITY"]:
            if not self._shared_conflict_pairs and not self._shared_student_exams:
                logger.warning(
                    f"⚠️ {self.constraint_id}: No conflict data available for {self.constraint_category}"
                )

        return True

    @abstractmethod
    def _create_local_variables(self):
        """Create module-specific variables if needed"""
        pass

    @abstractmethod
    def _add_constraint_implementation(self):
        """Add CP-SAT constraints using shared variables and data"""
        pass

    def add_constraints(self):
        """FIXED: Add constraints with enhanced validation and fail-fast logic"""
        if not self.enabled:
            logger.info(f"⏭️ {self.constraint_id}: Module disabled, skipping")
            return

        if self._constraints_added:
            logger.warning(f"⚠️ {self.constraint_id}: Constraints already added")
            return

        logger.info(f"➕ {self.constraint_id}: Adding constraints...")

        try:
            count_before = self._constraint_count
            self._add_constraint_implementation()
            constraints_added = self._constraint_count - count_before
            self._constraints_added = True

            # FIXED: Validate constraint generation results
            self._validate_constraint_generation(constraints_added)

            if constraints_added > 0:
                logger.info(
                    f"✅ {self.constraint_id}: Successfully added {constraints_added} constraints"
                )
            else:
                self._handle_zero_constraints()

        except Exception as e:
            logger.error(f"❌ {self.constraint_id}: Failed to add constraints: {e}")
            import traceback

            logger.debug(
                f"🐛 {self.constraint_id} traceback:\n{traceback.format_exc()}"
            )
            raise

    def _validate_constraint_generation(self, constraints_added: int):
        """FIXED: Validate constraint generation with fail-fast logic"""
        validation_issues = []

        # Check against minimum expected constraints
        if (
            self.min_expected_constraints > 0
            and constraints_added < self.min_expected_constraints
        ):
            validation_issues.append(
                f"Generated {constraints_added} constraints, expected >= {self.min_expected_constraints}"
            )

        # Check for critical constraints with zero generation
        if self.is_critical and constraints_added == 0:
            validation_issues.append("Critical constraint generated zero constraints")

        # Check for constraint explosion (performance guard)
        MAX_REASONABLE_CONSTRAINTS = 1000000
        if constraints_added > MAX_REASONABLE_CONSTRAINTS:
            validation_issues.append(
                f"Constraint explosion detected: {constraints_added} > {MAX_REASONABLE_CONSTRAINTS}"
            )

        # Handle validation failures
        if validation_issues:
            for issue in validation_issues:
                logger.error(f"❌ {self.constraint_id}: {issue}")

            # Fail fast for critical issues
            if self.is_critical and constraints_added == 0:
                raise RuntimeError(
                    f"{self.constraint_id}: Critical constraint validation failed"
                )
            elif constraints_added > MAX_REASONABLE_CONSTRAINTS:
                raise RuntimeError(
                    f"{self.constraint_id}: Constraint explosion prevented"
                )

    def _handle_zero_constraints(self):
        """FIXED: Handle zero constraint generation with appropriate response"""
        logger.warning(f"⚠️ {self.constraint_id}: No constraints were added!")

        # Provide context-specific guidance
        if self.constraint_category == "INVIGILATOR":
            logger.warning(
                "  This may indicate missing invigilator data or assignments"
            )
        elif self.constraint_category == "STUDENT_CONFLICT":
            logger.warning(
                "  This may indicate no student conflicts or missing student-exam mappings"
            )
        elif self.constraint_category == "CORE":
            logger.error("  CORE constraints should always generate constraints!")

        # Log debugging information
        logger.debug(f"🔍 {self.constraint_id}: Zero constraints debugging:")
        logger.debug(f"  Category: {self.constraint_category}")
        logger.debug(f"  Is critical: {self.is_critical}")
        logger.debug(f"  Min expected: {self.min_expected_constraints}")

    def _increment_constraint_count(self, n: int = 1):
        """Increment constraint counter with validation"""
        if n <= 0:
            logger.warning(
                f"⚠️ {self.constraint_id}: Invalid constraint count increment: {n}"
            )
            return

        self._constraint_count += n
        logger.debug(
            f"➕ {self.constraint_id}: Added {n} constraints (total: {self._constraint_count})"
        )

    def get_statistics(self) -> Dict[str, Any]:
        """FIXED: Return comprehensive constraint statistics with validation info"""
        validation = self._validate_essential_data()

        return {
            "constraint_id": self.constraint_id,
            "category": self.constraint_category,
            "enabled": self.enabled,
            "is_critical": self.is_critical,
            "min_expected_constraints": self.min_expected_constraints,
            "constraint_count": self._constraint_count,
            "constraints_added": self._constraints_added,
            "dependencies": self.dependencies,
            "validation_passed": validation,
            "shared_data_access": {
                "conflict_pairs": len(self.conflict_pairs),
                "student_exams": len(self.student_exams),
                "effective_capacities": len(self.effective_capacities),
                "allowed_rooms": len(self.allowed_rooms),
            },
            "local_variables": len(self._local_vars),
            "variables_initialized": hasattr(self, "_variables_initialized"),
        }

    def reset(self):
        """Reset constraint state with comprehensive cleanup"""
        logger.info(f"🔄 {self.constraint_id}: Resetting constraint state")
        self._constraints_added = False
        self._constraint_count = 0
        self._local_vars.clear()

        if hasattr(self, "_variables_initialized"):
            delattr(self, "_variables_initialized")

        logger.debug(f"✅ {self.constraint_id}: Reset complete")

    def validate_dependencies(self, available_modules: Set[str]) -> bool:
        """Validate dependencies with comprehensive checking"""
        if not self.dependencies:
            logger.debug(f"✅ {self.constraint_id}: No dependencies required")
            return True

        missing = set(self.dependencies) - available_modules
        if missing:
            logger.error(f"❌ {self.constraint_id}: Missing dependencies: {missing}")
            logger.error(f"  Available modules: {sorted(available_modules)}")
            logger.error(f"  Required dependencies: {self.dependencies}")
            return False

        logger.debug(
            f"✅ {self.constraint_id}: All dependencies satisfied: {self.dependencies}"
        )
        return True

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}(id={self.constraint_id}, "
            f"category={self.constraint_category}, "
            f"constraints={self._constraint_count}, "
            f"enabled={self.enabled}, "
            f"critical={self.is_critical})"
        )

    def __repr__(self) -> str:
        return self.__str__()
