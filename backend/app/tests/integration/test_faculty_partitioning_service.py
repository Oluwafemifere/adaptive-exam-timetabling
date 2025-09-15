import pytest
from uuid import UUID
from app.services.scheduling.faculty_partitioning_service import (
    FacultyPartitioningService,
    PartitionStrategy,
)


@pytest.mark.asyncio
async def test_faculty_partitioning_initialization(test_session, complete_test_data):
    """Test service initialization with real academic data"""
    service = FacultyPartitioningService(test_session)
    session_id = complete_test_data["academic_session"].id

    await service.initialize(session_id)

    assert service.academic_structure is not None
    assert len(service.academic_structure["faculties"]) > 0
    assert service.dependency_graph.number_of_nodes() > 0


@pytest.mark.asyncio
async def test_partition_strategies(test_session, complete_test_data):
    """Test all partition strategies with real data"""
    service = FacultyPartitioningService(test_session)
    session_id = complete_test_data["academic_session"].id

    await service.initialize(session_id)

    strategies = [
        PartitionStrategy.INDEPENDENT,
        PartitionStrategy.LOOSELY_COUPLED,
        PartitionStrategy.HIERARCHICAL,
        PartitionStrategy.HYBRID,
    ]

    for strategy in strategies:
        result = await service.create_partitioning_strategy(
            session_id=session_id, strategy_type=strategy
        )

        assert result is not None
        assert len(result.partition_groups) > 0
        assert result.strategy_used == strategy


@pytest.mark.asyncio
async def test_partition_validation(test_session, complete_test_data):
    """Test partition validation with real data"""
    service = FacultyPartitioningService(test_session)
    session_id = complete_test_data["academic_session"].id

    await service.initialize(session_id)
    result = await service.create_partitioning_strategy(session_id)

    validation = await service.validate_partitioning(result.partitioning_id)

    assert validation["valid"] is True
    assert validation["coverage_percentage"] == 100.0
