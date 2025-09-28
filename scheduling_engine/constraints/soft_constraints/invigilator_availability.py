"""
InvigilatorAvailabilityConstraint - S6 Implementation

S6: Invigilator availability violation (new soft constraint)

For each invigilator i and slot s, if i is unavailable at s,
define availabilityViol_{i,s} ∈ {0,1}:
availabilityViol_{i,s} ≥ ∑_{e,r} u_{i,e,r,s}
Penalty: W_availability × ∑_{i,s} availabilityViol_{i,s} where W_availability = 1500.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class InvigilatorAvailabilityConstraint(CPSATBaseConstraint):
    """S6: Invigilator availability violation penalty for unavailable assignments"""

    dependencies = ["InvigilatorSingleAssignmentConstraint"]
    constraint_category = "SOFT_CONSTRAINTS"
    is_critical = False
    min_expected_constraints = 0  # May be 0 if all invigilators are always available

    def __init__(self, constraint_id, problem, shared_vars, model, factory=None):
        super().__init__(constraint_id, problem, shared_vars, model, factory)
        self.penalty_weight = 1500  # W_availability
        logger.info(
            f"🟡 Initializing SOFT constraint {constraint_id} with weight {self.penalty_weight}"
        )

    def _create_local_variables(self):
        """Create auxiliary variables for availability violations"""
        self.availability_viol_vars = {}

        # Check if we have invigilators and availability data
        if not hasattr(self.problem, "invigilators") or not self.problem.invigilators:
            return

        # Get invigilator availability from precomputed data or problem
        availability_data = self.precomputed_data.get("invigilator_availability", {})
        if not availability_data and hasattr(self.problem, "invigilator_availability"):
            availability_data = self.problem.invigilator_availability

        if not availability_data:
            logger.info(f"{self.constraint_id}: No invigilator availability data found")
            return

        # Create availability violation variables for unavailable invigilator-slot pairs
        for invigilator_id in self.problem.invigilators:
            invigilator_availability = availability_data.get(invigilator_id, {})

            for slot_id in self._timeslots:
                # If invigilator is explicitly marked as unavailable for this slot
                is_available = invigilator_availability.get(
                    slot_id, True
                )  # Default to available

                if not is_available:
                    avail_key = (invigilator_id, slot_id)
                    self.availability_viol_vars[avail_key] = self.model.NewBoolVar(
                        f"availabilityViol_{invigilator_id}_{slot_id}"
                    )

    def _add_constraint_implementation(self):
        """Add invigilator availability penalty constraints"""
        constraints_added = 0

        if not hasattr(self.problem, "invigilators") or not self.problem.invigilators:
            logger.info(f"{self.constraint_id}: No invigilators found")
            self.constraint_count = 0
            return

        if not self.u:
            logger.info(
                f"{self.constraint_id}: No invigilator assignment variables found"
            )
            self.constraint_count = 0
            return

        if not self.availability_viol_vars:
            logger.info(f"{self.constraint_id}: No availability violations to track")
            self.constraint_count = 0
            return

        # Get availability data
        availability_data = self.precomputed_data.get("invigilator_availability", {})
        if not availability_data and hasattr(self.problem, "invigilator_availability"):
            availability_data = self.problem.invigilator_availability

        # For each invigilator-slot pair with availability violations
        for (
            invigilator_id,
            slot_id,
        ), avail_viol_var in self.availability_viol_vars.items():

            # Find all u variables for this invigilator-slot combination
            u_terms = []
            for exam_id in self._exams:
                for room_id in self._rooms:
                    u_key = (invigilator_id, exam_id, room_id, slot_id)
                    if u_key in self.u:
                        u_terms.append(self.u[u_key])

            if u_terms:
                # availabilityViol_{i,s} ≥ ∑_{e,r} u_{i,e,r,s}
                # Since u variables are binary and avail_viol_var is binary,
                # this becomes: avail_viol_var >= any assignment to this invigilator at this slot
                self.model.Add(avail_viol_var >= sum(u_terms))
                constraints_added += 1
            else:
                # No u variables for this combination, so no violation possible
                self.model.Add(avail_viol_var == 0)
                constraints_added += 1

        # Store penalty terms for objective function
        self.penalty_terms = []
        for avail_key, avail_viol_var in self.availability_viol_vars.items():
            self.penalty_terms.append((self.penalty_weight, avail_viol_var))

        self.constraint_count = constraints_added

        if constraints_added == 0:
            logger.info(
                f"{self.constraint_id}: No availability penalty constraints needed"
            )
        else:
            logger.info(
                f"{self.constraint_id}: Added {constraints_added} invigilator availability penalty constraints"
            )

    def get_penalty_terms(self):
        """Get penalty terms for the objective function"""
        return getattr(self, "penalty_terms", [])

    def get_statistics(self):
        """Get constraint statistics"""
        stats = super().get_constraint_statistics()
        stats.update(
            {
                "penalty_weight": self.penalty_weight,
                "unavailable_invigilator_slots": len(self.availability_viol_vars),
                "penalty_terms": len(getattr(self, "penalty_terms", [])),
            }
        )
        return stats
