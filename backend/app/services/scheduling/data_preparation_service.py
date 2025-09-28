# backend/app/services/scheduling/data_preparation_service.py
# FIXED VERSION - Data Preparation Service with Exact Problem Model Compatibility
from __future__ import annotations
from datetime import datetime, date, time, timedelta
import math
from typing import Dict, List, Set, Optional, Any, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from collections import defaultdict
import logging
import uuid
from sqlalchemy import text
import json


logger = logging.getLogger(__name__)


@dataclass
class ProblemModelCompatibleDataset:
    """Dataset structured EXACTLY as the Problem Model expects"""

    # Core entities - must match problem_model.py field names exactly
    exams: List[Dict[str, Any]] = field(default_factory=list)
    rooms: List[Dict[str, Any]] = field(default_factory=list)
    students: List[Dict[str, Any]] = field(default_factory=list)
    invigilators: List[Dict[str, Any]] = field(default_factory=list)
    instructors: List[Dict[str, Any]] = field(default_factory=list)
    staff: List[Dict[str, Any]] = field(default_factory=list)

    # Days and timeslots structure
    days: List[Dict[str, Any]] = field(default_factory=list)
    timeslots: List[Dict[str, Any]] = field(default_factory=list)

    # Relationships - critical for problem model
    course_registrations: List[Dict[str, Any]] = field(default_factory=list)
    student_exam_mappings: Dict[str, Set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )

    # Metadata
    session_id: UUID = field(default_factory=uuid4)
    date_range_config: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExactDataMapper:
    """Maps database data to EXACT problem model expectations"""

    @staticmethod
    def map_room_to_problem_model(db_room: Dict) -> Dict[str, Any]:
        """Map database room to EXACT problem model format"""
        # Handle adjacent_seat_pairs carefully as it may be null or an object
        adjacent_pairs = db_room.get("adjacent_seat_pairs")
        if not isinstance(adjacent_pairs, list):
            # If it's null or a dict like {"adjacent_rooms": [...]}, default to empty list.
            # The problem model expects a List[Tuple[int, int]] which this data doesn't match.
            adjacent_pairs = []

        return {
            # Required fields - must match Room class in problem_model.py
            "id": UUID(str(db_room["id"])),
            "code": db_room.get("code", ""),
            "capacity": db_room.get("capacity", 0),
            "exam_capacity": db_room.get("exam_capacity", db_room.get("capacity", 0)),
            # Optional fields
            "has_computers": db_room.get("has_computers", False),
            "adjacent_seat_pairs": adjacent_pairs,
            # Additional fields for reference
            "name": db_room.get("name", ""),
            "building_name": db_room.get("building_name"),
            "has_projector": db_room.get("has_projector", False),
            "has_ac": db_room.get("has_ac", False),
            "overbookable": db_room.get("overbookable", False),
            "max_inv_per_room": db_room.get("max_inv_per_room", 2),
        }

    @staticmethod
    def map_invigilator_to_problem_model(db_staff: Dict) -> Dict[str, Any]:
        """Map database staff to EXACT problem model invigilator format"""
        return {
            # Required fields - must match Invigilator class in problem_model.py
            "id": UUID(str(db_staff["id"])),
            "name": db_staff.get(
                "name", f"Staff {db_staff.get('staff_number', 'Unknown')}"
            ),
            # Optional fields with defaults
            "email": db_staff.get("email"),
            "department": db_staff.get("department"),
            "can_invigilate": db_staff.get("can_invigilate", True),
            "max_concurrent_exams": db_staff.get("max_concurrent_exams", 1),
            "max_students_per_exam": db_staff.get("max_students_per_exam", 50),
            "availability": {},
            # Additional staff fields
            "staff_number": db_staff.get("staff_number"),
            "staff_type": db_staff.get("staff_type"),
            "max_daily_sessions": db_staff.get("max_daily_sessions", 2),
            "max_consecutive_sessions": db_staff.get("max_consecutive_sessions", 1),
        }

    @staticmethod
    def map_timeslot_to_problem_model(db_timeslot: Dict) -> Dict[str, Any]:
        """Map timeslot to EXACT problem model format"""
        return {
            "id": UUID(str(db_timeslot["id"])),
            "parent_day_id": db_timeslot.get("parent_day_id"),
            "name": db_timeslot.get("name", ""),
            "start_time": db_timeslot.get("start_time"),
            "end_time": db_timeslot.get("end_time"),
            "duration_minutes": db_timeslot.get("duration_minutes", 180),
        }

    @staticmethod
    def _validate_and_convert_uuid(value: Any, field_name: str = "id") -> UUID:
        """Validate and convert value to UUID with comprehensive error handling"""
        if value is None:
            raise ValueError(f"{field_name} cannot be None")

        try:
            if isinstance(value, UUID):
                return value
            elif isinstance(value, str):
                # Remove any whitespace and validate UUID format
                cleaned_value = value.strip()
                if not cleaned_value:
                    raise ValueError(f"{field_name} cannot be empty string")
                return UUID(cleaned_value)
            elif isinstance(value, int):
                # Convert integer to UUID string representation
                return UUID(str(value))
            else:
                raise ValueError(f"Unsupported type for {field_name}: {type(value)}")
        except ValueError as e:
            raise ValueError(f"Invalid UUID format for {field_name} '{value}': {e}")

    @staticmethod
    def _validate_required_fields(
        data: Dict[str, Any], required_fields: List[str], context: str = ""
    ) -> None:
        """Validate that required fields are present and non-empty"""
        missing_fields = []
        invalid_fields = []

        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
            elif data[field] in (None, "", 0, []):
                invalid_fields.append(field)

        errors = []
        if missing_fields:
            errors.append(f"Missing required fields: {missing_fields}")
        if invalid_fields:
            errors.append(f"Empty/invalid fields: {invalid_fields}")

        if errors:
            error_msg = f"Validation failed for {context}: {'; '.join(errors)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    @staticmethod
    def map_exam_to_problem_model(db_exam: Dict) -> Dict[str, Any]:
        """Map database exam to EXACT problem model format with enhanced validation"""
        try:
            # Validate required fields
            ExactDataMapper._validate_required_fields(
                db_exam,
                ["id", "course_id", "duration_minutes"],
                f"exam {db_exam.get('id', 'unknown')}",
            )

            # Convert UUIDs with validation
            exam_id = ExactDataMapper._validate_and_convert_uuid(
                db_exam["id"], "exam_id"
            )
            course_id = ExactDataMapper._validate_and_convert_uuid(
                db_exam["course_id"], "course_id"
            )

            # Validate numeric fields
            duration = db_exam.get("duration_minutes", 180)
            # Define the maximum possible duration for a single day
            MAX_DURATION_MINUTES = 540  # 3 slots * 180 minutes/slot

            if not isinstance(duration, (int, float)) or duration <= 0:
                logger.warning(
                    f"Invalid duration_minutes for exam {exam_id}: {duration}, using default 180"
                )
                duration = 180
            elif duration > MAX_DURATION_MINUTES:
                logger.error(
                    f"CRITICAL: Exam {exam_id} has a duration of {duration} minutes, which exceeds the daily maximum of {MAX_DURATION_MINUTES}. Capping duration to prevent infeasibility."
                )
                # Cap the duration to the maximum possible value to allow scheduling.
                # The ideal solution is to fix the data in the database.
                duration = MAX_DURATION_MINUTES

            expected_students = db_exam.get("expected_students", 0)
            if not isinstance(expected_students, (int, float)) or expected_students < 0:
                logger.warning(
                    f"Invalid expected_students for exam {exam_id}: {expected_students}, using 0"
                )
                expected_students = 0

            exam_data = {
                "id": exam_id,
                "course_id": course_id,
                "duration_minutes": int(duration),
                "expected_students": int(expected_students),
                "is_practical": bool(db_exam.get("is_practical", False)),
                "morning_only": bool(db_exam.get("morning_only", False)),
                "actual_student_count": int(db_exam.get("actual_student_count", 0)),
                "students": set(),
                "course_code": db_exam.get("course_code", f"COURSE_{course_id}"),
                "course_title": db_exam.get("course_title", "Unknown Course"),
                "requires_projector": bool(db_exam.get("requires_projector", False)),
                "requires_special_arrangements": bool(
                    db_exam.get("requires_special_arrangements", False)
                ),
                "is_common": bool(db_exam.get("is_common", False)),
                "status": db_exam.get("status", "pending"),
                "prerequisite_exams": set(),
                "allowed_rooms": set(),
                "instructor_id": None,
            }

            # Validate student count consistency
            actual_count = exam_data["actual_student_count"]
            if actual_count > exam_data["expected_students"]:
                exam_data["expected_students"] = actual_count
                logger.info(
                    f"Adjusted expected_students to {actual_count} for exam {exam_id}"
                )

            return exam_data

        except Exception as e:
            logger.error(f"Failed to map exam data: {e}")
            raise

    @staticmethod
    def map_student_to_problem_model(db_student: Dict) -> Dict[str, Any]:
        """Map database student to EXACT problem model format with enhanced validation"""
        try:
            ExactDataMapper._validate_required_fields(
                db_student, ["id"], f"student {db_student.get('id', 'unknown')}"
            )

            student_id = ExactDataMapper._validate_and_convert_uuid(
                db_student["id"], "student_id"
            )

            return {
                "id": student_id,
                "department": db_student.get("department", "Unknown Department"),
                "registered_courses": set(),
                "matric_number": db_student.get("matric_number", f"STU_{student_id}"),
                "current_level": int(db_student.get("current_level", 100)),
                "student_type": db_student.get("student_type", "regular"),
                "programme_name": db_student.get("programme_name", "Unknown Programme"),
            }

        except Exception as e:
            logger.error(f"Failed to map student data: {e}")
            raise


class ExactDataFlowService:
    """Service that ensures EXACT data compatibility with problem model"""

    def __init__(self, session):
        self.session = session
        self.mapper = ExactDataMapper()

    # @track_data_flow("build_dataset")
    async def build_exact_problem_model_dataset(
        self, session_id: UUID
    ) -> ProblemModelCompatibleDataset:
        """Build dataset with EXACT problem model compatibility and comprehensive validation"""
        logger.info(f"Building EXACT problem model dataset for session {session_id}")

        try:
            # Phase 1: Validate raw data retrieval from PostgreSQL function
            raw_data = await self._validate_and_retrieve_raw_data(session_id)

            # Phase 2: Map entities with validation
            mapped_entities = await self._map_entities_with_validation(raw_data)

            # Phase 3: Build and validate relationships
            relationships = await self._build_and_validate_relationships(
                mapped_entities, raw_data
            )

            # Phase 4: Create final dataset with integrity check
            dataset = self._create_validated_dataset(
                session_id, mapped_entities, relationships
            )

            # Phase 5: Final integrity validation
            self._validate_final_dataset_integrity(dataset)

            # Log final dataset statistics
            self._log_dataset_statistics(dataset)

            logger.info(
                f"Successfully built validated dataset: {len(dataset.exams)} exams, "
                f"{len(dataset.students)} students, {len(dataset.rooms)} rooms"
            )

            return dataset

        except Exception as e:
            logger.error(f"Error building exact problem model dataset: {e}")
            raise

    def _log_dataset_statistics(self, dataset: ProblemModelCompatibleDataset):
        """Log detailed dataset statistics"""
        stats = {
            "exams_count": len(dataset.exams),
            "rooms_count": len(dataset.rooms),
            "students_count": len(dataset.students),
            "invigilators_count": len(dataset.invigilators),
            "days_count": len(dataset.days),
            "timeslots_count": len(dataset.timeslots),
            "total_registrations": len(dataset.course_registrations),
            "student_exam_mappings": len(dataset.student_exam_mappings),
        }
        logger.info(f"Dataset Statistics: {stats}")

    async def _validate_and_retrieve_raw_data(self, session_id: UUID) -> Dict[str, Any]:
        """
        Validate and retrieve raw data by calling the PostgreSQL function.
        """
        logger.info(f"Executing PostgreSQL function for session {session_id}")
        try:
            # Construct the SQL query to call the function
            query = text("SELECT exam_system.get_scheduling_dataset(:session_id)")
            result = await self.session.execute(query, {"session_id": session_id})

            # The function returns a single row with a single column containing the JSONB
            raw_data = result.scalar_one_or_none()

            if not raw_data:
                raise ValueError("PostgreSQL function returned no data.")

            # The database driver (asyncpg) automatically decodes JSONB to a Python dict
            if not isinstance(raw_data, dict):
                # Fallback if the result is a string that needs parsing
                raw_data = json.loads(raw_data)

            # Validate raw data structure
            if not raw_data or not isinstance(raw_data, dict):
                raise ValueError("Invalid raw data structure from PostgreSQL function")

            # Check for critical data components
            critical_components = ["exams", "rooms", "students"]
            missing_components = [
                comp for comp in critical_components if not raw_data.get(comp)
            ]

            if missing_components:
                raise ValueError(
                    f"Missing critical data components from PG function: {missing_components}"
                )

            logger.info(
                f"Retrieved valid raw data: {len(raw_data.get('exams', []))} exams"
            )
            return raw_data

        except Exception as e:
            logger.error(f"Failed to retrieve raw data for session {session_id}: {e}")
            raise

    # @track_data_flow("map_entities")
    async def _map_entities_with_validation(
        self, raw_data: Dict[str, Any]
    ) -> Dict[str, List[Dict]]:
        """Map entities with comprehensive validation"""
        mapped_entities = {}

        # Map exams with validation
        exams = []
        for exam_data in raw_data.get("exams", []):
            try:
                mapped_exam = self.mapper.map_exam_to_problem_model(exam_data)
                exams.append(mapped_exam)
            except Exception as e:
                logger.error(f"Failed to map exam: {e}")
                continue
        mapped_entities["exams"] = exams

        # Map rooms with validation
        rooms = []
        for room_data in raw_data.get("rooms", []):
            try:
                mapped_room = self.mapper.map_room_to_problem_model(room_data)
                rooms.append(mapped_room)
            except Exception as e:
                logger.error(f"Failed to map room: {e}")
                continue
        mapped_entities["rooms"] = rooms

        # Map students with validation
        students = []
        for student_data in raw_data.get("students", []):
            try:
                mapped_student = self.mapper.map_student_to_problem_model(student_data)
                students.append(mapped_student)
            except Exception as e:
                logger.error(f"Failed to map student: {e}")
                continue
        mapped_entities["students"] = students

        # Map staff
        staff = []
        for staff_data in raw_data.get("staff", []):
            try:
                # Use the invigilator mapper as it contains all necessary fields
                mapped_staff = self.mapper.map_invigilator_to_problem_model(staff_data)
                staff.append(mapped_staff)
            except Exception as e:
                logger.error(
                    f"Failed to map staff member {staff_data.get('id', 'unknown')}: {e}"
                )
                continue
        mapped_entities["staff"] = staff

        # Map invigilators (from invigilators key)
        invigilators = []
        for invigilator_data in raw_data.get("invigilators", []):
            try:
                mapped_invigilator = self.mapper.map_invigilator_to_problem_model(
                    invigilator_data
                )
                invigilators.append(mapped_invigilator)
            except Exception as e:
                logger.error(
                    f"Failed to map invigilator from staff {invigilator_data.get('id', 'unknown')}: {e}"
                )
                continue
        mapped_entities["invigilators"] = invigilators

        # Validate we have invigilators if we have exams
        if len(exams) > 0 and len(invigilators) == 0:
            logger.warning(
                "No valid invigilators were mapped from the provided staff data."
            )

        # Validate we have minimum required entities
        if len(exams) == 0:
            raise ValueError("No valid exams could be mapped")
        if len(rooms) == 0:
            raise ValueError("No valid rooms could be mapped")

        return mapped_entities

    async def validate_and_filter_phantom_exams(
        self, exams: List[Dict[str, Any]], student_exam_mappings: Dict[str, Set[str]]
    ) -> List[Dict[str, Any]]:
        """
        Detect and filter phantom exams (exams with no student mappings)
        This prevents model infeasibility caused by exams that cannot be scheduled.
        """
        logger.info("🔍 Validating and filtering phantom exams...")

        phantom_exams = []
        valid_exams = []

        for exam in exams:
            try:
                exam_id_str = str(exam["id"])
                has_students = False

                # Check student-exam mappings
                for student_id, exam_set in student_exam_mappings.items():
                    if exam_id_str in exam_set:
                        has_students = True
                        break

                # Check direct students field
                if not has_students and exam.get("students"):
                    has_students = len(exam["students"]) > 0

                # Check actual student count
                if not has_students and exam.get("actual_student_count", 0) > 0:
                    has_students = True

                if has_students:
                    valid_exams.append(exam)
                else:
                    phantom_exams.append(
                        {
                            "id": exam_id_str,
                            "course_code": exam.get("course_code", "Unknown"),
                        }
                    )
                    logger.warning(
                        f"👻 PHANTOM EXAM: {exam_id_str} - {exam.get('course_code')}"
                    )

            except Exception as e:
                logger.error(f"Error validating exam {exam.get('id', 'unknown')}: {e}")
                continue

        logger.info(
            f"📊 Valid exams: {len(valid_exams)}, Phantom exams filtered: {len(phantom_exams)}"
        )

        if len(valid_exams) == 0 and len(phantom_exams) > 0:
            raise ValueError(
                "No valid exams found after phantom filtering! All exams lack student registrations."
            )

        return valid_exams

    # @track_data_flow("build_relationships")
    async def _build_and_validate_relationships(
        self, mapped_entities: Dict[str, List[Dict]], raw_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build and validate all relationships between entities with comprehensive error handling"""
        logger.info("Building and validating entity relationships...")

        try:
            relationships = {}

            # Extract entities
            exams = mapped_entities.get("exams", [])
            raw_registrations = raw_data.get("course_registrations", [])
            raw_student_exam_mappings = raw_data.get("student_exam_mappings", {})

            # Build student-exam mappings from the raw JSON data
            student_exam_mappings = {
                str(student_id): {str(exam_id) for exam_id in exam_ids}
                for student_id, exam_ids in raw_student_exam_mappings.items()
            }

            # CRITICAL: Filter phantom exams before model creation
            filtered_exams = await self.validate_and_filter_phantom_exams(
                exams, student_exam_mappings
            )

            # Update with filtered exams
            mapped_entities["exams"] = filtered_exams
            relationships["student_exam_mappings"] = student_exam_mappings

            # Build course registrations
            course_registrations = self._build_course_registrations(raw_registrations)
            relationships["course_registrations"] = course_registrations

            # Populate exam student lists
            populated_exams = self._populate_exam_students(
                filtered_exams, student_exam_mappings
            )
            mapped_entities["exams"] = populated_exams

            # Days and timeslots are handled by the problem model as per user request
            relationships["timeslots"] = raw_data.get("timeslots", [])
            relationships["days"] = raw_data.get("days", [])

            # Validate relationship integrity
            self._validate_relationship_integrity(mapped_entities, relationships)

            logger.info(
                f"Successfully built relationships: {len(student_exam_mappings)} student mappings, "
                f"{len(course_registrations)} course registrations"
            )

            return relationships

        except Exception as e:
            logger.error(f"Error building relationships: {e}")
            raise

    def _create_validated_dataset(
        self,
        session_id: UUID,
        mapped_entities: Dict[str, List[Dict]],
        relationships: Dict[str, Any],
    ) -> ProblemModelCompatibleDataset:
        """Create final validated dataset with all entities and relationships"""
        logger.info("Creating final validated dataset...")

        try:
            dataset = ProblemModelCompatibleDataset(session_id=session_id)

            # Set core entities
            dataset.exams = mapped_entities.get("exams", [])
            dataset.rooms = mapped_entities.get("rooms", [])
            dataset.students = mapped_entities.get("students", [])
            dataset.invigilators = mapped_entities.get("invigilators", [])
            dataset.instructors = mapped_entities.get("instructors", [])
            dataset.staff = mapped_entities.get("staff", [])

            # Set relationships
            dataset.course_registrations = relationships.get("course_registrations", [])
            dataset.student_exam_mappings = relationships.get(
                "student_exam_mappings", defaultdict(set)
            )

            # Set timeslots and days
            dataset.timeslots = relationships.get("timeslots", [])
            dataset.days = relationships.get("days", [])

            # Set metadata
            dataset.date_range_config = self._build_date_range_config(dataset.timeslots)
            dataset.metadata = {
                "created_at": datetime.now().isoformat(),
                "total_exams": len(dataset.exams),
                "total_students": len(dataset.students),
                "total_rooms": len(dataset.rooms),
                "total_timeslots": len(dataset.timeslots),
                "total_days": len(dataset.days),
                "dataset_version": "1.0",
            }

            logger.info(
                f"Created dataset with {len(dataset.exams)} exams, {len(dataset.students)} students, "
                f"{len(dataset.rooms)} rooms, {len(dataset.timeslots)} timeslots"
            )

            return dataset

        except Exception as e:
            logger.error(f"Error creating validated dataset: {e}")
            raise

    def _build_course_registrations(
        self, raw_registrations: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Build course registrations in problem model format"""
        registrations = []

        for reg in raw_registrations:
            try:
                registration = {
                    "student_id": UUID(str(reg["student_id"])),
                    "course_id": UUID(str(reg["course_id"])),
                    "registration_date": reg.get("registration_date"),
                    "academic_session": reg.get("academic_session"),
                }
                registrations.append(registration)
            except Exception as e:
                logger.warning(f"Failed to process registration: {e}")
                continue

        return registrations

    async def _build_timeslots_and_days(
        self, raw_data: Dict[str, Any]
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        CRITICAL FIX: Build timeslots and days structure from raw data by grouping
        timeslots by date, instead of relying on a non-existent 'parent_day_id'.
        """
        timeslots = []
        days = []
        db_timeslots = raw_data.get("timeslots", [])

        if not db_timeslots:
            logger.warning("No timeslots found in raw data to build days.")
            return [], []

        # Group timeslots by their date
        slots_by_date = defaultdict(list)
        for ts_data in db_timeslots:
            try:
                # Ensure start_time is a time object to extract its date part for grouping
                start_time_obj = ts_data.get("start_time")
                if isinstance(start_time_obj, time):
                    # We can't get a date from a time object alone, assume today for grouping logic
                    # A more robust solution would require a date field on the timeslot in the DB
                    # For now, we'll group them into a single day as a fallback.
                    # A better approach requires exam_date on the exam object.
                    # Let's assume for now that all timeslots belong to a generic date.
                    # This is a limitation of the provided schema.
                    # A better fix would be to generate days based on problem's start/end dates.
                    # We'll use a simplified grouping here. Let's group by name.
                    slots_by_date[ts_data["name"]].append(ts_data)
                else:
                    slots_by_date[start_time_obj.date()].append(ts_data)

            except AttributeError:
                logger.warning(
                    f"Timeslot data missing 'start_time' or it's not a time object: {ts_data}"
                )
                continue

        # If grouping by date failed (e.g. only time objects), generate days from problem model
        if all(isinstance(k, str) for k in slots_by_date.keys()):
            logger.warning(
                "Could not group timeslots by date. Days will be generated by the problem model."
            )
            # Just map the timeslots and let the problem model handle day creation.
            for ts_data in db_timeslots:
                try:
                    timeslots.append(self.mapper.map_timeslot_to_problem_model(ts_data))
                except Exception as e:
                    logger.error(f"Failed to map timeslot: {e}")
            return timeslots, []

        # Create a Day for each unique date and link its timeslots
        for date_obj, date_slots_data in slots_by_date.items():
            day_id = uuid4()
            day_data = {"id": day_id, "date": date_obj, "timeslots": []}

            for ts_data in date_slots_data:
                try:
                    ts_data["parent_day_id"] = (
                        day_id  # Link timeslot to its new parent day
                    )
                    mapped_timeslot = self.mapper.map_timeslot_to_problem_model(ts_data)
                    day_data["timeslots"].append(mapped_timeslot)
                    timeslots.append(
                        mapped_timeslot
                    )  # Also add to the flat list for the dataset
                except Exception as e:
                    logger.error(
                        f"Failed to map timeslot {ts_data.get('id', 'unknown')}: {e}"
                    )

            days.append(day_data)

        logger.info(
            f"Correctly built {len(days)} days and {len(timeslots)} timeslots from raw data."
        )
        return timeslots, days

    def _validate_relationship_integrity(
        self, mapped_entities: Dict[str, List[Dict]], relationships: Dict[str, Any]
    ) -> None:
        """Validate the integrity of all relationships"""
        issues = []

        # Check student-exam mappings consistency
        student_exam_mappings = relationships.get("student_exam_mappings", {})
        exams = mapped_entities.get("exams", [])
        students = mapped_entities.get("students", [])

        # Verify all mapped students exist
        student_ids = {str(student["id"]) for student in students}
        for student_id in student_exam_mappings.keys():
            if student_id not in student_ids:
                issues.append(
                    f"Student {student_id} in mappings but not in student list"
                )

        # Verify all mapped exams exist
        exam_ids = {str(exam["id"]) for exam in exams}
        for student_id, exam_set in student_exam_mappings.items():
            for exam_id in exam_set:
                if exam_id not in exam_ids:
                    issues.append(f"Exam {exam_id} in mappings but not in exam list")

        if issues:
            logger.warning(f"Relationship integrity issues found: {issues}")

    def _build_date_range_config(self, timeslots: List[Dict]) -> Dict[str, Any]:
        """Build date range configuration from timeslots"""
        if not timeslots:
            return {}

        # Extract unique dates from timeslots
        dates = set()
        for ts in timeslots:
            start_time = ts.get("start_time")
            if start_time and hasattr(start_time, "date"):
                dates.add(start_time.date())

        if dates:
            min_date = min(dates)
            max_date = max(dates)
            return {
                "start_date": min_date.isoformat(),
                "end_date": max_date.isoformat(),
                "total_days": (max_date - min_date).days + 1,
                "exam_days": len(dates),
            }

        return {}

    def _validate_final_dataset_integrity(
        self, dataset: ProblemModelCompatibleDataset
    ) -> None:
        """Enhanced dataset validation with phantom exam handling - FIXED VERSION"""
        logger.info("🔍 Performing comprehensive dataset integrity validation...")

        integrity_issues = []
        warnings = []

        # Basic validation
        if len(dataset.exams) == 0:
            integrity_issues.append("No exams in dataset")
        if len(dataset.rooms) == 0:
            integrity_issues.append("No rooms in dataset")

        # Phantom exam detection and AUTOMATIC REMOVAL
        phantom_exams = []
        valid_exams = []

        for exam in dataset.exams:
            exam_students = exam.get("students", set())
            student_count = (
                len(exam_students) if isinstance(exam_students, (list, set)) else 0
            )

            # Check if exam has students via student_exam_mappings
            exam_id_str = str(exam.get("id"))
            has_students_in_mappings = False
            for student_id, exam_ids in dataset.student_exam_mappings.items():
                if exam_id_str in exam_ids:
                    has_students_in_mappings = True
                    break

            if student_count > 0 or has_students_in_mappings:
                valid_exams.append(exam)
            else:
                phantom_exams.append(
                    {
                        "id": exam.get("id"),
                        "course_code": exam.get("course_code", "Unknown"),
                    }
                )

        # FIXED: Automatically remove phantom exams instead of failing
        if phantom_exams:
            phantom_count = len(phantom_exams)
            logger.warning(f"🚨 Removing {phantom_count} phantom exams from dataset")

            for phantom in phantom_exams:
                logger.warning(
                    f"  👻 Removing phantom exam: {phantom['course_code']} (ID: {phantom['id']})"
                )

            # Replace exams list with only valid exams
            dataset.exams = valid_exams
            warnings.append(f"Removed {phantom_count} phantom exams")

        # Check if we have enough exams after removal
        if len(dataset.exams) == 0 and len(phantom_exams) > 0:
            integrity_issues.append("No valid exams remaining after phantom removal")

        # Report results
        if integrity_issues:
            issues_str = "; ".join(integrity_issues)
            logger.error(f"💥 CRITICAL dataset issues: {issues_str}")
            raise ValueError(f"Critical dataset integrity issues: {issues_str}")

        if warnings:
            logger.warning(f"Dataset warnings: {'; '.join(warnings)}")

        logger.info("✅ Dataset integrity validation passed!")

    async def _build_student_exam_mappings(
        self, exams, registrations, raw_registrations
    ):
        """Enhanced logging version"""
        logger.info("=== STUDENT-EXAM MAPPING PHASE START ===")

        # Log initial data state
        logger.info(
            f"📊 INPUT DATA: {len(exams)} exams, {len(registrations)} registrations"
        )

        # Create course-to-exam mapping with detailed logging
        course_to_exam = {}
        exam_details = {}

        for exam in exams:
            exam_id_str = str(exam["id"])
            course_id_str = str(exam["course_id"])
            exam_details[exam_id_str] = {
                "course_code": exam.get("course_code", "Unknown"),
                "expected_students": exam.get("expected_students", 0),
                "actual_students": exam.get("actual_student_count", 0),
            }

            if course_id_str in course_to_exam:
                logger.warning(
                    f"🔄 DUPLICATE COURSE MAPPING: Course {course_id_str} mapped to multiple exams"
                )

            course_to_exam[course_id_str] = exam_id_str

        logger.info(
            f"🗺️ COURSE-EXAM MAPPING: {len(course_to_exam)} unique course-exam pairs"
        )

        # Build mappings with detailed tracking
        student_exam_mappings = defaultdict(set)
        mapping_stats = {
            "successful_mappings": 0,
            "failed_mappings": 0,
            "students_with_exams": set(),
            "courses_with_students": set(),
            "exams_with_students": set(),
        }

        for reg in raw_registrations:
            try:
                student_id_str = str(reg["student_id"])
                course_id_str = str(reg["course_id"])

                if course_id_str in course_to_exam:
                    exam_id_str = course_to_exam[course_id_str]
                    student_exam_mappings[student_id_str].add(exam_id_str)

                    # Track statistics
                    mapping_stats["successful_mappings"] += 1
                    mapping_stats["students_with_exams"].add(student_id_str)
                    mapping_stats["courses_with_students"].add(course_id_str)
                    mapping_stats["exams_with_students"].add(exam_id_str)
                else:
                    mapping_stats["failed_mappings"] += 1
                    logger.debug(
                        f"⚠️ No exam found for course {course_id_str} in registration"
                    )

            except Exception as e:
                mapping_stats["failed_mappings"] += 1
                logger.error(f"❌ Failed to process registration: {e}")

        # Identify phantom exams with detailed reporting
        all_exam_ids = set(exam_details.keys())
        exams_with_students = mapping_stats["exams_with_students"]
        phantom_exams = all_exam_ids - exams_with_students

        if phantom_exams:
            logger.error(
                f"🚨 PHANTOM EXAMS DETECTED: {len(phantom_exams)} exams have no students!"
            )
            for phantom_id in phantom_exams:
                details = exam_details.get(phantom_id, {})
                logger.error(
                    f"  👻 {details.get('course_code', 'Unknown')} (ID: {phantom_id})"
                )
                logger.error(
                    f"     Expected: {details.get('expected_students', 0)}, Actual: {details.get('actual_students', 0)}"
                )

        # Log final statistics
        logger.info(f"✅ MAPPING STATISTICS:")
        logger.info(f"  📈 Successful mappings: {mapping_stats['successful_mappings']}")
        logger.info(f"  📉 Failed mappings: {mapping_stats['failed_mappings']}")
        logger.info(
            f"  👥 Students with exams: {len(mapping_stats['students_with_exams'])}"
        )
        logger.info(
            f"  📚 Exams with students: {len(exams_with_students)}/{len(all_exam_ids)}"
        )
        logger.info(f"  👻 Phantom exams: {len(phantom_exams)}")

        return dict(student_exam_mappings)

    def _validate_data_flow_integrity(
        self, raw_data: Dict, mapped_entities: Dict, relationships: Dict
    ) -> Dict:
        """Comprehensive data flow validation with detailed logging"""
        logger.info("=== DATA FLOW INTEGRITY VALIDATION ===")

        validation_report = {
            "stage": "data_flow_validation",
            "timestamp": datetime.now().isoformat(),
            "issues": [],
            "warnings": [],
            "statistics": {},
        }

        # Raw data validation
        raw_stats = {
            "exams": len(raw_data.get("exams", [])),
            "students": len(raw_data.get("students", [])),
            "rooms": len(raw_data.get("rooms", [])),
            "registrations": len(raw_data.get("course_registrations", [])),
        }

        # Mapped entities validation
        mapped_stats = {
            "exams": len(mapped_entities.get("exams", [])),
            "students": len(mapped_entities.get("students", [])),
            "rooms": len(mapped_entities.get("rooms", [])),
            "invigilators": len(mapped_entities.get("invigilators", [])),
        }

        # Check for data loss during mapping
        for entity_type in ["exams", "students", "rooms"]:
            raw_count = raw_stats.get(entity_type, 0)
            mapped_count = mapped_stats.get(entity_type, 0)

            if mapped_count < raw_count:
                loss_percentage = ((raw_count - mapped_count) / raw_count) * 100
                validation_report["warnings"].append(
                    f"{entity_type.upper()} DATA LOSS: {raw_count} → {mapped_count} ({loss_percentage:.1f}% lost)"
                )

        # Relationship validation
        student_exam_mappings = relationships.get("student_exam_mappings", {})
        total_mappings = sum(len(exams) for exams in student_exam_mappings.values())

        validation_report["statistics"] = {
            "raw_data": raw_stats,
            "mapped_data": mapped_stats,
            "total_student_exam_mappings": total_mappings,
            "students_with_mappings": len(student_exam_mappings),
        }

        logger.info(f"📊 DATA FLOW REPORT: {validation_report}")
        return validation_report

    def _validate_student_exam_mappings(
        self, mappings: Dict[str, Set[str]], exam_ids: Set[str], stats: Dict[str, Any]
    ) -> None:
        """Comprehensive validation of student-exam mappings"""

        # Find students without exams
        students_with_exams = set(mappings.keys())
        all_student_ids = set()  # This would come from student data
        # For now, we'll use the keys from mappings

        # Find exams without students
        exams_with_students = set()
        for student_id, exam_set in mappings.items():
            exams_with_students.update(exam_set)

        exams_without_students = exam_ids - exams_with_students

        # Update stats
        stats["students_without_exams"] = all_student_ids - students_with_exams
        stats["exams_without_students"] = exams_without_students

        # Log validation results
        if stats["students_without_exams"]:
            logger.warning(
                f"{len(stats['students_without_exams'])} students have no exam mappings"
            )

        if exams_without_students:
            logger.error(
                f"{len(exams_without_students)} exams have no student mappings: {list(exams_without_students)[:5]}..."
            )

        if not mappings:
            logger.error("CRITICAL: No student-exam mappings were created!")
            raise ValueError("No student-exam mappings generated")

        if len(mappings) < 10:  # Arbitrary threshold, adjust based on your data
            logger.warning(f"Very few student-exam mappings created: {len(mappings)}")

    def _populate_exam_students(
        self, exams: List[Dict], student_exam_mappings: Dict[str, Set[str]]
    ) -> List[Dict]:
        """Populate exam student lists with enhanced validation"""

        # Create reverse mapping: exam_id -> set of student_ids
        exam_student_mappings = defaultdict(set)
        student_count_per_exam = {}

        for student_id, exam_ids in student_exam_mappings.items():
            try:
                student_uuid = UUID(student_id)
                for exam_id in exam_ids:
                    exam_student_mappings[exam_id].add(student_uuid)
            except Exception as e:
                logger.warning(
                    f"Invalid student ID in mapping: {student_id}, error: {e}"
                )
                continue

        # Populate each exam with student data
        exams_with_students = 0
        total_students_assigned = 0

        for exam in exams:
            exam_id_str = str(exam["id"])
            student_ids = exam_student_mappings.get(exam_id_str, set())

            exam["students"] = student_ids
            exam["actual_student_count"] = len(student_ids)
            student_count_per_exam[exam_id_str] = len(student_ids)

            # Update expected students if actual is higher
            if len(student_ids) > exam["expected_students"]:
                old_count = exam["expected_students"]
                exam["expected_students"] = len(student_ids)
                logger.info(
                    f"Updated exam {exam_id_str} expected students from {old_count} to {len(student_ids)}"
                )

            if student_ids:
                exams_with_students += 1
                total_students_assigned += len(student_ids)

        # Validation summary
        total_exams = len(exams)
        logger.info(
            f"Student population summary: {exams_with_students}/{total_exams} exams have students, "
            f"{total_students_assigned} total student assignments"
        )

        if exams_with_students == 0 and total_exams > 0:
            logger.error("CRITICAL: No exams have students assigned after population!")
        elif exams_with_students < total_exams:
            logger.warning(
                f"{total_exams - exams_with_students} exams have no students assigned"
            )

        return exams

    def _generate_days_from_timeslots(self, timeslots: List[Dict]) -> List[Dict]:
        """Generate days structure exactly as problem model expects"""
        days_dict = {}

        # Group timeslots by day
        for ts in timeslots:
            day_id = ts.get("parent_day_id")
            if not day_id:
                continue

            if day_id not in days_dict:
                days_dict[day_id] = {
                    "id": day_id,
                    "date": date.today(),  # Will be set properly in real implementation
                    "timeslots": [],
                }
            days_dict[day_id]["timeslots"].append(ts)

        return list(days_dict.values())
