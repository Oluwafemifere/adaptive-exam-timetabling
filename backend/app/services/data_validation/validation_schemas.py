# backend/app/services/data_validation/validation_schemas.py
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
    transform_string_to_array,
)

ENTITY_SCHEMAS = {
    "faculties": {
        "required_columns": ["name", "code"],
        "column_mappings": {"faculty_name": "name", "faculty_code": "code"},
        "transformers": {"name": str, "code": str},
        "validators": {"name": validate_required, "code": validate_required},
    },
    "departments": {
        "required_columns": ["name", "code", "faculty_code"],
        "column_mappings": {
            "department_name": "name",
            "dept_name": "name",
            "department_code": "code",
            "dept_code": "code",
            "faculty_name": "faculty_code",
        },
        "transformers": {"name": str, "code": str, "faculty_code": str},
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
            "department_name": "department_code",
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
    # --- UPDATED SCHEMAS ---
    "buildings": {
        "required_columns": ["code", "name"],
        "column_mappings": {
            "building_code": "code",
            "building_name": "name",
            "faculty": "faculty_code",
        },
        "transformers": {"code": str, "name": str, "faculty_code": str},
        "validators": {"code": validate_required, "name": validate_required},
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
            "room_type": "room_type_code",
            "floor": "floor_number",
        },
        "transformers": {
            "code": str,
            "name": str,
            "building_code": str,
            "room_type_code": str,
            "capacity": transform_integer,
            "exam_capacity": transform_integer,
            "floor_number": transform_integer,
            "has_ac": transform_boolean,
            "has_projector": transform_boolean,
            "has_computers": transform_boolean,
            "max_inv_per_room": transform_integer,
            "accessibility_features": transform_string_to_array,
            "notes": str,
        },
        "validators": {
            "code": validate_required,
            "name": validate_required,
            "building_code": validate_required,
            "capacity": validate_required,
            "exam_capacity": validate_required,
        },
    },
    "courses": {
        "required_columns": ["code", "title", "credit_units", "course_level"],
        "column_mappings": {
            "course_code": "code",
            "course_title": "title",
            "credits": "credit_units",
            "level": "course_level",
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
        },
        "validators": {
            "code": validate_required,
            "title": validate_required,
            "credit_units": validate_required,
            "course_level": validate_required,
        },
    },
    "staff": {
        "required_columns": [
            "staff_number",
            "first_name",
            "last_name",
            "department_code",
            "email",
        ],
        "column_mappings": {
            "staff_no": "staff_number",
            "firstname": "first_name",
            "lastname": "last_name",
            "department_name": "department_code",
            "invigilator": "can_invigilate",
            "instructor": "is_instructor",
            # REMOVED: "user_email": "email" mapping
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
            "user_email": str,  # ADDED user_email transformer
        },
        "validators": {
            "staff_number": validate_required,
            "first_name": validate_required,
            "last_name": validate_required,
            "department_code": validate_required,
            "email": [validate_required, validate_email],
            "user_email": [validate_email],  # ADDED user_email validator (optional)
        },
    },
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
            # REMOVED: "user_email": "email" mapping
        },
        "transformers": {
            "matric_number": str,
            "first_name": str,
            "last_name": str,
            "entry_year": transform_integer,
            "programme_code": str,
            "email": str,  # This should be user_email
            "user_email": str,  # ADDED user_email transformer
        },
        "validators": {
            "matric_number": validate_required,
            "first_name": validate_required,
            "last_name": validate_required,
            "programme_code": validate_required,
            "entry_year": validate_required,
            "user_email": [validate_email],  # ADDED user_email validator (optional)
        },
    },
    "course_instructors": {
        "required_columns": ["staff_number", "course_code"],
        "column_mappings": {"staff_no": "staff_number"},
        "transformers": {"staff_number": str, "course_code": str},
        "validators": {
            "staff_number": validate_required,
            "course_code": validate_required,
        },
    },
    # --- NEW SCHEMAS FOR MANY-TO-MANY RELATIONSHIPS ---
    "course_departments": {
        "required_columns": ["course_code", "department_code"],
        "column_mappings": {"course": "course_code", "department": "department_code"},
        "transformers": {"course_code": str, "department_code": str},
        "validators": {
            "course_code": validate_required,
            "department_code": validate_required,
        },
    },
    "course_faculties": {
        "required_columns": ["course_code", "faculty_code"],
        "column_mappings": {"course": "course_code", "faculty": "faculty_code"},
        "transformers": {"course_code": str, "faculty_code": str},
        "validators": {
            "course_code": validate_required,
            "faculty_code": validate_required,
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
    "course_registrations": {
        "required_columns": ["student_matric_number", "course_code"],
        "column_mappings": {
            "matric_number": "student_matric_number",
            "matric_no": "student_matric_number",
            "type": "registration_type",
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
