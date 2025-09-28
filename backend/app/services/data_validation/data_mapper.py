# services/data_validation/data_mapper.py
"""
MODIFIED Data Mapper Module for the Adaptive Exam Timetabling System.
This module now focuses on mapping and transforming data into a clean JSON format
for the database seeding function, without performing database lookups itself.
"""

import re
import logging
import inspect
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date, time
from decimal import Decimal
import uuid
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class MappingResult:
    """Result of data mapping operation."""

    success: bool
    data: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class DataMappingError(Exception):
    """Custom exception for data mapping errors."""

    pass


class DataMapper:
    """
    Maps external data to a JSON format suitable for the database seeding function.
    It handles transformations but delegates foreign key resolution to the database.
    """

    def __init__(self, db_session: AsyncSession):
        # db_session is kept for potential future use or complex validation, but not for lookups.
        self.db_session = db_session
        self.entity_schemas: Dict[str, Dict[str, Any]] = {}
        self._initialize_schemas()

    def _initialize_schemas(self) -> None:
        """Initialize entity mapping schemas for JSON preparation."""

        # Academic Sessions Schema
        self.entity_schemas["academic_sessions"] = {
            "table_name": "academic_sessions",
            "required_fields": ["name", "start_date", "end_date", "semester_system"],
            "field_mappings": {
                "session_name": "name",
                "academic_session": "name",
                "start": "start_date",
                "end": "end_date",
                "semester_type": "semester_system",
            },
            "transformers": {
                "id": lambda x: str(uuid.uuid4()),
                "start_date": self._transform_date,
                "end_date": self._transform_date,
                "is_active": self._transform_boolean,
                "name": self._transform_string,
            },
            "validators": {
                "name": self._validate_required,
                "start_date": self._validate_date_range,
                "end_date": self._validate_date_range,
            },
        }

        # Faculties Schema
        self.entity_schemas["faculties"] = {
            "table_name": "faculties",
            "required_fields": ["name", "code"],
            "field_mappings": {"faculty_name": "name", "faculty_code": "code"},
            "transformers": {
                "id": lambda x: str(uuid.uuid4()),
                "name": self._transform_string,
                "code": self._transform_code,
                "is_active": self._transform_boolean,
            },
            "validators": {
                "name": self._validate_required,
                "code": self._validate_required,
            },
        }

        # Departments Schema - now uses faculty_code instead of faculty_id lookup
        self.entity_schemas["departments"] = {
            "table_name": "departments",
            "required_fields": ["name", "code", "faculty_code"],
            "field_mappings": {
                "department_name": "name",
                "dept_name": "name",
                "department_code": "code",
                "dept_code": "code",
                "faculty_name": "faculty_code",
            },
            "transformers": {
                "id": lambda x: str(uuid.uuid4()),
                "name": self._transform_string,
                "code": self._transform_code,
                "faculty_code": self._transform_code,
                "is_active": self._transform_boolean,
            },
            "validators": {
                "name": self._validate_required,
                "code": self._validate_required,
                "faculty_code": self._validate_required,
            },
        }

        # Programmes Schema - now uses department_code instead of department_id
        self.entity_schemas["programmes"] = {
            "table_name": "programmes",
            "required_fields": [
                "name",
                "code",
                "department_code",
                "degree_type",
                "duration_years",
            ],
            "field_mappings": {
                "programme_name": "name",
                "program_name": "name",
                "programme_code": "code",
                "program_code": "code",
                "department_name": "department_code",
                "degree": "degree_type",
            },
            "transformers": {
                "id": lambda x: str(uuid.uuid4()),
                "name": self._transform_string,
                "code": self._transform_code,
                "department_code": self._transform_code,
                "duration_years": self._transform_integer,
                "degree_type": self._transform_string,
                "is_active": self._transform_boolean,
            },
            "validators": {
                "name": self._validate_required,
                "code": self._validate_required,
                "department_code": self._validate_required,
                "duration_years": self._validate_positive_integer,
            },
        }

        # Courses Schema - now uses department_code instead of department_id
        self.entity_schemas["courses"] = {
            "table_name": "courses",
            "required_fields": [
                "code",
                "title",
                "credit_units",
                "course_level",
                "department_code",
            ],
            "field_mappings": {
                "course_code": "code",
                "course_title": "title",
                "course_name": "title",
                "credits": "credit_units",
                "units": "credit_units",
                "level": "course_level",
                "year": "course_level",
                "department_name": "department_code",
                "exam_duration": "exam_duration_minutes",
            },
            "transformers": {
                "id": lambda x: str(uuid.uuid4()),
                "code": self._transform_code,
                "title": self._transform_string,
                "credit_units": self._transform_integer,
                "course_level": self._transform_integer,
                "department_code": self._transform_code,
                "exam_duration_minutes": self._transform_integer,
                "semester": self._transform_integer,
                "is_practical": self._transform_boolean,
                "morning_only": self._transform_boolean,
                "is_active": self._transform_boolean,
            },
            "validators": {
                "code": self._validate_required,
                "title": self._validate_required,
                "credit_units": self._validate_positive_integer,
                "course_level": self._validate_course_level,
                "department_code": self._validate_required,
            },
        }

        # Students Schema - now uses programme_code instead of programme_id
        self.entity_schemas["students"] = {
            "table_name": "students",
            "required_fields": [
                "matric_number",
                "first_name",
                "last_name",
                "programme_code",
                "entry_year",
            ],
            "field_mappings": {
                "matric_no": "matric_number",
                "registration_number": "matric_number",
                "reg_no": "matric_number",
                "programme_name": "programme_code",
                "level": "current_level",
                "year_of_entry": "entry_year",
                "admission_year": "entry_year",
            },
            "transformers": {
                "id": lambda x: str(uuid.uuid4()),
                "matric_number": self._transform_matric_number,
                "first_name": self._transform_string,
                "last_name": self._transform_string,
                "current_level": self._transform_integer,
                "entry_year": self._transform_integer,
                "programme_code": self._transform_code,
                "student_type": self._transform_string,
                "is_active": self._transform_boolean,
                "special_needs": self._transform_array,
            },
            "validators": {
                "matric_number": self._validate_required,
                "first_name": self._validate_required,
                "last_name": self._validate_required,
                "programme_code": self._validate_required,
                "current_level": self._validate_positive_integer,
                "entry_year": self._validate_entry_year,
            },
        }

        # Staff Schema - now uses department_code instead of department_id
        self.entity_schemas["staff"] = {
            "table_name": "staff",
            "required_fields": ["staff_number", "staff_type", "department_code"],
            "field_mappings": {
                "staff_no": "staff_number",
                "employee_id": "staff_number",
                "emp_id": "staff_number",
                "type": "staff_type",
                "department_name": "department_code",
            },
            "transformers": {
                "id": lambda x: str(uuid.uuid4()),
                "staff_number": self._transform_staff_number,
                "staff_type": self._transform_string,
                "department_code": self._transform_code,
                "position": self._transform_string,
                "can_invigilate": self._transform_boolean,
                "max_daily_sessions": self._transform_integer,
                "max_consecutive_sessions": self._transform_integer,
                "is_active": self._transform_boolean,
            },
            "validators": {
                "staff_number": self._validate_required,
                "staff_type": self._validate_staff_type,
                "department_code": self._validate_required,
            },
        }

        # Buildings Schema
        self.entity_schemas["buildings"] = {
            "table_name": "buildings",
            "required_fields": ["name", "code"],
            "field_mappings": {"building_name": "name", "building_code": "code"},
            "transformers": {
                "id": lambda x: str(uuid.uuid4()),
                "name": self._transform_string,
                "code": self._transform_code,
                "is_active": self._transform_boolean,
            },
            "validators": {
                "name": self._validate_required,
                "code": self._validate_required,
            },
        }

        # Room Types Schema
        self.entity_schemas["room_types"] = {
            "table_name": "room_types",
            "required_fields": ["name"],
            "field_mappings": {"type_name": "name", "room_type_name": "name"},
            "transformers": {
                "id": lambda x: str(uuid.uuid4()),
                "name": self._transform_string,
                "description": self._transform_string,
                "is_active": self._transform_boolean,
            },
            "validators": {"name": self._validate_required},
        }

        # Rooms Schema - now uses building_code and room_type_name instead of IDs
        self.entity_schemas["rooms"] = {
            "table_name": "rooms",
            "required_fields": [
                "code",
                "name",
                "capacity",
                "building_code",
                "room_type_name",
            ],
            "field_mappings": {
                "room_code": "code",
                "room_name": "name",
                "room_capacity": "capacity",
                "building_name": "building_code",
                "room_type_name": "room_type_name",
                "type": "room_type_name",
                "floor": "floor_number",
                "air_conditioning": "has_ac",
                "ac": "has_ac",
                "computers": "has_computers",
                "projector": "has_projector",
            },
            "transformers": {
                "id": lambda x: str(uuid.uuid4()),
                "code": self._transform_code,
                "name": self._transform_string,
                "capacity": self._transform_integer,
                "building_code": self._transform_code,
                "room_type_name": self._transform_string,
                "exam_capacity": self._transform_integer,
                "floor_number": self._transform_integer,
                "has_ac": self._transform_boolean,
                "has_computers": self._transform_boolean,
                "has_projector": self._transform_boolean,
                "is_active": self._transform_boolean,
                "accessibility_features": self._transform_array,
                "notes": self._transform_string,
            },
            "validators": {
                "code": self._validate_required,
                "capacity": self._validate_positive_integer,
                "building_code": self._validate_required,
                "room_type_name": self._validate_required,
            },
        }

        # Time Slots Schema
        self.entity_schemas["time_slots"] = {
            "table_name": "time_slots",
            "required_fields": ["name", "start_time", "end_time"],
            "field_mappings": {
                "slot_name": "name",
                "time_slot_name": "name",
                "start": "start_time",
                "end": "end_time",
                "duration": "duration_minutes",
            },
            "transformers": {
                "id": lambda x: str(uuid.uuid4()),
                "name": self._transform_string,
                "start_time": self._transform_time,
                "end_time": self._transform_time,
                "duration_minutes": self._transform_integer,
                "is_active": self._transform_boolean,
            },
            "validators": {
                "name": self._validate_required,
                "start_time": self._validate_required,
                "end_time": self._validate_required,
            },
        }

        logger.info(f"Initialized {len(self.entity_schemas)} simplified entity schemas")

    async def map_data(
        self, raw_data: List[Dict[str, Any]], entity_type: str
    ) -> Dict[str, Any]:
        """
        Map raw data to JSON format for database seeding.

        Args:
            raw_data: List of raw data dictionaries
            entity_type: Type of entity being mapped

        Returns:
            dict: Mapping results
        """
        result: Dict[str, Any] = {
            "success": False,
            "total_records": len(raw_data),
            "processed_records": 0,
            "mapped_data": [],
            "errors": [],
            "warnings": [],
        }

        if entity_type not in self.entity_schemas:
            result["errors"].append(f"Unknown entity type: {entity_type}")
            return result

        schema = self.entity_schemas[entity_type]

        for idx, record in enumerate(raw_data):
            try:
                # Use synchronous mapping since we don't do DB lookups anymore
                mapping_result = self._map_single_record_sync(record, schema, idx + 1)

                if mapping_result.success:
                    result["mapped_data"].append(mapping_result.data)
                    result["processed_records"] += 1
                else:
                    result["errors"].extend(
                        [
                            f"Record {idx + 1}: {error}"
                            for error in mapping_result.errors
                        ]
                    )

                result["warnings"].extend(
                    [
                        f"Record {idx + 1}: {warning}"
                        for warning in mapping_result.warnings
                    ]
                )

            except Exception as e:
                result["errors"].append(
                    f"Record {idx + 1}: Unexpected mapping error: {e}"
                )
                logger.error(f"Mapping error for record {idx + 1}: {e}")

        result["success"] = result["processed_records"] > 0

        logger.info(
            f"Mapped {result['processed_records']}/{result['total_records']} records for {entity_type}"
        )

        return result

    def _map_single_record_sync(
        self, record: Dict[str, Any], schema: Dict[str, Any], record_number: int
    ) -> MappingResult:
        """Map a single record using the schema synchronously."""
        result = MappingResult(success=False)
        mapped_data: Dict[str, Any] = {}

        try:
            # Apply field mappings
            normalized_record = self._apply_field_mappings(record, schema)

            # Transform fields
            for field, value in normalized_record.items():
                transformers = schema.get("transformers", {})

                if field in transformers:
                    try:
                        mapped_data[field] = transformers[field](value)
                    except Exception as e:
                        result.errors.append(
                            f"Field '{field}': Transformation error: {e}"
                        )
                        continue
                else:
                    mapped_data[field] = value

            # Generate UUID if not already present
            if "id" not in mapped_data:
                mapped_data["id"] = str(uuid.uuid4())

            # Validate required fields
            required_fields = schema.get("required_fields", [])
            for field in required_fields:
                if field not in mapped_data or mapped_data[field] is None:
                    result.errors.append(f"Missing required field: {field}")

            # Run validators
            validators = schema.get("validators", {})
            for field, validator in validators.items():
                if field in mapped_data:
                    try:
                        validation_result = validator(mapped_data[field], mapped_data)

                        if not validation_result.get("is_valid", True):
                            error_msg = validation_result.get(
                                "error", f"Validation failed for {field}"
                            )
                            result.errors.append(f"Field '{field}': {error_msg}")

                    except Exception as e:
                        result.warnings.append(
                            f"Field '{field}': Validation error: {e}"
                        )

            if not result.errors:
                result.success = True
                result.data = mapped_data

        except Exception as e:
            result.errors.append(f"Mapping failed: {e}")
            logger.error(f"Record mapping error: {e}")

        return result

    def _apply_field_mappings(
        self, record: Dict[str, Any], schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply field name mappings."""
        field_mappings = schema.get("field_mappings", {})
        normalized: Dict[str, Any] = {}

        # First, copy all fields with their original names
        for key, value in record.items():
            normalized[key] = value

        # Apply mappings
        for source_field, target_field in field_mappings.items():
            if source_field in record:
                normalized[target_field] = record[source_field]
                # Remove the original field if it's different from target
                if source_field != target_field and source_field in normalized:
                    del normalized[source_field]

        return normalized

    # Transformation methods (keep as is)
    def _transform_string(self, value: Any) -> Optional[str]:
        """Transform value to string."""
        if value is None or value == "":
            return None
        return str(value).strip()

    def _transform_code(self, value: Any) -> Optional[str]:
        """Transform value to uppercase code."""
        if value is None or value == "":
            return None
        return str(value).strip().upper()

    def _transform_integer(self, value: Any) -> Optional[int]:
        """Transform value to integer."""
        if value is None or value == "":
            return None

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

        if isinstance(value, str):
            try:
                return int(float(value.strip().replace(",", "")))
            except ValueError:
                raise ValueError(f"Cannot convert '{value}' to integer")

        raise ValueError(f"Cannot convert '{value}' to integer")

    def _transform_decimal(self, value: Any) -> Optional[Decimal]:
        """Transform value to decimal."""
        if value is None or value == "":
            return None

        if isinstance(value, Decimal):
            return value

        if isinstance(value, (int, float)):
            return Decimal(str(value))

        if isinstance(value, str):
            try:
                return Decimal(value.strip().replace(",", ""))
            except Exception:
                raise ValueError(f"Cannot convert '{value}' to decimal")

        raise ValueError(f"Cannot convert '{value}' to decimal")

    def _transform_boolean(self, value: Any) -> Optional[bool]:
        """Transform value to boolean."""
        if value is None or value == "":
            return None

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            value = value.strip().lower()

            if value in ("true", "1", "yes", "y", "on", "active"):
                return True
            elif value in ("false", "0", "no", "n", "off", "inactive"):
                return False

        if isinstance(value, (int, float)):
            return bool(value)

        return bool(value)

    def _transform_date(self, value: Any) -> Optional[date]:
        """Transform value to date."""
        if value is None or value == "":
            return None

        if isinstance(value, date):
            return value

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, str):
            try:
                from dateutil import parser

                return parser.parse(value.strip()).date()
            except Exception:
                raise ValueError(f"Cannot convert '{value}' to date")

        raise ValueError(f"Cannot convert '{value}' to date")

    def _transform_time(self, value: Any) -> Optional[time]:
        """Transform value to time."""
        if value is None or value == "":
            return None

        if isinstance(value, time):
            return value

        if isinstance(value, datetime):
            return value.time()

        if isinstance(value, str):
            try:
                from dateutil import parser

                return parser.parse(value.strip()).time()
            except Exception:
                raise ValueError(f"Cannot convert '{value}' to time")

        raise ValueError(f"Cannot convert '{value}' to time")

    def _transform_array(self, value: Any) -> Optional[List[str]]:
        """Transform value to array."""
        if value is None or value == "":
            return None

        if isinstance(value, list):
            return [str(item).strip() for item in value if item]

        if isinstance(value, str):
            # Handle comma-separated values
            items = [item.strip() for item in value.split(",")]
            return [item for item in items if item]

        return [str(value)]

    def _transform_matric_number(self, value: Any) -> Optional[str]:
        """Transform matric number."""
        if value is None or value == "":
            return None

        # Clean and format matric number
        matric = str(value).strip().upper()
        # Remove any non-alphanumeric characters except forward slash
        matric = re.sub(r"[^A-Z0-9/]", "", matric)

        return matric

    def _transform_staff_number(self, value: Any) -> Optional[str]:
        """Transform staff number."""
        if value is None or value == "":
            return None

        return str(value).strip().upper()

    # Validation methods (keep as is, remove database-dependent ones)
    def _validate_required(self, value: Any, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate required field."""
        is_valid = value is not None and value != ""

        return {
            "is_valid": is_valid,
            "error": "Field is required" if not is_valid else None,
        }

    def _validate_positive_integer(
        self, value: Any, record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate positive integer."""
        try:
            if value is None:
                return {"is_valid": False, "error": "Value cannot be None"}

            int_value = int(value)
            is_valid = int_value > 0

            return {
                "is_valid": is_valid,
                "error": "Must be a positive integer" if not is_valid else None,
            }
        except (TypeError, ValueError):
            return {"is_valid": False, "error": "Must be a valid integer"}

    def _validate_course_level(
        self, value: Any, record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate course level."""
        try:
            if value is None:
                return {"is_valid": False, "error": "Course level cannot be None"}

            level = int(value)
            is_valid = 100 <= level <= 900

            return {
                "is_valid": is_valid,
                "error": (
                    "Course level must be between 100 and 900" if not is_valid else None
                ),
            }
        except (TypeError, ValueError):
            return {"is_valid": False, "error": "Course level must be a valid integer"}

    def _validate_entry_year(
        self, value: Any, record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate entry year."""
        try:
            if value is None:
                return {"is_valid": False, "error": "Entry year cannot be None"}

            year = int(value)
            current_year = datetime.now().year
            is_valid = 2000 <= year <= current_year + 1

            return {
                "is_valid": is_valid,
                "error": (
                    f"Entry year must be between 2000 and {current_year + 1}"
                    if not is_valid
                    else None
                ),
            }
        except (TypeError, ValueError):
            return {"is_valid": False, "error": "Entry year must be a valid integer"}

    def _validate_staff_type(
        self, value: Any, record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate staff type."""
        valid_types = ["academic", "administrative", "technical", "support"]

        if value is None:
            return {"is_valid": False, "error": "Staff type cannot be None"}

        is_valid = str(value).lower() in valid_types

        return {
            "is_valid": is_valid,
            "error": (
                f"Staff type must be one of: {valid_types}" if not is_valid else None
            ),
        }

    def _validate_date_range(
        self, value: Any, record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate date range."""
        if not value:
            return {"is_valid": False, "error": "Date is required"}

        try:
            # Convert to date if it's a string
            if isinstance(value, str):
                from dateutil import parser

                date_value = parser.parse(value).date()
            elif isinstance(value, datetime):
                date_value = value.date()
            elif isinstance(value, date):
                date_value = value
            else:
                return {"is_valid": False, "error": "Invalid date format"}

            # Check if date is in reasonable range
            min_date = date(2000, 1, 1)
            max_date = date(2050, 12, 31)

            is_valid = min_date <= date_value <= max_date

            return {
                "is_valid": is_valid,
                "error": (
                    f"Date must be between {min_date} and {max_date}"
                    if not is_valid
                    else None
                ),
            }
        except Exception as e:
            return {"is_valid": False, "error": f"Invalid date format: {e}"}


# Export main components
__all__ = ["DataMapper", "MappingResult", "DataMappingError"]
