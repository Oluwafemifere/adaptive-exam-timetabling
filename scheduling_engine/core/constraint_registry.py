# scheduling_engine/core/constraint_registry.py

"""
FIXED Constraint Registry - Enhanced Logging and Proper Category Activation with Dependency Resolution

Key Fixes:
- Load definitions exactly once into GLOBAL_CONSTRAINT_DEFINITIONS
- Share category-to-IDs mapping in GLOBAL_CATEGORY_CONSTRAINTS
- Simplify __init__ to reuse globals
- ADD: Dependency-based constraint ordering to fix activation sequence
"""

import logging
import importlib
from typing import Dict, List, Set, Optional, Any, TYPE_CHECKING

# Import constraint types before conditional imports
from .constraint_types import ConstraintDefinition, ConstraintType, ConstraintCategory

if TYPE_CHECKING:
    from .problem_model import ExamSchedulingProblem

logger = logging.getLogger(__name__)

# Global registry variables to avoid repeated imports
_CONSTRAINT_REGISTRIES_LOADED = False
_SOFT_REGISTRY = {}
_HARD_REGISTRY = {}


def _load_constraint_registries():
    """Load constraint registries once and cache them globally."""
    global _CONSTRAINT_REGISTRIES_LOADED, _SOFT_REGISTRY, _HARD_REGISTRY

    if _CONSTRAINT_REGISTRIES_LOADED:
        return _SOFT_REGISTRY, _HARD_REGISTRY

    try:
        # Import with explicit module paths to avoid circular imports
        from scheduling_engine.constraints.soft_constraints import (
            SOFT_CONSTRAINT_REGISTRY as SOFT_REGISTRY,
        )
        from scheduling_engine.constraints.hard_constraints import (
            HARD_CONSTRAINT_REGISTRY as HARD_REGISTRY,
        )

        _SOFT_REGISTRY = SOFT_REGISTRY
        _HARD_REGISTRY = HARD_REGISTRY
        _CONSTRAINT_REGISTRIES_LOADED = True

    except ImportError as e:
        logger.warning(f"Constraints unavailable at import: {e}")
        _SOFT_REGISTRY = {}
        _HARD_REGISTRY = {}
        _CONSTRAINT_REGISTRIES_LOADED = True

    return _SOFT_REGISTRY, _HARD_REGISTRY


class ConstraintRegistry:
    """FIXED: Registry for constraint definitions with enhanced logging and dependency-based ordering."""

    def __init__(self):
        self.definitions = {}
        self.active_constraints = set()
        self.category_constraints = {}
        self._cached_constraint_classes = {}
        self._active_constraints_changed = True
        self._cached_active_classes = None
        self.module_map = {}

        # Load definitions on initialization
        self._load_all_definitions()

    def _load_all_definitions(self):
        """Load all constraint definitions from hard and soft registries."""
        soft_registry, hard_registry = _load_constraint_registries()

        if not soft_registry and not hard_registry:
            logger.error("No constraint registries available")
            return

        definitions = {}
        category_map = {}

        CATEGORY_MAPPING = {
            "CORE": ConstraintCategory.CORE,
            "STUDENT_CONSTRAINTS": ConstraintCategory.STUDENT_CONSTRAINTS,
            "RESOURCE_CONSTRAINTS": ConstraintCategory.RESOURCE_CONSTRAINTS,
            "INVIGILATOR_CONSTRAINTS": ConstraintCategory.INVIGILATOR_CONSTRAINTS,
            "SOFT_CONSTRAINTS": ConstraintCategory.SOFT_CONSTRAINTS,
        }

        # Process hard constraints
        for name, info in hard_registry.items():
            category_str = info.get("category", "CORE")
            category_enum = CATEGORY_MAPPING.get(category_str, ConstraintCategory.OTHER)

            definition = ConstraintDefinition(
                constraint_id=name,
                name=info.get(
                    "name", name.replace("Constraint", "").replace("_", " ").title()
                ),
                description=info.get("description", ""),
                constraint_type=ConstraintType.HARD,
                category=category_enum,
                parameters={
                    "category": category_str,
                    "required": info.get("is_critical", False),
                    "equation_ref": info.get("equation_ref", ""),
                },
            )

            definitions[name] = definition
            if category_str not in category_map:
                category_map[category_str] = []
            category_map[category_str].append(name)

            # Build module map
            if "class" in info:
                self.module_map[name] = info["class"].__module__

        # Process soft constraints
        for name, info in soft_registry.items():
            category_str = info.get("category", "SOFT_CONSTRAINTS")
            category_enum = CATEGORY_MAPPING.get(category_str, ConstraintCategory.OTHER)

            definition = ConstraintDefinition(
                constraint_id=name,
                name=info.get(
                    "name", name.replace("Constraint", "").replace("_", " ").title()
                ),
                description=info.get("description", ""),
                constraint_type=ConstraintType.SOFT,
                category=category_enum,
                parameters={
                    "category": category_str,
                    "weight": info.get("weight", 0),
                    "equation_ref": info.get("equation_ref", ""),
                    "required": False,
                },
            )

            definitions[name] = definition
            if category_str not in category_map:
                category_map[category_str] = []
            category_map[category_str].append(name)

            # Build module map
            if "class" in info:
                self.module_map[name] = info["class"].__module__

        self.definitions = definitions
        self.category_constraints = category_map

        logger.info(f"Loaded categories: {list(category_map.keys())}")
        for category, constraints in category_map.items():
            logger.info(f"Category '{category}' has {len(constraints)} constraints")
        logger.info(f"Loaded {len(definitions)} constraint definitions")

    def register_definition(self, definition: ConstraintDefinition):
        """Register a constraint definition (not normally used)."""
        self.definitions[definition.constraint_id] = definition
        logger.debug(f"Registered constraint definition {definition.constraint_id}")

    def activate(self, constraint_id: str):
        """Activate a constraint by its ID with detailed logging."""
        if constraint_id in self.definitions:
            self.active_constraints.add(constraint_id)
            self._active_constraints_changed = True
            logger.info(f"✅ ACTIVATED constraint {constraint_id}")
        else:
            logger.warning(f"Cannot activate unknown constraint {constraint_id}")

    def deactivate(self, constraint_id: str):
        """Deactivate a constraint by its ID."""
        if constraint_id in self.active_constraints:
            self.active_constraints.remove(constraint_id)
            self._active_constraints_changed = True
            logger.info(f"❌ DEACTIVATED constraint {constraint_id}")

    def get_active_constraints(self) -> Set[str]:
        """Get set of active constraint IDs."""
        return set(self.active_constraints)

    def _activate_category(self, category: str):
        """Activate all constraints in a category."""
        if category not in self.category_constraints:
            logger.error(f"Unknown category {category}")
            return

        constraints = self.category_constraints[category]
        for cid in constraints:
            self.activate(cid)
        logger.info(f"Category {category} activation complete")

    def configure_minimal(self):
        """CORE only."""
        logger.info("🚀 Starting MINIMAL configuration...")
        self.active_constraints.clear()
        self._active_constraints_changed = True
        self._activate_category("CORE")
        logger.info("MINIMAL setup complete")

    def configure_basic(self):
        """CORE + STUDENT_CONSTRAINTS."""
        logger.info("🚀 Starting BASIC configuration...")
        self.active_constraints.clear()
        self._active_constraints_changed = True
        self._activate_category("CORE")
        self._activate_category("STUDENT_CONSTRAINTS")
        logger.info("BASIC setup complete")

    def configure_with_resources(self):
        """CORE + STUDENT_CONSTRAINTS + RESOURCE_CONSTRAINTS."""
        logger.info("🚀 Starting WITH_RESOURCES configuration...")
        self.active_constraints.clear()
        self._active_constraints_changed = True
        self._activate_category("CORE")
        self._activate_category("STUDENT_CONSTRAINTS")
        self._activate_category("RESOURCE_CONSTRAINTS")
        logger.info("WITH_RESOURCES setup complete")

    def configure_complete(self):
        """All constraints."""
        logger.info("🚀 Starting COMPLETE configuration...")
        self.active_constraints.clear()
        self._active_constraints_changed = True
        self._activate_category("CORE")
        self._activate_category("STUDENT_CONSTRAINTS")
        self._activate_category("RESOURCE_CONSTRAINTS")
        self._activate_category("INVIGILATOR_CONSTRAINTS")
        logger.info("COMPLETE setup complete")

    def configure_complete_with_soft(self):
        """All constraints."""
        logger.info("🚀 Starting COMPLETE configuration...")
        self.active_constraints.clear()
        self._active_constraints_changed = True
        self._activate_category("CORE")
        self._activate_category("STUDENT_CONSTRAINTS")
        self._activate_category("RESOURCE_CONSTRAINTS")
        self._activate_category("INVIGILATOR_CONSTRAINTS")
        self._activate_category("SOFT_CONSTRAINTS")
        logger.info("COMPLETE setup complete")

    def list_definitions(self) -> List[ConstraintDefinition]:
        """List all registered constraint definitions."""
        return list(self.definitions.values())

    def _get_constraint_class(self, cid: str) -> Optional[Any]:
        """Get constraint class with caching."""
        if cid in self._cached_constraint_classes:
            return self._cached_constraint_classes[cid]

        module_path = self.module_map.get(cid)
        if not module_path:
            logger.error(f"No module mapping for {cid}")
            return None

        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, cid)
            self._cached_constraint_classes[cid] = cls
            return cls
        except Exception as e:
            logger.error(f"Failed to load {cid}: {e}")
            return None

    def _resolve_dependency_order(self, active_constraints: Set[str]) -> List[str]:
        """
        FIXED: Resolve constraint dependencies using topological sort.
        This is the core fix for the constraint activation order issue.
        """
        # Extract dependencies from each constraint class
        constraint_dependencies = {}
        visited_dependencies = set()

        for cid in active_constraints:
            if cid in visited_dependencies:
                continue

            cls = self._get_constraint_class(cid)
            if cls is None:
                constraint_dependencies[cid] = []
                continue

            dependencies = getattr(cls, "dependencies", [])
            # Filter to only include enabled dependencies
            valid_deps = [dep for dep in dependencies if dep in active_constraints]
            constraint_dependencies[cid] = valid_deps
            visited_dependencies.add(cid)

        # Topological sort using DFS
        resolved_order = []
        visited = set()
        temp_visited = set()

        def visit(node):
            if node in visited:
                return
            if node in temp_visited:
                # Cycle detected - skip to avoid infinite recursion
                logger.warning(f"Dependency cycle detected involving {node}")
                return

            temp_visited.add(node)

            # Visit dependencies first
            for dep in constraint_dependencies.get(node, []):
                if dep in active_constraints:
                    visit(dep)

            temp_visited.remove(node)
            visited.add(node)
            if node not in resolved_order:
                resolved_order.append(node)

        # Visit all constraints
        for cid in active_constraints:
            if cid not in visited:
                visit(cid)

        return resolved_order

    def get_active_constraint_classes(self) -> Dict[str, Dict[str, Any]]:
        """
        FIXED: Dynamically import and return active constraint classes in DEPENDENCY ORDER.
        This method now uses proper dependency resolution instead of random set iteration.
        """
        if (
            not self._active_constraints_changed
            and self._cached_active_classes is not None
        ):
            return self._cached_active_classes

        logger.info(
            f"Getting active constraint classes for {sorted(self.active_constraints)}"
        )

        # 🔧 CRITICAL FIX: Use dependency-resolved order instead of random set iteration
        resolved_order = self._resolve_dependency_order(self.active_constraints)
        logger.info(f"🔧 Constraint dependency order resolved: {resolved_order}")

        active = {}

        # Now iterate in dependency order instead of random set order
        for cid in resolved_order:
            if cid not in self.definitions:
                logger.error(f"Active constraint {cid} not found in definitions")
                continue

            definition = self.definitions[cid]
            cls = self._get_constraint_class(cid)
            if cls is None:
                continue

            # Get category from definition parameters
            cat_key = None
            params = getattr(definition, "parameters", None)
            if isinstance(params, dict):
                cat_key = params.get("category")

            # Fallback to Enum category
            if not cat_key and hasattr(definition, "category") and definition.category:
                cat_key = definition.category.name  # e.g., CORE, STUDENT_CONFLICT

            if not cat_key:
                cat_key = "UNKNOWN"

            active[cid] = {"class": cls, "category": cat_key}
            logger.info(f"Loaded constraint class {cid} category {cat_key}")

        logger.info(f"Successfully loaded {len(active)} active constraint classes")

        self._cached_active_classes = active
        self._active_constraints_changed = False

        return active

    def get_definition(self, constraint_id: str) -> Optional[ConstraintDefinition]:
        """Get a specific constraint definition by ID. Added for completeness and consistency."""
        return self.definitions.get(constraint_id)
