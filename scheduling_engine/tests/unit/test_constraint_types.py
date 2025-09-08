# scheduling_engine/tests/unit/test_constraint_types.py

"""
Tests for constraint type definitions and enumerations.
"""

import pytest
from uuid import UUID, uuid4
from datetime import datetime

from scheduling_engine.core.constraint_types import (
    ConstraintType,
    ConstraintCategory,
    ConstraintSeverity,
    ConstraintViolation,
    ConstraintDefinition,
)


class TestConstraintEnums:
    """Tests for constraint enumerations"""

    def test_constraint_type_enum(self):
        """Test ConstraintType enum values"""
        assert ConstraintType.HARD.value == "hard"
        assert ConstraintType.SOFT.value == "soft"

        # Test membership
        assert ConstraintType.HARD in ConstraintType
        assert ConstraintType.SOFT in ConstraintType
        assert "invalid" not in ConstraintType

    def test_constraint_category_enum(self):
        """Test ConstraintCategory enum values"""
        categories = [
            ConstraintCategory.STUDENT_CONSTRAINTS,
            ConstraintCategory.RESOURCE_CONSTRAINTS,
            ConstraintCategory.TEMPORAL_CONSTRAINTS,
            ConstraintCategory.ACADEMIC_POLICIES,
            ConstraintCategory.OPTIMIZATION_CONSTRAINTS,
            ConstraintCategory.CONVENIENCE_CONSTRAINTS,
            ConstraintCategory.WORKLOAD_BALANCE,
        ]

        for category in categories:
            assert isinstance(category.value, str)
            assert len(category.value) > 0

        # Test specific values
        assert ConstraintCategory.STUDENT_CONSTRAINTS.value == "student_constraints"

    def test_constraint_severity_enum(self):
        """Test ConstraintSeverity enum values"""
        severities = [
            ConstraintSeverity.CRITICAL,
            ConstraintSeverity.HIGH,
            ConstraintSeverity.MEDIUM,
            ConstraintSeverity.LOW,
        ]

        for severity in severities:
            assert isinstance(severity.value, str)
            assert len(severity.value) > 0

        # Test specific values
        assert ConstraintSeverity.CRITICAL.value == "critical"


class TestConstraintViolation:
    """Tests for ConstraintViolation dataclass"""

    def test_constraint_violation_initialization(self):
        """Test ConstraintViolation initialization"""
        constraint_id = uuid4()
        violation_id = uuid4()
        exam_id = uuid4()
        resource_id = uuid4()

        violation = ConstraintViolation(
            constraint_id=constraint_id,
            violation_id=violation_id,
            severity=ConstraintSeverity.HIGH,
            affected_exams=[exam_id],
            affected_resources=[resource_id],
            description="Test violation",
            penalty=10.0,
            suggestions=["Fix this"],
            constraint_code="TEST_VIOLATION",
            database_rule_id=uuid4(),
            violation_metadata={"key": "value"},
        )

        assert violation.constraint_id == constraint_id
        assert violation.violation_id == violation_id
        assert violation.severity == ConstraintSeverity.HIGH
        assert violation.affected_exams == [exam_id]
        assert violation.affected_resources == [resource_id]
        assert violation.description == "Test violation"
        assert violation.penalty == 10.0
        assert violation.suggestions == ["Fix this"]
        assert violation.constraint_code == "TEST_VIOLATION"
        assert isinstance(violation.database_rule_id, UUID)
        assert violation.violation_metadata == {"key": "value"}

    def test_constraint_violation_default_values(self):
        """Test ConstraintViolation with default values"""
        violation = ConstraintViolation(
            constraint_id=uuid4(),
            violation_id=uuid4(),
            severity=ConstraintSeverity.MEDIUM,
            affected_exams=[],
            affected_resources=[],
            description="",
            penalty=0.0,
        )

        assert violation.suggestions == []
        assert violation.constraint_code is None
        assert violation.database_rule_id is None
        assert violation.violation_metadata == {}


class TestConstraintDefinition:
    """Tests for ConstraintDefinition dataclass"""

    def test_constraint_definition_initialization(self):
        """Test ConstraintDefinition initialization"""
        constraint_id = "TEST_CONSTRAINT"
        created_at = datetime.now()
        updated_at = datetime.now()

        definition = ConstraintDefinition(
            constraint_id=constraint_id,
            name="Test Constraint",
            description="A test constraint definition",
            constraint_type=ConstraintType.HARD,
            category=ConstraintCategory.STUDENT_CONSTRAINTS,
            parameters={"param1": "value1"},
            validation_rules=["rule1", "rule2"],
            constraint_class=None,  # Would be a class in real usage
            database_rule_id=uuid4(),
            is_database_loaded=True,
            default_weight=1.5,
            is_configurable=True,
            created_at=created_at,
            updated_at=updated_at,
        )

        assert definition.constraint_id == constraint_id
        assert definition.name == "Test Constraint"
        assert definition.description == "A test constraint definition"
        assert definition.constraint_type == ConstraintType.HARD
        assert definition.category == ConstraintCategory.STUDENT_CONSTRAINTS
        assert definition.parameters == {"param1": "value1"}
        assert definition.validation_rules == ["rule1", "rule2"]
        assert definition.constraint_class is None
        assert isinstance(definition.database_rule_id, UUID)
        assert definition.is_database_loaded is True
        assert definition.default_weight == 1.5
        assert definition.is_configurable is True
        assert definition.created_at == created_at
        assert definition.updated_at == updated_at

    def test_constraint_definition_default_values(self):
        """Test ConstraintDefinition with default values"""
        definition = ConstraintDefinition(
            constraint_id="TEST_CONSTRAINT",
            name="Test Constraint",
            description="A test constraint",
            constraint_type=ConstraintType.SOFT,
            category=ConstraintCategory.OPTIMIZATION_CONSTRAINTS,
        )

        assert definition.parameters == {}
        assert definition.validation_rules == []
        assert definition.constraint_class is None
        assert definition.database_rule_id is None
        assert definition.is_database_loaded is False
        assert definition.default_weight == 1.0
        assert definition.is_configurable is True
        assert definition.created_at is None
        assert definition.updated_at is None


if __name__ == "__main__":
    pytest.main([__file__])
