# services/data_validation/integrity_checker.py
"""
Data Integrity Checker Module for the Adaptive Exam Timetabling System.
Validates data consistency, referential integrity, and business rules across entities.
"""

import logging
from typing import Dict, List, Optional, Any, Set, Tuple, Callable
from datetime import datetime, date, time
from collections import defaultdict, Counter
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid

logger = logging.getLogger(__name__)

@dataclass
class IntegrityError:
    """Represents a data integrity error."""
    severity: str  # 'error', 'warning', 'info'
    category: str  # 'referential', 'business_rule', 'consistency', 'duplicate'
    entity_type: str
    record_id: Optional[str]
    field: Optional[str]
    message: str
    details: Optional[Dict[str, Any]] = None

@dataclass
class IntegrityCheckResult:
    """Result of integrity checking operation."""
    success: bool
    total_records: int
    valid_records: int
    errors: List[IntegrityError]
    warnings: List[IntegrityError]
    summary: Dict[str, Any]

class DataIntegrityChecker:
    """Checks data integrity across multiple entities with comprehensive validation."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.business_rules: Dict[str, List[Callable[[List[Dict[str, Any]], str, Dict[str, List[Dict[str, Any]]]], List[IntegrityError]]]] = {}
        self.referential_constraints: Dict[str, Dict[str, Tuple[str, str, str]]] = {}
        self.uniqueness_constraints: Dict[str, List[str]] = {}
        self._initialize_constraints()
    
    def _initialize_constraints(self) -> None:
        """Initialize integrity constraints and business rules."""
        
        # Referential integrity constraints
        self.referential_constraints = {
            'departments': {
                'faculty_id': ('faculties', 'id', 'Faculty must exist')
            },
            'programmes': {
                'department_id': ('departments', 'id', 'Department must exist')
            },
            'courses': {
                'department_id': ('departments', 'id', 'Department must exist')
            },
            'students': {
                'programme_id': ('programmes', 'id', 'Programme must exist')
            },
            'staff': {
                'department_id': ('departments', 'id', 'Department must exist')
            },
            'rooms': {
                'building_id': ('buildings', 'id', 'Building must exist'),
                'room_type_id': ('room_types', 'id', 'Room type must exist')
            },
            'exams': {
                'course_id': ('courses', 'id', 'Course must exist'),
                'session_id': ('academic_sessions', 'id', 'Academic session must exist'),
                'time_slot_id': ('time_slots', 'id', 'Time slot must exist')
            },
            'course_registrations': {
                'student_id': ('students', 'id', 'Student must exist'),
                'course_id': ('courses', 'id', 'Course must exist'),
                'session_id': ('academic_sessions', 'id', 'Academic session must exist')
            }
        }
        
        # Uniqueness constraints
        self.uniqueness_constraints = {
            'academic_sessions': ['name'],
            'faculties': ['code', 'name'],
            'departments': ['code'],
            'programmes': ['code'],
            'courses': ['code'],
            'students': ['matric_number'],
            'staff': ['staff_number'],
            'buildings': ['code'],
            'rooms': ['code'],
            'time_slots': ['name']
        }
        
        # Business rules
        self.business_rules = {
            'academic_sessions': [
                self._validate_session_dates,
                self._validate_session_overlap
            ],
            'students': [
                self._validate_student_level,
                self._validate_student_programme_consistency
            ],
            'courses': [
                self._validate_course_level,
                self._validate_course_semester
            ],
            'rooms': [
                self._validate_room_capacity,
                self._validate_room_exam_capacity
            ],
            'time_slots': [
                self._validate_time_slot_duration,
                self._validate_time_slot_overlap
            ],
            'exams': [
                self._validate_exam_scheduling,
                self._validate_exam_duration
            ],
            'course_registrations': [
                self._validate_registration_eligibility,
                self._validate_registration_duplicates
            ]
        }
        
        logger.info("Initialized data integrity constraints and business rules")
    
    def check_integrity(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        check_referential: bool = True,
        check_uniqueness: bool = True,
        check_business_rules: bool = True
    ) -> IntegrityCheckResult:
        """
        Perform comprehensive integrity checking on data.
        
        Args:
            data: Dictionary mapping entity types to lists of records
            check_referential: Whether to check referential integrity
            check_uniqueness: Whether to check uniqueness constraints
            check_business_rules: Whether to check business rules
            
        Returns:
            IntegrityCheckResult: Results of integrity checking
        """
        errors: List[IntegrityError] = []
        warnings: List[IntegrityError] = []
        total_records = sum(len(records) for records in data.values())
        
        logger.info(f"Starting integrity check for {total_records} records across {len(data)} entity types")
        
        try:
            # Check uniqueness constraints
            if check_uniqueness:
                uniqueness_errors = self._check_uniqueness_constraints(data)
                errors.extend(uniqueness_errors)
            
            # Check referential integrity
            if check_referential:
                referential_errors = self._check_referential_integrity(data)
                errors.extend(referential_errors)
            
            # Check business rules
            if check_business_rules:
                business_rule_errors = self._check_business_rules(data)
                errors.extend(business_rule_errors)
            
            # Separate errors and warnings
            error_list = [e for e in errors if e.severity == 'error']
            warning_list = [e for e in errors if e.severity == 'warning']
            
            # Calculate valid records
            error_record_ids = {e.record_id for e in error_list if e.record_id}
            valid_records = total_records - len(error_record_ids)
            
            # Generate summary
            summary = self._generate_summary(data, error_list, warning_list)
            
            result = IntegrityCheckResult(
                success=len(error_list) == 0,
                total_records=total_records,
                valid_records=valid_records,
                errors=error_list,
                warnings=warning_list,
                summary=summary
            )
            
            logger.info(f"Integrity check complete: {valid_records}/{total_records} valid records")
            if error_list:
                logger.warning(f"Found {len(error_list)} integrity errors")
            if warning_list:
                logger.info(f"Found {len(warning_list)} warnings")
            
            return result
            
        except Exception as e:
            logger.error(f"Integrity check failed: {e}")
            return IntegrityCheckResult(
                success=False,
                total_records=total_records,
                valid_records=0,
                errors=[IntegrityError(
                    severity='error',
                    category='system',
                    entity_type='system',
                    record_id=None,
                    field=None,
                    message=f"Integrity check failed: {e}"
                )],
                warnings=[],
                summary={}
            )
    
    def _check_uniqueness_constraints(self, data: Dict[str, List[Dict[str, Any]]]) -> List[IntegrityError]:
        """Check uniqueness constraints within the dataset."""
        errors: List[IntegrityError] = []
        
        for entity_type, records in data.items():
            if entity_type not in self.uniqueness_constraints:
                continue
            
            unique_fields = self.uniqueness_constraints[entity_type]
            
            for field in unique_fields:
                field_values: Dict[Any, List[Tuple[int, Dict[str, Any]]]] = defaultdict(list)
                
                # Collect all values for this field
                for idx, record in enumerate(records):
                    if field in record and record[field] is not None:
                        value = record[field]
                        field_values[value].append((idx, record))
                
                # Check for duplicates
                for value, record_list in field_values.items():
                    if len(record_list) > 1:
                        for idx, record in record_list:
                            errors.append(IntegrityError(
                                severity='error',
                                category='duplicate',
                                entity_type=entity_type,
                                record_id=str(idx),
                                field=field,
                                message=f"Duplicate value '{value}' for unique field '{field}'",
                                details={'duplicate_value': value, 'occurrences': len(record_list)}
                            ))
        
        return errors
    
    def _check_referential_integrity(self, data: Dict[str, List[Dict[str, Any]]]) -> List[IntegrityError]:
        """Check referential integrity constraints."""
        errors: List[IntegrityError] = []
        
        # Build reference maps for efficient lookup
        reference_maps: Dict[str, Set[Any]] = {}
        for entity_type, records in data.items():
            reference_maps[entity_type] = set()
            for record in records:
                if 'id' in record and record['id'] is not None:
                    reference_maps[entity_type].add(record['id'])
        
        # Check each entity's foreign key references
        for entity_type, records in data.items():
            if entity_type not in self.referential_constraints:
                continue
            
            constraints = self.referential_constraints[entity_type]
            
            for idx, record in enumerate(records):
                for foreign_key, (ref_table, ref_field, error_msg) in constraints.items():
                    if foreign_key in record and record[foreign_key] is not None:
                        ref_value = record[foreign_key]
                        
                        # Check if referenced value exists
                        if ref_table in reference_maps:
                            if ref_value not in reference_maps[ref_table]:
                                errors.append(IntegrityError(
                                    severity='error',
                                    category='referential',
                                    entity_type=entity_type,
                                    record_id=str(idx),
                                    field=foreign_key,
                                    message=f"{error_msg}: '{ref_value}' not found in {ref_table}",
                                    details={
                                        'foreign_key': foreign_key,
                                        'referenced_table': ref_table,
                                        'referenced_value': ref_value
                                    }
                                ))
                        else:
                            errors.append(IntegrityError(
                                severity='warning',
                                category='referential',
                                entity_type=entity_type,
                                record_id=str(idx),
                                field=foreign_key,
                                message=f"Referenced table '{ref_table}' not found in dataset",
                                details={
                                    'foreign_key': foreign_key,
                                    'referenced_table': ref_table
                                }
                            ))
        
        return errors
    
    def _check_business_rules(self, data: Dict[str, List[Dict[str, Any]]]) -> List[IntegrityError]:
        """Check business rules for each entity type."""
        errors: List[IntegrityError] = []
        
        for entity_type, records in data.items():
            if entity_type not in self.business_rules:
                continue
            
            rules = self.business_rules[entity_type]
            
            for rule_func in rules:
                try:
                    rule_errors = rule_func(records, entity_type, data)
                    errors.extend(rule_errors)
                except Exception as e:
                    logger.warning(f"Business rule check failed for {entity_type}: {e}")
                    errors.append(IntegrityError(
                        severity='warning',
                        category='business_rule',
                        entity_type=entity_type,
                        record_id=None,
                        field=None,
                        message=f"Business rule check failed: {e}"
                    ))
        
        return errors
    
    # Business rule validation methods
    def _validate_session_dates(self, records: List[Dict[str, Any]], entity_type: str, all_data: Dict[str, List[Dict[str, Any]]]) -> List[IntegrityError]:
        """Validate academic session date ranges."""
        errors: List[IntegrityError] = []
        
        for idx, record in enumerate(records):
            start_date = record.get('start_date')
            end_date = record.get('end_date')
            
            if start_date and end_date:
                try:
                    if isinstance(start_date, str):
                        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                    if isinstance(end_date, str):
                        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                    
                    if start_date >= end_date:
                        errors.append(IntegrityError(
                            severity='error',
                            category='business_rule',
                            entity_type=entity_type,
                            record_id=str(idx),
                            field='start_date',
                            message="Session start date must be before end date",
                            details={'start_date': str(start_date), 'end_date': str(end_date)}
                        ))
                except Exception as e:
                    errors.append(IntegrityError(
                        severity='warning',
                        category='business_rule',
                        entity_type=entity_type,
                        record_id=str(idx),
                        field='start_date',
                        message=f"Invalid date format: {e}"
                    ))
        
        return errors
    
    def _validate_session_overlap(self, records: List[Dict[str, Any]], entity_type: str, all_data: Dict[str, List[Dict[str, Any]]]) -> List[IntegrityError]:
        """Check for overlapping academic sessions."""
        errors: List[IntegrityError] = []
        
        # Convert dates and create date ranges
        date_ranges: List[Tuple[int, date, date, str]] = []
        for idx, record in enumerate(records):
            try:
                start_date = record.get('start_date')
                end_date = record.get('end_date')
                
                if start_date and end_date:
                    if isinstance(start_date, str):
                        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                    if isinstance(end_date, str):
                        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                    
                    date_ranges.append((idx, start_date, end_date, record.get('name', f'Session {idx}')))
            except Exception:
                continue
        
        # Check for overlaps
        for i, (idx1, start1, end1, name1) in enumerate(date_ranges):
            for j, (idx2, start2, end2, name2) in enumerate(date_ranges[i+1:], i+1):
                # Check if date ranges overlap
                if not (end1 < start2 or end2 < start1):
                    errors.append(IntegrityError(
                        severity='warning',
                        category='business_rule',
                        entity_type=entity_type,
                        record_id=str(idx1),
                        field='start_date',
                        message=f"Session overlaps with '{name2}'",
                        details={
                            'overlapping_session': name2,
                            'session1_dates': f"{start1} to {end1}",
                            'session2_dates': f"{start2} to {end2}"
                        }
                    ))
        
        return errors
    
    def _validate_student_level(self, records: List[Dict[str, Any]], entity_type: str, all_data: Dict[str, List[Dict[str, Any]]]) -> List[IntegrityError]:
        """Validate student academic level."""
        errors: List[IntegrityError] = []
        
        for idx, record in enumerate(records):
            current_level = record.get('current_level')
            entry_year = record.get('entry_year')
            
            if current_level is not None:
                try:
                    level = int(current_level)
                    if not (100 <= level <= 800):
                        errors.append(IntegrityError(
                            severity='error',
                            category='business_rule',
                            entity_type=entity_type,
                            record_id=str(idx),
                            field='current_level',
                            message=f"Invalid student level: {level}. Must be between 100-800",
                            details={'current_level': level}
                        ))
                except (ValueError, TypeError):
                    errors.append(IntegrityError(
                        severity='error',
                        category='business_rule',
                        entity_type=entity_type,
                        record_id=str(idx),
                        field='current_level',
                        message=f"Invalid level format: {current_level}"
                    ))
            
            # Check level progression based on entry year
            if current_level and entry_year:
                try:
                    level = int(current_level)
                    year = int(entry_year)
                    current_year = datetime.now().year
                    years_since_entry = current_year - year
                    expected_min_level = 100 + (years_since_entry * 100)
                    
                    if level < expected_min_level - 100:  # Allow one year behind
                        errors.append(IntegrityError(
                            severity='warning',
                            category='business_rule',
                            entity_type=entity_type,
                            record_id=str(idx),
                            field='current_level',
                            message=f"Student level ({level}) seems low for entry year {year}",
                            details={
                                'current_level': level,
                                'entry_year': year,
                                'expected_min_level': expected_min_level
                            }
                        ))
                except (ValueError, TypeError):
                    pass
        
        return errors
    
    def _validate_student_programme_consistency(self, records: List[Dict[str, Any]], entity_type: str, all_data: Dict[str, List[Dict[str, Any]]]) -> List[IntegrityError]:
        """Validate student-programme consistency."""
        errors: List[IntegrityError] = []
        
        # Get programme data for validation
        programmes = all_data.get('programmes', [])
        programme_map = {p.get('id'): p for p in programmes if p.get('id')}
        
        for idx, record in enumerate(records):
            programme_id = record.get('programme_id')
            current_level = record.get('current_level')
            
            if programme_id and programme_id in programme_map:
                programme = programme_map[programme_id]
                duration_years = programme.get('duration_years')
                
                if current_level and duration_years:
                    try:
                        level = int(current_level)
                        max_level = duration_years * 100
                        
                        if level > max_level:
                            errors.append(IntegrityError(
                                severity='error',
                                category='business_rule',
                                entity_type=entity_type,
                                record_id=str(idx),
                                field='current_level',
                                message=f"Student level ({level}) exceeds programme duration ({duration_years} years)",
                                details={
                                    'current_level': level,
                                    'programme_duration': duration_years,
                                    'max_level': max_level
                                }
                            ))
                    except (ValueError, TypeError):
                        pass
        
        return errors
    
    def _validate_course_level(self, records: List[Dict[str, Any]], entity_type: str, all_data: Dict[str, List[Dict[str, Any]]]) -> List[IntegrityError]:
        """Validate course level."""
        errors: List[IntegrityError] = []
        
        for idx, record in enumerate(records):
            course_level = record.get('course_level')
            
            if course_level is not None:
                try:
                    level = int(course_level)
                    if not (100 <= level <= 900):
                        errors.append(IntegrityError(
                            severity='error',
                            category='business_rule',
                            entity_type=entity_type,
                            record_id=str(idx),
                            field='course_level',
                            message=f"Invalid course level: {level}. Must be between 100-900",
                            details={'course_level': level}
                        ))
                except (ValueError, TypeError):
                    errors.append(IntegrityError(
                        severity='error',
                        category='business_rule',
                        entity_type=entity_type,
                        record_id=str(idx),
                        field='course_level',
                        message=f"Invalid course level format: {course_level}"
                    ))
        
        return errors
    
    def _validate_course_semester(self, records: List[Dict[str, Any]], entity_type: str, all_data: Dict[str, List[Dict[str, Any]]]) -> List[IntegrityError]:
        """Validate course semester."""
        errors: List[IntegrityError] = []
        
        for idx, record in enumerate(records):
            semester = record.get('semester')
            
            if semester is not None:
                try:
                    sem = int(semester)
                    if not (1 <= sem <= 3):  # 1=First, 2=Second, 3=Both/Year-long
                        errors.append(IntegrityError(
                            severity='warning',
                            category='business_rule',
                            entity_type=entity_type,
                            record_id=str(idx),
                            field='semester',
                            message=f"Unusual semester value: {sem}. Expected 1, 2, or 3",
                            details={'semester': sem}
                        ))
                except (ValueError, TypeError):
                    errors.append(IntegrityError(
                        severity='warning',
                        category='business_rule',
                        entity_type=entity_type,
                        record_id=str(idx),
                        field='semester',
                        message=f"Invalid semester format: {semester}"
                    ))
        
        return errors
    
    def _validate_room_capacity(self, records: List[Dict[str, Any]], entity_type: str, all_data: Dict[str, List[Dict[str, Any]]]) -> List[IntegrityError]:
        """Validate room capacity constraints."""
        errors: List[IntegrityError] = []
        
        for idx, record in enumerate(records):
            capacity = record.get('capacity')
            exam_capacity = record.get('exam_capacity')
            
            if capacity is not None:
                try:
                    cap = int(capacity)
                    if cap <= 0:
                        errors.append(IntegrityError(
                            severity='error',
                            category='business_rule',
                            entity_type=entity_type,
                            record_id=str(idx),
                            field='capacity',
                            message="Room capacity must be positive",
                            details={'capacity': cap}
                        ))
                except (ValueError, TypeError):
                    errors.append(IntegrityError(
                        severity='error',
                        category='business_rule',
                        entity_type=entity_type,
                        record_id=str(idx),
                        field='capacity',
                        message=f"Invalid capacity format: {capacity}"
                    ))
            
            if capacity and exam_capacity:
                try:
                    cap = int(capacity)
                    exam_cap = int(exam_capacity)
                    
                    if exam_cap > cap:
                        errors.append(IntegrityError(
                            severity='error',
                            category='business_rule',
                            entity_type=entity_type,
                            record_id=str(idx),
                            field='exam_capacity',
                            message="Exam capacity cannot exceed room capacity",
                            details={'capacity': cap, 'exam_capacity': exam_cap}
                        ))
                except (ValueError, TypeError):
                    pass
        
        return errors
    
    def _validate_room_exam_capacity(self, records: List[Dict[str, Any]], entity_type: str, all_data: Dict[str, List[Dict[str, Any]]]) -> List[IntegrityError]:
        """Validate room exam capacity is reasonable."""
        errors: List[IntegrityError] = []
        
        for idx, record in enumerate(records):
            capacity = record.get('capacity')
            exam_capacity = record.get('exam_capacity')
            
            if capacity and exam_capacity:
                try:
                    cap = int(capacity)
                    exam_cap = int(exam_capacity)
                    
                    # Exam capacity should typically be 50-80% of room capacity
                    if exam_cap < cap * 0.3:
                        errors.append(IntegrityError(
                            severity='warning',
                            category='business_rule',
                            entity_type=entity_type,
                            record_id=str(idx),
                            field='exam_capacity',
                            message=f"Exam capacity ({exam_cap}) seems low for room capacity ({cap})",
                            details={'capacity': cap, 'exam_capacity': exam_cap}
                        ))
                    elif exam_cap > cap * 0.9:
                        errors.append(IntegrityError(
                            severity='warning',
                            category='business_rule',
                            entity_type=entity_type,
                            record_id=str(idx),
                            field='exam_capacity',
                            message=f"Exam capacity ({exam_cap}) seems high for room capacity ({cap})",
                            details={'capacity': cap, 'exam_capacity': exam_cap}
                        ))
                except (ValueError, TypeError):
                    pass
        
        return errors
    
    def _validate_time_slot_duration(self, records: List[Dict[str, Any]], entity_type: str, all_data: Dict[str, List[Dict[str, Any]]]) -> List[IntegrityError]:
        """Validate time slot duration."""
        errors: List[IntegrityError] = []
        
        for idx, record in enumerate(records):
            start_time = record.get('start_time')
            end_time = record.get('end_time')
            duration_minutes = record.get('duration_minutes')
            
            if start_time and end_time:
                try:
                    # Calculate actual duration
                    if isinstance(start_time, str):
                        start_time = datetime.strptime(start_time, '%H:%M:%S').time()
                    if isinstance(end_time, str):
                        end_time = datetime.strptime(end_time, '%H:%M:%S').time()
                    
                    start_minutes = start_time.hour * 60 + start_time.minute
                    end_minutes = end_time.hour * 60 + end_time.minute
                    
                    if end_minutes <= start_minutes:
                        errors.append(IntegrityError(
                            severity='error',
                            category='business_rule',
                            entity_type=entity_type,
                            record_id=str(idx),
                            field='end_time',
                            message="End time must be after start time",
                            details={'start_time': str(start_time), 'end_time': str(end_time)}
                        ))
                    else:
                        actual_duration = end_minutes - start_minutes
                        
                        if duration_minutes and abs(actual_duration - int(duration_minutes)) > 5:
                            errors.append(IntegrityError(
                                severity='warning',
                                category='business_rule',
                                entity_type=entity_type,
                                record_id=str(idx),
                                field='duration_minutes',
                                message=f"Duration mismatch: specified {duration_minutes} min, actual {actual_duration} min",
                                details={
                                    'specified_duration': duration_minutes,
                                    'actual_duration': actual_duration
                                }
                            ))
                
                except Exception as e:
                    errors.append(IntegrityError(
                        severity='warning',
                        category='business_rule',
                        entity_type=entity_type,
                        record_id=str(idx),
                        field='start_time',
                        message=f"Error parsing time values: {e}"
                    ))
        
        return errors
    
    def _validate_time_slot_overlap(self, records: List[Dict[str, Any]], entity_type: str, all_data: Dict[str, List[Dict[str, Any]]]) -> List[IntegrityError]:
        """Check for overlapping time slots."""
        errors: List[IntegrityError] = []
        
        time_ranges: List[Tuple[int, time, time, str]] = []
        for idx, record in enumerate(records):
            try:
                start_time = record.get('start_time')
                end_time = record.get('end_time')
                
                if start_time and end_time:
                    if isinstance(start_time, str):
                        start_time = datetime.strptime(start_time, '%H:%M:%S').time()
                    if isinstance(end_time, str):
                        end_time = datetime.strptime(end_time, '%H:%M:%S').time()
                    
                    time_ranges.append((idx, start_time, end_time, record.get('name', f'Slot {idx}')))
            except Exception:
                continue
        
        # Check for overlaps
        for i, (idx1, start1, end1, name1) in enumerate(time_ranges):
            for j, (idx2, start2, end2, name2) in enumerate(time_ranges[i+1:], i+1):
                # Convert to minutes for easier comparison
                start1_min = start1.hour * 60 + start1.minute
                end1_min = end1.hour * 60 + end1.minute
                start2_min = start2.hour * 60 + start2.minute
                end2_min = end2.hour * 60 + end2.minute
                
                # Check if time ranges overlap
                if not (end1_min <= start2_min or end2_min <= start1_min):
                    errors.append(IntegrityError(
                        severity='warning',
                        category='business_rule',
                        entity_type=entity_type,
                        record_id=str(idx1),
                        field='start_time',
                        message=f"Time slot overlaps with '{name2}'",
                        details={
                            'overlapping_slot': name2,
                            'slot1_time': f"{start1} to {end1}",
                            'slot2_time': f"{start2} to {end2}"
                        }
                    ))
        
        return errors
    
    def _validate_exam_scheduling(self, records: List[Dict[str, Any]], entity_type: str, all_data: Dict[str, List[Dict[str, Any]]]) -> List[IntegrityError]:
        """Validate exam scheduling constraints."""
        errors: List[IntegrityError] = []
        
        for idx, record in enumerate(records):
            exam_date = record.get('exam_date')
            time_slot_id = record.get('time_slot_id')
            expected_students = record.get('expected_students')
            
            # Check if exam date is reasonable
            if exam_date:
                try:
                    if isinstance(exam_date, str):
                        exam_date = datetime.strptime(exam_date, '%Y-%m-%d').date()
                    
                    # Check if exam is scheduled too far in the past or future
                    today = date.today()
                    days_diff = (exam_date - today).days
                    
                    if days_diff < -30:
                        errors.append(IntegrityError(
                            severity='warning',
                            category='business_rule',
                            entity_type=entity_type,
                            record_id=str(idx),
                            field='exam_date',
                            message=f"Exam date is {abs(days_diff)} days in the past",
                            details={'exam_date': str(exam_date), 'days_ago': abs(days_diff)}
                        ))
                    elif days_diff > 365:
                        errors.append(IntegrityError(
                            severity='warning',
                            category='business_rule',
                            entity_type=entity_type,
                            record_id=str(idx),
                            field='exam_date',
                            message=f"Exam date is {days_diff} days in the future",
                            details={'exam_date': str(exam_date), 'days_ahead': days_diff}
                        ))
                
                except Exception:
                    errors.append(IntegrityError(
                        severity='error',
                        category='business_rule',
                        entity_type=entity_type,
                        record_id=str(idx),
                        field='exam_date',
                        message=f"Invalid exam date format: {exam_date}"
                    ))
            
            # Check expected students count
            if expected_students is not None:
                try:
                    count = int(expected_students)
                    if count < 0:
                        errors.append(IntegrityError(
                            severity='error',
                            category='business_rule',
                            entity_type=entity_type,
                            record_id=str(idx),
                            field='expected_students',
                            message="Expected students count cannot be negative",
                            details={'expected_students': count}
                        ))
                    elif count == 0:
                        errors.append(IntegrityError(
                            severity='warning',
                            category='business_rule',
                            entity_type=entity_type,
                            record_id=str(idx),
                            field='expected_students',
                            message="No students expected for exam",
                            details={'expected_students': count}
                        ))
                except (ValueError, TypeError):
                    errors.append(IntegrityError(
                        severity='error',
                        category='business_rule',
                        entity_type=entity_type,
                        record_id=str(idx),
                        field='expected_students',
                        message=f"Invalid expected students format: {expected_students}"
                    ))
        
        return errors
    
    def _validate_exam_duration(self, records: List[Dict[str, Any]], entity_type: str, all_data: Dict[str, List[Dict[str, Any]]]) -> List[IntegrityError]:
        """Validate exam duration."""
        errors: List[IntegrityError] = []
        
        for idx, record in enumerate(records):
            duration_minutes = record.get('duration_minutes')
            
            if duration_minutes is not None:
                try:
                    duration = int(duration_minutes)
                    
                    if duration <= 0:
                        errors.append(IntegrityError(
                            severity='error',
                            category='business_rule',
                            entity_type=entity_type,
                            record_id=str(idx),
                            field='duration_minutes',
                            message="Exam duration must be positive",
                            details={'duration_minutes': duration}
                        ))
                    elif duration < 60:
                        errors.append(IntegrityError(
                            severity='warning',
                            category='business_rule',
                            entity_type=entity_type,
                            record_id=str(idx),
                            field='duration_minutes',
                            message=f"Very short exam duration: {duration} minutes",
                            details={'duration_minutes': duration}
                        ))
                    elif duration > 300:  # 5 hours
                        errors.append(IntegrityError(
                            severity='warning',
                            category='business_rule',
                            entity_type=entity_type,
                            record_id=str(idx),
                            field='duration_minutes',
                            message=f"Very long exam duration: {duration} minutes",
                            details={'duration_minutes': duration}
                        ))
                
                except (ValueError, TypeError):
                    errors.append(IntegrityError(
                        severity='error',
                        category='business_rule',
                        entity_type=entity_type,
                        record_id=str(idx),
                        field='duration_minutes',
                        message=f"Invalid duration format: {duration_minutes}"
                    ))
        
        return errors
    
    def _validate_registration_eligibility(self, records: List[Dict[str, Any]], entity_type: str, all_data: Dict[str, List[Dict[str, Any]]]) -> List[IntegrityError]:
        """Validate course registration eligibility."""
        errors: List[IntegrityError] = []
        
        # Get related data
        students = all_data.get('students', [])
        courses = all_data.get('courses', [])
        
        student_map = {s.get('id'): s for s in students if s.get('id')}
        course_map = {c.get('id'): c for c in courses if c.get('id')}
        
        for idx, record in enumerate(records):
            student_id = record.get('student_id')
            course_id = record.get('course_id')
            
            if student_id in student_map and course_id in course_map:
                student = student_map[student_id]
                course = course_map[course_id]
                
                student_level = student.get('current_level')
                course_level = course.get('course_level')
                
                if student_level and course_level:
                    try:
                        s_level = int(student_level)
                        c_level = int(course_level)
                        
                        # Check if student is eligible for course level
                        if s_level < c_level:
                            errors.append(IntegrityError(
                                severity='warning',
                                category='business_rule',
                                entity_type=entity_type,
                                record_id=str(idx),
                                field='course_id',
                                message=f"Student level ({s_level}) below course level ({c_level})",
                                details={
                                    'student_level': s_level,
                                    'course_level': c_level,
                                    'student_id': student_id,
                                    'course_id': course_id
                                }
                            ))
                    except (ValueError, TypeError):
                        pass
        
        return errors
    
    def _validate_registration_duplicates(self, records: List[Dict[str, Any]], entity_type: str, all_data: Dict[str, List[Dict[str, Any]]]) -> List[IntegrityError]:
        """Check for duplicate course registrations."""
        errors: List[IntegrityError] = []
        
        # Track registrations by (student_id, course_id, session_id)
        registrations: Dict[Tuple[Any, Any, Any], List[Tuple[int, Dict[str, Any]]]] = defaultdict(list)
        
        for idx, record in enumerate(records):
            student_id = record.get('student_id')
            course_id = record.get('course_id')
            session_id = record.get('session_id')
            
            if student_id and course_id and session_id:
                key = (student_id, course_id, session_id)
                registrations[key].append((idx, record))
        
        # Check for duplicates
        for key, reg_list in registrations.items():
            if len(reg_list) > 1:
                for idx, record in reg_list:
                    errors.append(IntegrityError(
                        severity='error',
                        category='duplicate',
                        entity_type=entity_type,
                        record_id=str(idx),
                        field='student_id',
                        message="Duplicate course registration",
                        details={
                            'student_id': key[0],
                            'course_id': key[1],
                            'session_id': key[2],
                            'occurrences': len(reg_list)
                        }
                    ))
        
        return errors
    
    def _generate_summary(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        errors: List[IntegrityError],
        warnings: List[IntegrityError]
    ) -> Dict[str, Any]:
        """Generate integrity check summary."""
        
        error_by_category = Counter(e.category for e in errors)
        error_by_entity = Counter(e.entity_type for e in errors)
        warning_by_category = Counter(w.category for w in warnings)
        
        return {
            'total_entities': len(data),
            'total_records': sum(len(records) for records in data.values()),
            'records_by_entity': {entity: len(records) for entity, records in data.items()},
            'total_errors': len(errors),
            'total_warnings': len(warnings),
            'errors_by_category': dict(error_by_category),
            'errors_by_entity': dict(error_by_entity),
            'warnings_by_category': dict(warning_by_category),
            'most_common_errors': error_by_category.most_common(5),
            'entities_with_errors': list(error_by_entity.keys())
        }

# Export main components
__all__ = [
    'DataIntegrityChecker',
    'IntegrityError',
    'IntegrityCheckResult'
]