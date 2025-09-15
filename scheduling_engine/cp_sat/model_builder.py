# scheduling_engine/cp_sat/model_builder.py

"""
FIXED Model Builder - Comprehensive Enhancement

Key Fixes:
- Enhanced error handling and validation
- Better constraint registration and activation
- Improved logging and debugging
- Robust configuration management
- Proper dependency resolution
"""

from ortools.sat.python import cp_model
from typing import Dict, Any, List, Optional
import logging
import traceback

logger = logging.getLogger(__name__)


class CPSATModelBuilder:
    """
    FIXED model builder with comprehensive enhancements.
    """

    def __init__(self, problem):
        """Initialize model builder with enhanced validation."""
        self.problem = problem
        self.model = cp_model.CpModel()
        self._build_stats = {}

        logger.info(
            f"🏗️ Initialized CPSATModelBuilder for problem: {getattr(problem, 'id', 'unknown')}"
        )

    def configure_standard(self):
        """Configure for standard operation (recommended)."""
        logger.info("⚙️ Configuring STANDARD setup...")
        try:
            if hasattr(self.problem, "constraint_registry"):
                self.problem.constraint_registry.configure_standard()
                active = self.problem.constraint_registry.get_active_constraints()
                logger.info(
                    f"✅ STANDARD configuration complete. Active: {sorted(active)}"
                )
            else:
                logger.warning(
                    "⚠️ Problem has no constraint_registry - creating default configuration"
                )
                self._create_default_registry()
        except Exception as e:
            logger.error(f"❌ Failed to configure STANDARD setup: {e}")
            raise
        return self

    def configure_with_student_conflicts(self):
        """Configure with student conflict prevention."""
        logger.info("⚙️ Configuring STUDENT_CONFLICTS setup...")
        try:
            if hasattr(self.problem, "constraint_registry"):
                self.problem.constraint_registry.configure_with_student_conflicts()
                active = self.problem.constraint_registry.get_active_constraints()
                logger.info(
                    f"✅ STUDENT_CONFLICTS configuration complete. Active: {sorted(active)}"
                )
            else:
                logger.warning(
                    "⚠️ Problem has no constraint_registry - creating default configuration"
                )
                self._create_default_registry()
                self.problem.constraint_registry.configure_with_student_conflicts()
        except Exception as e:
            logger.error(f"❌ Failed to configure STUDENT_CONFLICTS setup: {e}")
            raise
        return self

    def configure_complete(self):
        """Configure complete system with all features."""
        logger.info("⚙️ Configuring COMPLETE setup...")
        try:
            if hasattr(self.problem, "constraint_registry"):
                self.problem.constraint_registry.configure_complete()
                active = self.problem.constraint_registry.get_active_constraints()
                logger.info(
                    f"✅ COMPLETE configuration complete. Active: {sorted(active)}"
                )
            else:
                logger.warning(
                    "⚠️ Problem has no constraint_registry - creating default configuration"
                )
                self._create_default_registry()
                self.problem.constraint_registry.configure_complete()
        except Exception as e:
            logger.error(f"❌ Failed to configure COMPLETE setup: {e}")
            raise
        return self

    def _create_default_registry(self):
        """Create default constraint registry if missing."""
        try:
            from scheduling_engine.core.constraint_registry import ConstraintRegistry

            self.problem.constraint_registry = ConstraintRegistry()
            logger.info("✅ Created default constraint registry")
        except ImportError as e:
            logger.error(f"❌ Cannot create constraint registry: {e}")
            raise

    def build(self):
        """
        Build CP-SAT model with comprehensive error handling and validation.
        """
        logger.info("🚀 Starting ENHANCED CP-SAT model build process...")

        try:
            # Validate problem data
            self._validate_problem_data()

            # Validate constraint configuration
            validation = self.validate_configuration()
            if not validation["valid"]:
                raise RuntimeError(
                    f"Configuration validation failed: {validation['errors']}"
                )

            # Log warnings if any
            for warning in validation.get("warnings", []):
                logger.warning(f"⚠️ Configuration warning: {warning}")

            # Create optimized shared variables
            logger.info("🔧 Creating optimized variables with enhanced validation...")
            shared_variables = self._create_shared_variables()

            # Create and configure constraint manager
            logger.info("🔧 Creating and configuring constraint manager...")
            constraint_manager = self._create_constraint_manager()

            # Build constraints
            logger.info("🏗️ Building constraints using shared variables...")
            build_stats = self._build_constraints(constraint_manager, shared_variables)

            # Store build statistics
            self._build_stats = build_stats

            # Log successful build
            self._log_build_success(build_stats)

            return self.model, shared_variables

        except Exception as e:
            logger.error(f"❌ Model build FAILED: {e}")
            logger.error(f"🐛 Traceback:\n{traceback.format_exc()}")
            raise

    def _validate_problem_data(self):
        """Comprehensive problem data validation."""
        logger.info("🔍 Validating problem data...")

        required_attributes = ["exams", "time_slots", "rooms", "days"]
        missing_attrs = []

        for attr in required_attributes:
            if not hasattr(self.problem, attr):
                missing_attrs.append(attr)
            elif not getattr(self.problem, attr):
                missing_attrs.append(f"{attr} (empty)")

        if missing_attrs:
            raise ValueError(f"Problem missing essential data: {missing_attrs}")

        # Log data sizes
        logger.info(f"📊 Problem size validation:")
        logger.info(f"  • Exams: {len(self.problem.exams)}")
        logger.info(f"  • Time slots: {len(self.problem.time_slots)}")
        logger.info(f"  • Rooms: {len(self.problem.rooms)}")
        logger.info(f"  • Days: {len(self.problem.days)}")

        # Validate minimum requirements
        if len(self.problem.exams) == 0:
            raise ValueError("No exams to schedule")
        if len(self.problem.time_slots) == 0:
            raise ValueError("No time slots available")
        if len(self.problem.rooms) == 0:
            raise ValueError("No rooms available")

        logger.info("✅ Problem data validation passed")

    def _create_shared_variables(self):
        """Create shared variables with enhanced error handling."""
        try:
            from scheduling_engine.cp_sat.constraint_encoder import ConstraintEncoder

            encoder = ConstraintEncoder(self.problem, self.model)
            shared_variables = encoder.encode()

            logger.info(f"✅ Shared variables created successfully:")
            logger.info(f"  • x_vars: {len(shared_variables.x_vars)}")
            logger.info(f"  • z_vars: {len(shared_variables.z_vars)}")
            logger.info(f"  • y_vars: {len(shared_variables.y_vars)}")
            logger.info(f"  • u_vars: {len(shared_variables.u_vars)}")

            return shared_variables

        except Exception as e:
            logger.error(f"❌ Failed to create shared variables: {e}")
            raise

    def _create_constraint_manager(self):
        """Create and configure constraint manager."""
        try:
            from scheduling_engine.constraints.constraint_manager import (
                CPSATConstraintManager,
            )

            constraint_manager = CPSATConstraintManager()

            # Get active constraint classes from registry
            active_constraint_info = self._get_active_constraint_classes()

            if not active_constraint_info:
                raise RuntimeError("No constraint classes loaded from registry")

            # Register constraint classes with manager
            self._register_constraints_with_manager(
                constraint_manager, active_constraint_info
            )

            # Enable categories
            self._enable_constraint_categories(
                constraint_manager, active_constraint_info
            )

            return constraint_manager

        except Exception as e:
            logger.error(f"❌ Failed to create constraint manager: {e}")
            raise

    def _get_active_constraint_classes(self):
        """Get active constraint classes from registry."""
        try:
            if not hasattr(self.problem, "constraint_registry"):
                raise RuntimeError("Problem has no constraint registry")

            active_constraint_info = (
                self.problem.constraint_registry.get_active_constraint_classes()
            )

            if not active_constraint_info:
                raise RuntimeError("No active constraints found in registry")

            logger.info(f"📦 Loaded {len(active_constraint_info)} constraint classes:")
            for constraint_id, info in active_constraint_info.items():
                logger.info(f"  ✓ {constraint_id} (category: {info['category']})")

            return active_constraint_info

        except Exception as e:
            logger.error(f"❌ Failed to get active constraint classes: {e}")
            raise

    def _register_constraints_with_manager(
        self, constraint_manager, active_constraint_info
    ):
        """Register constraint classes with the manager."""
        logger.info("📝 Registering constraint classes with manager...")

        registration_success = 0
        registration_failed = 0

        for constraint_id, info in active_constraint_info.items():
            try:
                constraint_class = info["class"]
                category = info["category"]
                constraint_manager.register_module(constraint_class, category)
                registration_success += 1
                logger.debug(f"  ✓ Registered {constraint_id} in category {category}")
            except Exception as e:
                logger.error(f"  ❌ Failed to register {constraint_id}: {e}")
                registration_failed += 1

        logger.info(
            f"📝 Registration complete: {registration_success} success, {registration_failed} failed"
        )

        if registration_failed > 0:
            raise RuntimeError(
                f"Failed to register {registration_failed} constraint classes"
            )

    def _enable_constraint_categories(self, constraint_manager, active_constraint_info):
        """Enable constraint categories in the manager."""
        active_categories = set(
            info["category"] for info in active_constraint_info.values()
        )

        logger.info(
            f"🔧 Enabling {len(active_categories)} constraint categories: {sorted(active_categories)}"
        )

        for category in active_categories:
            try:
                constraint_manager.enable_module_category(category)
                logger.debug(f"  ✓ Enabled category: {category}")
            except Exception as e:
                logger.error(f"  ❌ Failed to enable category {category}: {e}")
                raise

    def _build_constraints(self, constraint_manager, shared_variables):
        """Build constraints using the manager."""
        try:
            build_stats = constraint_manager.build_model(
                self.model, self.problem, shared_variables
            )

            if not build_stats["build_successful"]:
                error_msg = build_stats.get("error", "Unknown error")
                raise RuntimeError(f"Constraint build failed: {error_msg}")

            return build_stats

        except Exception as e:
            logger.error(f"❌ Failed to build constraints: {e}")
            raise

    def _log_build_success(self, build_stats):
        """Log successful build statistics."""
        logger.info(f"🎉 Model build SUCCESS!")
        logger.info(f"📊 Build statistics:")
        logger.info(f"  • Total modules: {build_stats['total_modules']}")
        logger.info(f"  • Total constraints: {build_stats['total_constraints']}")
        logger.info(f"  • Dependency order: {build_stats['dependency_order']}")

        # Log module-specific statistics
        module_stats = build_stats.get("module_statistics", {})
        if module_stats:
            logger.info("📋 Per-module constraint breakdown:")
            for module_id, stats in module_stats.items():
                constraint_count = stats.get("constraint_count", 0)
                category = stats.get("category", "UNKNOWN")
                logger.info(
                    f"  • {module_id} ({category}): {constraint_count} constraints"
                )

        # Log optimizations applied
        optimizations = build_stats.get("optimizations_applied", [])
        if optimizations:
            logger.info("🚀 Applied optimizations:")
            for opt in optimizations:
                logger.info(f"  • {opt}")

    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration with enhanced reporting."""
        validation = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": [],
        }

        try:
            # Check if constraint registry exists
            if not hasattr(self.problem, "constraint_registry"):
                validation["errors"].append("Problem has no constraint registry")
                validation["valid"] = False
                return validation

            # Check if any constraints are active
            active_constraints = (
                self.problem.constraint_registry.get_active_constraints()
            )
            if not active_constraints:
                validation["errors"].append(
                    "No constraints activated - model will be incomplete"
                )
                validation["valid"] = False

            # Check for essential CORE constraints
            core_constraints = [
                "StartUniquenessConstraint",
                "OccupancyDefinitionConstraint",
                "RoomAssignmentBasicConstraint",
            ]

            active_core = [c for c in core_constraints if c in active_constraints]
            if len(active_core) < len(core_constraints):
                missing = set(core_constraints) - set(active_core)
                validation["errors"].append(
                    f"Missing essential CORE constraints: {missing}"
                )
                validation["valid"] = False

            # Check for constraint class availability
            try:
                active_classes = (
                    self.problem.constraint_registry.get_active_constraint_classes()
                )
                if len(active_classes) < len(active_constraints):
                    validation["warnings"].append(
                        f"Some constraint classes could not be loaded: "
                        f"{len(active_classes)}/{len(active_constraints)} loaded"
                    )
            except Exception as e:
                validation["errors"].append(f"Failed to load constraint classes: {e}")
                validation["valid"] = False

        except Exception as e:
            validation["errors"].append(f"Configuration validation failed: {e}")
            validation["valid"] = False

        return validation

    def get_build_statistics(self) -> Dict[str, Any]:
        """Get comprehensive build statistics."""
        try:
            registry_summary = (
                self.problem.constraint_registry.get_configuration_summary()
                if hasattr(self.problem, "constraint_registry")
                else {}
            )
            validation = self.validate_configuration()

            return {
                "builder_type": "CPSATModelBuilder",
                "constraint_registry": registry_summary,
                "validation": validation,
                "build_stats": self._build_stats,
                "features": {
                    "optimized_variables": True,
                    "c6_domain_restriction": True,
                    "shared_precomputed_data": True,
                    "enhanced_error_handling": True,
                    "comprehensive_logging": True,
                    "mathematical_compliance": True,
                },
            }
        except Exception as e:
            logger.error(f"❌ Failed to get build statistics: {e}")
            return {"error": str(e)}


def create_optimized_model_builder(
    problem, configuration: str = "standard"
) -> CPSATModelBuilder:
    """
    Factory function to create configured model builder with enhanced validation.
    """
    logger.info(
        f"🏭 Creating optimized model builder with '{configuration}' configuration..."
    )

    try:
        builder = CPSATModelBuilder(problem)

        # Configure based on requested configuration
        if configuration == "minimal":
            if hasattr(problem, "constraint_registry"):
                problem.constraint_registry.configure_minimal()
            else:
                logger.warning("Problem has no constraint registry - using defaults")
        elif configuration == "standard":
            builder.configure_standard()
        elif configuration == "with_conflicts":
            builder.configure_with_student_conflicts()
        elif configuration == "complete":
            builder.configure_complete()
        else:
            raise ValueError(
                f"Unknown configuration: {configuration}. "
                f"Valid: minimal, standard, with_conflicts, complete"
            )

        # Validate configuration
        validation = builder.validate_configuration()
        if not validation["valid"]:
            logger.error(f"❌ Configuration validation FAILED: {validation['errors']}")
            raise RuntimeError(
                f"Configuration validation failed: {validation['errors']}"
            )

        # Log warnings
        for warning in validation.get("warnings", []):
            logger.warning(f"⚠️ Configuration warning: {warning}")

        logger.info(
            f"✅ Created optimized model builder with '{configuration}' configuration"
        )
        return builder

    except Exception as e:
        logger.error(f"❌ Failed to create model builder: {e}")
        raise
