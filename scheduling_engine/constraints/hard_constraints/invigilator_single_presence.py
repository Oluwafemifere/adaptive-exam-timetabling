"""
CRITICAL FIX - InvigilatorSinglePresenceConstraint
This constraint ensures that an invigilator can only be assigned to ONE room at a time during any given time slot.
An invigilator cannot be in multiple rooms simultaneously.
"""

from collections import defaultdict
from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class InvigilatorSinglePresenceConstraint(CPSATBaseConstraint):
    """
    H12: Ensure invigilators are assigned to at most one room per time slot.

    Constraint Logic:
    - For each invigilator I and time slot T:
      - Sum of all u(I, exam, room, T) variables <= 1
    - This prevents an invigilator from being assigned to multiple rooms simultaneously
    """

    dependencies = ["MinimumInvigilatorsConstraint"]
    constraint_category = "INVIGILATORCONSTRAINTS"
    is_critical = True  # CRITICAL - must be applied
    min_expected_constraints = 0  # May be 0 if no invigilators

    def _create_local_variables(self):
        """No local variables needed"""
        pass

    def _add_constraint_implementation(self):
        """
        Enhanced constraint to prevent invigilator conflicts.

        Core Logic: For each (invigilator, timeslot) pair, ensure that the invigilator
        is assigned to at most one room/exam combination at that time.
        """
        # Get u variables (invigilator assignments)
        uvars = self.u

        if not uvars:
            logger.info(f"{self.constraint_id}: No u variables, skipping")
            return

        logger.info(
            f"{self.constraint_id}: Processing {len(uvars)} invigilator assignment variables"
        )

        # Group u variables by (invigilator_id, slot_id) for conflict detection
        # Key: (invigilator_id, slot_id)
        # Value: List of {'var': uvar, 'examid': examid, 'roomid': roomid}
        invigilator_slot_assignments = defaultdict(list)

        for (invid, examid, roomid, slotid), uvar in uvars.items():
            key = (invid, slotid)
            invigilator_slot_assignments[key].append(
                {"var": uvar, "examid": examid, "roomid": roomid}
            )

        constraints_added = 0

        # Add constraint for each (invigilator, timeslot) pair
        for (invid, slotid), assignments in invigilator_slot_assignments.items():
            if len(assignments) > 1:
                # CRITICAL CONSTRAINT: An invigilator can only be in one place at a time
                # Sum of all u(invid, *, *, slotid) <= 1
                assignment_vars = [a["var"] for a in assignments]
                self.model.Add(sum(assignment_vars) <= 1)
                constraints_added += 1

                # Detailed logging for debugging
                room_exam_pairs = [(a["roomid"], a["examid"]) for a in assignments]
                logger.debug(
                    f"{self.constraint_id}: CONSTRAINT - Invigilator {invid} in slot {slotid}"
                )
                logger.debug(
                    f"  -> Can only be assigned to ONE of {len(assignments)} possible locations:"
                )
                for i, (roomid, examid) in enumerate(room_exam_pairs):
                    logger.debug(f"     {i+1}. Room {roomid} for Exam {examid}")
                logger.debug(
                    f"  -> Added constraint: sum({len(assignment_vars)} vars) <= 1"
                )

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} invigilator single-presence constraints"
        )

        # Summary statistics
        total_invigilators = len(
            set(invid for (invid, slotid) in invigilator_slot_assignments.keys())
        )
        total_slots = len(
            set(slotid for (invid, slotid) in invigilator_slot_assignments.keys())
        )

        logger.info(f"{self.constraint_id}: Summary:")
        logger.info(
            f"  -> {total_invigilators} invigilators across {total_slots} time slots"
        )
        logger.info(f"  -> {constraints_added} potential conflicts prevented")

        # Log sample constraints for verification
        if constraints_added > 0:
            logger.info(f"{self.constraint_id}: Sample constraint details:")
            sample_conflicts = list(invigilator_slot_assignments.items())[:3]
            for i, ((invid, slotid), assignments) in enumerate(sample_conflicts):
                if len(assignments) > 1:
                    logger.info(f"  Sample {i+1}: Invigilator {invid} in slot {slotid}")
                    logger.info(
                        f"    -> Prevented from being in {len(assignments)} places simultaneously"
                    )
                    logger.info(f"    -> Exams: {[a['examid'] for a in assignments]}")
                    logger.info(f"    -> Rooms: {[a['roomid'] for a in assignments]}")
        else:
            logger.info(
                f"{self.constraint_id}: No conflicts detected - all invigilators have unique assignments"
            )

    def validate_constraint_effectiveness(self, solution):
        """
        Validate that the constraint is working correctly by checking the solution.
        This method can be called after solving to verify no conflicts exist.
        """
        if not hasattr(solution, "assignments"):
            logger.warning(
                f"{self.constraint_id}: Cannot validate - no solution assignments"
            )
            return True

        # Build invigilator schedule from solution
        invigilator_schedule = defaultdict(
            list
        )  # invigilator_id -> [(exam, room, slot), ...]

        for examid, assignment in solution.assignments.items():
            if hasattr(assignment, "invigilator_ids") and assignment.invigilator_ids:
                for invid in assignment.invigilator_ids:
                    for roomid in getattr(assignment, "room_ids", []):
                        invigilator_schedule[invid].append(
                            (examid, roomid, assignment.timeslot_id)
                        )

        # Check for conflicts
        conflicts_found = 0
        for invid, schedule in invigilator_schedule.items():
            # Group by timeslot
            slot_assignments = defaultdict(list)
            for exam, room, slot in schedule:
                slot_assignments[slot].append((exam, room))

            # Check each timeslot for multiple assignments
            for slot, assignments in slot_assignments.items():
                if len(assignments) > 1:
                    conflicts_found += 1
                    logger.error(f"{self.constraint_id}: CONSTRAINT VIOLATION!")
                    logger.error(
                        f"  -> Invigilator {invid} assigned to {len(assignments)} locations in slot {slot}"
                    )
                    logger.error(f"  -> Assignments: {assignments}")

        if conflicts_found == 0:
            logger.info(
                f"{self.constraint_id}: ✅ VALIDATION PASSED - No invigilator conflicts in solution"
            )
            return True
        else:
            logger.error(
                f"{self.constraint_id}: ❌ VALIDATION FAILED - {conflicts_found} conflicts found"
            )
            return False
