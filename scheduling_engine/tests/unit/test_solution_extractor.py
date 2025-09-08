# scheduling_engine/tests/unit/test_solution_extractor.py

"""
Tests for SolutionExtractor class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID, uuid4
from datetime import datetime, date
from ortools.sat.python import cp_model

from scheduling_engine.cp_sat.solution_extractor import (
    SolutionExtractor,
    ExtractionContext,
    SolutionExtractionResult,
)
from scheduling_engine.core.problem_model import (
    ExamSchedulingProblem,
    Exam,
    Room,
    TimeSlot,
)
from scheduling_engine.core.solution import (
    TimetableSolution,
    ExamAssignment,
    AssignmentStatus,
)
from scheduling_engine.core.metrics import SolutionMetrics


class TestSolutionExtractor:
    """Tests for SolutionExtractor functionality"""

    def test_extraction_context_creation(self):
        """Test ExtractionContext dataclass"""
        mock_solver = Mock()
        mock_model = Mock()
        mock_variables = {"test_var": Mock()}
        mock_problem = Mock()

        context = ExtractionContext(
            solver=mock_solver,
            model=mock_model,
            variables=mock_variables,  # type: ignore[arg-type]
            problem=mock_problem,
            solver_status=cp_model.OPTIMAL,
            solve_time_seconds=10.5,
        )

        assert context.solver == mock_solver
        assert context.model == mock_model
        assert context.variables == mock_variables
        assert context.problem == mock_problem
        assert context.solver_status == cp_model.OPTIMAL
        assert context.solve_time_seconds == 10.5

    def test_extractor_initialization(self):
        """Test SolutionExtractor initialization"""
        extractor = SolutionExtractor()
        assert hasattr(extractor, "metrics_calculator")
        assert isinstance(extractor.metrics_calculator, SolutionMetrics)

    @patch("scheduling_engine.cp_sat.solution_extractor.logger")
    def test_extract_solution_no_solution(self, mock_logger):
        """Test extraction when solver has no solution"""
        extractor = SolutionExtractor()
        context = ExtractionContext(
            solver=Mock(),
            model=Mock(),
            variables={},
            problem=Mock(),
            solver_status=cp_model.INFEASIBLE,
            solve_time_seconds=10.0,
        )

        result = extractor.extract_solution(context)

        assert result.extraction_successful is False
        assert result.solution is None
        assert len(result.errors) > 0
        mock_logger.info.assert_called()

    @patch("scheduling_engine.cp_sat.solution_extractor.logger")
    def test_extract_variable_assignments(self, mock_logger):
        """Test variable assignment extraction"""
        extractor = SolutionExtractor()

        # Mock solver with value method
        mock_solver = Mock()
        mock_solver.value.side_effect = [1, 0, 1]  # Return values for variables

        # Mock variables
        mock_var1 = Mock()
        mock_var2 = Mock()
        mock_var3 = Mock()
        variables = {"var1": mock_var1, "var2": mock_var2, "var3": mock_var3}

        context = ExtractionContext(
            solver=mock_solver,
            model=Mock(),
            variables=variables,  # type: ignore[arg-type]
            problem=Mock(),
            solver_status=cp_model.FEASIBLE,
            solve_time_seconds=5.0,
        )

        assignments = extractor._extract_variable_assignments(context)

        assert assignments["var1"] == 1
        assert assignments["var2"] == 0
        assert assignments["var3"] == 1
        assert mock_solver.value.call_count == 3

    def test_convert_to_exam_assignments(self):
        """Test conversion of variable assignments to exam assignments"""
        extractor = SolutionExtractor()

        # Create test data
        exam_id = uuid4()
        room_id = uuid4()
        time_slot_id = uuid4()

        # Mock variables with assignment pattern
        variables = {f"x_{exam_id}_{room_id}_{time_slot_id}": Mock()}

        # Mock problem with exam and room
        mock_exam = Mock()
        mock_exam.expected_students = 30
        mock_room = Mock()
        mock_room.exam_capacity = 50
        mock_time_slot = Mock()

        mock_problem = Mock()
        mock_problem.exams = {exam_id: mock_exam}
        mock_problem.rooms = {room_id: mock_room}
        mock_problem.time_slots = {time_slot_id: mock_time_slot}

        context = ExtractionContext(
            solver=Mock(),
            model=Mock(),
            variables=variables,  # type: ignore[arg-type]
            problem=mock_problem,
            solver_status=cp_model.FEASIBLE,
            solve_time_seconds=5.0,
        )

        # Mock solver to return 1 for our variable
        context.solver.value = Mock(return_value=1)

        assignments = extractor._convert_to_exam_assignments(
            {f"x_{exam_id}_{room_id}_{time_slot_id}": 1}, context
        )

        assert len(assignments) == 1
        assignment = assignments[0]
        assert assignment.exam_id == exam_id
        assert assignment.time_slot_id == time_slot_id
        assert assignment.room_ids == [room_id]

    @patch("scheduling_engine.cp_sat.solution_extractor.logger")
    def test_build_solution_object(self, mock_logger):
        """Test building solution object from assignments"""
        extractor = SolutionExtractor()

        # Create test exam assignment
        exam_id = uuid4()
        time_slot_id = uuid4()
        room_id = uuid4()

        assignment = ExamAssignment(exam_id=exam_id)
        assignment.time_slot_id = time_slot_id
        assignment.room_ids = [room_id]
        assignment.status = AssignmentStatus.ASSIGNED
        assignment.add_room_allocation(room_id, 30)

        # Mock problem
        mock_exam = Mock()
        mock_exam.exam_date = date(2024, 1, 15)
        mock_exam.weight = 1
        mock_problem = Mock()
        mock_problem.exams = {exam_id: mock_exam}

        context = ExtractionContext(
            solver=Mock(),
            model=Mock(),
            variables={},
            problem=mock_problem,
            solver_status=cp_model.FEASIBLE,
            solve_time_seconds=5.0,
        )

        solution = extractor._build_solution_object([assignment], context)

        assert solution is not None
        assert exam_id in solution.assignments
        mock_logger.info.assert_called()

    @patch("scheduling_engine.cp_sat.solution_extractor.SolutionMetrics")
    def test_calculate_solution_quality(self, mock_metrics_class):
        """Test solution quality calculation"""
        extractor = SolutionExtractor()

        # Mock metrics calculator
        mock_metrics = Mock()
        mock_metrics.evaluate_solution_quality.return_value = Mock(
            total_score=0.95,
            feasibility_score=1.0,
            objective_value_score=0.9,
            constraint_satisfaction_score=0.95,
            resource_utilization_score=0.85,
            student_satisfaction_score=0.88,
            hard_constraint_penalty=0.0,
            soft_constraint_penalty=5.0,
            unassigned_exam_penalty=0.0,
        )
        extractor.metrics_calculator = mock_metrics

        context = ExtractionContext(
            solver=Mock(),
            model=Mock(),
            variables={},
            problem=Mock(),
            solver_status=cp_model.FEASIBLE,
            solve_time_seconds=10.0,
        )

        mock_problem = Mock()
        mock_problem.exams = {}
        mock_problem.session_id = uuid4()
        solution = TimetableSolution(problem=mock_problem, solution_id=uuid4())

        quality_metrics = extractor._calculate_solution_quality(solution, context)

        assert quality_metrics["total_score"] == 0.95
        assert quality_metrics["cp_sat_solve_time"] == 10.0
        mock_metrics.evaluate_solution_quality.assert_called_once()

    def test_validate_solution_consistency(self):
        """Test solution consistency validation"""
        extractor = SolutionExtractor()

        # Create a solution with assignments
        mock_problem = Mock()
        mock_problem.exams = {}
        mock_problem.session_id = uuid4()
        solution = TimetableSolution(problem=mock_problem, solution_id=uuid4())

        # Add a complete assignment
        exam_id = uuid4()
        assignment = ExamAssignment(exam_id=exam_id)
        assignment.time_slot_id = uuid4()
        assignment.room_ids = [uuid4()]
        assignment.status = AssignmentStatus.ASSIGNED
        solution.assignments[exam_id] = assignment

        context = ExtractionContext(
            solver=Mock(),
            model=Mock(),
            variables={},
            problem=Mock(),
            solver_status=cp_model.FEASIBLE,
            solve_time_seconds=5.0,
        )

        validation_result = extractor._validate_solution_consistency(solution, context)

        assert "is_consistent" in validation_result
        assert "errors" in validation_result
        assert "warnings" in validation_result

    def test_extract_partial_solution(self):
        """Test partial solution extraction"""
        extractor = SolutionExtractor()

        context = ExtractionContext(
            solver=Mock(),
            model=Mock(),
            variables={},
            problem=Mock(),
            solver_status=cp_model.FEASIBLE,
            solve_time_seconds=5.0,
        )

        # Mock variable extraction to return empty
        with patch.object(extractor, "_extract_variable_assignments", return_value={}):
            result = extractor.extract_partial_solution(context)

            assert result.extraction_successful is False
            assert "No partial assignments" in result.errors[0]

    def test_get_solver_statistics(self):
        """Test solver statistics extraction"""
        extractor = SolutionExtractor()

        # Mock solver with statistics methods
        mock_solver = Mock()
        mock_solver.NumBooleans.return_value = 100
        mock_solver.NumConflicts.return_value = 50
        mock_solver.NumBranches.return_value = 200
        mock_solver.num_branches = 200
        mock_solver.WallTime.return_value = 10.5
        mock_solver.UserTime.return_value = 8.2

        context = ExtractionContext(
            solver=mock_solver,
            model=Mock(),
            variables={},
            problem=Mock(),
            solver_status=cp_model.FEASIBLE,
            solve_time_seconds=5.0,
        )

        stats = extractor.get_solver_statistics(context)

        assert stats["solver_status"] in ("FEASIBLE", str(cp_model.FEASIBLE))
        assert stats["solve_time_seconds"] == 5.0
        assert stats["num_branches"] == 200

    def test_export_solution_for_ga(self):
        """Test solution export for genetic algorithm"""
        extractor = SolutionExtractor()

        # Create a solution with assignments using assign_exam method
        mock_problem = Mock()
        exam_id = uuid4()
        mock_exam = Mock()
        mock_exam.expected_students = 30
        mock_exam.exam_date = date(2024, 1, 15)
        mock_problem.exams = {exam_id: mock_exam}
        mock_problem.session_id = uuid4()

        solution = TimetableSolution(problem=mock_problem, solution_id=uuid4())
        solution.fitness_score = 0.95

        # Add an assignment using the solution's method
        time_slot_id = uuid4()
        room_id = uuid4()
        solution.assign_exam(
            exam_id=exam_id,
            time_slot_id=time_slot_id,
            room_ids=[room_id],
            assigned_date=mock_exam.exam_date,
            room_allocations={room_id: 30},
        )

        ga_data = extractor.export_solution_for_ga(solution)

        assert ga_data["fitness_score"] == 0.95
        assert len(ga_data["assignments"]) == 1
        assert str(exam_id) in ga_data["assignments"][0]["exam_id"]

    def test_extract_infeasibility_analysis(self):
        """Test infeasibility analysis extraction"""
        extractor = SolutionExtractor()

        context = ExtractionContext(
            solver=Mock(),
            model=Mock(),
            variables={},
            problem=Mock(),
            solver_status=cp_model.INFEASIBLE,
            solve_time_seconds=5.0,
        )

        analysis = extractor.extract_infeasibility_analysis(context)

        assert analysis["is_infeasible"] is True
        assert "conflicting_constraints" in analysis
        assert "recommendations" in analysis


if __name__ == "__main__":
    pytest.main([__file__])
