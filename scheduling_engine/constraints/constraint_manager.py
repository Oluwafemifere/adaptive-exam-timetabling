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
    UnifiedStudentConflictConstraint,
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

    async def build_phase1_model(
        self, model, shared_variables: SharedVariables
    ) -> Dict[str, Any]:
        """Builds the Phase 1 (Timetabling) model with time-based constraints."""
        logger.info("🏗️  Building Phase 1 (Timetabling) model constraints...")
        # Define which constraints are essential and time-related for Phase 1
        core_constraints = {
            StartUniquenessConstraint,
            StartFeasibilityConstraint,
            OccupancyDefinitionConstraint,
            AggregateCapacityConstraint,
            UnifiedStudentConflictConstraint,  # Critical for timetabling
        }
        logger.info(
            f"Phase 1 will use these CORE constraints: {[c.__name__ for c in core_constraints]}"
        )
        return await self._build_model(model, shared_variables, core_constraints)

    async def build_phase2_model(
        self, model, shared_variables: SharedVariables
    ) -> Dict[str, Any]:
        """Builds the full Phase 2 (Packing) model."""
        logger.info("🏗️  Building Full Phase 2 (Packing) model constraints...")
        # Define which constraints are essential for packing and resource assignment
        core_constraints = {
            RoomAssignmentConsistencyConstraint,
            RoomCapacityHardConstraint,
            RoomContinuityConstraint,
            InvigilatorRequirementConstraint,
            InvigilatorSinglePresenceConstraint,
            InvigilatorContinuityConstraint,
        }
        logger.info(
            f"Phase 2 will use these CORE constraints: {[c.__name__ for c in core_constraints]}"
        )
        return await self._build_model(model, shared_variables, core_constraints)

    async def _build_model(
        self,
        model,
        shared_variables: SharedVariables,
        core_classes: Set[type],
    ) -> Dict[str, Any]:
        """Generic model builder that separates core from dynamic constraints for a given phase."""
        build_start_time = time.time()
        self._build_errors = []
        self._constraint_instances = {}
        total_constraints_added = 0
        successful_modules = 0

        # --- 1. APPLY CORE, NON-CONFIGURABLE CONSTRAINTS for this phase ---
        logger.info(f"Applying {len(core_classes)} CORE constraints for this phase...")
        for cls in core_classes:
            try:
                # Core constraints are not configurable; create a default definition.
                definition = ConstraintDefinition(
                    id=cls.__name__,
                    name=cls.__name__,
                    description="Core foundational constraint.",
                    constraint_type=ConstraintType.HARD,
                    category=ConstraintCategory.CORE,
                    enabled=True,
                    constraint_class=cls,
                )

                instance = await self._instantiate_and_apply(
                    definition, model, shared_variables
                )
                if instance:
                    stats = instance.get_statistics()
                    total_constraints_added += stats.get("constraint_count", 0)
                    successful_modules += 1
            except Exception as e:
                error_msg = f"Failed to build CORE module '{cls.__name__}': {e}"
                logger.error(f"❌ {error_msg}\n{traceback.format_exc()}")
                self._build_errors.append(error_msg)

        # --- 2. APPLY ALL DYNAMIC, CONFIGURABLE CONSTRAINTS ---
        # Constraints will self-disable if their required variables (x, y, w) are not present for the current phase.
        active_definitions = self.registry.get_active_constraint_classes()
        dynamic_definitions = [
            d for d in active_definitions if d.constraint_class not in core_classes
        ]
        logger.info(
            f"Applying {len(dynamic_definitions)} DYNAMIC (configurable) constraints..."
        )
        for definition in dynamic_definitions:
            try:
                instance = await self._instantiate_and_apply(
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
            "total_modules_processed": len(core_classes) + len(dynamic_definitions),
            "successful_modules": successful_modules,
            "total_constraints_added": total_constraints_added,
            "build_time_seconds": build_time,
            "errors": self._build_errors,
        }
        logger.info("🎉 DYNAMIC CONSTRAINT MODEL BUILD COMPLETE FOR PHASE!")
        logger.info(f"   • Total constraints added: {total_constraints_added}")
        logger.info(
            f"   • Successful modules: {successful_modules}/{self._build_stats['total_modules_processed']}"
        )
        if self._build_errors:
            logger.error(f"   • Errors encountered: {len(self._build_errors)}")
            for err in self._build_errors:
                logger.error(f"     - {err}")
        logger.info(f"   • Build time: {build_time:.2f}s")
        return self._build_stats

    async def _instantiate_and_apply(self, definition, model, shared_variables):
        """Instantiates, initializes, and applies a single constraint definition."""
        if not definition.constraint_class:
            logger.warning(
                f"Skipping '{definition.id}', no linked implementation class found."
            )
            return None

        logger.info(
            f"-> Applying module '{definition.id}' ({definition.constraint_type.value.upper()})..."
        )
        instance = definition.constraint_class(
            definition=definition,
            problem=self.problem,
            shared_vars=shared_variables,
            model=model,
        )
        self._constraint_instances[definition.id] = instance
        instance.initialize_variables()
        # --- START OF FIX ---
        # Await the add_constraints method if it's a coroutine
        import inspect

        if inspect.iscoroutinefunction(instance.add_constraints):
            await instance.add_constraints()
        else:
            instance.add_constraints()
        # --- END OF FIX ---
        stats = instance.get_statistics()
        count = stats.get("constraint_count", 0)
        if count > 0:
            logger.info(f"   ✅ Module '{definition.id}' added {count} constraints.")
        else:
            logger.info(
                f"   - Module '{definition.id}' added 0 constraints (this may be expected if not applicable)."
            )
        return instance

    def get_build_statistics(self) -> Dict[str, Any]:
        """Return comprehensive build statistics."""
        return self._build_stats.copy()

    def get_constraint_instances(self) -> list:
        """Returns the list of instantiated constraint objects."""
        return list(self._constraint_instances.values())
