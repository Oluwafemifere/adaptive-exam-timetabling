# backend/app/services/data_validation/__init__.py
"""
Data Validation Package for the Adaptive Exam Timetabling System.
Provides tools for processing and validating incoming CSV data before
it is passed to the database for seeding.
"""

from .csv_processor import (
    CSVProcessor,
    CSVValidationError,
    transform_date,
    transform_time,
    transform_integer,
    transform_decimal,
    transform_boolean,
    transform_uuid,
    validate_required,
    validate_email,
    transform_string_to_array,
)

from .validation_schemas import ENTITY_SCHEMAS

# The DataMapper and DataIntegrityChecker are deprecated and no longer exposed
# as part of the public package API.

__all__ = [
    # Main CSV Processor
    "CSVProcessor",
    "CSVValidationError",
    # Centralized Schemas
    "ENTITY_SCHEMAS",
    # Re-usable transformer and validator functions
    "transform_date",
    "transform_time",
    "transform_integer",
    "transform_decimal",
    "transform_boolean",
    "transform_uuid",
    "transform_string_to_array",
    "validate_required",
    "validate_email",
]
