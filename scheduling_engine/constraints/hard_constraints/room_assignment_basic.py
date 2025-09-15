# scheduling_engine/constraints/hard_constraints/room_assignment_basic.py

"""
FIXED C3: Room Assignment Basic Constraint - Mathematically Accurate Implementation

∀e ∈ E, d ∈ D, t ∈ T: ∑{y[e,r,d,t] : r ∈ allowedRooms_e} = z[e,d,t]

NOTE: allowedRooms_e filtering is handled by C6 DOMAIN RESTRICTION in variable creation.
This constraint only needs to enforce the sum equals occupancy.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class RoomAssignmentBasicConstraint(CPSATBaseConstraint):
    """
    CORE_MODULE - C3: Room Assignment Basic

    Mathematical formulation: ∀e ∈ E, d ∈ D, t ∈ T: ∑{y[e,r,d,t] : r ∈ allowedRooms_e} = z[e,d,t]

    Note: C6 (allowedRooms_e) is handled by domain restriction during y-variable creation.
    """

    dependencies = ["OccupancyDefinitionConstraint"]
    constraint_category = "CORE"

    def _create_local_variables(self):
        """No local variables needed."""
        logger.debug(
            f"{self.constraint_id}: C6 domain restriction handled in variable creation"
        )

    def _add_constraint_implementation(self):
        """Add room assignment sum constraints, skipping inactive slots."""
        if not self.y or not self.z:
            raise RuntimeError(f"{self.constraint_id}: Missing y or z variables")

        for exam in self.problem.exams.values():
            exam_id = exam.id

            for day in self.problem.days:
                for slot_id in self.problem.time_slots:
                    # Guard: skip inactive time slots
                    ts = self.problem.time_slots.get(slot_id)
                    if ts is not None and hasattr(ts, "is_active") and not ts.is_active:
                        continue

                    z_key = (exam_id, day, slot_id)
                    if z_key not in self.z:
                        continue

                    z_var = self.z[z_key]

                    # Collect y variables for this exam-day-slot (C6 domain restriction applies)
                    y_vars = []
                    for room_id in self.problem.rooms:
                        y_key = (exam_id, room_id, day, slot_id)
                        if y_key in self.y:
                            y_vars.append(self.y[y_key])

                    if y_vars:
                        # ∑{y[e,r,d,t] : r ∈ allowedRooms_e} = z[e,d,t]
                        self.model.Add(sum(y_vars) == z_var)
                        self._increment_constraint_count()

                        logger.debug(
                            f"{self.constraint_id}: Added room assignment for "
                            f"{exam_id},{day},{slot_id} with {len(y_vars)} rooms"
                        )
                    else:
                        logger.warning(
                            f"{self.constraint_id}: No allowed rooms for "
                            f"exam {exam_id},{day},{slot_id}"
                        )
