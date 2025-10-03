# scheduling_engine/constraints/__init__.py

"""
This package contains the implementations for various scheduling constraints.

Constraints are dynamically loaded and managed by the ConstraintRegistry and
CPSATConstraintManager based on the configuration provided to the ExamSchedulingProblem.
"""

from .hard_constraints import *

# Soft constraints would be imported here as well, e.g.:
# from .soft_constraints import *
