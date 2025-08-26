"""
Data Validation Package for the Adaptive Exam Timetabling System.
Combines CSV processing, data mapping, and integrity checking functionality.
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
    validate_unique
)

from .data_mapper import (
    DataMapper,
    MappingResult,
    DataMappingError
)

from .integrity_checker import (
    DataIntegrityChecker,
    IntegrityError,
    IntegrityCheckResult
)

_all_ = [
    # CSV Processor
    'CSVProcessor',
    'CSVValidationError',
    'transform_date',
    'transform_time',
    'transform_integer',
    'transform_decimal',
    'transform_boolean',
    'transform_uuid',
    'validate_required',
    'validate_email',
    'validate_unique',
    
    # Data Mapper
    'DataMapper',
    'MappingResult',
    'DataMappingError',
    
    # Integrity Checker
    'DataIntegrityChecker',
    'IntegrityError',
    'IntegrityCheckResult'
]

