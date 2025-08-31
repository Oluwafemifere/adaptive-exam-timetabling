# backend/Scripts/seeders/__init__.py
"""
Database Seeders Package

This package contains refactored database seeding scripts for the Baze University
Adaptive Exam Timetabling System.

Modules:
- fake_seed: Generates large amounts of realistic fake data using Faker
- seed_data: Handles structured data seeding and CSV imports with validation

Both seeders work with Alembic migrations and integrate with the backend app structure.
"""

from .fake_seed import ComprehensiveFakeSeeder
from .seed_data import EnhancedDatabaseSeeder

__all__ = ["ComprehensiveFakeSeeder", "EnhancedDatabaseSeeder"]

# Version information
__version__ = "2.0.0"
__author__ = "Baze University Development Team"
__description__ = "Enhanced database seeders with Alembic integration"
