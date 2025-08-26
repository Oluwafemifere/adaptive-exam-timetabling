# services/data_validation/data_mapper.py
"""
Data Mapper Module for the Adaptive Exam Timetabling System.
Maps external data formats to internal database models with relationship handling.
"""

import re
import logging
from typing import Dict, List, Optional,TypedDict, Any
from datetime import datetime, date, time
from decimal import Decimal
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import text
from dataclasses import dataclass, field



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

class ValidationResult(TypedDict):
    valid: bool
    errors: List[str]
    warnings: List[str]

class DataMapper:
    """Maps external data to internal database models with validation and transformation."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.entity_schemas: Dict[str, Dict[str, Any]] = {}
        self.lookup_caches: Dict[str, Dict[str, uuid.UUID]] = {}
        self._table_exists_cache: Dict[str, bool] = {}
        self._initialize_schemas()
    
    def _initialize_schemas(self) -> None:
        """Initialize entity mapping schemas."""
        
        # Academic Sessions Schema
        self.entity_schemas['academic_sessions'] = {
            'table_name': 'academic_sessions',
            'required_fields': ['name', 'start_date', 'end_date', 'semester_system'],
            'field_mappings': {
                'session_name': 'name',
                'academic_session': 'name',
                'start': 'start_date',
                'end': 'end_date',
                'semester_type': 'semester_system'
            },
            'transformers': {
                'start_date': self._transform_date,
                'end_date': self._transform_date,
                'is_active': self._transform_boolean,
                'name': self._transform_string
            },
            'validators': {
                'name': self._validate_unique_session_name,
                'start_date': self._validate_date_range,
                'end_date': self._validate_date_range
            }
        }
        
        # Faculties Schema
        self.entity_schemas['faculties'] = {
            'table_name': 'faculties',
            'required_fields': ['name', 'code'],
            'field_mappings': {
                'faculty_name': 'name',
                'faculty_code': 'code'
            },
            'transformers': {
                'name': self._transform_string,
                'code': self._transform_code,
                'is_active': self._transform_boolean
            },
            'validators': {
                'name': self._validate_required,
                'code': self._validate_unique_faculty_code
            }
        }
        
        # Departments Schema
        self.entity_schemas['departments'] = {
            'table_name': 'departments',
            'required_fields': ['name', 'code', 'faculty_id'],
            'field_mappings': {
                'department_name': 'name',
                'dept_name': 'name',
                'department_code': 'code',
                'dept_code': 'code',
                'faculty_name': 'faculty_lookup',
                'faculty_code': 'faculty_lookup'
            },
            'transformers': {
                'name': self._transform_string,
                'code': self._transform_code,
                'is_active': self._transform_boolean
            },
            'validators': {
                'name': self._validate_required,
                'code': self._validate_unique_department_code,
                'faculty_id': self._validate_required
            },
            'lookups': {
                'faculty_id': self._lookup_faculty
            }
        }
        
        # Programmes Schema
        self.entity_schemas['programmes'] = {
            'table_name': 'programmes',
            'required_fields': ['name', 'code', 'department_id', 'degree_type', 'duration_years'],
            'field_mappings': {
                'programme_name': 'name',
                'program_name': 'name',
                'programme_code': 'code',
                'program_code': 'code',
                'department_name': 'department_lookup',
                'department_code': 'department_lookup',
                'degree': 'degree_type'
            },
            'transformers': {
                'name': self._transform_string,
                'code': self._transform_code,
                'duration_years': self._transform_integer,
                'degree_type': self._transform_string,
                'is_active': self._transform_boolean
            },
            'validators': {
                'name': self._validate_required,
                'code': self._validate_unique_programme_code,
                'duration_years': self._validate_positive_integer
            },
            'lookups': {
                'department_id': self._lookup_department
            }
        }
        
        # Courses Schema
        self.entity_schemas['courses'] = {
            'table_name': 'courses',
            'required_fields': ['code', 'title', 'credit_units', 'course_level', 'department_id'],
            'field_mappings': {
                'course_code': 'code',
                'course_title': 'title',
                'course_name': 'title',
                'credits': 'credit_units',
                'units': 'credit_units',
                'level': 'course_level',
                'year': 'course_level',
                'department_name': 'department_lookup',
                'department_code': 'department_lookup',
                'exam_duration': 'exam_duration_minutes'
            },
            'transformers': {
                'code': self._transform_code,
                'title': self._transform_string,
                'credit_units': self._transform_integer,
                'course_level': self._transform_integer,
                'exam_duration_minutes': self._transform_integer,
                'semester': self._transform_integer,
                'is_practical': self._transform_boolean,
                'morning_only': self._transform_boolean,
                'is_active': self._transform_boolean
            },
            'validators': {
                'code': self._validate_unique_course_code,
                'title': self._validate_required,
                'credit_units': self._validate_positive_integer,
                'course_level': self._validate_course_level
            },
            'lookups': {
                'department_id': self._lookup_department
            }
        }
        
        # Students Schema
        self.entity_schemas['students'] = {
            'table_name': 'students',
            'required_fields': ['matric_number', 'programme_id', 'current_level', 'entry_year'],
            'field_mappings': {
                'matric_no': 'matric_number',
                'registration_number': 'matric_number',
                'reg_no': 'matric_number',
                'programme_name': 'programme_lookup',
                'programme_code': 'programme_lookup',
                'program_name': 'programme_lookup',
                'level': 'current_level',
                'year_of_entry': 'entry_year',
                'admission_year': 'entry_year'
            },
            'transformers': {
                'matric_number': self._transform_matric_number,
                'current_level': self._transform_integer,
                'entry_year': self._transform_integer,
                'student_type': self._transform_string,
                'is_active': self._transform_boolean,
                'special_needs': self._transform_array
            },
            'validators': {
                'matric_number': self._validate_unique_matric_number,
                'current_level': self._validate_positive_integer,
                'entry_year': self._validate_entry_year
            },
            'lookups': {
                'programme_id': self._lookup_programme
            }
        }
        
        # Staff Schema
        self.entity_schemas['staff'] = {
            'table_name': 'staff',
            'required_fields': ['staff_number', 'staff_type'],
            'field_mappings': {
                'staff_no': 'staff_number',
                'employee_id': 'staff_number',
                'emp_id': 'staff_number',
                'type': 'staff_type',
                'department_name': 'department_lookup',
                'department_code': 'department_lookup'
            },
            'transformers': {
                'staff_number': self._transform_staff_number,
                'staff_type': self._transform_string,
                'position': self._transform_string,
                'can_invigilate': self._transform_boolean,
                'max_daily_sessions': self._transform_integer,
                'max_consecutive_sessions': self._transform_integer,
                'is_active': self._transform_boolean
            },
            'validators': {
                'staff_number': self._validate_unique_staff_number,
                'staff_type': self._validate_staff_type
            },
            'lookups': {
                'department_id': self._lookup_department
            }
        }
        
        # Buildings Schema
        self.entity_schemas['buildings'] = {
            'table_name': 'buildings',
            'required_fields': ['name', 'code'],
            'field_mappings': {
                'building_name': 'name',
                'building_code': 'code'
            },
            'transformers': {
                'name': self._transform_string,
                'code': self._transform_code,
                'is_active': self._transform_boolean
            },
            'validators': {
                'name': self._validate_required,
                'code': self._validate_unique_building_code
            }
        }
        
        # Room Types Schema
        self.entity_schemas['room_types'] = {
            'table_name': 'room_types',
            'required_fields': ['name'],
            'field_mappings': {
                'type_name': 'name',
                'room_type_name': 'name'
            },
            'transformers': {
                'name': self._transform_string,
                'description': self._transform_string,
                'is_active': self._transform_boolean
            },
            'validators': {
                'name': self._validate_required
            }
        }
        
        # Rooms Schema
        self.entity_schemas['rooms'] = {
            'table_name': 'rooms',
            'required_fields': ['code', 'name', 'capacity', 'building_id', 'room_type_id'],
            'field_mappings': {
                'room_code': 'code',
                'room_name': 'name',
                'room_capacity': 'capacity',
                'building_name': 'building_lookup',
                'building_code': 'building_lookup',
                'room_type_name': 'room_type_lookup',
                'type': 'room_type_lookup',
                'floor': 'floor_number',
                'air_conditioning': 'has_ac',
                'ac': 'has_ac',
                'computers': 'has_computers',
                'projector': 'has_projector'
            },
            'transformers': {
                'code': self._transform_code,
                'name': self._transform_string,
                'capacity': self._transform_integer,
                'exam_capacity': self._transform_integer,
                'floor_number': self._transform_integer,
                'has_ac': self._transform_boolean,
                'has_computers': self._transform_boolean,
                'has_projector': self._transform_boolean,
                'is_active': self._transform_boolean,
                'accessibility_features': self._transform_array,
                'notes': self._transform_string
            },
            'validators': {
                'code': self._validate_unique_room_code,
                'capacity': self._validate_positive_integer
            },
            'lookups': {
                'building_id': self._lookup_building,
                'room_type_id': self._lookup_room_type
            }
        }
        
        # Time Slots Schema
        self.entity_schemas['time_slots'] = {
            'table_name': 'time_slots',
            'required_fields': ['name', 'start_time', 'end_time'],
            'field_mappings': {
                'slot_name': 'name',
                'time_slot_name': 'name',
                'start': 'start_time',
                'end': 'end_time',
                'duration': 'duration_minutes'
            },
            'transformers': {
                'name': self._transform_string,
                'start_time': self._transform_time,
                'end_time': self._transform_time,
                'duration_minutes': self._transform_integer,
                'is_active': self._transform_boolean
            },
            'validators': {
                'name': self._validate_required,
                'start_time': self._validate_required,
                'end_time': self._validate_required
            }
        }
        
        logger.info(f"Initialized {len(self.entity_schemas)} entity schemas")
    
    def _table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        if table_name in self._table_exists_cache:
            return self._table_exists_cache[table_name]
        
        try:
            # Use SQLAlchemy's text() for raw SQL queries
            query = text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_name = :table_name
                AND table_schema = DATABASE()
            """)
            result = self.db_session.execute(query, {"table_name": table_name}).scalar()
            exists = result > 0 if result is not None else False
            self._table_exists_cache[table_name] = exists
            return exists
        except Exception as e:
            logger.warning(f"Could not check if table {table_name} exists: {e}")
            # Assume table exists to avoid blocking functionality
            self._table_exists_cache[table_name] = True
            return True
    
    def _execute_lookup_query(self, table_name: str, field_name: str, value: Any) -> Optional[str]:
        """Execute a generic lookup query."""
        if not self._table_exists(table_name):
            logger.warning(f"Table {table_name} does not exist, skipping lookup")
            return None
        
        try:
            # Use parameterized query to prevent SQL injection
            query = text(f"""
                SELECT id FROM {table_name} 
                WHERE {field_name} = :value 
                LIMIT 1
            """)
            result = self.db_session.execute(query, {"value": value}).first()
            return str(result[0]) if result else None
        except Exception as e:
            logger.warning(f"Lookup query failed for {table_name}.{field_name} = {value}: {e}")
            return None
    
    def _execute_uniqueness_check(self, table_name: str, field_name: str, value: Any) -> bool:
        """Execute a generic uniqueness check."""
        if not self._table_exists(table_name):
            logger.warning(f"Table {table_name} does not exist, assuming value is unique")
            return True
        
        try:
            query = text(f"""
                SELECT COUNT(*) FROM {table_name} 
                WHERE {field_name} = :value
            """)
            result = self.db_session.execute(query, {"value": value}).scalar()
            return result == 0 if result is not None else True
        except Exception as e:
            logger.warning(f"Uniqueness check failed for {table_name}.{field_name} = {value}: {e}")
            # Assume unique to avoid blocking
            return True
    
    def map_data(self, raw_data: List[Dict[str, Any]], entity_type: str) -> Dict[str, Any]:
        """
        Map raw data to database format.
        
        Args:
            raw_data: List of raw data dictionaries
            entity_type: Type of entity being mapped
            
        Returns:
            dict: Mapping results
        """
        result: Dict[str, Any] = {
            'success': False,
            'total_records': len(raw_data),
            'processed_records': 0,
            'mapped_data': [],
            'errors': [],
            'warnings': []
        }
        
        if entity_type not in self.entity_schemas:
            result['errors'].append(f"Unknown entity type: {entity_type}")
            return result
        
        schema = self.entity_schemas[entity_type]
        
        for idx, record in enumerate(raw_data):
            try:
                mapping_result = self._map_single_record(record, schema, idx + 1)
                
                if mapping_result.success:
                    result['mapped_data'].append(mapping_result.data)
                    result['processed_records'] += 1
                else:
                    result['errors'].extend([
                        f"Record {idx + 1}: {error}" for error in mapping_result.errors
                    ])
                
                result['warnings'].extend([
                    f"Record {idx + 1}: {warning}" for warning in mapping_result.warnings
                ])
                
            except Exception as e:
                result['errors'].append(f"Record {idx + 1}: Unexpected mapping error: {e}")
                logger.error(f"Mapping error for record {idx + 1}: {e}")
        
        result['success'] = result['processed_records'] > 0
        
        logger.info(f"Mapped {result['processed_records']}/{result['total_records']} records for {entity_type}")
        
        return result
    
    def _map_single_record(self, record: Dict[str, Any], schema: Dict[str, Any], record_number: int) -> MappingResult:
        """Map a single record using the schema."""
        result = MappingResult(success=False)
        mapped_data: Dict[str, Any] = {}
        
        try:
            # Apply field mappings
            normalized_record = self._apply_field_mappings(record, schema)
            
            # Handle lookups first
            lookup_results = self._handle_lookups(normalized_record, schema)
            mapped_data.update(lookup_results.get('data', {}))
            result.errors.extend(lookup_results.get('errors', []))
            result.warnings.extend(lookup_results.get('warnings', []))
            
            # Transform fields
            for field, value in normalized_record.items():
                if field.endswith('_lookup'):
                    continue  # Skip lookup fields, already handled
                
                transformers = schema.get('transformers', {})
                
                if field in transformers:
                    try:
                        mapped_data[field] = transformers[field](value)
                    except Exception as e:
                        result.errors.append(f"Field '{field}': Transformation error: {e}")
                        continue
                else:
                    mapped_data[field] = value
            
            # Validate required fields
            required_fields = schema.get('required_fields', [])
            for field in required_fields:
                if field not in mapped_data or mapped_data[field] is None:
                    result.errors.append(f"Missing required field: {field}")
            
            # Run validators
            validators = schema.get('validators', {})
            for field, validator in validators.items():
                if field in mapped_data:
                    try:
                        validation_result = validator(mapped_data[field], mapped_data)
                        
                        if not validation_result.get('is_valid', True):
                            error_msg = validation_result.get('error', f'Validation failed for {field}')
                            result.errors.append(f"Field '{field}': {error_msg}")
                            
                    except Exception as e:
                        result.warnings.append(f"Field '{field}': Validation error: {e}")
            
            # Add metadata
            mapped_data['_metadata'] = {
                'record_number': record_number,
                'mapped_at': datetime.utcnow().isoformat(),
                'entity_type': schema['table_name']
            }
            
            if not result.errors:
                result.success = True
                result.data = mapped_data
            
        except Exception as e:
            result.errors.append(f"Mapping failed: {e}")
            logger.error(f"Record mapping error: {e}")
        
        return result
    
    def _apply_field_mappings(self, record: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Apply field name mappings."""
        field_mappings = schema.get('field_mappings', {})
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
    
    def _handle_lookups(self, record: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Handle foreign key lookups."""
        lookup_result: Dict[str, Any] = {
            'data': {},
            'errors': [],
            'warnings': []
        }
        
        lookups = schema.get('lookups', {})
        
        for target_field, lookup_func in lookups.items():
            lookup_value = None
            
            # Find lookup value
            lookup_field = target_field.replace('_id', '_lookup')
            
            if lookup_field in record:
                lookup_value = record[lookup_field]
            elif target_field in record:
                lookup_value = record[target_field]
            
            if lookup_value:
                try:
                    resolved_id = lookup_func(lookup_value)
                    
                    if resolved_id:
                        lookup_result['data'][target_field] = resolved_id
                    else:
                        lookup_result['errors'].append(f"Could not resolve {target_field} for value: {lookup_value}")
                        
                except Exception as e:
                    lookup_result['errors'].append(f"Lookup error for {target_field}: {e}")
        
        return lookup_result
    
    # Transformation methods
    def _transform_string(self, value: Any) -> Optional[str]:
        """Transform value to string."""
        if value is None or value == '':
            return None
        return str(value).strip()
    
    def _transform_code(self, value: Any) -> Optional[str]:
        """Transform value to uppercase code."""
        if value is None or value == '':
            return None
        return str(value).strip().upper()
    
    def _transform_integer(self, value: Any) -> Optional[int]:
        """Transform value to integer."""
        if value is None or value == '':
            return None
        
        if isinstance(value, int):
            return value
        
        if isinstance(value, float):
            return int(value)
        
        if isinstance(value, str):
            try:
                return int(float(value.strip().replace(',', '')))
            except ValueError:
                raise ValueError(f"Cannot convert '{value}' to integer")
        
        raise ValueError(f"Cannot convert '{value}' to integer")
    
    def _transform_decimal(self, value: Any) -> Optional[Decimal]:
        """Transform value to decimal."""
        if value is None or value == '':
            return None
        
        if isinstance(value, Decimal):
            return value
        
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        
        if isinstance(value, str):
            try:
                return Decimal(value.strip().replace(',', ''))
            except Exception:
                raise ValueError(f"Cannot convert '{value}' to decimal")
        
        raise ValueError(f"Cannot convert '{value}' to decimal")
    
    def _transform_boolean(self, value: Any) -> Optional[bool]:
        """Transform value to boolean."""
        if value is None or value == '':
            return None
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            value = value.strip().lower()
            
            if value in ('true', '1', 'yes', 'y', 'on', 'active'):
                return True
            elif value in ('false', '0', 'no', 'n', 'off', 'inactive'):
                return False
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        return bool(value)
    
    def _transform_date(self, value: Any) -> Optional[date]:
        """Transform value to date."""
        if value is None or value == '':
            return None
        
        if isinstance(value, date):
            return value
        
        if isinstance(value, datetime):
            return value.date()
        
        if isinstance(value, str):
            try:
                # Import dateutil parser locally to avoid stub issues
                from dateutil import parser
                return parser.parse(value.strip()).date()
            except Exception:
                raise ValueError(f"Cannot convert '{value}' to date")
        
        raise ValueError(f"Cannot convert '{value}' to date")
    
    def _transform_time(self, value: Any) -> Optional[time]:
        """Transform value to time."""
        if value is None or value == '':
            return None
        
        if isinstance(value, time):
            return value
        
        if isinstance(value, datetime):
            return value.time()
        
        if isinstance(value, str):
            try:
                # Import dateutil parser locally to avoid stub issues
                from dateutil import parser
                return parser.parse(value.strip()).time()
            except Exception:
                raise ValueError(f"Cannot convert '{value}' to time")
        
        raise ValueError(f"Cannot convert '{value}' to time")
    
    def _transform_array(self, value: Any) -> Optional[List[str]]:
        """Transform value to array."""
        if value is None or value == '':
            return None
        
        if isinstance(value, list):
            return [str(item).strip() for item in value if item]
        
        if isinstance(value, str):
            # Handle comma-separated values
            items = [item.strip() for item in value.split(',')]
            return [item for item in items if item]
        
        return [str(value)]
    
    def _transform_matric_number(self, value: Any) -> Optional[str]:
        """Transform matric number."""
        if value is None or value == '':
            return None
        
        # Clean and format matric number
        matric = str(value).strip().upper()
        # Remove any non-alphanumeric characters except forward slash
        matric = re.sub(r'[^A-Z0-9/]', '', matric)
        
        return matric
    
    def _transform_staff_number(self, value: Any) -> Optional[str]:
        """Transform staff number."""
        if value is None or value == '':
            return None
        
        return str(value).strip().upper()
    
    # Validation methods
    def _validate_required(self, value: Any, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate required field."""
        is_valid = value is not None and value != ''
        
        return {
            'is_valid': is_valid,
            'error': 'Field is required' if not is_valid else None
        }
    
    def _validate_positive_integer(self, value: Any, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate positive integer."""
        try:
            if value is None:
                return {
                    'is_valid': False,
                    'error': 'Value cannot be None'
                }
            
            int_value = int(value)
            is_valid = int_value > 0
            
            return {
                'is_valid': is_valid,
                'error': 'Must be a positive integer' if not is_valid else None
            }
        except (TypeError, ValueError):
            return {
                'is_valid': False,
                'error': 'Must be a valid integer'
            }
    
    def _validate_course_level(self, value: Any, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate course level."""
        try:
            if value is None:
                return {
                    'is_valid': False,
                    'error': 'Course level cannot be None'
                }
            
            level = int(value)
            is_valid = 100 <= level <= 900
            
            return {
                'is_valid': is_valid,
                'error': 'Course level must be between 100 and 900' if not is_valid else None
            }
        except (TypeError, ValueError):
            return {
                'is_valid': False,
                'error': 'Course level must be a valid integer'
            }
    
    def _validate_entry_year(self, value: Any, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate entry year."""
        try:
            if value is None:
                return {
                    'is_valid': False,
                    'error': 'Entry year cannot be None'
                }
            
            year = int(value)
            current_year = datetime.now().year
            is_valid = 2000 <= year <= current_year + 1
            
            return {
                'is_valid': is_valid,
                'error': f'Entry year must be between 2000 and {current_year + 1}' if not is_valid else None
            }
        except (TypeError, ValueError):
            return {
                'is_valid': False,
                'error': 'Entry year must be a valid integer'
            }
    
    def _validate_staff_type(self, value: Any, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate staff type."""
        valid_types = ['academic', 'administrative', 'technical', 'support']
        
        if value is None:
            return {
                'is_valid': False,
                'error': 'Staff type cannot be None'
            }
        
        is_valid = str(value).lower() in valid_types
        
        return {
            'is_valid': is_valid,
            'error': f'Staff type must be one of: {valid_types}' if not is_valid else None
        }
    
    # Uniqueness validation methods using direct SQL queries
    def _validate_unique_session_name(self, value: Any, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate unique session name."""
        if not value:
            return {'is_valid': False, 'error': 'Session name is required'}
        
        is_unique = self._execute_uniqueness_check('academic_sessions', 'name', value)
        
        return {
            'is_valid': is_unique,
            'error': f'Session name "{value}" already exists' if not is_unique else None
        }
    
    def _validate_unique_faculty_code(self, value: Any, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate unique faculty code."""
        if not value:
            return {'is_valid': False, 'error': 'Faculty code is required'}
        
        is_unique = self._execute_uniqueness_check('faculties', 'code', value)
        
        return {
            'is_valid': is_unique,
            'error': f'Faculty code "{value}" already exists' if not is_unique else None
        }
    
    def _validate_unique_department_code(self, value: Any, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate unique department code."""
        if not value:
            return {'is_valid': False, 'error': 'Department code is required'}
        
        is_unique = self._execute_uniqueness_check('departments', 'code', value)
        
        return {
            'is_valid': is_unique,
            'error': f'Department code "{value}" already exists' if not is_unique else None
        }
    
    def _validate_unique_programme_code(self, value: Any, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate unique programme code."""
        if not value:
            return {'is_valid': False, 'error': 'Programme code is required'}
        
        is_unique = self._execute_uniqueness_check('programmes', 'code', value)
        
        return {
            'is_valid': is_unique,
            'error': f'Programme code "{value}" already exists' if not is_unique else None
        }
    
    def _validate_unique_course_code(self, value: Any, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate unique course code."""
        if not value:
            return {'is_valid': False, 'error': 'Course code is required'}
        
        is_unique = self._execute_uniqueness_check('courses', 'code', value)
        
        return {
            'is_valid': is_unique,
            'error': f'Course code "{value}" already exists' if not is_unique else None
        }
    
    def _validate_unique_matric_number(self, value: Any, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate unique matric number."""
        if not value:
            return {'is_valid': False, 'error': 'Matric number is required'}
        
        is_unique = self._execute_uniqueness_check('students', 'matric_number', value)
        
        return {
            'is_valid': is_unique,
            'error': f'Matric number "{value}" already exists' if not is_unique else None
        }
    
    def _validate_unique_staff_number(self, value: Any, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate unique staff number."""
        if not value:
            return {'is_valid': False, 'error': 'Staff number is required'}
        
        is_unique = self._execute_uniqueness_check('staff', 'staff_number', value)
        
        return {
            'is_valid': is_unique,
            'error': f'Staff number "{value}" already exists' if not is_unique else None
        }
    
    def _validate_unique_building_code(self, value: Any, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate unique building code."""
        if not value:
            return {'is_valid': False, 'error': 'Building code is required'}
        
        is_unique = self._execute_uniqueness_check('buildings', 'code', value)
        
        return {
            'is_valid': is_unique,
            'error': f'Building code "{value}" already exists' if not is_unique else None
        }
    
    def _validate_unique_room_code(self, value: Any, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate unique room code."""
        if not value:
            return {'is_valid': False, 'error': 'Room code is required'}
        
        is_unique = self._execute_uniqueness_check('rooms', 'code', value)
        
        return {
            'is_valid': is_unique,
            'error': f'Room code "{value}" already exists' if not is_unique else None
        }
    
    def _validate_date_range(self, value: Any, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate date range."""
        if not value:
            return {'is_valid': False, 'error': 'Date is required'}
        
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
                return {'is_valid': False, 'error': 'Invalid date format'}
            
            # Check if date is in reasonable range
            min_date = date(2000, 1, 1)
            max_date = date(2050, 12, 31)
            
            is_valid = min_date <= date_value <= max_date
            
            return {
                'is_valid': is_valid,
                'error': f'Date must be between {min_date} and {max_date}' if not is_valid else None
            }
        except Exception as e:
            return {
                'is_valid': False,
                'error': f'Invalid date format: {e}'
            }
    
    # Lookup methods using direct SQL queries with caching
    def _lookup_faculty(self, value: Any) -> Optional[str]:
        """Look up faculty by name or code."""
        if not value:
            return None
        
        # Check cache first
        cache_key = f'faculty_{str(value).lower()}'
        if cache_key in self.lookup_caches.get('faculties', {}):
            return str(self.lookup_caches['faculties'][cache_key])
        
        # Try lookup by code first
        result = self._execute_lookup_query('faculties', 'code', str(value).upper())
        
        # If not found by code, try by name (case-insensitive)
        if not result:
            try:
                query = text("""
                    SELECT id FROM faculties 
                    WHERE LOWER(name) LIKE LOWER(:value) 
                    LIMIT 1
                """)
                db_result = self.db_session.execute(query, {"value": f'%{value}%'}).first()
                result = str(db_result[0]) if db_result else None
            except Exception as e:
                logger.warning(f"Faculty name lookup error for '{value}': {e}")
        
        # Cache the result if found
        if result:
            if 'faculties' not in self.lookup_caches:
                self.lookup_caches['faculties'] = {}
            self.lookup_caches['faculties'][cache_key] = uuid.UUID(result)
        
        return result
    
    def _lookup_department(self, value: Any) -> Optional[str]:
        """Look up department by name or code."""
        if not value:
            return None
        
        # Check cache first
        cache_key = f'department_{str(value).lower()}'
        if cache_key in self.lookup_caches.get('departments', {}):
            return str(self.lookup_caches['departments'][cache_key])
        
        # Try lookup by code first
        result = self._execute_lookup_query('departments', 'code', str(value).upper())
        
        # If not found by code, try by name (case-insensitive)
        if not result:
            try:
                query = text("""
                    SELECT id FROM departments 
                    WHERE LOWER(name) LIKE LOWER(:value) 
                    LIMIT 1
                """)
                db_result = self.db_session.execute(query, {"value": f'%{value}%'}).first()
                result = str(db_result[0]) if db_result else None
            except Exception as e:
                logger.warning(f"Department name lookup error for '{value}': {e}")
        
        # Cache the result if found
        if result:
            if 'departments' not in self.lookup_caches:
                self.lookup_caches['departments'] = {}
            self.lookup_caches['departments'][cache_key] = uuid.UUID(result)
        
        return result
    
    def _lookup_programme(self, value: Any) -> Optional[str]:
        """Look up programme by name or code."""
        if not value:
            return None
        
        # Check cache first
        cache_key = f'programme_{str(value).lower()}'
        if cache_key in self.lookup_caches.get('programmes', {}):
            return str(self.lookup_caches['programmes'][cache_key])
        
        # Try lookup by code first
        result = self._execute_lookup_query('programmes', 'code', str(value).upper())
        
        # If not found by code, try by name (case-insensitive)
        if not result:
            try:
                query = text("""
                    SELECT id FROM programmes 
                    WHERE LOWER(name) LIKE LOWER(:value) 
                    LIMIT 1
                """)
                db_result = self.db_session.execute(query, {"value": f'%{value}%'}).first()
                result = str(db_result[0]) if db_result else None
            except Exception as e:
                logger.warning(f"Programme name lookup error for '{value}': {e}")
        
        # Cache the result if found
        if result:
            if 'programmes' not in self.lookup_caches:
                self.lookup_caches['programmes'] = {}
            self.lookup_caches['programmes'][cache_key] = uuid.UUID(result)
        
        return result
    
    def _lookup_building(self, value: Any) -> Optional[str]:
        """Look up building by name or code."""
        if not value:
            return None
        
        # Check cache first
        cache_key = f'building_{str(value).lower()}'
        if cache_key in self.lookup_caches.get('buildings', {}):
            return str(self.lookup_caches['buildings'][cache_key])
        
        # Try lookup by code first
        result = self._execute_lookup_query('buildings', 'code', str(value).upper())
        
        # If not found by code, try by name (case-insensitive)
        if not result:
            try:
                query = text("""
                    SELECT id FROM buildings 
                    WHERE LOWER(name) LIKE LOWER(:value) 
                    LIMIT 1
                """)
                db_result = self.db_session.execute(query, {"value": f'%{value}%'}).first()
                result = str(db_result[0]) if db_result else None
            except Exception as e:
                logger.warning(f"Building name lookup error for '{value}': {e}")
        
        # Cache the result if found
        if result:
            if 'buildings' not in self.lookup_caches:
                self.lookup_caches['buildings'] = {}
            self.lookup_caches['buildings'][cache_key] = uuid.UUID(result)
        
        return result
    
    def _lookup_room_type(self, value: Any) -> Optional[str]:
        """Look up room type by name."""
        if not value:
            return None
        
        # Check cache first
        cache_key = f'room_type_{str(value).lower()}'
        if cache_key in self.lookup_caches.get('room_types', {}):
            return str(self.lookup_caches['room_types'][cache_key])
        
        # Look up by name (case-insensitive)
        try:
            query = text("""
                SELECT id FROM room_types 
                WHERE LOWER(name) LIKE LOWER(:value) 
                LIMIT 1
            """)
            db_result = self.db_session.execute(query, {"value": f'%{value}%'}).first()
            result = str(db_result[0]) if db_result else None
        except Exception as e:
            logger.warning(f"Room type lookup error for '{value}': {e}")
            return None
        
        # Cache the result if found
        if result:
            if 'room_types' not in self.lookup_caches:
                self.lookup_caches['room_types'] = {}
            self.lookup_caches['room_types'][cache_key] = uuid.UUID(result)
        
        return result
    
    def clear_cache(self) -> None:
        """Clear all lookup caches."""
        self.lookup_caches.clear()
        self._table_exists_cache.clear()
        logger.info("All caches cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        stats = {
            entity_type: len(cache) 
            for entity_type, cache in self.lookup_caches.items()
        }
        stats['table_exists_cache'] = len(self._table_exists_cache)
        return stats
    
    def validate_schema(self, entity_type: str) -> ValidationResult:
        """Validate that the schema can be used with the current database."""
        if entity_type not in self.entity_schemas:
            return {
                "valid": False,
                "errors": [f"Unknown entity type: {entity_type}"],
                "warnings": [],
            }

        schema = self.entity_schemas[entity_type]
        table_name = schema["table_name"]

        result: ValidationResult = {
            "valid": True,
            "errors": [],
            "warnings": [],
        }

        if not self._table_exists(table_name):
            result["warnings"].append(f"Table {table_name} does not exist")

        return result


# Export main components
__all__ = [
    'DataMapper',
    'MappingResult',
    'DataMappingError'
]