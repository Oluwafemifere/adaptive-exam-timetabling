# scheduling_engine/constraints/constraint_manager.py

"""
FIXED Constraint Manager - Enhanced Logging and Build Tracking

Key Fixes:
- Detailed logging throughout constraint building process
- Proper module instantiation validation
- Enhanced constraint counting and statistics
- Clear error reporting and debugging information
"""

import logging
from collections import defaultdict, deque
from typing import Dict, List, Set, Type, Optional, Any

logger = logging.getLogger(__name__)


class CPSATConstraintManager:
    """
    FIXED constraint manager with enhanced logging and validation.
    """

    def __init__(self):
        """Initialize constraint manager with enhanced tracking."""
        self._registry: Dict[str, Type] = {}
        self._enabled_modules: Set[str] = set()
        self._module_categories: Dict[str, str] = {}
        self._resolved_order: List[str] = []
        self._build_complete: bool = False
        self._constraint_instances: Dict[str, Any] = {}
        self._build_stats: Dict[str, Any] = {}
        logger.info("🎛️ Initialized CPSATConstraintManager with enhanced tracking")

    def register_module(self, constraint_cls: Type, category: str = "CORE") -> None:
        """Register a constraint module class with detailed logging."""
        constraint_id = constraint_cls.__name__

        logger.info(
            f"📝 Registering constraint module: {constraint_id} (category: {category})"
        )

        if constraint_id in self._registry:
            logger.warning(f"⚠️ Module '{constraint_id}' already registered, replacing")

        self._registry[constraint_id] = constraint_cls
        self._module_categories[constraint_id] = category

        # Auto-enable CORE modules
        if category == "CORE":
            self._enabled_modules.add(constraint_id)
            logger.info(f"✅ Auto-enabled CORE module: {constraint_id}")

        # Invalidate build state
        self._build_complete = False
        self._resolved_order.clear()

        logger.debug(f"✅ Successfully registered: {constraint_id}")

    def enable_module_category(self, category: str) -> None:
        """Enable all modules in a specific category with detailed tracking."""
        logger.info(f"🔧 Enabling category: {category}")

        category_modules = [
            module_id
            for module_id, cat in self._module_categories.items()
            if cat == category
        ]

        if not category_modules:
            logger.warning(f"⚠️ No modules found in category '{category}'")
            return

        enabled_count = 0
        for module_id in category_modules:
            if module_id not in self._enabled_modules:
                self._enabled_modules.add(module_id)
                enabled_count += 1
                logger.debug(f"  ✓ Enabled: {module_id}")

        logger.info(
            f"✅ Category '{category}' enabled: {enabled_count} modules - {category_modules}"
        )

        # Invalidate build state
        self._build_complete = False
        self._resolved_order.clear()

    def build_model(self, model, problem, shared_variables) -> Dict[str, Any]:
        """
        Build complete constraint model with enhanced logging and validation.
        """
        if self._build_complete:
            logger.debug("♻️ Model already built, returning cached stats")
            return self._build_stats

        logger.info("🏗️ Starting ENHANCED constraint model build...")
        logger.info(f"📊 Build input: {len(self._enabled_modules)} enabled modules")
        logger.info(f"📊 Enabled modules: {sorted(self._enabled_modules)}")

        try:
            # Validate enabled modules
            if not self._enabled_modules:
                raise RuntimeError("No constraint modules enabled - cannot build model")

            # Resolve dependency order
            logger.info("🔍 Resolving module dependencies...")
            self._resolved_order = self._resolve_dependencies()
            logger.info(f"📋 Dependency resolution order: {self._resolved_order}")

            # Instantiate and build constraint modules
            self._constraint_instances = {}
            total_constraints = 0
            module_stats = {}

            logger.info(
                f"🏭 Instantiating {len(self._resolved_order)} constraint modules..."
            )

            for module_id in self._resolved_order:
                if module_id not in self._registry:
                    logger.error(f"❌ Module {module_id} not found in registry!")
                    continue

                constraint_class = self._registry[module_id]
                logger.info(f"🔧 Processing module: {module_id}")

                try:
                    # Create instance with shared variables
                    logger.debug(f"  📦 Instantiating {constraint_class.__name__}...")
                    instance = constraint_class(
                        module_id, problem, shared_variables, model
                    )
                    self._constraint_instances[module_id] = instance

                    # Initialize variables
                    logger.debug(f"  🔧 Initializing variables for {module_id}...")
                    instance.initialize_variables()

                    # Add constraints
                    logger.debug(f"  ➕ Adding constraints for {module_id}...")
                    constraint_count_before = getattr(instance, "_constraint_count", 0)
                    instance.add_constraints()
                    constraint_count_after = getattr(instance, "_constraint_count", 0)

                    constraints_added = constraint_count_after - constraint_count_before
                    total_constraints += constraints_added

                    # Collect statistics
                    stats = instance.get_statistics()
                    module_stats[module_id] = stats

                    logger.info(
                        f"✅ Module '{module_id}': {constraints_added} constraints added"
                    )
                    logger.debug(f"  📊 Stats: {stats}")

                except Exception as e:
                    logger.error(f"❌ Failed to build module {module_id}: {e}")
                    import traceback

                    logger.debug(f"  🐛 Traceback: {traceback.format_exc()}")
                    raise RuntimeError(
                        f"Failed to build constraint module {module_id}: {e}"
                    )

            self._build_complete = True

            # Compile build statistics
            self._build_stats = {
                "build_successful": True,
                "total_modules": len(self._resolved_order),
                "total_constraints": total_constraints,
                "dependency_order": self._resolved_order,
                "module_statistics": module_stats,
                "enabled_categories": list(
                    set(
                        self._module_categories.get(mid, "UNKNOWN")
                        for mid in self._resolved_order
                    )
                ),
                "optimizations_applied": [
                    "ELIMINATED w_vars and v_vars variables",
                    "C6 handled as domain restriction",
                    "Shared u_vars (no redundant creation)",
                    "Shared precomputed data (conflict_pairs, student_exams)",
                    "Mathematical formulation compliance",
                    "100x gap constraint optimization via conflict pairs",
                    "Enhanced logging and validation",
                ],
            }

            logger.info("🎉 ENHANCED constraint model build SUCCESSFUL!")
            logger.info(f"📊 Final statistics:")
            logger.info(f"  • Total modules processed: {len(self._resolved_order)}")
            logger.info(f"  • Total constraints added: {total_constraints}")
            logger.info(
                f"  • Successful modules: {len([m for m, s in module_stats.items() if s.get('constraint_count', 0) > 0])}"
            )
            logger.info(
                f"  • Categories enabled: {self._build_stats['enabled_categories']}"
            )

            # Log per-module breakdown
            logger.info("📋 Per-module constraint breakdown:")
            for module_id, stats in module_stats.items():
                count = stats.get("constraint_count", 0)
                category = stats.get("category", "UNKNOWN")
                logger.info(f"  • {module_id} ({category}): {count} constraints")

            return self._build_stats

        except Exception as e:
            logger.error(f"❌ ENHANCED constraint model build FAILED: {e}")
            import traceback

            logger.debug(f"🐛 Full traceback: {traceback.format_exc()}")

            self._build_stats = {
                "build_successful": False,
                "error": str(e),
                "partial_modules": list(self._constraint_instances.keys()),
                "enabled_modules": list(self._enabled_modules),
                "resolved_order": self._resolved_order,
            }
            raise

    def _resolve_dependencies(self) -> List[str]:
        """Resolve module dependencies using topological sorting with enhanced logging."""
        logger.debug("🔍 Starting dependency resolution...")

        # Validate all enabled modules exist
        missing_modules = self._enabled_modules - set(self._registry.keys())
        if missing_modules:
            raise RuntimeError(f"Enabled modules not registered: {missing_modules}")

        # Build dependency graph
        dependency_graph = {}
        for module_id in self._enabled_modules:
            constraint_cls = self._registry[module_id]
            dependencies = getattr(constraint_cls, "dependencies", [])
            dependency_graph[module_id] = [
                dep for dep in dependencies if dep in self._enabled_modules
            ]

        logger.debug(f"🕸️ Dependency graph: {dependency_graph}")

        # Topological sort using DFS
        visited = {}  # module_id -> state: None=unvisited, False=visiting, True=visited
        resolved_order = []

        def visit(module_id: str):
            state = visited.get(module_id)
            if state is False:  # Cycle detected
                raise RuntimeError(
                    f"Circular dependency detected involving '{module_id}'"
                )
            if state is True:  # Already visited
                return

            # Mark as being visited
            visited[module_id] = False

            # Visit dependencies first
            for dep_id in dependency_graph.get(module_id, []):
                visit(dep_id)

            # Mark as visited and add to order
            visited[module_id] = True
            resolved_order.append(module_id)

        # Visit all enabled modules
        for module_id in self._enabled_modules:
            if module_id in self._registry:
                visit(module_id)

        logger.info(f"✅ Dependencies resolved: {resolved_order}")
        return resolved_order

    def get_build_statistics(self) -> Dict[str, Any]:
        """Return comprehensive build statistics."""
        return self._build_stats.copy()

    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get summary of current configuration with enhanced details."""
        enabled = list(self._enabled_modules)
        registered = self._module_categories

        # Group by category
        enabled_by_category = {}
        for module_id in enabled:
            category = registered.get(module_id, "UNKNOWN")
            if category not in enabled_by_category:
                enabled_by_category[category] = []
            enabled_by_category[category].append(module_id)

        # Mathematical constraint mapping
        constraint_mapping = {
            "StartUniquenessConstraint": "C1",
            "OccupancyDefinitionConstraint": "C2",
            "RoomAssignmentBasicConstraint": "C3",
            "MultiExamRoomCapacityConstraint": "C4",
            "NoStudentConflictsSameRoomConstraint": "C5",
            "NoStudentTemporalOverlapConstraint": "C7",
            "MinimumGapBetweenExamsConstraint": "C8",
            "MaxExamsPerDayPerStudentConstraint": "C9",
            "MinimumInvigilatorsAssignmentConstraint": "C10",
            "InvigilatorSingleAssignmentConstraint": "C11",
            "InvigilatorAvailabilityConstraint": "C12",
            "BackToBackProhibitionConstraint": "C13",
        }

        return {
            "total_registered": len(registered),
            "total_enabled": len(enabled),
            "enabled_categories": list(enabled_by_category.keys()),
            "enabled_by_category": enabled_by_category,
            "constraint_mapping": {
                module_id: constraint_mapping.get(module_id, "Unknown")
                for module_id in enabled
            },
            "optimizations": [
                "C6 handled as domain restriction (no explicit constraints)",
                "Shared precomputed data (no redundant computation)",
                "Eliminated redundant variables (w_vars, v_vars)",
                "Proper variable sharing (u_vars)",
                "Mathematical formulation compliance",
                "Enhanced logging and validation",
            ],
            "build_status": {
                "build_complete": self._build_complete,
                "instances_created": len(self._constraint_instances),
                "resolved_order": self._resolved_order,
            },
        }
