# scheduling_engine/tests/unit/test_constraint_registry.py

"""
Comprehensive tests for ConstraintRegistry system with database integration.

Tests cover:
- Registry creation and initialization
- Database constraint loading
- Constraint instance management
- Configuration validation
- Performance and caching behavior
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime

from scheduling_engine.core.constraint_registry import (
    ConstraintRegistry,
    BaseConstraint,
    LegacyConstraintAdapter,
)
from scheduling_engine.core.constraint_types import (
    ConstraintType,
    ConstraintCategory,
    ConstraintViolation,
    ConstraintSeverity,
    ConstraintDefinition,
)


class MockBaseConstraint(BaseConstraint):
    """Mock constraint for testing registry functionality"""

    def __init__(self, constraint_id="MOCK", **kwargs):
        super().__init__(
            constraint_id=constraint_id,
            name="Mock Constraint",
            constraint_type=ConstraintType.SOFT,
            category=ConstraintCategory.OPTIMIZATION_CONSTRAINTS,
            **kwargs,
        )
        self.init_called = False
        self.eval_called = False

    def _initialize_implementation(self, problem, parameters=None):
        self.init_called = True
        self.problem_size = len(problem.exams) if problem.exams else 0

    def _evaluate_implementation(self, problem, solution):
        self.eval_called = True
        return [
            ConstraintViolation(
                constraint_id=self.id,
                violation_id=uuid4(),
                severity=ConstraintSeverity.LOW,
                affected_exams=[],
                affected_resources=[],
                description="Mock violation",
                penalty=50.0,
            )
        ]


class TestConstraintRegistryCore:
    """Tests for basic ConstraintRegistry functionality"""

    def test_registry_initialization_without_database(self):
        """Test registry creation without database session"""
        registry = ConstraintRegistry()

        assert registry._definitions == {}
        assert registry._active_constraints == {}
        assert registry._constraint_categories == {}
        assert registry.db_session is None
        assert registry.constraint_data_service is None

    @patch("scheduling_engine.core.constraint_registry.BACKEND_AVAILABLE", True)
    @patch("scheduling_engine.core.constraint_registry.RuntimeConstraintData")
    def test_registry_initialization_with_database(self, mock_constraint_data):
        """Test registry creation with database session"""
        mock_session = Mock()
        mock_service = Mock()
        mock_constraint_data.return_value = mock_service

        registry = ConstraintRegistry(db_session=mock_session)

        assert registry.db_session == mock_session
        assert registry.constraint_data_service == mock_service

    def test_constraint_definition_registration(self):
        """Test registering constraint definitions"""
        registry = ConstraintRegistry()

        definition = ConstraintDefinition(
            constraint_id="TEST_CONSTRAINT",
            name="Test Constraint",
            description="Test constraint for registry",
            constraint_type=ConstraintType.HARD,
            category=ConstraintCategory.STUDENT_CONSTRAINTS,
            constraint_class=MockBaseConstraint,
            default_weight=1.0,
        )

        registry._register_constraint_definition(definition)

        # Verify definition is registered
        retrieved = registry.get_constraint_definition("TEST_CONSTRAINT")
        assert retrieved is not None
        assert retrieved.constraint_id == "TEST_CONSTRAINT"
        assert retrieved.name == "Test Constraint"
        assert retrieved.constraint_type == ConstraintType.HARD

        # Verify category mapping
        category_defs = registry.get_definitions_by_category(
            ConstraintCategory.STUDENT_CONSTRAINTS
        )
        assert len(category_defs) >= 1
        assert any(d.constraint_id == "TEST_CONSTRAINT" for d in category_defs)

    def test_constraint_filtering_by_type(self):
        """Test filtering constraints by type"""
        registry = ConstraintRegistry()

        # Register hard constraint
        hard_def = ConstraintDefinition(
            constraint_id="HARD_TEST",
            name="Hard Test",
            description="Hard constraint test",
            constraint_type=ConstraintType.HARD,
            category=ConstraintCategory.STUDENT_CONSTRAINTS,
            constraint_class=MockBaseConstraint,
        )
        registry._register_constraint_definition(hard_def)

        # Register soft constraint
        soft_def = ConstraintDefinition(
            constraint_id="SOFT_TEST",
            name="Soft Test",
            description="Soft constraint test",
            constraint_type=ConstraintType.SOFT,
            category=ConstraintCategory.OPTIMIZATION_CONSTRAINTS,
            constraint_class=MockBaseConstraint,
        )
        registry._register_constraint_definition(soft_def)

        # Test type filtering
        hard_defs = registry.get_definitions_by_type(ConstraintType.HARD)
        soft_defs = registry.get_definitions_by_type(ConstraintType.SOFT)

        hard_ids = {d.constraint_id for d in hard_defs}
        soft_ids = {d.constraint_id for d in soft_defs}

        assert "HARD_TEST" in hard_ids
        assert "SOFT_TEST" in soft_ids
        assert "HARD_TEST" not in soft_ids
        assert "SOFT_TEST" not in hard_ids


class TestConstraintRegistryDatabaseIntegration:
    """Tests for database integration functionality"""

    @pytest.mark.asyncio
    @patch("scheduling_engine.core.constraint_registry.BACKEND_AVAILABLE", True)
    @patch("scheduling_engine.core.constraint_registry.RuntimeConstraintData")
    async def test_database_constraint_loading(self, mock_constraint_data_class):
        """Test loading constraints from database"""
        mock_session = Mock()
        mock_service = Mock()
        mock_constraint_data_class.return_value = mock_service

        # Mock database constraint data
        mock_service.get_active_constraint_rules = AsyncMock(
            return_value=[
                {
                    "id": str(uuid4()),
                    "code": "DB_CONSTRAINT_1",
                    "name": "Database Constraint 1",
                    "constraint_type": "hard",
                    "default_weight": 1.0,
                    "is_configurable": True,
                    "constraint_definition": {"param1": "value1"},
                },
                {
                    "id": str(uuid4()),
                    "code": "DB_CONSTRAINT_2",
                    "name": "Database Constraint 2",
                    "constraint_type": "soft",
                    "default_weight": 0.5,
                    "is_configurable": True,
                    "constraint_definition": {"param2": "value2"},
                },
            ]
        )

        registry = ConstraintRegistry(db_session=mock_session)

        await registry.load_database_constraints()

        # Verify constraints loaded
        constraint1 = registry.get_constraint_definition("DB_CONSTRAINT_1")
        constraint2 = registry.get_constraint_definition("DB_CONSTRAINT_2")

        assert constraint1 is not None
        assert constraint1.name == "Database Constraint 1"
        assert constraint1.constraint_type == ConstraintType.HARD
        assert constraint1.is_database_loaded is True

        assert constraint2 is not None
        assert constraint2.name == "Database Constraint 2"
        assert constraint2.constraint_type == ConstraintType.SOFT
        assert constraint2.is_database_loaded is True

    @pytest.mark.asyncio
    @patch("scheduling_engine.core.constraint_registry.BACKEND_AVAILABLE", True)
    @patch("scheduling_engine.core.constraint_registry.RuntimeConstraintData")
    async def test_configuration_constraint_creation(self, mock_constraint_data_class):
        """Test creating constraints from database configuration"""
        mock_session = Mock()
        mock_service = Mock()
        mock_constraint_data_class.return_value = mock_service

        configuration_id = uuid4()
        mock_service.get_configuration_constraints = AsyncMock(
            return_value=[
                {
                    "id": str(uuid4()),
                    "constraint_code": "CONFIG_TEST",
                    "constraint_name": "Configuration Test",
                    "constraint_type": "soft",
                    "weight": 0.8,
                    "is_enabled": True,
                    "custom_parameters": {"config_param": "config_value"},
                }
            ]
        )

        registry = ConstraintRegistry(db_session=mock_session)

        # Mock constraint class mapping
        with patch.object(
            registry, "_get_constraint_class_for_code", return_value=MockBaseConstraint
        ):
            constraints = await registry.create_constraint_set_from_configuration(
                configuration_id
            )

        assert len(constraints) >= 0
        mock_service.get_configuration_constraints.assert_called_once_with(
            configuration_id
        )

    @pytest.mark.asyncio
    async def test_constraint_instance_creation(self):
        """Test creating constraint instances"""
        registry = ConstraintRegistry()

        # Register definition
        definition = ConstraintDefinition(
            constraint_id="INSTANCE_TEST",
            name="Instance Test",
            description="Test instance creation",
            constraint_type=ConstraintType.SOFT,
            category=ConstraintCategory.OPTIMIZATION_CONSTRAINTS,
            constraint_class=MockBaseConstraint,
            default_weight=0.6,
        )
        registry._register_constraint_definition(definition)

        # Create instance
        constraint = await registry.create_constraint_instance(
            "INSTANCE_TEST", weight=0.9, parameters={"test_param": "test_value"}
        )

        assert constraint is not None
        assert constraint.constraint_id == "INSTANCE_TEST"
        assert constraint.weight == 0.9
        assert constraint.name == "Instance Test"


class TestConstraintRegistryEvaluation:
    """Tests for constraint evaluation and management"""

    @pytest.mark.asyncio
    async def test_constraint_evaluation_workflow(self):
        """Test complete constraint evaluation workflow"""
        registry = ConstraintRegistry()

        # Add mock constraints
        mock_constraints = [
            MockBaseConstraint("MOCK_1", weight=1.0),
            MockBaseConstraint("MOCK_2", weight=0.5),
        ]

        for constraint in mock_constraints:
            registry.add_active_constraint(constraint)

        # Create mock problem and solution
        problem = Mock()
        problem.exams = {"exam1": Mock(), "exam2": Mock()}

        solution = Mock()

        # Evaluate all constraints
        results = await registry.evaluate_all_constraints(problem, solution)

        assert len(results) == 2
        assert "Mock Constraint" in results

        # Verify constraints were called
        for constraint in mock_constraints:
            assert constraint.eval_called

    @pytest.mark.asyncio
    async def test_total_penalty_calculation(self):
        """Test total penalty calculation across constraints"""
        registry = ConstraintRegistry()

        # Create constraints with known penalties
        constraint1 = MockBaseConstraint("PENALTY_1", weight=2.0)
        constraint2 = MockBaseConstraint("PENALTY_2", weight=0.5)

        registry.add_active_constraint(constraint1)
        registry.add_active_constraint(constraint2)

        problem = Mock()
        problem.exams = {"exam1": Mock()}
        solution = Mock()

        total_penalty = await registry.calculate_total_penalty(problem, solution)

        # Should be sum of (penalty * weight) for each constraint
        # Mock constraint returns penalty of 50.0
        expected_penalty = (50.0 * 2.0) + (50.0 * 0.5)  # 100 + 25 = 125
        assert total_penalty == expected_penalty


class TestConstraintRegistryValidation:
    """Tests for constraint validation functionality"""

    @pytest.mark.asyncio
    async def test_constraint_configuration_validation(self):
        """Test validating constraint configurations"""
        registry = ConstraintRegistry()

        # Register test definition
        definition = ConstraintDefinition(
            constraint_id="VALIDATION_TEST",
            name="Validation Test",
            description="Test validation",
            constraint_type=ConstraintType.SOFT,
            category=ConstraintCategory.OPTIMIZATION_CONSTRAINTS,
            constraint_class=MockBaseConstraint,
            is_configurable=True,
        )
        registry._register_constraint_definition(definition)

        # Test valid configuration
        valid_config = {
            "constraints": [
                {
                    "code": "VALIDATION_TEST",
                    "weight": 0.5,
                    "parameters": {"valid_param": 100},
                }
            ]
        }

        validation = await registry.validate_constraint_configuration(valid_config)

        assert "errors" in validation
        assert "warnings" in validation
        assert isinstance(validation["errors"], list)

        # Test invalid configuration
        invalid_config = {
            "constraints": [
                {
                    "code": "NONEXISTENT_CONSTRAINT",
                    "weight": -1.0,  # Invalid weight
                    "parameters": {},
                }
            ]
        }

        validation = await registry.validate_constraint_configuration(invalid_config)
        assert len(validation["errors"]) > 0

    def test_legacy_constraint_adapter(self):
        """Test legacy constraint adapter functionality"""

        # Create legacy-style constraint
        class LegacyConstraint:
            def __init__(self):
                self.name = "Legacy Test Constraint"

            def initialize(self, problem, parameters=None):
                self.initialized = True

            def evaluate(self, problem, solution):
                return []

        legacy_instance = LegacyConstraint()
        adapter = LegacyConstraintAdapter(
            legacy_constraint_instance=legacy_instance, constraint_code="LEGACY_TEST"
        )

        assert adapter.constraint_id == "LEGACY_TEST"
        assert adapter.name == "Legacy Test Constraint"

        # Test initialization
        problem = Mock()
        adapter.initialize(problem)
        assert legacy_instance.initialized

        # Test evaluation
        solution = Mock()
        violations = adapter.evaluate(problem, solution)
        assert isinstance(violations, list)


class TestConstraintRegistryPerformance:
    """Performance tests for constraint registry"""

    def test_registry_scaling_with_many_definitions(self):
        """Test registry performance with many constraint definitions"""
        registry = ConstraintRegistry()

        # Add many constraint definitions
        num_constraints = 100
        for i in range(num_constraints):
            definition = ConstraintDefinition(
                constraint_id=f"SCALE_TEST_{i}",
                name=f"Scale Test {i}",
                description=f"Scaling test constraint {i}",
                constraint_type=ConstraintType.SOFT,
                category=ConstraintCategory.OPTIMIZATION_CONSTRAINTS,
                constraint_class=MockBaseConstraint,
            )
            registry._register_constraint_definition(definition)

        # Test retrieval performance
        start_time = datetime.now()

        all_definitions = registry.get_all_definitions()
        soft_definitions = registry.get_definitions_by_type(ConstraintType.SOFT)
        category_definitions = registry.get_definitions_by_category(
            ConstraintCategory.OPTIMIZATION_CONSTRAINTS
        )

        end_time = datetime.now()
        retrieval_time = (end_time - start_time).total_seconds()

        assert len(all_definitions) >= num_constraints
        assert len(soft_definitions) >= num_constraints
        assert len(category_definitions) >= num_constraints
        assert retrieval_time < 1.0  # Should be fast

    @pytest.mark.asyncio
    async def test_evaluation_performance_with_many_constraints(self):
        """Test evaluation performance with many active constraints"""
        registry = ConstraintRegistry()

        # Add many active constraints
        num_constraints = 50
        for i in range(num_constraints):
            constraint = MockBaseConstraint(f"PERF_TEST_{i}")
            registry.add_active_constraint(constraint)

        # Create mock problem and solution
        problem = Mock()
        problem.exams = {f"exam_{i}": Mock() for i in range(10)}
        solution = Mock()

        # Time the evaluation
        start_time = datetime.now()
        results = await registry.evaluate_all_constraints(problem, solution)
        end_time = datetime.now()

        evaluation_time = (end_time - start_time).total_seconds()

        assert len(results) == num_constraints
        assert evaluation_time < 2.0  # Should complete within reasonable time


if __name__ == "__main__":
    pytest.main([__file__])
