# scheduling_engine/constraints/constraint_manager.py

"""
MODIFIED Constraint Manager for a dynamic, configurable, two-phase system.
This manager builds the model by instantiating constraint classes based on the
active, ordered list of ConstraintDefinition objects provided by the registry.
It now strictly separates non-configurable CORE constraints from DYNAMIC ones.
"""

import logging
from typing import Dict, Any, List, Set, cast
import time
import traceback

from scheduling_engine.core.problem_model import ExamSchedulingProblem
from scheduling_engine.cp_sat.constraint_encoder import SharedVariables
from scheduling_engine.core.constraint_types import (
    ConstraintDefinition,
    ConstraintType,
    ConstraintCategory,
)
from scheduling_engine.constraints.hard_constraints import (
    # Foundational (Core) Constraints
    StartUniquenessConstraint,
    StartFeasibilityConstraint,
    OccupancyDefinitionConstraint,
    RoomAssignmentConsistencyConstraint,
    RoomContinuityConstraint,
    InvigilatorRequirementConstraint,
    InvigilatorSinglePresenceConstraint,
    InvigilatorContinuityConstraint,
    RoomCapacityHardConstraint,
    AggregateCapacityConstraint,
    UnifiedStudentConflictConstraint,  # <-- MOVED TO CORE
)

logger = logging.getLogger(__name__)


class CPSATConstraintManager:
    """Builds a CP-SAT model from a dynamic list of constraint definitions."""

    def __init__(self, problem: ExamSchedulingProblem):
        self.problem = problem
        self.registry = problem.constraint_registry
        self._build_stats: Dict[str, Any] = {}
        self._build_errors: List[str] = []
        self._constraint_instances: Dict[str, Any] = {}
        logger.info("🎛️  Initialized DYNAMIC CPSATConstraintManager.")

    def build_phase1_model(
        self, model, shared_variables: SharedVariables
    ) -> Dict[str, Any]:
        """Builds the Phase 1 (Timetabling) model with time-based constraints."""
        logger.info("🏗️  Starting DYNAMIC Phase 1 model build...")

        # --- CORE CONSTRAINTS (ALWAYS APPLIED) ---
        # These are foundational for a valid timetabling model.
        # --- START OF MODIFICATION ---
        core_constraints = {
            StartUniquenessConstraint,
            StartFeasibilityConstraint,
            OccupancyDefinitionConstraint,
            # AggregateCapacityConstraint,
            UnifiedStudentConflictConstraint,  # Now a core, non-configurable constraint
        }
        # --- END OF MODIFICATION ---

        # --- DYNAMIC CONSTRAINTS (APPLIED IF ACTIVE) ---
        # These represent configurable business rules.
        active_definitions = self.registry.get_active_constraint_classes()

        return self._build_model_from_definitions(
            model, shared_variables, active_definitions, core_constraints
        )

    def build_phase2_model(
        self, model, shared_variables: SharedVariables
    ) -> Dict[str, Any]:
        """Builds the full Phase 2 (Packing) model."""
        logger.info("🏗️  Starting DYNAMIC Full Phase 2 model build...")

        # --- CORE CONSTRAINTS (ALWAYS APPLIED) ---
        # These are foundational for a valid packing and assignment model.
        core_constraints = {
            RoomAssignmentConsistencyConstraint,
            RoomCapacityHardConstraint,
            RoomContinuityConstraint,
            InvigilatorRequirementConstraint,
            InvigilatorSinglePresenceConstraint,
            InvigilatorContinuityConstraint,
        }

        # --- DYNAMIC CONSTRAINTS (APPLIED IF ACTIVE) ---
        active_definitions = self.registry.get_active_constraint_classes()

        return self._build_model_from_definitions(
            model, shared_variables, active_definitions, core_constraints
        )

    def _build_model_from_definitions(
        self,
        model,
        shared_variables: SharedVariables,
        active_definitions: List[ConstraintDefinition],
        core_classes: Set[type],
    ) -> Dict[str, Any]:
        """Generic model builder that separates core from dynamic constraints."""
        build_start_time = time.time()
        total_constraints_added = 0
        successful_modules = 0
        self._build_errors = []
        self._constraint_instances = {}
        processed_classes = set()

        # --- 1. APPLY CORE, NON-CONFIGURABLE CONSTRAINTS ---
        logger.info(f"Applying {len(core_classes)} CORE constraints...")
        for cls in core_classes:
            try:
                # Use the definition from the registry if available (e.g., for params),
                # otherwise create a default one.
                definition = next(
                    (d for d in active_definitions if d.constraint_class == cls),
                    ConstraintDefinition(
                        id=cls.__name__,
                        name=cls.__name__,
                        description="Core foundational constraint.",
                        constraint_type=ConstraintType.HARD,
                        category=ConstraintCategory.CORE,
                        enabled=True,
                        constraint_class=cls,
                    ),
                )

                instance = self._instantiate_and_apply(
                    definition, model, shared_variables
                )
                if instance:
                    stats = instance.get_statistics()
                    total_constraints_added += stats.get("constraint_count", 0)
                    successful_modules += 1
                processed_classes.add(cls)
            except Exception as e:
                error_msg = f"Failed to build CORE module '{cls.__name__}': {e}"
                logger.error(f"❌ {error_msg}\n{traceback.format_exc()}")
                self._build_errors.append(error_msg)

        # --- 2. APPLY DYNAMIC, CONFIGURABLE CONSTRAINTS ---
        dynamic_definitions = [
            d for d in active_definitions if d.constraint_class not in processed_classes
        ]
        logger.info(
            f"Applying {len(dynamic_definitions)} DYNAMIC (configurable) constraints..."
        )
        for definition in dynamic_definitions:
            try:
                instance = self._instantiate_and_apply(
                    definition, model, shared_variables
                )
                if instance:
                    stats = instance.get_statistics()
                    total_constraints_added += stats.get("constraint_count", 0)
                    successful_modules += 1
            except Exception as e:
                error_msg = f"Failed to build DYNAMIC module '{definition.id}': {e}"
                logger.error(f"❌ {error_msg}\n{traceback.format_exc()}")
                self._build_errors.append(error_msg)

        build_time = time.time() - build_start_time
        self._build_stats = {
            "build_successful": not self._build_errors,
            "total_modules_processed": len(active_definitions),
            "successful_modules": successful_modules,
            "total_constraints_added": total_constraints_added,
            "build_time_seconds": build_time,
            "errors": self._build_errors,
        }
        logger.info("🎉 DYNAMIC CONSTRAINT MODEL BUILD COMPLETE!")
        logger.info(f"   • Total constraints added: {total_constraints_added}")
        logger.info(f"   • Build time: {build_time:.2f}s")
        return self._build_stats

    def _instantiate_and_apply(self, definition, model, shared_variables):
        """Instantiates, initializes, and applies a single constraint definition."""
        if not definition.constraint_class:
            logger.warning(f"Skipping '{definition.id}', no linked class.")
            return None

        instance = definition.constraint_class(
            definition=definition,
            problem=self.problem,
            shared_vars=shared_variables,
            model=model,
        )
        self._constraint_instances[definition.id] = instance
        instance.initialize_variables()
        instance.add_constraints()
        logger.info(
            f"✅ Module '{definition.id}' ({definition.constraint_type.value}): {instance.get_statistics().get('constraint_count', 0)} constraints added."
        )
        return instance

    def get_build_statistics(self) -> Dict[str, Any]:
        """Return comprehensive build statistics."""
        return self._build_stats.copy()

    def get_constraint_instances(self) -> list:
        """Returns the list of instantiated constraint objects."""
        return list(self._constraint_instances.values())
