# scheduling_engine/tests/unit/test_metrics.py

"""
Comprehensive tests for solution quality metrics and performance evaluation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID, uuid4
import time
from datetime import datetime, date, time as dt_time
from typing import cast, List
from scheduling_engine.core.metrics import (
    SolutionMetrics,
    QualityScore,
    PerformanceMetrics,
)
from scheduling_engine.core.problem_model import (
    ExamSchedulingProblem,
    Exam,
    TimeSlot,
    Room,
    Student,
)
from scheduling_engine.core.solution import (
    TimetableSolution,
    ExamAssignment,
    AssignmentStatus,
)
from scheduling_engine.core.constraint_types import ConstraintType, ConstraintCategory


class TestQualityScore:
    """Tests for QualityScore dataclass"""

    def test_quality_score_initialization(self):
        """Test QualityScore initialization with default values"""
        score = QualityScore()

        assert score.total_score == 0.0
        assert score.feasibility_score == 0.0
        assert score.objective_value_score == 0.0
        assert score.constraint_satisfaction_score == 0.0
        assert score.resource_utilization_score == 0.0
        assert score.student_satisfaction_score == 0.0
        assert score.hard_constraint_penalty == 0.0
        assert score.soft_constraint_penalty == 0.0
        assert score.unassigned_exam_penalty == 0.0
        assert score.weights == {}

    def test_quality_score_custom_values(self):
        """Test QualityScore with custom values"""
        weights = {"feasibility": 1.0, "objective_value": 0.8}
        score = QualityScore(
            total_score=85.5,
            feasibility_score=1.0,
            objective_value_score=0.9,
            constraint_satisfaction_score=0.8,
            resource_utilization_score=0.7,
            student_satisfaction_score=0.6,
            hard_constraint_penalty=0.0,
            soft_constraint_penalty=5.0,
            unassigned_exam_penalty=0.0,
            weights=weights,
        )

        assert score.total_score == 85.5
        assert score.feasibility_score == 1.0
        assert score.objective_value_score == 0.9
        assert score.constraint_satisfaction_score == 0.8
        assert score.resource_utilization_score == 0.7
        assert score.student_satisfaction_score == 0.6
        assert score.hard_constraint_penalty == 0.0
        assert score.soft_constraint_penalty == 5.0
        assert score.unassigned_exam_penalty == 0.0
        assert score.weights == weights


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics dataclass"""

    def test_performance_metrics_initialization(self):
        """Test PerformanceMetrics initialization with default values"""
        metrics = PerformanceMetrics()

        assert metrics.total_runtime_seconds == 0.0
        assert metrics.cp_sat_runtime_seconds == 0.0
        assert metrics.ga_runtime_seconds == 0.0
        assert metrics.coordination_overhead_seconds == 0.0
        assert metrics.total_iterations == 0
        assert metrics.cp_sat_iterations == 0
        assert metrics.ga_generations == 0
        assert metrics.peak_memory_mb == 0.0
        assert metrics.average_memory_mb == 0.0
        assert metrics.generations_to_best == 0
        assert metrics.improvement_rate == 0.0
        assert metrics.convergence_stability == 0.0
        assert metrics.initial_solution_quality == 0.0
        assert metrics.final_solution_quality == 0.0
        assert metrics.quality_improvement == 0.0

    def test_performance_metrics_custom_values(self):
        """Test PerformanceMetrics with custom values"""
        metrics = PerformanceMetrics(
            total_runtime_seconds=120.5,
            cp_sat_runtime_seconds=60.2,
            ga_runtime_seconds=55.3,
            coordination_overhead_seconds=5.0,
            total_iterations=1000,
            cp_sat_iterations=500,
            ga_generations=20,
            peak_memory_mb=512.0,
            average_memory_mb=256.0,
            generations_to_best=15,
            improvement_rate=0.75,
            convergence_stability=0.9,
            initial_solution_quality=0.5,
            final_solution_quality=0.9,
            quality_improvement=0.4,
        )

        assert metrics.total_runtime_seconds == 120.5
        assert metrics.cp_sat_runtime_seconds == 60.2
        assert metrics.ga_runtime_seconds == 55.3
        assert metrics.coordination_overhead_seconds == 5.0
        assert metrics.total_iterations == 1000
        assert metrics.cp_sat_iterations == 500
        assert metrics.ga_generations == 20
        assert metrics.peak_memory_mb == 512.0
        assert metrics.average_memory_mb == 256.0
        assert metrics.generations_to_best == 15
        assert metrics.improvement_rate == 0.75
        assert metrics.convergence_stability == 0.9
        assert metrics.initial_solution_quality == 0.5
        assert metrics.final_solution_quality == 0.9
        assert metrics.quality_improvement == 0.4


class TestSolutionMetrics:
    """Tests for SolutionMetrics class functionality"""

    @pytest.fixture
    def setup_problem_and_solution(self):
        """Set up a basic problem and solution for testing"""
        # Create a mock problem
        problem = ExamSchedulingProblem(session_id=uuid4(), session_name="Test Session")

        # Add time slots
        time_slot = TimeSlot(
            id=uuid4(),
            name="Morning Slot",
            start_time=dt_time(9, 0),
            end_time=dt_time(12, 0),
            duration_minutes=180,
        )
        problem.time_slots[time_slot.id] = time_slot

        # Add rooms
        room = Room(
            id=uuid4(), code="ROOM001", name="Test Room", capacity=50, exam_capacity=45
        )
        problem.rooms[room.id] = room

        # Add students
        student = Student(
            id=uuid4(), matric_number="STU001", programme_id=uuid4(), current_level=200
        )
        problem.students[student.id] = student

        # Add exams
        exam = Exam(
            id=uuid4(),
            course_id=uuid4(),
            course_code="TEST001",
            course_title="Test Course",
            expected_students=30,
            duration_minutes=180,
        )
        problem.exams[exam.id] = exam

        # Create a solution
        solution = TimetableSolution(problem)

        # Create a complete assignment
        assignment = ExamAssignment(
            exam_id=exam.id,
            time_slot_id=time_slot.id,
            room_ids=[room.id],
            assigned_date=date(2024, 1, 15),
            status=AssignmentStatus.ASSIGNED,
        )
        solution.assignments[exam.id] = assignment

        return problem, solution

    def test_solution_metrics_initialization(self):
        """Test SolutionMetrics initialization"""
        metrics = SolutionMetrics()

        assert len(metrics.evaluation_history) == 0
        assert isinstance(metrics.performance_metrics, PerformanceMetrics)

    def test_default_weights(self):
        """Test getting default weights"""
        metrics = SolutionMetrics()
        weights = metrics._get_default_weights()

        assert "feasibility" in weights
        assert "objective_value" in weights
        assert "constraint_satisfaction" in weights
        assert "resource_utilization" in weights
        assert "student_satisfaction" in weights
        assert "hard_constraint_penalty" in weights
        assert "soft_constraint_penalty" in weights
        assert "unassigned_penalty" in weights

    def test_evaluate_solution_quality(self, setup_problem_and_solution):
        """Test comprehensive solution quality evaluation"""
        problem, solution = setup_problem_and_solution
        metrics = SolutionMetrics()

        # Mock the internal calculation methods
        with patch.object(
            metrics, "_calculate_feasibility_score", return_value=1.0
        ), patch.object(
            metrics, "_calculate_objective_score", return_value=0.9
        ), patch.object(
            metrics, "_calculate_constraint_satisfaction", return_value=0.8
        ), patch.object(
            metrics, "_calculate_utilization_score", return_value=0.7
        ), patch.object(
            metrics, "_calculate_student_satisfaction", return_value=0.6
        ), patch.object(
            metrics, "_calculate_hard_constraint_penalty", return_value=0.0
        ), patch.object(
            metrics, "_calculate_soft_constraint_penalty", return_value=5.0
        ), patch.object(
            metrics, "_calculate_unassigned_penalty", return_value=0.0
        ):

            quality = metrics.evaluate_solution_quality(problem, solution)

            # Verify all components were calculated
            assert quality.feasibility_score == 1.0
            assert quality.objective_value_score == 0.9
            assert quality.constraint_satisfaction_score == 0.8
            assert quality.resource_utilization_score == 0.7
            assert quality.student_satisfaction_score == 0.6
            assert quality.hard_constraint_penalty == 0.0
            assert quality.soft_constraint_penalty == 5.0
            assert quality.unassigned_exam_penalty == 0.0

            # Verify total score was calculated
            assert quality.total_score != 0.0

            # Verify history was updated
            assert len(metrics.evaluation_history) == 1

    def test_calculate_feasibility_score(self, setup_problem_and_solution):
        """Test feasibility score calculation"""
        problem, solution = setup_problem_and_solution
        metrics = SolutionMetrics()

        # Test with feasible solution
        with patch.object(solution, "is_feasible", return_value=True), patch.object(
            solution, "get_completion_percentage", return_value=100.0
        ):

            score = metrics._calculate_feasibility_score(problem, solution)
            assert score == 1.0  # 100% completion for feasible solution

        # Test with infeasible solution
        with patch.object(solution, "is_feasible", return_value=False):
            score = metrics._calculate_feasibility_score(problem, solution)
            assert score == 0.0  # 0 for infeasible

        # Test with partial completion
        with patch.object(solution, "is_feasible", return_value=True), patch.object(
            solution, "get_completion_percentage", return_value=75.0
        ):

            score = metrics._calculate_feasibility_score(problem, solution)
            assert score == 0.75  # Proportional to completion

    def test_calculate_objective_score(self, setup_problem_and_solution):
        """Test objective value score calculation"""
        problem, solution = setup_problem_and_solution
        metrics = SolutionMetrics()

        # Test with finite objective value
        with patch.object(solution, "calculate_objective_value", return_value=50.0):
            score = metrics._calculate_objective_score(solution)
            assert 0 <= score <= 1.0  # Should be normalized

        # Test with infinite objective value
        with patch.object(
            solution, "calculate_objective_value", return_value=float("inf")
        ):
            score = metrics._calculate_objective_score(solution)
            assert score == 0.0

        # Test with zero objective value
        with patch.object(solution, "calculate_objective_value", return_value=0.0):
            score = metrics._calculate_objective_score(solution)
            assert score == 1.0

    def test_calculate_fitness_for_ga(self, setup_problem_and_solution):
        """Test fitness calculation for genetic algorithm"""
        problem, solution = setup_problem_and_solution
        metrics = SolutionMetrics()

        # Mock the evaluation to return a known quality score
        mock_quality = QualityScore(total_score=85.0)
        with patch.object(
            metrics, "evaluate_solution_quality", return_value=mock_quality
        ):
            fitness = metrics.calculate_fitness_for_ga(problem, solution)

            # Fitness should be positive and based on quality score
            assert fitness > 0
            assert fitness == 185.0  # total_score + 100

    def test_calculate_diversity_metrics(self, setup_problem_and_solution):
        """Test diversity metrics calculation"""
        problem, solution = setup_problem_and_solution
        metrics = SolutionMetrics()

        # Create a few mock solutions
        solutions: List[TimetableSolution] = [
            cast(TimetableSolution, Mock(spec=TimetableSolution)) for _ in range(3)
        ]

        # Mock the diversity calculation
        with patch.object(
            metrics, "_calculate_solution_diversity", return_value=0.5
        ), patch.object(metrics, "_count_unique_solutions", return_value=2):

            diversity_metrics = metrics.calculate_diversity_metrics(solutions)

            assert "diversity" in diversity_metrics
            assert "uniqueness" in diversity_metrics
            assert "population_size" in diversity_metrics
            assert "unique_solutions" in diversity_metrics

            assert diversity_metrics["population_size"] == 3
            assert diversity_metrics["unique_solutions"] == 2

    def test_update_performance_metrics(self):
        """Test performance metrics updating"""
        metrics = SolutionMetrics()

        # Test CP-SAT phase
        metrics.update_performance_metrics(
            runtime=10.5, solver_phase="cp_sat", iterations=100, memory_usage=256.0
        )

        assert metrics.performance_metrics.cp_sat_runtime_seconds == 10.5
        assert metrics.performance_metrics.cp_sat_iterations == 100
        assert metrics.performance_metrics.total_runtime_seconds == 10.5
        assert metrics.performance_metrics.total_iterations == 100
        assert metrics.performance_metrics.peak_memory_mb == 256.0

        # Test GA phase
        metrics.update_performance_metrics(
            runtime=15.2, solver_phase="ga", iterations=50, memory_usage=512.0
        )

        assert metrics.performance_metrics.ga_runtime_seconds == 15.2
        assert metrics.performance_metrics.ga_generations == 50
        assert metrics.performance_metrics.total_runtime_seconds == 25.7
        assert metrics.performance_metrics.total_iterations == 150
        assert metrics.performance_metrics.peak_memory_mb == 512.0

    def test_calculate_convergence_metrics(self):
        """Test convergence metrics calculation"""
        metrics = SolutionMetrics()

        # Test with empty history
        empty_metrics = metrics.calculate_convergence_metrics([])
        assert empty_metrics["convergence_rate"] == 0.0
        assert empty_metrics["stability"] == 0.0
        assert empty_metrics["improvement_rate"] == 0.0

        # Test with fitness history
        fitness_history = [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.87, 0.88, 0.89, 0.9]
        convergence_metrics = metrics.calculate_convergence_metrics(fitness_history)

        assert "convergence_rate" in convergence_metrics
        assert "stability" in convergence_metrics
        assert "improvement_rate" in convergence_metrics
        assert "generations_evaluated" in convergence_metrics

        assert convergence_metrics["generations_evaluated"] == 10
        assert (
            convergence_metrics["improvement_rate"] == (0.9 - 0.5) / 0.5
        )  # 80% improvement

    def test_generate_quality_report(self, setup_problem_and_solution):
        """Test quality report generation"""
        problem, solution = setup_problem_and_solution
        metrics = SolutionMetrics()

        # Mock the evaluation
        mock_quality = QualityScore(
            total_score=85.0,
            feasibility_score=1.0,
            objective_value_score=0.9,
            constraint_satisfaction_score=0.8,
            resource_utilization_score=0.7,
            student_satisfaction_score=0.6,
            hard_constraint_penalty=0.0,
            soft_constraint_penalty=5.0,
            unassigned_exam_penalty=0.0,
        )

        with patch.object(
            metrics, "evaluate_solution_quality", return_value=mock_quality
        ), patch.object(solution, "update_statistics"), patch.object(
            solution, "fitness_score", 0.85
        ), patch.object(
            solution, "objective_value", 50.0
        ):

            report = metrics.generate_quality_report(problem, solution)

            # Verify report structure
            assert "solution_id" in report
            assert "evaluation_timestamp" in report
            assert "total_quality_score" in report
            assert "fitness_score" in report
            assert "objective_value" in report
            assert "quality_components" in report
            assert "penalties" in report
            assert "statistics" in report
            assert "performance" in report

            # Verify values
            assert report["total_quality_score"] == 85.0
            assert report["fitness_score"] == 0.85
            assert report["objective_value"] == 50.0
            assert report["quality_components"]["feasibility_score"] == 1.0
            assert report["penalties"]["soft_constraint_penalty"] == 5.0


if __name__ == "__main__":
    pytest.main([__file__])
