# scheduling_engine/constraints/constraint_manager.py

"""
MODIFIED Constraint Manager for a dynamic, configurable system.
This manager builds the model by instantiating constraint classes based on the
active, ordered list of ConstraintDefinition objects provided by the registry.
This version ensures that foundational constraints are always enforced.
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
    StartUniquenessConstraint,
    StartFeasibilityConstraint,
    RoomContinuityConstraint,
    OccupancyDefinitionConstraint,
    RoomAssignmentConsistencyConstraint,
    InvigilatorSinglePresenceConstraint,
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

    # def _apply_manual_locks(self, model, shared_variables: SharedVariables):
    #     """
    #     Enforces HITL locks as immutable hard constraints.
    #     This is a critical step for HITL integration, applied after foundational constraints.
    #     """
    #     if not self.problem.locks:
    #         logger.info("No manual locks to apply.")
    #         return

    #     logger.info(f"Applying {len(self.problem.locks)} manual locks...")
    #     locks_applied = 0
    #     x_vars = shared_variables.x_vars
    #     y_vars = shared_variables.y_vars

    #     for lock in self.problem.locks:
    #         try:
    #             exam_id = self.problem._ensure_uuid(lock["exam_id"])
    #             slot_id = self.problem._ensure_uuid(lock.get("time_slot_id"))
    #             room_ids_data = lock.get("room_ids") or []
    #             room_ids = [self.problem._ensure_uuid(rid) for rid in room_ids_data]

    #             if exam_id not in self.problem.exams:
    #                 logger.warning(f"Skipping lock for unknown exam ID: {exam_id}")
    #                 continue

    #             # Lock to a specific time slot
    #             if slot_id:
    #                 if not self.problem.is_start_feasible(exam_id, slot_id):
    #                     logger.error(
    #                         f"CRITICAL: Cannot apply lock for exam {exam_id} in slot {slot_id}. "
    #                         "The exam's duration exceeds the available time in the day. "
    #                         "This lock makes the problem infeasible. Skipping this lock."
    #                     )
    #                     continue

    #                 x_key = (exam_id, slot_id)
    #                 if x_key in x_vars:
    #                     model.Add(x_vars[x_key] == 1)
    #                     locks_applied += 1

    #                 if room_ids:
    #                     for room_id in room_ids:
    #                         y_key = (exam_id, room_id, slot_id)
    #                         if y_key in y_vars:
    #                             model.Add(y_vars[y_key] == 1)

    #         except Exception as e:
    #             logger.error(f"Failed to apply lock {lock}: {e}")

    #     logger.info(f"Successfully applied {locks_applied} lock constraints.")

    def build_model(self, model, shared_variables: SharedVariables) -> Dict[str, Any]:
        """Builds the complete constraint model from active, configured definitions."""
        logger.info("🏗️  Starting DYNAMIC constraint model build...")
        build_start_time = time.time()
        processed_constraint_ids: Set[str] = set()
        total_constraints_added = 0
        successful_modules = 0

        foundational_constraints = {
            StartUniquenessConstraint: "Ensures each exam starts exactly once.",
            StartFeasibilityConstraint: "Ensures exams only start in feasible slots.",
            RoomContinuityConstraint: "Ensures multi-slot exams remain in the same room.",
            OccupancyDefinitionConstraint: "Defines exam occupancy based on start times.",
            RoomAssignmentConsistencyConstraint: "Links room assignments to occupancy.",
            InvigilatorSinglePresenceConstraint: "Prevents invigilators being in two places at once.",
        }

        logger.info("Building foundational constraints that are always enforced...")
        for cls, desc in foundational_constraints.items():
            constraint_id = cls.__name__
            try:
                definition = ConstraintDefinition(
                    id=constraint_id,
                    name=constraint_id.replace("Constraint", ""),
                    description=desc,
                    constraint_type=ConstraintType.HARD,
                    category=ConstraintCategory.CORE,
                    enabled=True,
                    constraint_class=cls,
                )

                instance = cls(
                    definition=definition,
                    problem=self.problem,
                    shared_vars=shared_variables,
                    model=model,
                )
                self._constraint_instances[definition.id] = instance

                instance.initialize_variables()
                instance.add_constraints()

                stats = instance.get_statistics()
                constraints_added = stats.get("constraint_count", 0)
                total_constraints_added += constraints_added
                successful_modules += 1
                logger.info(
                    f"✅ Foundational Module '{definition.id}': {constraints_added} constraints added."
                )
                processed_constraint_ids.add(constraint_id)

            except Exception as e:
                error_msg = (
                    f"Failed to build foundational module '{constraint_id}': {e}"
                )
                logger.error(f"❌ {error_msg}\n{traceback.format_exc()}")
                self._build_errors.append(error_msg)

        # logger.info("Applying manual HITL locks...")
        # try:
        #     self._apply_manual_locks(model, shared_variables)
        # except Exception as e:
        #     error_msg = f"Failed to apply manual locks: {e}"
        #     logger.error(f"❌ {error_msg}\n{traceback.format_exc()}")
        #     self._build_errors.append(error_msg)

        active_definitions = self.registry.get_active_constraint_classes()

        if not active_definitions:
            logger.warning("No active (dynamic) constraint definitions found to build.")
        else:
            logger.info(
                f"Building model with {len(active_definitions)} active dynamic constraints."
            )
            logger.info(f"Dynamic build order: {[d.id for d in active_definitions]}")

        for definition in active_definitions:
            try:
                if definition.id in processed_constraint_ids:
                    logger.info(
                        f"Skipping '{definition.id}' as it was already enforced."
                    )
                    continue

                if not definition.constraint_class:
                    logger.warning(
                        f"Skipping constraint '{definition.id}' as it has no linked class."
                    )
                    continue

                instance = definition.constraint_class(
                    definition=definition,
                    problem=self.problem,
                    shared_vars=shared_variables,
                    model=model,
                )
                self._constraint_instances[definition.id] = instance
                instance.initialize_variables()
                instance.add_constraints()

                stats = instance.get_statistics()
                constraints_added = stats.get("constraint_count", 0)
                total_constraints_added += constraints_added
                successful_modules += 1
                logger.info(
                    f"✅ Module '{definition.id}': {constraints_added} constraints added."
                )

            except Exception as e:
                error_msg = f"Failed to build module '{definition.id}': {e}"
                logger.error(f"❌ {error_msg}\n{traceback.format_exc()}")
                self._build_errors.append(error_msg)

        build_time = time.time() - build_start_time
        self._build_stats = {
            "build_successful": not self._build_errors,
            "total_modules_processed": len(foundational_constraints)
            + len(active_definitions),
            "successful_modules": successful_modules,
            "total_constraints_added": total_constraints_added,
            "build_time_seconds": build_time,
            "errors": self._build_errors,
        }

        logger.info("🎉 DYNAMIC CONSTRAINT MODEL BUILD COMPLETE!")
        logger.info(f"   • Total constraints added: {total_constraints_added}")
        logger.info(f"   • Build time: {build_time:.2f}s")

        return self._build_stats

    def get_build_statistics(self) -> Dict[str, Any]:
        """Return comprehensive build statistics."""
        return self._build_stats.copy()

    def get_constraint_instances(self) -> list:
        """Returns the list of instantiated constraint objects."""
        return list(self._constraint_instances.values())
