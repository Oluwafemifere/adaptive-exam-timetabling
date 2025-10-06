# services/data_validation/validation_schemas.py
"""
Centralized schemas for CSV processing.

Each schema defines how to validate, map, and transform a CSV file
for a specific entity type before sending it to the database's
staging tables.
"""

from .csv_processor import (
    transform_date,
    transform_integer,
    transform_boolean,
    validate_required,
    validate_email,
)

# This dictionary is imported by the upload endpoint to validate entity types
# and by the CSV processing task to validate file contents.
ENTITY_SCHEMAS = {
    "faculties": {
        "required_columns": ["name", "code"],
        "column_mappings": {
            "faculty_name": "name",
            "faculty_code": "code",
        },
        "transformers": {
            "name": str,
            "code": str,
        },
        "validators": {
            "name": validate_required,
            "code": validate_required,
        },
    },
    "departments": {
        "required_columns": ["name", "code", "faculty_code"],
        "column_mappings": {
            "department_name": "name",
            "dept_name": "name",
            "department_code": "code",
            "dept_code": "code",
            "faculty_name": "faculty_code",  # Allow for name as an alias
        },
        "transformers": {
            "name": str,
            "code": str,
            "faculty_code": str,
        },
        "validators": {
            "name": validate_required,
            "code": validate_required,
            "faculty_code": validate_required,
        },
    },
    "programmes": {
        "required_columns": [
            "name",
            "code",
            "department_code",
            "degree_type",
            "duration_years",
        ],
        "column_mappings": {
            "programme_name": "name",
            "program_name": "name",
            "programme_code": "code",
            "program_code": "code",
            "department_name": "department_code",  # Allow for name as an alias
            "degree": "degree_type",
            "duration": "duration_years",
        },
        "transformers": {
            "name": str,
            "code": str,
            "department_code": str,
            "degree_type": str,
            "duration_years": transform_integer,
        },
        "validators": {
            "name": validate_required,
            "code": validate_required,
            "department_code": validate_required,
            "duration_years": validate_required,
        },
    },
    # --- START OF ADDED SCHEMAS ---
    "buildings": {
        "required_columns": ["code", "name"],
        "column_mappings": {
            "building_code": "code",
            "building_name": "name",
        },
        "transformers": {
            "code": str,
            "name": str,
        },
        "validators": {
            "code": validate_required,
            "name": validate_required,
        },
    },
    "rooms": {
        "required_columns": [
            "code",
            "name",
            "building_code",
            "capacity",
            "exam_capacity",
        ],
        "column_mappings": {
            "room_code": "code",
            "room_name": "name",
            "ac": "has_ac",
            "projector": "has_projector",
            "computers": "has_computers",
            "max_invigilators": "max_inv_per_room",
        },
        "transformers": {
            "code": str,
            "name": str,
            "building_code": str,
            "building_name": str,
            "capacity": transform_integer,
            "exam_capacity": transform_integer,
            "has_ac": transform_boolean,
            "has_projector": transform_boolean,
            "has_computers": transform_boolean,
            "max_inv_per_room": transform_integer,
        },
        "validators": {
            "code": validate_required,
            "name": validate_required,
            "building_code": validate_required,
            "capacity": validate_required,
            "exam_capacity": validate_required,
        },
    },
    # --- END OF ADDED SCHEMAS ---
    "courses": {
        "required_columns": [
            "code",
            "title",
            "credit_units",
            "course_level",
            "department_code",
        ],
        "column_mappings": {
            "course_code": "code",
            "course_title": "title",
            "credits": "credit_units",
            "level": "course_level",
            "department_name": "department_code",  # Allow for name as an alias
            "duration": "exam_duration_minutes",
            "practical": "is_practical",
            "morning": "morning_only",
        },
        "transformers": {
            "code": str,
            "title": str,
            "credit_units": transform_integer,
            "course_level": transform_integer,
            "semester": transform_integer,
            "is_practical": transform_boolean,
            "morning_only": transform_boolean,
            "exam_duration_minutes": transform_integer,
            "department_code": str,
        },
        "validators": {
            "code": validate_required,
            "title": validate_required,
            "credit_units": validate_required,
            "course_level": validate_required,
            "department_code": validate_required,
        },
    },
    # --- START OF ADDED SCHEMAS ---
    "staff": {
        "required_columns": [
            "staff_number",
            "first_name",
            "last_name",
            "email",
            "department_code",
        ],
        "column_mappings": {
            "staff_no": "staff_number",
            "firstname": "first_name",
            "lastname": "last_name",
            "department_name": "department_code",
            "invigilator": "can_invigilate",
            "instructor": "is_instructor",
        },
        "transformers": {
            "staff_number": str,
            "first_name": str,
            "last_name": str,
            "email": str,
            "department_code": str,
            "staff_type": str,
            "can_invigilate": transform_boolean,
            "is_instructor": transform_boolean,
            "max_daily_sessions": transform_integer,
            "max_consecutive_sessions": transform_integer,
            "max_concurrent_exams": transform_integer,
            "max_students_per_invigilator": transform_integer,
        },
        "validators": {
            "staff_number": validate_required,
            "first_name": validate_required,
            "last_name": validate_required,
            "department_code": validate_required,
            "email": [validate_required, validate_email],
        },
    },
    # --- END OF ADDED SCHEMAS ---
    "students": {
        "required_columns": [
            "matric_number",
            "first_name",
            "last_name",
            "programme_code",
            "entry_year",
        ],
        "column_mappings": {
            "matric_no": "matric_number",
            "reg_no": "matric_number",
            "firstname": "first_name",
            "lastname": "last_name",
            "program_code": "programme_code",
            "year_of_entry": "entry_year",
        },
        "transformers": {
            "matric_number": str,
            "first_name": str,
            "last_name": str,
            "entry_year": transform_integer,
            "programme_code": str,
        },
        "validators": {
            "matric_number": validate_required,
            "first_name": validate_required,
            "last_name": validate_required,
            "programme_code": validate_required,
            "entry_year": validate_required,
        },
    },
    # --- START OF ADDED SCHEMAS ---
    "course_instructors": {
        "required_columns": ["staff_number", "course_code"],
        "column_mappings": {
            "staff_no": "staff_number",
        },
        "transformers": {
            "staff_number": str,
            "course_code": str,
        },
        "validators": {
            "staff_number": validate_required,
            "course_code": validate_required,
        },
    },
    "staff_unavailability": {
        "required_columns": ["staff_number", "unavailable_date"],
        "column_mappings": {
            "staff_no": "staff_number",
            "date": "unavailable_date",
            "period": "period_name",
        },
        "transformers": {
            "staff_number": str,
            "unavailable_date": transform_date,
            "period_name": str,
            "reason": str,
        },
        "validators": {
            "staff_number": validate_required,
            "unavailable_date": validate_required,
        },
    },
    # --- END OF ADDED SCHEMAS ---
    "course_registrations": {
        "required_columns": ["student_matric_number", "course_code"],
        "column_mappings": {
            "matric_number": "student_matric_number",
            "matric_no": "student_matric_number",
            "type": "registration_type",  # e.g., 'regular', 'carryover'
        },
        "transformers": {
            "student_matric_number": str,
            "course_code": str,
            "registration_type": str,
        },
        "validators": {
            "student_matric_number": validate_required,
            "course_code": validate_required,
        },
    },
}
