# scheduling_engine/core/constraint_registry.py

"""
MODIFIED Constraint Registry - For dynamic, database-driven constraint definitions.
This registry is populated at runtime based on the configuration for the current scheduling job.
"""

import logging
import importlib
from typing import Dict, List, Set, Optional, Any, TYPE_CHECKING, Type

from .constraint_types import ConstraintDefinition

if TYPE_CHECKING:
    from .problem_model import ExamSchedulingProblem

logger = logging.getLogger(__name__)


class ConstraintRegistry:
    """Registry for dynamically loaded, parameterized constraint definitions."""

    def __init__(self):
        self.definitions: Dict[str, ConstraintDefinition] = {}
        self.active_constraints: Set[str] = set()
        self.category_constraints: Dict[str, List[str]] = {}
        self._class_name_to_id: Dict[str, str] = {}
        self._cached_constraint_classes: Dict[str, Type] = {}
        self._active_constraints_changed = True
        self._cached_active_classes: Optional[List[ConstraintDefinition]] = None

    def load_definitions(
        self, definitions: List[ConstraintDefinition], module_map: Dict[str, str]
    ):
        """
        Load constraint definitions dynamically from the problem model.
        This replaces the old static loading mechanism.
        """
        self.definitions.clear()
        self.category_constraints.clear()
        self._class_name_to_id.clear()

        for definition in definitions:
            self.definitions[definition.id] = definition
            category_name = definition.category.name
            if category_name not in self.category_constraints:
                self.category_constraints[category_name] = []
            self.category_constraints[category_name].append(definition.id)

            # Link the definition to its implementing class from the module map
            try:
                full_class_path = module_map.get(definition.id)
                if not full_class_path:
                    # Also check for class name for foundational constraints
                    full_class_path = module_map.get(definition.name)

                if full_class_path:
                    module_path, class_name = full_class_path.rsplit(".", 1)
                    mod = importlib.import_module(module_path)
                    cls = getattr(mod, class_name)
                    definition.constraint_class = cls
                    self._class_name_to_id[class_name] = definition.id
                else:
                    raise KeyError
            except (KeyError, ImportError, AttributeError) as e:
                logger.warning(
                    f"Could not find or load class for constraint '{definition.id}': {e}"
                )

        logger.info(
            f"Loaded {len(self.definitions)} configurable constraint definitions."
        )
        logger.info(f"Available categories: {list(self.category_constraints.keys())}")

    def activate(self, constraint_id: str):
        """Activate a constraint by its ID."""
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

    def get_definitions(self) -> List[ConstraintDefinition]:
        """Returns a list of all loaded constraint definitions."""
        return list(self.definitions.values())

    def get_active_constraints(self) -> Set[str]:
        """Get set of active constraint IDs."""
        return self.active_constraints

    def _resolve_dependency_order(self, active_constraints: Set[str]) -> List[str]:
        """Resolve constraint dependencies using topological sort."""
        dependency_graph = {}
        for cid in active_constraints:
            definition = self.definitions.get(cid)
            if not definition or not definition.constraint_class:
                dependency_graph[cid] = []
                continue

            dependencies = getattr(definition.constraint_class, "dependencies", [])
            dependency_ids = [
                self._class_name_to_id.get(dep_name) for dep_name in dependencies
            ]
            valid_deps = [
                dep_id
                for dep_id in dependency_ids
                if dep_id and dep_id in active_constraints
            ]
            dependency_graph[cid] = valid_deps

        resolved_order = []
        visited = set()
        recursion_stack = set()

        def visit(node):
            if node in recursion_stack:
                logger.error(f"Circular dependency detected involving {node}")
                raise RuntimeError(f"Circular dependency: {recursion_stack}")
            if node in visited:
                return

            recursion_stack.add(node)
            for dep in dependency_graph.get(node, []):
                visit(dep)

            recursion_stack.remove(node)
            visited.add(node)
            resolved_order.append(node)

        for cid in sorted(list(active_constraints)):
            if cid not in visited:
                visit(cid)

        return resolved_order

    def get_active_constraint_classes(self) -> List[ConstraintDefinition]:
        """
        Returns the full ConstraintDefinition objects for active constraints,
        ordered by dependency.
        """
        if (
            not self._active_constraints_changed
            and self._cached_active_classes is not None
        ):
            return self._cached_active_classes

        logger.info(
            f"Resolving active constraint classes for {len(self.active_constraints)} constraints."
        )

        resolved_order = self._resolve_dependency_order(self.active_constraints)
        logger.info(f"🔧 Constraint dependency order resolved: {resolved_order}")

        active_definitions = []
        for cid in resolved_order:
            definition = self.definitions.get(cid)
            if definition and definition.constraint_class:
                active_definitions.append(definition)
            else:
                logger.warning(
                    f"Active constraint '{cid}' has no valid definition or class, skipping."
                )
        self._cached_active_classes = active_definitions
        self._active_constraints_changed = False

        logger.info(
            f"Successfully loaded {len(active_definitions)} active constraint classes."
        )
        return active_definitions

    def get_definition(self, constraint_id: str) -> Optional[ConstraintDefinition]:
        """Get a specific constraint definition by ID."""
        return self.definitions.get(constraint_id)
