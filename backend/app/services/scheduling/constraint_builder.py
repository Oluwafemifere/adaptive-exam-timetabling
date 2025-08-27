#C:\Users\fresh\OneDrive\Dokumen\thesis\proj\CODE\adaptive-exam-timetabling\backend\app\services\scheduling\constraint_builder.py
from sqlalchemy import select
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.constraints import ConstraintRule


class ConstraintBuilder:
    """Builds in-memory constraint model from database rules."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_constraints(self, problem_data: Dict[str, Any], configuration_id: str) -> Dict[str, Any]:
        """
        Load active constraint rules for the given configuration and merge with problem_data.
        Returns a dict with 'constraints' and original problem_data.
        """
        # Query enabled constraints for this configuration
        rows = await self.db.execute(
            select(ConstraintRule)
            .join(ConstraintRule.category)
            .where(ConstraintRule.is_active)
        )
        rules = rows.scalars().all()
        constraints: List[Dict[str, Any]] = []
        for rule in rules:
            constraints.append({
                'code': rule.code,
                'definition': rule.constraint_definition,
                'weight': rule.default_weight
            })
        return {
            'problem': problem_data,
            'constraints': constraints
        }
