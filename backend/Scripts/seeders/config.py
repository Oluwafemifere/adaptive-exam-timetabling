#!/usr/bin/env python3

# backend/Scripts/seeders/config.py

"""
Configuration settings for database seeders.
Provides centralized configuration management for both fake and structured data seeding.
"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path


class SeederConfig:
    """
    Centralized configuration for database seeders.
    Supports environment variable overrides and different deployment modes.
    """

    # Default scale limits for fake data generation
    DEFAULT_SCALE_LIMITS = {
        "faculties": 8,
        "departments": 35,
        "programmes": 80,
        "buildings": 12,
        "room_types": 8,
        "rooms": 300,
        "time_slots": 15,
        "academic_sessions": 3,
        "courses": 800,
        "students": 8000,
        "course_registrations": 50000,
        "exams": 800,
        "staff": 400,
        "users": 500,
        "user_roles": 10,
        "user_role_assignments": 600,
    }

    # Development mode scale limits (smaller for faster seeding)
    DEV_SCALE_LIMITS = {
        "faculties": 4,
        "departments": 15,
        "programmes": 25,
        "buildings": 6,
        "room_types": 5,
        "rooms": 50,
        "time_slots": 10,
        "academic_sessions": 2,
        "courses": 100,
        "students": 500,
        "course_registrations": 2000,
        "exams": 100,
        "staff": 50,
        "users": 100,
        "user_roles": 8,
        "user_role_assignments": 150,
    }

    # Production mode scale limits (larger, realistic numbers)
    PROD_SCALE_LIMITS = {
        "faculties": 12,
        "departments": 60,
        "programmes": 150,
        "buildings": 20,
        "room_types": 12,
        "rooms": 500,
        "time_slots": 20,
        "academic_sessions": 5,
        "courses": 2000,
        "students": 15000,
        "course_registrations": 100000,
        "exams": 2000,
        "staff": 800,
        "users": 1000,
        "user_roles": 15,
        "user_role_assignments": 1200,
    }

    # CSV schema configurations
    CSV_SCHEMAS = {
        "academic_sessions": {
            "required_columns": ["name", "start_date", "end_date", "semester_system"],
            "optional_columns": ["is_active"],
            "column_mappings": {
                "session_name": "name",
                "start": "start_date",
                "end": "end_date",
                "active": "is_active",
            },
            "date_columns": ["start_date", "end_date"],
            "boolean_columns": ["is_active"],
        },
        "faculties": {
            "required_columns": ["name", "code"],
            "optional_columns": ["is_active"],
            "column_mappings": {
                "faculty_name": "name",
                "faculty_code": "code",
                "active": "is_active",
            },
            "uppercase_columns": ["code"],
            "boolean_columns": ["is_active"],
        },
        "departments": {
            "required_columns": ["name", "code", "faculty_code"],
            "optional_columns": ["is_active"],
            "column_mappings": {
                "department_name": "name",
                "department_code": "code",
                "parent_faculty": "faculty_code",
                "active": "is_active",
            },
            "uppercase_columns": ["code", "faculty_code"],
            "boolean_columns": ["is_active"],
        },
        "programmes": {
            "required_columns": [
                "name",
                "code",
                "department_code",
                "degree_type",
                "duration_years",
            ],
            "optional_columns": ["is_active"],
            "column_mappings": {
                "programme_name": "name",
                "programme_code": "code",
                "dept_code": "department_code",
                "type": "degree_type",
                "duration": "duration_years",
                "active": "is_active",
            },
            "uppercase_columns": ["code", "department_code"],
            "integer_columns": ["duration_years"],
            "boolean_columns": ["is_active"],
        },
        "students": {
            "required_columns": ["matric_number", "programme_code", "entry_year"],
            "optional_columns": [
                "current_level",
                "student_type",
                "special_needs",
                "is_active",
            ],
            "column_mappings": {
                "matric": "matric_number",
                "program": "programme_code",
                "level": "current_level",
                "type": "student_type",
                "needs": "special_needs",
                "active": "is_active",
            },
            "uppercase_columns": ["matric_number", "programme_code"],
            "integer_columns": ["entry_year", "current_level"],
            "array_columns": ["special_needs"],
            "boolean_columns": ["is_active"],
        },
        "courses": {
            "required_columns": ["code", "title", "credit_units", "department_code"],
            "optional_columns": [
                "course_level",
                "semester",
                "is_practical",
                "morning_only",
                "exam_duration_minutes",
                "is_active",
            ],
            "column_mappings": {
                "course_code": "code",
                "course_title": "title",
                "credits": "credit_units",
                "dept_code": "department_code",
                "level": "course_level",
                "practical": "is_practical",
                "morning": "morning_only",
                "duration": "exam_duration_minutes",
                "active": "is_active",
            },
            "uppercase_columns": ["code", "department_code"],
            "integer_columns": [
                "credit_units",
                "course_level",
                "semester",
                "exam_duration_minutes",
            ],
            "boolean_columns": ["is_practical", "morning_only", "is_active"],
        },
    }

    @classmethod
    def get_scale_limits(cls, mode: str = "default") -> Dict[str, int]:
        """
        Get scale limits based on deployment mode.

        Args:
            mode: One of 'dev', 'prod', 'default'

        Returns:
            Dictionary of scale limits with environment variable overrides applied
        """
        if mode == "dev":
            base_limits = cls.DEV_SCALE_LIMITS.copy()
        elif mode == "prod":
            base_limits = cls.PROD_SCALE_LIMITS.copy()
        else:
            base_limits = cls.DEFAULT_SCALE_LIMITS.copy()

        # Apply environment variable overrides
        for key in base_limits:
            env_key = f"SEED_{key.upper()}"
            env_value = os.getenv(env_key)
            if env_value:
                try:
                    base_limits[key] = int(env_value)
                except ValueError:
                    print(f"Warning: Invalid value for {env_key}: {env_value}")

        return base_limits

    @classmethod
    def get_csv_schema(cls, entity_type: str) -> Optional[Dict[str, Any]]:
        """
        Get CSV schema configuration for an entity type.

        Args:
            entity_type: The type of entity (e.g., 'students', 'courses')

        Returns:
            Schema configuration dict or None if not found
        """
        return cls.CSV_SCHEMAS.get(entity_type)

    @classmethod
    def get_database_url(cls) -> str:
        """
        Get database URL from environment or return default.

        Returns:
            Database connection URL
        """
        return os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:password@localhost:5432/postgres",
        )

    @classmethod
    def get_batch_size(cls) -> int:
        """
        Get batch size for bulk operations.

        Returns:
            Batch size for processing records
        """
        return int(os.getenv("SEED_BATCH_SIZE", "500"))

    @classmethod
    def get_progress_interval(cls) -> int:
        """
        Get interval for progress reporting.

        Returns:
            Number of records between progress reports
        """
        return int(os.getenv("SEED_PROGRESS_INTERVAL", "1000"))

    @classmethod
    def is_debug_mode(cls) -> bool:
        """
        Check if debug mode is enabled.

        Returns:
            True if debug mode is enabled
        """
        return os.getenv("SEED_DEBUG", "false").lower() in ("true", "1", "yes")

    @classmethod
    def get_admin_credentials(cls) -> Dict[str, str]:
        """
        Get admin user credentials.

        Returns:
            Dictionary with admin user details
        """
        return {
            "email": os.getenv("ADMIN_EMAIL", "admin@baze.edu.ng"),
            "password": os.getenv("ADMIN_PASSWORD", "admin123"),
            "first_name": os.getenv("ADMIN_FIRST_NAME", "System"),
            "last_name": os.getenv("ADMIN_LAST_NAME", "Administrator"),
        }

    @classmethod
    def get_file_paths(cls) -> Dict[str, Path]:
        """
        Get common file paths for seeding operations.

        Returns:
            Dictionary of file paths
        """
        backend_dir = Path(__file__).parent.parent.parent
        return {
            "backend": backend_dir,
            "scripts": backend_dir / "scripts",
            "seeders": backend_dir / "scripts" / "seeders",
            "data": backend_dir / "data",  # For CSV files
            "logs": backend_dir / "logs",
            "env": backend_dir / ".env",
        }

    @classmethod
    def validate_environment(cls) -> Dict[str, Any]:
        """
        Validate seeder environment and return status.

        Returns:
            Dictionary with validation results
        """
        errors: List[str] = []
        warnings: List[str] = []
        info: Dict[str, Any] = {}
        valid = True

        paths = cls.get_file_paths()

        # Check if backend directory structure exists
        if not paths["backend"].exists():
            errors.append(f"Backend directory not found: {paths['backend']}")
            valid = False

        # Check for .env file
        if not paths["env"].exists():
            warnings.append(f".env file not found: {paths['env']}")

        # Check database URL
        db_url = cls.get_database_url()
        if "localhost" in db_url:
            warnings.append("Using localhost database - ensure it's running")

        # Check scale limits
        scale_limits = cls.get_scale_limits()
        total_students = scale_limits["students"]
        total_courses = scale_limits["courses"]

        if total_students > 10000:
            warnings.append(
                f"Large student count ({total_students}) - seeding may take time"
            )

        if total_courses > 1000:
            warnings.append(
                f"Large course count ({total_courses}) - seeding may take time"
            )

        # Info
        info["database_url"] = db_url
        info["scale_mode"] = (
            "custom"
            if any(f"SEED_{k.upper()}" in os.environ for k in scale_limits)
            else "default"
        )
        info["debug_mode"] = cls.is_debug_mode()
        info["batch_size"] = cls.get_batch_size()

        return {"valid": valid, "errors": errors, "warnings": warnings, "info": info}


# Convenience functions for backward compatibility
def get_scale_limits(mode: str = "default") -> Dict[str, int]:
    """Get scale limits for the specified mode."""
    return SeederConfig.get_scale_limits(mode)


def get_database_url() -> str:
    """Get database URL from environment."""
    return SeederConfig.get_database_url()


def validate_environment() -> Dict[str, Any]:
    """Validate seeder environment."""
    return SeederConfig.validate_environment()
