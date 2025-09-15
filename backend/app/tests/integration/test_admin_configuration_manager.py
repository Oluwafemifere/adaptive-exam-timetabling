import pytest
from uuid import UUID
from app.services.scheduling.admin_configuration_manager import (
    AdminConfigurationManager,
    ConstraintConfiguration,
    ObjectiveFunction,
    ConfigurationTemplate,
)


@pytest.mark.asyncio
async def test_get_available_constraint_categories(test_session, complete_test_data):
    """Test getting available constraint categories"""
    service = AdminConfigurationManager(test_session)
    user_id = complete_test_data["user"].id

    categories = await service.get_available_constraint_categories(user_id)
    assert isinstance(categories, list)


@pytest.mark.asyncio
async def test_create_configuration(test_session, complete_test_data):
    """Test creating a configuration"""
    service = AdminConfigurationManager(test_session)
    user_id = complete_test_data["user"].id
    constraint_rule = complete_test_data["constraint_rule"]

    constraint_config = ConstraintConfiguration(
        constraint_id=constraint_rule.id,
        constraint_code=constraint_rule.code,
        constraint_name=constraint_rule.name,
        constraint_type=constraint_rule.constraint_type,
        is_enabled=True,
        weight=1.0,
    )

    result = await service.create_configuration(
        user_id=user_id,
        configuration_name="Test Config",
        configuration_description="Test Description",
        objective_function=ObjectiveFunction.MINIMIZE_CONFLICTS,
        constraint_configurations=[constraint_config],
    )

    assert "success" in result
