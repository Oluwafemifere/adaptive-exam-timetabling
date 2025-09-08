# scheduling_engine/tests/unit/test_constraint_encoder.py

"""
Tests for ConstraintEncoder class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID, uuid4
from datetime import datetime

from ortools.sat.python import cp_model

from scheduling_engine.cp_sat.constraint_encoder import (
    ConstraintEncoder,
    EncodingContext,
)
from scheduling_engine.core.problem_model import (
    ExamSchedulingProblem,
    Exam,
    Room,
    TimeSlot,
)
from scheduling_engine.core.constraint_registry import ConstraintRegistry


class TestConstraintEncoder:
    """Tests for ConstraintEncoder functionality"""

    def test_encoding_context_creation(self):
        """Test EncodingContext dataclass"""
        mock_model = Mock()
        mock_variables = {"test_var": Mock()}
        mock_problem = Mock()
        constraint_weights = {"constraint1": 1.0}

        context = EncodingContext(
            model=mock_model,
            variables=mock_variables,
            problem=mock_problem,
            constraint_weights=constraint_weights,
            partition_id="test_partition",
        )

        assert context.model == mock_model
        assert context.variables == mock_variables
        assert context.problem == mock_problem
        assert context.constraint_weights == constraint_weights
        assert context.partition_id == "test_partition"

    def test_encoder_initialization(self):
        """Test ConstraintEncoder initialization"""
        mock_registry = Mock()
        encoder = ConstraintEncoder(constraint_registry=mock_registry)

        assert encoder.constraint_registry == mock_registry
        assert "NO_STUDENT_CONFLICT" in encoder.encoding_methods

    @patch("scheduling_engine.cp_sat.constraint_encoder.logger")
    def test_encode_constraints(self, mock_logger):
        """Test constraint encoding"""
        encoder = ConstraintEncoder()

        # Mock context
        mock_model = Mock()
        mock_variables = {}
        mock_problem = Mock()
        context = EncodingContext(
            model=mock_model,
            variables=mock_variables,
            problem=mock_problem,
            constraint_weights={},
        )

        # Mock constraints
        hard_constraint = {
            "code": "NO_STUDENT_CONFLICT",
            "constraint_type": "hard",
            "weight": 1.0,
        }
        soft_constraint = {
            "code": "EXAM_DISTRIBUTION",
            "constraint_type": "soft",
            "weight": 0.5,
        }
        active_constraints = [hard_constraint, soft_constraint]

        # Mock encoding methods by replacing them in the encoding_methods dictionary
        mock_hard_method = Mock(return_value=[Mock()])
        mock_soft_method = Mock(return_value=[Mock()])
        encoder.encoding_methods["NO_STUDENT_CONFLICT"] = mock_hard_method
        encoder.encoding_methods["EXAM_DISTRIBUTION"] = mock_soft_method

        constraints, stats = encoder.encode_constraints(context, active_constraints)

        assert len(constraints) == 2
        assert stats["hard_constraints"] == 1
        assert stats["soft_constraints"] == 1
        mock_logger.info.assert_called()

    def test_encode_no_student_conflicts(self):
        """Test encoding no student conflicts constraint"""
        encoder = ConstraintEncoder()

        # Create mock context with problem data
        mock_model = Mock()
        mock_variables = {}
        mock_problem = Mock()

        # Mock course registrations
        course_id = uuid4()
        student_id = uuid4()
        mock_registration = Mock()
        mock_registration.course_id = course_id
        mock_registration.student_id = student_id

        mock_problem.course_registrations = {"reg1": mock_registration}
        mock_problem.students = [student_id]

        # Mock exam
        mock_exam = Mock()
        mock_exam.course_id = course_id
        mock_problem.exams = {uuid4(): mock_exam}

        # Mock time slot
        mock_time_slot = Mock()
        mock_problem.time_slots = {uuid4(): mock_time_slot}

        # Mock room
        mock_problem.rooms = {uuid4(): Mock()}

        context = EncodingContext(
            model=mock_model,
            variables=mock_variables,
            problem=mock_problem,
            constraint_weights={},
        )

        constraints = encoder._encode_no_student_conflicts(context, {})

        # Should create constraints (implementation specific)
        assert constraints is not None

    def test_encode_room_capacity(self):
        """Test encoding room capacity constraint"""
        encoder = ConstraintEncoder()

        # Create mock context
        mock_model = Mock()
        mock_variables = {}
        mock_problem = Mock()

        # Mock room
        room_id = uuid4()
        mock_room = Mock()
        mock_room.exam_capacity = 50
        mock_problem.rooms = {room_id: mock_room}

        # Mock time slot
        time_slot_id = uuid4()
        mock_problem.time_slots = {time_slot_id: Mock()}

        # Mock exam
        exam_id = uuid4()
        mock_exam = Mock()
        mock_exam.expected_students = 30
        mock_problem.exams = {exam_id: mock_exam}

        context = EncodingContext(
            model=mock_model,
            variables=mock_variables,
            problem=mock_problem,
            constraint_weights={},
        )

        constraints = encoder._encode_room_capacity(context, {})

        # Should create constraints (implementation specific)
        assert constraints is not None

    def test_encode_exam_assignment(self):
        """Test encoding exam assignment constraint"""
        encoder = ConstraintEncoder()

        # Create mock context
        mock_model = Mock()
        mock_variables = {}
        mock_problem = Mock()

        # Mock exam
        exam_id = uuid4()
        mock_problem.exams = {exam_id: Mock()}

        # Mock rooms and time slots
        mock_problem.rooms = {uuid4(): Mock()}
        mock_problem.time_slots = {uuid4(): Mock()}

        context = EncodingContext(
            model=mock_model,
            variables=mock_variables,
            problem=mock_problem,
            constraint_weights={},
        )

        constraints = encoder._encode_exam_assignment(context, {})

        # Should create constraints (implementation specific)
        assert constraints is not None

    @patch("scheduling_engine.cp_sat.constraint_encoder.logger")
    def test_validate_encoding(self, mock_logger):
        """Test encoding validation"""
        encoder = ConstraintEncoder()

        # Mock context
        mock_model = Mock()
        mock_variables = {"var1": Mock()}
        mock_problem = Mock()
        mock_problem.exams = {"exam1": Mock()}
        mock_problem.rooms = {"room1": Mock()}
        mock_problem.time_slots = {"slot1": Mock()}

        context = EncodingContext(
            model=mock_model,
            variables=mock_variables,
            problem=mock_problem,
            constraint_weights={},
        )

        encoded_constraints = [Mock(), Mock()]

        validation = encoder.validate_encoding(context, encoded_constraints)

        assert "is_valid" in validation
        assert "errors" in validation
        assert "warnings" in validation
        assert "metrics" in validation
        mock_logger.info.assert_called()

    def test_get_constraint_statistics(self):
        """Test getting constraint statistics"""
        encoder = ConstraintEncoder()
        encoded_constraints = [Mock(), Mock(), Mock()]

        stats = encoder.get_constraint_statistics(encoded_constraints)

        assert stats["total_constraints"] == 3
        assert "encoding_timestamp" in stats
        assert "constraint_types_encoded" in stats


if __name__ == "__main__":
    pytest.main([__file__])
