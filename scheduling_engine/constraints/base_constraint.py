# scheduling_engine/constraints/base_constraint.py

"""
BASE CONSTRAINT ENHANCEMENT - for dynamic, parameterized constraints.
Each constraint instance is now initialized with its full definition,
giving it access to runtime parameters, weights, and scope.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from ortools.sat.python import cp_model
from uuid import UUID

from scheduling_engine.core.constraint_types import ConstraintDefinition

logger = logging.getLogger(__name__)


class CPSATBaseConstraint(ABC):
    """Base class for dynamically configured CP-SAT constraints."""

    def __init__(
        self,
        definition: ConstraintDefinition,
        problem,
        shared_vars: Any,
        model: cp_model.CpModel,
    ):
        """Initialize with a full ConstraintDefinition object."""
        self.definition = definition
        self.problem = problem
        self.model = model
        self.penalty_terms = []
        self.constraint_id = self.definition.id
        self.constraint_category = self.definition.category.name

        self.constraint_count = 0

        # Unpack shared variables for easier access
        self.x = shared_vars.x_vars
        self.y = shared_vars.y_vars
        self.z = shared_vars.z_vars
        # --- NEW: Simplified invigilator assignment model ---
        self.w = shared_vars.w_vars
        # --- Deprecated ---
        # self.t = shared_vars.t_vars
        # self.a = shared_vars.a_vars
        # self.u = shared_vars.u_vars
        self.precomputed_data = shared_vars.precomputed_data

        # Precompute entity lookups
        self._exams = getattr(problem, "exams", {})
        self._timeslots = getattr(problem, "timeslots", {})
        self._rooms = getattr(problem, "rooms", {})

        logger.debug(
            f"Initialized constraint '{self.constraint_id}' with dynamic definition."
        )

    def get_parameter_value(self, key: str, default: Any = None) -> Any:
        """Helper to safely retrieve a parameter's value from the definition."""
        return self.definition.get_parameter_value(key, default)

    @abstractmethod
    def initialize_variables(self):
        """Hook for creating constraint-specific variables."""
        pass

    def get_penalty_terms(self) -> list[tuple[float, cp_model.IntVar]]:
        """Returns the penalty terms collected by this constraint."""
        return self.penalty_terms

    @abstractmethod
    def add_constraints(self):
        """Main method to add the constraint's logic to the CP-SAT model."""
        pass

    def get_statistics(self) -> Dict[str, Any]:
        """Return statistics about the constraint's execution."""
        return {
            "constraint_id": self.constraint_id,
            "constraint_count": self.constraint_count,
            "category": self.constraint_category,
            "config_id": (
                str(self.definition.config_id) if self.definition.config_id else None
            ),
            "weight": self.definition.weight,
        }
