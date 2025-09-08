# scheduling_engine/tests/unit/test_solver_manager.py

"""
Tests for CPSATSolverManager class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID, uuid4
import time
from datetime import datetime

from ortools.sat.python import cp_model

from scheduling_engine.cp_sat.solver_manager import (
    CPSATSolverManager,
    SolverCallback,
)
from scheduling_engine.core.problem_model import ExamSchedulingProblem
from scheduling_engine.config import CPSATConfig
from ...cp_sat.model_builder import CPSATModelBuilder


class TestSolverManager:
    """Tests for CPSATSolverManager functionality"""

    def test_solver_manager_initialization(self):
        """Test solver manager initialization"""
        config = CPSATConfig(
            time_limit_seconds=300, num_workers=4, log_search_progress=True
        )

        manager = CPSATSolverManager(config)

        assert manager.config == config
        assert hasattr(manager, "solver")
        assert hasattr(manager, "solution_extractor")
        assert isinstance(manager.solver, cp_model.CpSolver)

    def test_solver_callback_initialization(self):
        """Test solver callback initialization"""
        mock_callback = Mock()
        callback = SolverCallback(progress_callback=mock_callback)

        assert callback.progress_callback == mock_callback
        assert callback.solution_count == 0
        assert callback.best_objective == float("inf")

    @patch("scheduling_engine.cp_sat.solver_manager.logger")
    def test_solver_callback_on_solution(self, mock_logger):
        """Test solver callback on solution"""
        mock_callback = Mock()
        callback = SolverCallback(progress_callback=mock_callback)

        # Mock the ObjectiveValue method
        with patch.object(callback, "ObjectiveValue", return_value=100.0):
            callback.on_solution_callback()

            assert callback.solution_count == 1
            assert callback.best_objective == 100.0
            mock_callback.assert_called_once()
            mock_logger.debug.assert_called()

    def test_configure_solver(self):
        """Test solver configuration"""
        config = CPSATConfig(
            time_limit_seconds=600, num_workers=8, log_search_progress=False
        )

        manager = CPSATSolverManager(config)

        # Check that parameters were set
        params = manager.solver.parameters
        # Note: Actual parameter names might vary by OR-Tools version

    @patch("scheduling_engine.cp_sat.solver_manager.threading")
    @patch(
        "scheduling_engine.cp_sat.solver_manager.psutil", None
    )  # Mock psutil as unavailable
    def test_memory_monitoring_no_psutil(self, mock_threading):
        """Test memory monitoring when psutil is not available"""
        manager = CPSATSolverManager()

        # Mock thread
        mock_thread = Mock()
        mock_threading.Thread.return_value = mock_thread

        manager._start_memory_monitoring()
        assert manager._monitor_memory is True
        assert manager.memory_monitor == mock_thread
        mock_thread.start.assert_called_once()

        manager._stop_memory_monitoring()
        mock_thread.join.assert_called_once()

    @patch("scheduling_engine.cp_sat.solver_manager.logger")
    def test_solve_method(self, mock_logger):
        """Test solve method"""
        manager = CPSATSolverManager()

        # Mock model, problem, and variables
        mock_model = Mock()
        mock_problem = Mock()
        mock_variables = {"test_var": Mock()}

        # Mock solver response
        manager.solver.Solve = Mock(return_value=cp_model.OPTIMAL)
        manager.solver.value = Mock(return_value=1)

        # Mock solution extraction
        mock_solution = Mock()
        mock_solution.objective_value = 100.0
        manager.solution_extractor.extract_solution = Mock(
            return_value=Mock(solution=mock_solution, extraction_successful=True)
        )

        result = manager.solve(mock_model, mock_problem, mock_variables)

        assert result["status"] == "OPTIMAL"
        assert result["objective_value"] == 100.0
        mock_logger.info.assert_called()

    def test_solve_with_time_limit(self):
        """Test solving with time limit"""
        manager = CPSATSolverManager()

        # Mock model, problem, and variables
        mock_model = Mock()
        mock_problem = Mock()
        mock_variables = {"test_var": Mock()}

        # Mock the solve method
        with patch.object(
            manager, "solve", return_value={"status": "FEASIBLE"}
        ) as mock_solve:
            result = manager.solve_with_time_limit(
                mock_model, mock_problem, mock_variables, 30
            )

            assert result["status"] == "FEASIBLE"
            mock_solve.assert_called_once()

    def test_solve_for_feasibility(self):
        """Test solving for feasibility"""
        manager = CPSATSolverManager()

        # Mock model, problem, and variables
        mock_model = Mock()
        mock_problem = Mock()
        mock_variables = {"test_var": Mock()}

        # Mock the solve method
        with patch.object(
            manager, "solve", return_value={"status": "FEASIBLE"}
        ) as mock_solve:
            result = manager.solve_for_feasibility(
                mock_model, mock_problem, mock_variables
            )

            assert result["status"] == "FEASIBLE"
            assert result["solving_phase"] == "feasibility"
            mock_solve.assert_called_once()

    def test_validate_model_before_solving(self):
        """Test model validation"""
        manager = CPSATSolverManager()

        # Test with valid model
        mock_model = Mock()
        mock_proto = Mock()
        mock_proto.variables = [Mock()]
        mock_proto.constraints = [Mock()]
        mock_model.Proto.return_value = mock_proto

        validation = manager.validate_model_before_solving(mock_model)

        assert len(validation["errors"]) == 0

        # Test with invalid model
        mock_model.Proto.return_value.variables = []
        validation = manager.validate_model_before_solving(mock_model)

        assert len(validation["errors"]) > 0

    def test_get_solving_statistics(self):
        """Test getting solving statistics"""
        manager = CPSATSolverManager()
        manager.solving_statistics = {"test_stat": 100}

        stats = manager.get_solving_statistics()

        assert stats["solver_version"] == "OR-Tools CP-SAT"
        assert "configuration" in stats
        assert "last_solve_statistics" in stats

    def test_solve_with_variable_ordering(self):
        """Test solving with variable ordering"""
        manager = CPSATSolverManager()

        # Mock problem and model builder
        mock_problem = Mock()
        variable_ordering = {uuid4(): 0.8}

        # Mock model building and solving
        with patch(
            "scheduling_engine.cp_sat.model_builder.CPSATModelBuilder"
        ) as mock_builder:
            mock_instance = Mock()
            mock_instance.build_model.return_value = Mock()
            mock_instance.get_variables.return_value = {}
            mock_builder.return_value = mock_instance

            with patch.object(
                manager, "solve_with_time_limit", return_value={"status": "FEASIBLE"}
            ):
                result = manager.solve_with_variable_ordering(
                    mock_problem, variable_ordering, 30
                )

                assert result["status"] == "FEASIBLE"


if __name__ == "__main__":
    pytest.main([__file__])
