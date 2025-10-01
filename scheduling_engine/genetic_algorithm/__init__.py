# scheduling_engine/genetic_algorithm/__init__.py
"""
Initializes the GA pre-filtering module.

This module provides a lightweight, DEAP-based genetic algorithm designed to
pre-process and prune the variable search space for the main CP-SAT solver.
Its primary goal is to quickly identify a promising subset of variable assignments,
thereby reducing the complexity of the constraint programming model.

Key components:
- GAProcessor: The main orchestrator for running the GA.
- ga_model: Defines the core DEAP structures, fitness functions, and genetic operators.
"""

from .ga_processor import GAProcessor, GAInput, GAResult

__all__ = ["GAProcessor", "GAInput", "GAResult"]
