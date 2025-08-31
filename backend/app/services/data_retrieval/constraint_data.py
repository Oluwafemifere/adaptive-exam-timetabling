# backend/app/services/data_retrieval/constraint_data.py

"""
Service for retrieving constraint data from the database
"""

from typing import Dict, List, cast, Any
from uuid import UUID
from datetime import datetime as ddatetime
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.constraints import (
    ConstraintCategory,
    ConstraintRule,
    ConfigurationConstraint,
)


class ConstraintData:
    """Service for retrieving constraint-related data"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _convert_numeric_to_float(self, value: Any) -> float:
        """Convert SQLAlchemy Numeric type to float"""
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    # Constraint Categories
    async def get_all_constraint_categories(self) -> List[Dict]:
        """Get all constraint categories with their rules"""
        stmt = (
            select(ConstraintCategory)
            .options(selectinload(ConstraintCategory.rules))
            .order_by(ConstraintCategory.name)
        )
        result = await self.session.execute(stmt)
        categories = result.scalars().all()

        return [
            {
                "id": str(category.id),
                "name": category.name,
                "description": category.description,
                "enforcement_layer": category.enforcement_layer,
                "rule_count": len(category.rules),
                "active_rule_count": len([r for r in category.rules if r.is_active]),
                "created_at": (
                    cast(ddatetime, category.created_at).isoformat()
                    if category.created_at
                    else None
                ),
                "updated_at": (
                    cast(ddatetime, category.updated_at).isoformat()
                    if category.updated_at
                    else None
                ),
            }
            for category in categories
        ]

    async def get_constraint_category_by_id(self, category_id: UUID) -> Dict | None:
        """Get constraint category by ID with rules"""
        stmt = (
            select(ConstraintCategory)
            .options(selectinload(ConstraintCategory.rules))
            .where(ConstraintCategory.id == category_id)
        )
        result = await self.session.execute(stmt)
        category = result.scalar_one_or_none()

        if not category:
            return None

        return {
            "id": str(category.id),
            "name": category.name,
            "description": category.description,
            "enforcement_layer": category.enforcement_layer,
            "rules": [
                {
                    "id": str(rule.id),
                    "code": rule.code,
                    "name": rule.name,
                    "constraint_type": rule.constraint_type,
                    "default_weight": self._convert_numeric_to_float(
                        rule.default_weight
                    ),
                    "is_active": rule.is_active,
                    "is_configurable": rule.is_configurable,
                }
                for rule in category.rules
            ],
            "created_at": (
                cast(ddatetime, category.created_at).isoformat()
                if category.created_at
                else None
            ),
            "updated_at": (
                cast(ddatetime, category.updated_at).isoformat()
                if category.updated_at
                else None
            ),
        }

    # Constraint Rules
    async def get_all_constraint_rules(self) -> List[Dict]:
        """Get all constraint rules with category information"""
        stmt = (
            select(ConstraintRule)
            .options(selectinload(ConstraintRule.category))
            .order_by(ConstraintRule.code)
        )
        result = await self.session.execute(stmt)
        rules = result.scalars().all()

        return [
            {
                "id": str(rule.id),
                "code": rule.code,
                "name": rule.name,
                "description": rule.description,
                "constraint_type": rule.constraint_type,
                "constraint_definition": rule.constraint_definition,
                "category_id": str(rule.category_id),
                "category_name": rule.category.name if rule.category else None,
                "default_weight": self._convert_numeric_to_float(rule.default_weight),
                "is_active": rule.is_active,
                "is_configurable": rule.is_configurable,
                "created_at": (
                    cast(ddatetime, rule.created_at).isoformat()
                    if rule.created_at
                    else None
                ),
                "updated_at": (
                    cast(ddatetime, rule.updated_at).isoformat()
                    if rule.updated_at
                    else None
                ),
            }
            for rule in rules
        ]

    async def get_active_constraint_rules(self) -> List[Dict]:
        """Get only active constraint rules"""
        stmt = (
            select(ConstraintRule)
            .options(selectinload(ConstraintRule.category))
            .where(ConstraintRule.is_active)
            .order_by(ConstraintRule.code)
        )
        result = await self.session.execute(stmt)
        rules = result.scalars().all()

        return [
            {
                "id": str(rule.id),
                "code": rule.code,
                "name": rule.name,
                "description": rule.description,
                "constraint_type": rule.constraint_type,
                "constraint_definition": rule.constraint_definition,
                "category_name": rule.category.name if rule.category else None,
                "default_weight": self._convert_numeric_to_float(rule.default_weight),
                "is_configurable": rule.is_configurable,
            }
            for rule in rules
        ]

    async def get_constraint_rule_by_id(self, rule_id: UUID) -> Dict | None:
        """Get constraint rule by ID with complete information"""
        stmt = (
            select(ConstraintRule)
            .options(
                selectinload(ConstraintRule.category),
                selectinload(ConstraintRule.configurations),
            )
            .where(ConstraintRule.id == rule_id)
        )
        result = await self.session.execute(stmt)
        rule = result.scalar_one_or_none()

        if not rule:
            return None

        return {
            "id": str(rule.id),
            "code": rule.code,
            "name": rule.name,
            "description": rule.description,
            "constraint_type": rule.constraint_type,
            "constraint_definition": rule.constraint_definition,
            "category": (
                {
                    "id": str(rule.category.id),
                    "name": rule.category.name,
                    "description": rule.category.description,
                    "enforcement_layer": rule.category.enforcement_layer,
                }
                if rule.category
                else None
            ),
            "default_weight": self._convert_numeric_to_float(rule.default_weight),
            "is_active": rule.is_active,
            "is_configurable": rule.is_configurable,
            "configuration_count": len(rule.configurations),
            "created_at": (
                cast(ddatetime, rule.created_at).isoformat()
                if rule.created_at
                else None
            ),
            "updated_at": (
                cast(ddatetime, rule.updated_at).isoformat()
                if rule.updated_at
                else None
            ),
        }

    async def get_constraint_rule_by_code(self, code: str) -> Dict | None:
        """Get constraint rule by code"""
        stmt = (
            select(ConstraintRule)
            .options(selectinload(ConstraintRule.category))
            .where(ConstraintRule.code == code)
        )
        result = await self.session.execute(stmt)
        rule = result.scalar_one_or_none()

        if not rule:
            return None

        return {
            "id": str(rule.id),
            "code": rule.code,
            "name": rule.name,
            "description": rule.description,
            "constraint_type": rule.constraint_type,
            "constraint_definition": rule.constraint_definition,
            "category_name": rule.category.name if rule.category else None,
            "default_weight": self._convert_numeric_to_float(rule.default_weight),
            "is_active": rule.is_active,
            "is_configurable": rule.is_configurable,
        }

    async def get_rules_by_category(self, category_id: UUID) -> List[Dict]:
        """Get constraint rules by category"""
        stmt = (
            select(ConstraintRule)
            .where(ConstraintRule.category_id == category_id)
            .order_by(ConstraintRule.code)
        )
        result = await self.session.execute(stmt)
        rules = result.scalars().all()

        return [
            {
                "id": str(rule.id),
                "code": rule.code,
                "name": rule.name,
                "description": rule.description,
                "constraint_type": rule.constraint_type,
                "default_weight": self._convert_numeric_to_float(rule.default_weight),
                "is_active": rule.is_active,
                "is_configurable": rule.is_configurable,
            }
            for rule in rules
        ]

    async def get_rules_by_type(self, constraint_type: str) -> List[Dict]:
        """Get constraint rules by type"""
        stmt = (
            select(ConstraintRule)
            .options(selectinload(ConstraintRule.category))
            .where(ConstraintRule.constraint_type == constraint_type)
            .order_by(ConstraintRule.code)
        )
        result = await self.session.execute(stmt)
        rules = result.scalars().all()

        return [
            {
                "id": str(rule.id),
                "code": rule.code,
                "name": rule.name,
                "description": rule.description,
                "constraint_definition": rule.constraint_definition,
                "category_name": rule.category.name if rule.category else None,
                "default_weight": self._convert_numeric_to_float(rule.default_weight),
                "is_active": rule.is_active,
                "is_configurable": rule.is_configurable,
            }
            for rule in rules
        ]

    # Configuration Constraints
    async def get_configuration_constraints(
        self, configuration_id: UUID | None = None
    ) -> List[Dict]:
        """Get configuration constraints with filters"""
        stmt = select(ConfigurationConstraint).options(
            selectinload(ConfigurationConstraint.rule).selectinload(
                ConstraintRule.category
            ),
            selectinload(ConfigurationConstraint.configuration),
        )

        if configuration_id:
            stmt = stmt.where(
                ConfigurationConstraint.configuration_id == configuration_id
            )

        result = await self.session.execute(stmt)
        config_constraints = result.scalars().all()

        return [
            {
                "id": str(config_constraint.id),
                "configuration_id": str(config_constraint.configuration_id),
                "configuration_name": (
                    config_constraint.configuration.name
                    if config_constraint.configuration
                    else None
                ),
                "constraint_id": str(config_constraint.constraint_id),
                "constraint_code": (
                    config_constraint.rule.code if config_constraint.rule else None
                ),
                "constraint_name": (
                    config_constraint.rule.name if config_constraint.rule else None
                ),
                "constraint_type": (
                    config_constraint.rule.constraint_type
                    if config_constraint.rule
                    else None
                ),
                "category_name": (
                    config_constraint.rule.category.name
                    if config_constraint.rule and config_constraint.rule.category
                    else None
                ),
                "custom_parameters": config_constraint.custom_parameters,
                "weight": self._convert_numeric_to_float(config_constraint.weight),
                "is_enabled": config_constraint.is_enabled,
            }
            for config_constraint in config_constraints
        ]

    async def get_configuration_constraint_by_id(
        self, config_constraint_id: UUID
    ) -> Dict | None:
        """Get configuration constraint by ID"""
        stmt = (
            select(ConfigurationConstraint)
            .options(
                selectinload(ConfigurationConstraint.rule).selectinload(
                    ConstraintRule.category
                ),
                selectinload(ConfigurationConstraint.configuration),
            )
            .where(ConfigurationConstraint.id == config_constraint_id)
        )
        result = await self.session.execute(stmt)
        config_constraint = result.scalar_one_or_none()

        if not config_constraint:
            return None

        return {
            "id": str(config_constraint.id),
            "configuration_id": str(config_constraint.configuration_id),
            "configuration_name": (
                config_constraint.configuration.name
                if config_constraint.configuration
                else None
            ),
            "constraint_id": str(config_constraint.constraint_id),
            "constraint": (
                {
                    "id": str(config_constraint.rule.id),
                    "code": config_constraint.rule.code,
                    "name": config_constraint.rule.name,
                    "description": config_constraint.rule.description,
                    "constraint_type": config_constraint.rule.constraint_type,
                    "constraint_definition": config_constraint.rule.constraint_definition,
                    "default_weight": self._convert_numeric_to_float(
                        config_constraint.rule.default_weight
                    ),
                    "category": (
                        {
                            "id": str(config_constraint.rule.category.id),
                            "name": config_constraint.rule.category.name,
                        }
                        if config_constraint.rule.category
                        else None
                    ),
                }
                if config_constraint.rule
                else None
            ),
            "custom_parameters": config_constraint.custom_parameters,
            "weight": self._convert_numeric_to_float(config_constraint.weight),
            "is_enabled": config_constraint.is_enabled,
        }

    # Statistics and analysis
    async def get_constraint_statistics(self) -> Dict:
        """Get constraint statistics"""
        # Total rules by category
        category_stmt = (
            select(
                ConstraintCategory.name,
                func.count(ConstraintRule.id).label("rule_count"),
                func.count(func.nullif(ConstraintRule.is_active, False)).label(
                    "active_rules"
                ),
            )
            .outerjoin(
                ConstraintRule, ConstraintRule.category_id == ConstraintCategory.id
            )
            .group_by(ConstraintCategory.id, ConstraintCategory.name)
            .order_by(ConstraintCategory.name)
        )

        category_result = await self.session.execute(category_stmt)
        category_stats = [
            {
                "category_name": row.name,
                "total_rules": row.rule_count or 0,
                "active_rules": row.active_rules or 0,
            }
            for row in category_result
        ]

        # Rules by type
        type_stmt = select(
            ConstraintRule.constraint_type, func.count(ConstraintRule.id).label("count")
        ).group_by(ConstraintRule.constraint_type)

        type_result = await self.session.execute(type_stmt)
        type_stats = {row.constraint_type: row.count for row in type_result}

        # Configuration usage
        config_stmt = select(func.count(ConfigurationConstraint.id))
        config_result = await self.session.execute(config_stmt)
        total_configurations = config_result.scalar()

        return {
            "category_breakdown": category_stats,
            "type_breakdown": type_stats,
            "total_configuration_constraints": total_configurations,
        }

    async def search_constraint_rules(self, search_term: str) -> List[Dict]:
        """Search constraint rules by name, code, or description"""
        search_pattern = f"%{search_term}%"

        stmt = (
            select(ConstraintRule)
            .options(selectinload(ConstraintRule.category))
            .where(
                or_(
                    ConstraintRule.code.ilike(search_pattern),
                    ConstraintRule.name.ilike(search_pattern),
                    ConstraintRule.description.ilike(search_pattern),
                )
            )
            .order_by(ConstraintRule.code)
        )
        result = await self.session.execute(stmt)
        rules = result.scalars().all()

        return [
            {
                "id": str(rule.id),
                "code": rule.code,
                "name": rule.name,
                "description": rule.description,
                "constraint_type": rule.constraint_type,
                "category_name": rule.category.name if rule.category else None,
                "default_weight": self._convert_numeric_to_float(rule.default_weight),
                "is_active": rule.is_active,
                "is_configurable": rule.is_configurable,
            }
            for rule in rules
        ]

    async def get_configurable_rules(self) -> List[Dict]:
        """Get only configurable constraint rules"""
        stmt = (
            select(ConstraintRule)
            .options(selectinload(ConstraintRule.category))
            .where(
                and_(
                    ConstraintRule.is_active,
                    ConstraintRule.is_configurable,
                )
            )
            .order_by(ConstraintRule.code)
        )
        result = await self.session.execute(stmt)
        rules = result.scalars().all()

        return [
            {
                "id": str(rule.id),
                "code": rule.code,
                "name": rule.name,
                "description": rule.description,
                "constraint_type": rule.constraint_type,
                "constraint_definition": rule.constraint_definition,
                "category_name": rule.category.name if rule.category else None,
                "default_weight": self._convert_numeric_to_float(rule.default_weight),
            }
            for rule in rules
        ]
