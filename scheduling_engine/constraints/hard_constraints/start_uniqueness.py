# scheduling_engine\constraints\hard_constraints\start_uniqueness.py - Day data class version

"""
FIXED StartUniquenessConstraint - Foundation Core Constraint with Day data class

CRITICAL FIXES:
- Updated to use Day data class and problem.timeslots property
- Removed string conversion that broke UUID key lookups
- Use UUID objects directly as keys (UUID-based system)
- Fixed constraint count attribute (self.constraint_count not self._constraint_count)
- Added proper debugging for UUID key system
- Maintained comprehensive error reporting

OPTIMIZATIONS:
- Precompute exam and slot IDs once outside loops
- Use local references to avoid repeated attribute lookups
- Build exam-to-variables mapping in a single pass
- Replace list appends with list comprehensions where possible
- Reduce debug logging overhead in tight loops
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class StartUniquenessConstraint(CPSATBaseConstraint):
    """H1: Each exam starts exactly once - ∑ x[e,s] = 1 ∀ e ∈ E"""

    dependencies = []  # Foundation constraint - no dependencies
    constraint_category = "CORE"
    is_critical = True
    min_expected_constraints = 1

    def _create_local_variables(self):
        """No local variables needed for this constraint"""
        pass

    def _add_constraint_implementation(self):
        """Add start uniqueness constraints: each exam starts exactly once"""
        # Use local references for frequent access
        problem = self.problem
        x_variables = self.x
        model = self.model

        # Precompute exam and slot lists
        exam_ids = list(problem.exams.keys())
        slot_ids = list(problem.timeslots.keys())

        logger.debug(
            f"{self.constraint_id}: Processing {len(exam_ids)} exams across {len(slot_ids)} time slots"
        )

        # Precompute all exam variables using a single pass
        exam_vars = defaultdict(list)
        for slot_id in slot_ids:
            for exam_id in exam_ids:
                x_key = (exam_id, slot_id)
                if x_key in x_variables:
                    exam_vars[exam_id].append(x_variables[x_key])

        constraints_added = 0
        # Add constraints for each exam with variables
        for exam_id, vars_list in exam_vars.items():
            model.AddExactlyOne(vars_list)
            constraints_added += 1

        # Handle exams without variables
        missing_vars = set(exam_ids) - set(exam_vars.keys())
        if missing_vars:
            logger.warning(f"No start variables for exams: {missing_vars}")

        self.constraint_count = constraints_added

        logger.info(
            f"{self.constraint_id}: Added {constraints_added} start uniqueness constraints"
        )

        # Critical validation for foundation constraint
        if constraints_added == 0:
            logger.error(
                f"CRITICAL: {self.constraint_id} (foundation) generated 0 constraints!"
            )
            logger.error(f"Available x variables: {len(x_variables)}")
            logger.error(f"This will cause model infeasibility!")

            # Detailed debugging
            if hasattr(problem, "exams") and hasattr(problem, "timeslots"):
                logger.error(
                    f"Problem has {len(problem.exams)} exams and {len(problem.timeslots)} time slots"
                )

            # Check x variable patterns
            x_sample = list(x_variables.keys())[:10] if x_variables else []
            logger.error(f"Sample x variables: {x_sample}")

            if not x_variables:
                logger.error("ROOT CAUSE: No x (start) variables created at all!")
                logger.error(
                    "This indicates a problem in the ConstraintEncoder variable creation"
                )
            else:
                # Check if exam IDs match (without string conversion)
                x_exam_ids = {key[0] for key in x_variables.keys()}
                problem_exam_ids = set(exam_ids)

                logger.error(f"X variable exam IDs (sample): {list(x_exam_ids)[:5]}")
                logger.error(f"Problem exam IDs (sample): {list(problem_exam_ids)[:5]}")

                # Check types
                if x_exam_ids:
                    x_exam_type = type(next(iter(x_exam_ids)))
                    problem_exam_type = type(next(iter(problem_exam_ids)))
                    logger.error(f"X variable exam ID type: {x_exam_type}")
                    logger.error(f"Problem exam ID type: {problem_exam_type}")

                if x_exam_ids != problem_exam_ids:
                    logger.error(
                        "ROOT CAUSE: Exam ID mismatch between variables and problem!"
                    )
                    logger.error("This could be due to UUID vs string type mismatch")

            raise RuntimeError(
                f"{self.constraint_id}: Foundation constraint failed - no start variables available"
            )
