# scheduling_engine/cp_sat/model_builder.py

"""
CP-SAT Model Builder for exam scheduling.
Creates constraint programming models from problem instances.
Based on the research paper's CP formulation (constraints 2-5).
"""

from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from ortools.sat.python import cp_model

from ..config import get_logger, CPSATConfig
from ..core.problem_model import ExamSchedulingProblem, Exam, Room
from ..core.solution import TimetableSolution

logger = get_logger("cp_sat.model_builder")


class CPSATModelBuilder:
    """
    Builds CP-SAT constraint models from exam scheduling problems.
    Implements the RCJS formulation from the research paper.
    """

    def __init__(self, config: Optional[CPSATConfig] = None):
        self.config = config or CPSATConfig()
        self.model: Optional[cp_model.CpModel] = None
        self.variables: Dict[str, cp_model.IntVar] = {}

        # Problem instance
        self.problem: Optional[ExamSchedulingProblem] = None

        # Variable mappings
        self.exam_start_vars: Dict[UUID, cp_model.IntVar] = {}
        self.exam_end_vars: Dict[UUID, cp_model.IntVar] = {}
        self.exam_room_vars: Dict[Tuple[UUID, UUID], cp_model.IntVar] = (
            {}
        )  # (exam_id, room_id)
        self.exam_timeslot_vars: Dict[Tuple[UUID, UUID], cp_model.IntVar] = (
            {}
        )  # (exam_id, timeslot_id)

        logger.debug("CPSATModelBuilder initialized")

    def build_model(
        self,
        problem: ExamSchedulingProblem,
        hint_solution: Optional[TimetableSolution] = None,
    ) -> cp_model.CpModel:
        """
        Build complete CP-SAT model from problem instance.

        Args:
            problem: The exam scheduling problem instance
            hint_solution: Optional hint solution to guide search

        Returns:
            Configured CP-SAT model ready for solving
        """
        logger.info(f"Building CP-SAT model for {len(problem.exams)} exams")

        self.problem = problem
        self.model = cp_model.CpModel()
        self.variables.clear()
        self.exam_start_vars.clear()
        self.exam_end_vars.clear()
        self.exam_room_vars.clear()
        self.exam_timeslot_vars.clear()

        # Build model components
        self._create_decision_variables()
        self._add_basic_constraints()
        self._add_resource_constraints()
        self._add_precedence_constraints()
        self._add_objective_function()

        # Add solution hint if provided
        if hint_solution and self.config.use_hint_from_previous:
            self._add_solution_hint(hint_solution)

        logger.info(f"CP-SAT model built with {len(self.variables)} variables")
        return self.model

    def _create_decision_variables(self) -> None:
        """
        Create decision variables for the CP-SAT model.
        Based on research paper formulation: start times sj and end times ej.
        """
        assert self.model is not None
        assert self.problem is not None

        logger.debug("Creating decision variables")

        # Calculate time horizon
        max_time = self._calculate_time_horizon()

        # Create start and end time variables for each exam
        for exam_id, exam in self.problem.exams.items():
            # Start time variable (sj in research paper)
            start_var = self.model.NewIntVar(
                0, max_time - exam.duration_minutes, f"start_exam_{exam.course_code}"
            )
            self.exam_start_vars[exam_id] = start_var
            self.variables[f"start_{exam_id}"] = start_var

            # End time variable (ej in research paper)
            end_var = self.model.NewIntVar(
                exam.duration_minutes, max_time, f"end_exam_{exam.course_code}"
            )
            self.exam_end_vars[exam_id] = end_var
            self.variables[f"end_{exam_id}"] = end_var

        # Create room assignment variables
        for exam_id, exam in self.problem.exams.items():
            for room_id, room in self.problem.rooms.items():
                # Check if room is compatible with exam
                if self._is_room_compatible(exam, room):
                    var = self.model.NewBoolVar(
                        f"exam_{exam.course_code}_room_{room.code}"
                    )
                    self.exam_room_vars[(exam_id, room_id)] = var
                    self.variables[f"exam_{exam_id}_room_{room_id}"] = var

        # Create time slot assignment variables
        for exam_id, exam in self.problem.exams.items():
            for timeslot_id, timeslot in self.problem.time_slots.items():
                var = self.model.NewBoolVar(
                    f"exam_{exam.course_code}_slot_{timeslot.name}"
                )
                self.exam_timeslot_vars[(exam_id, timeslot_id)] = var
                self.variables[f"exam_{exam_id}_slot_{timeslot_id}"] = var

        logger.debug(f"Created {len(self.variables)} decision variables")

    def _calculate_time_horizon(self) -> int:
        """Calculate time horizon for the scheduling problem"""
        assert self.problem is not None

        if not self.problem.time_slots:
            return 24 * 60  # Default 24 hours in minutes

        # Calculate based on exam period duration
        if self.problem.exam_period_start and self.problem.exam_period_end:
            period_days = (
                self.problem.exam_period_end - self.problem.exam_period_start
            ).days + 1
            return period_days * 24 * 60  # Total minutes in exam period
        else:
            # Default to 7 days if dates not available
            return 7 * 24 * 60

    def _is_room_compatible(self, exam: Exam, room: Room) -> bool:
        """Check if a room is compatible with an exam"""
        # Check basic capacity
        if room.get_effective_capacity(exam.exam_type) < exam.expected_students:
            return False

        # Check room features for practical exams
        if exam.is_practical and not room.has_computers:
            return False

        # Check if room is active
        if not room.is_active:
            return False

        return True

    def _add_basic_constraints(self) -> None:
        """
        Add basic scheduling constraints.
        Implements constraints 2-4 from research paper.
        """
        assert self.model is not None
        assert self.problem is not None

        logger.debug("Adding basic constraints")

        # Constraint 2: Job starts after release time (∀j ∈J : sj ≥ rj)
        for exam_id, exam in self.problem.exams.items():
            if exam.release_time:
                # Convert release time to minutes from start of exam period
                release_minutes = self._datetime_to_minutes(exam.release_time)
                self.model.Add(self.exam_start_vars[exam_id] >= release_minutes)

        # Constraint 3: End time = start time + processing time (∀j ∈J : ej = sj + pj)
        for exam_id, exam in self.problem.exams.items():
            self.model.Add(
                self.exam_end_vars[exam_id]
                == self.exam_start_vars[exam_id] + exam.duration_minutes
            )

        # Each exam must be assigned to exactly one time slot
        for exam_id in self.problem.exams.keys():
            timeslot_assignments = [
                self.exam_timeslot_vars[(exam_id, ts_id)]
                for ts_id in self.problem.time_slots.keys()
                if (exam_id, ts_id) in self.exam_timeslot_vars
            ]
            if timeslot_assignments:
                self.model.Add(sum(timeslot_assignments) == 1)

        # Each exam must be assigned to at least one room
        for exam_id, _ in self.problem.exams.items():
            room_assignments = [
                self.exam_room_vars[(exam_id, room_id)]
                for room_id in self.problem.rooms.keys()
                if (exam_id, room_id) in self.exam_room_vars
            ]
            if room_assignments:
                self.model.Add(sum(room_assignments) >= 1)

        # Link time slot assignment to start time
        for exam_id in self.problem.exams.keys():
            for timeslot_id, timeslot in self.problem.time_slots.items():
                if (exam_id, timeslot_id) in self.exam_timeslot_vars:
                    timeslot_start_minutes = self._time_to_minutes(timeslot.start_time)

                    # If exam is assigned to this time slot, start time must match
                    self.model.Add(
                        self.exam_start_vars[exam_id] == timeslot_start_minutes
                    ).OnlyEnforceIf(self.exam_timeslot_vars[(exam_id, timeslot_id)])

        logger.debug("Basic constraints added")

    def _add_resource_constraints(self) -> None:
        """
        Add resource constraints (rooms, capacity).
        Implements disjunctive constraints (constraint 4 from research paper).
        """
        assert self.model is not None
        assert self.problem is not None

        logger.debug("Adding resource constraints")

        # No room double-booking: ∀i,j ∈J : mi = mj ⇒ si > ej ∨ sj > ei
        for room_id in self.problem.rooms.keys():
            exams_using_room = [
                exam_id
                for exam_id in self.problem.exams.keys()
                if (exam_id, room_id) in self.exam_room_vars
            ]

            # Add disjunctive constraints for exams potentially using same room
            for i, exam1_id in enumerate(exams_using_room):
                for exam2_id in exams_using_room[i + 1 :]:
                    # Create disjunctive constraint: if both use room, they can't overlap
                    both_use_room = self.model.NewBoolVar(
                        f"both_use_room_{room_id}_{i}"
                    )

                    # both_use_room iff both exams use this room
                    self.model.Add(
                        both_use_room
                        == (
                            self.exam_room_vars[(exam1_id, room_id)]
                            + self.exam_room_vars[(exam2_id, room_id)]
                            - 1
                        )
                    )

                    # If both use room, one must end before other starts
                    exam1_ends_first = self.model.NewBoolVar(f"exam1_ends_first_{i}")

                    self.model.Add(
                        self.exam_end_vars[exam1_id] <= self.exam_start_vars[exam2_id]
                    ).OnlyEnforceIf([both_use_room, exam1_ends_first])

                    self.model.Add(
                        self.exam_end_vars[exam2_id] <= self.exam_start_vars[exam1_id]
                    ).OnlyEnforceIf([both_use_room, exam1_ends_first.Not()])

        # Room capacity constraints
        self._add_room_capacity_constraints()

        logger.debug("Resource constraints added")

    def _add_room_capacity_constraints(self) -> None:
        """Add room capacity constraints"""
        assert self.model is not None
        assert self.problem is not None

        for room_id, room in self.problem.rooms.items():
            # For each time slot, total students assigned to room cannot exceed capacity
            for timeslot_id in self.problem.time_slots.keys():
                students_in_room = []

                for exam_id, exam in self.problem.exams.items():
                    if (exam_id, room_id) in self.exam_room_vars and (
                        exam_id,
                        timeslot_id,
                    ) in self.exam_timeslot_vars:

                        # Indicator: exam is in this room and time slot
                        exam_here = self.model.NewBoolVar(
                            f"exam_{exam_id}_here_{room_id}_{timeslot_id}"
                        )

                        # exam_here iff exam uses both this room and time slot
                        self.model.AddBoolAnd(
                            [
                                self.exam_room_vars[(exam_id, room_id)],
                                self.exam_timeslot_vars[(exam_id, timeslot_id)],
                            ]
                        ).OnlyEnforceIf(exam_here)

                        self.model.AddBoolOr(
                            [
                                self.exam_room_vars[(exam_id, room_id)].Not(),
                                self.exam_timeslot_vars[(exam_id, timeslot_id)].Not(),
                            ]
                        ).OnlyEnforceIf(exam_here.Not())

                        # Add student count for this exam if it's scheduled here
                        students_in_room.append(exam.expected_students * exam_here)

                # Total students cannot exceed room capacity
                if students_in_room:
                    self.model.Add(
                        sum(students_in_room) <= room.get_effective_capacity()
                    )

    def _add_precedence_constraints(self) -> None:
        """
        Add precedence constraints.
        Implements constraint 5 from research paper: ∀(i,j) ∈P : sj > ei
        """
        assert self.model is not None
        assert self.problem is not None

        logger.debug("Adding precedence constraints")

        for exam_id, exam in self.problem.exams.items():
            for prereq_exam_id in exam.prerequisite_exams:
                if prereq_exam_id in self.exam_end_vars:
                    # Prerequisite exam must end before this exam starts
                    self.model.Add(
                        self.exam_start_vars[exam_id]
                        > self.exam_end_vars[prereq_exam_id]
                    )

        logger.debug("Precedence constraints added")

    def _add_objective_function(self) -> None:
        """
        Add objective function for optimization.
        Based on Total Weighted Tardiness from research paper.
        """
        assert self.model is not None
        assert self.problem is not None

        logger.debug("Adding objective function")

        tardiness_terms = []

        for exam_id, exam in self.problem.exams.items():
            if exam.due_date:
                # Calculate due time in minutes
                due_minutes = self._datetime_to_minutes(exam.due_date)

                # Tardiness = max(0, completion_time - due_time)
                tardiness_var = self.model.NewIntVar(
                    0, 10000, f"tardiness_{exam.course_code}"
                )
                self.model.Add(
                    tardiness_var >= self.exam_end_vars[exam_id] - due_minutes
                )
                self.model.Add(tardiness_var >= 0)

                # Weighted tardiness
                weighted_tardiness = tardiness_var * int(
                    exam.weight * 100
                )  # Scale for integer
                tardiness_terms.append(weighted_tardiness)

        # Minimize total weighted tardiness
        if tardiness_terms:
            self.model.Minimize(sum(tardiness_terms))
        else:
            # Default objective: minimize total completion time
            completion_terms = list(self.exam_end_vars.values())
            self.model.Minimize(sum(completion_terms))

        logger.debug("Objective function added")

    def _add_solution_hint(self, hint_solution: TimetableSolution) -> None:
        """Add solution hint to guide CP-SAT search"""
        assert self.model is not None
        assert self.problem is not None

        logger.debug("Adding solution hint")

        for exam_id, assignment in hint_solution.assignments.items():
            if not assignment.is_complete():
                continue

            # Hint start time - Add None check here
            if (
                exam_id in self.exam_start_vars
                and assignment.assigned_date
                and assignment.time_slot_id is not None
            ):
                timeslot = self.problem.time_slots.get(assignment.time_slot_id)
                if timeslot:
                    start_minutes = self._time_to_minutes(timeslot.start_time)
                    self.model.AddHint(self.exam_start_vars[exam_id], start_minutes)

            # Hint room assignments
            for room_id in assignment.room_ids:
                if (exam_id, room_id) in self.exam_room_vars:
                    self.model.AddHint(self.exam_room_vars[(exam_id, room_id)], 1)

            # Hint time slot assignment - Add None check here
            if assignment.time_slot_id is not None:
                if (exam_id, assignment.time_slot_id) in self.exam_timeslot_vars:
                    self.model.AddHint(
                        self.exam_timeslot_vars[(exam_id, assignment.time_slot_id)], 1
                    )

    def _datetime_to_minutes(self, dt: Any) -> int:
        """Convert datetime to minutes from start of exam period"""
        assert self.problem is not None

        if hasattr(dt, "date"):
            days_from_start = 0
            if self.problem.exam_period_start:
                days_from_start = (dt.date() - self.problem.exam_period_start).days
        else:
            days_from_start = 0

        if hasattr(dt, "time"):
            minutes_in_day = dt.time().hour * 60 + dt.time().minute
        else:
            minutes_in_day = 0

        return days_from_start * 24 * 60 + minutes_in_day

    def _time_to_minutes(self, t: Any) -> int:
        """Convert time to minutes from midnight"""
        if hasattr(t, "hour") and hasattr(t, "minute"):
            return t.hour * 60 + t.minute
        return 0

    def get_model_statistics(self) -> Dict[str, Any]:
        """Get statistics about the built model"""
        if not self.model or not self.problem:
            return {}

        return {
            "total_variables": len(self.variables),
            "start_time_variables": len(self.exam_start_vars),
            "end_time_variables": len(self.exam_end_vars),
            "room_assignment_variables": len(self.exam_room_vars),
            "timeslot_assignment_variables": len(self.exam_timeslot_vars),
            "constraints": "Not available in OR-Tools",  # OR-Tools doesn't expose constraint count
            "exams": len(self.problem.exams),
            "rooms": len(self.problem.rooms),
            "time_slots": len(self.problem.time_slots),
        }

    def validate_model(self) -> Dict[str, List[str]]:
        """Validate the built model for consistency"""
        errors: List[str] = []
        warnings: List[str] = []

        if not self.model:
            errors.append("No model has been built")
            return {"errors": errors, "warnings": warnings}

        # Check variable creation
        if not self.exam_start_vars:
            errors.append("No start time variables created")

        if not self.exam_end_vars:
            errors.append("No end time variables created")

        if not self.exam_room_vars:
            warnings.append("No room assignment variables created")

        if not self.exam_timeslot_vars:
            warnings.append("No time slot assignment variables created")

        # Check problem data consistency
        if self.problem:
            unschedulable_exams = []
            for exam_id, exam in self.problem.exams.items():
                compatible_rooms = [
                    room_id
                    for room_id, room in self.problem.rooms.items()
                    if self._is_room_compatible(exam, room)
                ]
                if not compatible_rooms:
                    unschedulable_exams.append(exam.course_code)

            if unschedulable_exams:
                errors.extend(
                    [
                        f"Exam {code} has no compatible rooms"
                        for code in unschedulable_exams
                    ]
                )

        return {"errors": errors, "warnings": warnings}

    def get_variables(self) -> Dict[str, cp_model.IntVar]:
        """
        Get all variables created during model building.

        Returns:
            Dictionary mapping variable names to CP-SAT integer variables.
        """
        return self.variables
