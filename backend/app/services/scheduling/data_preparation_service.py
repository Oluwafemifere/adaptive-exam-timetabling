# backend/app/services/scheduling/data_preparation_service.py
# FIXED VERSION - Data Preparation Service with Exact Problem Model Compatibility
from __future__ import annotations
from datetime import datetime, date, time, timedelta
import math
from typing import Dict, List, Set, Optional, Any, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass, field, asdict
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

    # Days and timeslots structure from pg_func
    days: List[Dict[str, Any]] = field(default_factory=list)

    # HITL and Configuration capabilities
    constraints: Dict[str, Any] = field(default_factory=dict)
    locks: List[Dict[str, Any]] = field(default_factory=list)

    # Relationships - critical for problem model
    course_registrations: List[Dict[str, Any]] = field(default_factory=list)
    student_exam_mappings: Dict[str, Set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )

    # Metadata
    session_id: UUID = field(default_factory=uuid4)
    metadata: Dict[str, Any] = field(default_factory=dict)
    exam_period_start: Optional[date] = None
    exam_period_end: Optional[date] = None
    slot_generation_mode: str = "fixed"


class ExactDataMapper:
    """Maps database data to EXACT problem model expectations"""

    @staticmethod
    def map_room_to_problem_model(db_room: Dict) -> Dict[str, Any]:
        """Map database room to EXACT problem model format"""
        adjacent_pairs = db_room.get("adjacent_seat_pairs")
        if not isinstance(adjacent_pairs, list):
            adjacent_pairs = []

        return {
            "id": UUID(str(db_room["id"])),
            "code": db_room.get("code", ""),
            "capacity": db_room.get("capacity", 0),
            "exam_capacity": db_room.get("exam_capacity", db_room.get("capacity", 0)),
            "has_computers": db_room.get("has_computers", False),
            "adjacent_seat_pairs": adjacent_pairs,
            "name": db_room.get("name", ""),
            "building_name": db_room.get("building_name"),
            "has_projector": db_room.get("has_projector", False),
            "has_ac": db_room.get("has_ac", False),
            "overbookable": db_room.get("overbookable", False),
            "max_inv_per_room": db_room.get("max_inv_per_room", 2),
            "is_accessible": db_room.get("is_accessible", False),
        }

    @staticmethod
    def map_invigilator_to_problem_model(db_staff: Dict) -> Dict[str, Any]:
        """Map database staff to EXACT problem model invigilator format"""
        first_name = db_staff.get("first_name", "")
        last_name = db_staff.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip()

        # Process unavailable_periods into the availability dictionary
        availability = {}
        for period in db_staff.get("unavailable_periods", []):
            unavail_date = period.get("date")
            if unavail_date:
                availability.setdefault(unavail_date, []).append(period.get("period"))

        return {
            "id": UUID(str(db_staff["id"])),
            "name": full_name or f"Staff {db_staff.get('staff_number', 'Unknown')}",
            "email": db_staff.get("email"),
            "department": db_staff.get("department"),
            "can_invigilate": db_staff.get("can_invigilate", True),
            "max_concurrent_exams": db_staff.get("max_concurrent_exams", 1),
            "max_students_per_exam": db_staff.get("max_students_per_exam", 50),
            "availability": availability,
            "staff_number": db_staff.get("staff_number"),
            "staff_type": db_staff.get("staff_type"),
            "max_daily_sessions": db_staff.get("max_daily_sessions", 2),
            "max_consecutive_sessions": db_staff.get("max_consecutive_sessions", 1),
        }

    @staticmethod
    def map_instructor_to_problem_model(db_instructor: Dict) -> Dict[str, Any]:
        """Map database instructor to EXACT problem model format."""
        first_name = db_instructor.get("first_name", "")
        last_name = db_instructor.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip()
        return {
            "id": UUID(str(db_instructor["id"])),
            "name": full_name or db_instructor.get("name", "Unknown Instructor"),
            "email": db_instructor.get("email"),
            "department": db_instructor.get("department"),
            "availability": db_instructor.get("availability", {}),
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
                cleaned_value = value.strip()
                if not cleaned_value:
                    raise ValueError(f"{field_name} cannot be empty string")
                return UUID(cleaned_value)
            elif isinstance(value, int):
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
            ExactDataMapper._validate_required_fields(
                db_exam,
                ["id", "course_id", "duration_minutes"],
                f"exam {db_exam.get('id', 'unknown')}",
            )

            exam_id = ExactDataMapper._validate_and_convert_uuid(
                db_exam["id"], "exam_id"
            )
            course_id = ExactDataMapper._validate_and_convert_uuid(
                db_exam["course_id"], "course_id"
            )

            duration = db_exam.get("duration_minutes", 180)
            MAX_DURATION_MINUTES = 540

            if not isinstance(duration, (int, float)) or duration <= 0:
                logger.warning(
                    f"Invalid duration_minutes for exam {exam_id}: {duration}, using default 180"
                )
                duration = 180
            elif duration > MAX_DURATION_MINUTES:
                logger.error(
                    f"CRITICAL: Exam {exam_id} has a duration of {duration} minutes, which exceeds the daily maximum of {MAX_DURATION_MINUTES}. Capping duration."
                )
                duration = MAX_DURATION_MINUTES

            expected_students = db_exam.get("expected_students", 0)
            if not isinstance(expected_students, (int, float)) or expected_students < 0:
                logger.warning(
                    f"Invalid expected_students for exam {exam_id}: {expected_students}, using 0"
                )
                expected_students = 0

            # Process registered_students to create a dictionary for the problem model
            students_dict = {
                UUID(str(s["student_id"])): s.get("registration_type", "normal")
                for s in db_exam.get("registered_students", [])
            }

            # Process instructors from the nested list of objects into a set of IDs
            instructor_ids = {
                UUID(str(instr["id"])) for instr in db_exam.get("instructors", [])
            }

            department_objects = db_exam.get("departments", [])
            department_ids = {UUID(str(dept["id"])) for dept in department_objects}

            faculty_objects = db_exam.get("faculties", [])
            faculty_ids = {UUID(str(faculty["id"])) for faculty in faculty_objects}

            exam_data = {
                "id": exam_id,
                "course_id": course_id,
                "duration_minutes": int(duration),
                "expected_students": int(expected_students),
                "is_practical": bool(db_exam.get("is_practical", False)),
                "morning_only": bool(db_exam.get("morning_only", False)),
                "actual_student_count": len(students_dict),
                "students": students_dict,
                "course_code": db_exam.get("course_code", f"COURSE_{course_id}"),
                "course_title": db_exam.get("course_title", "Unknown Course"),
                "requires_projector": bool(db_exam.get("requires_projector", False)),
                "requires_special_arrangements": bool(
                    db_exam.get("requires_special_arrangements", False)
                ),
                "is_common": bool(db_exam.get("is_common", False)),
                "status": db_exam.get("status", "pending"),
                "prerequisite_exams": {
                    UUID(str(eid)) for eid in db_exam.get("prerequisite_exam_ids", [])
                },
                "instructor_ids": instructor_ids,
                "department_ids": list(department_ids),
                "faculty_ids": list(faculty_ids),
                # Pass through full objects for enrichment lookup
                "instructors": db_exam.get("instructors", []),
                "departments": department_objects,
                "faculties": faculty_objects,
            }

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

    # --- MODIFICATION START ---
    async def build_exact_problem_model_dataset(
        self, job_id: UUID
    ) -> ProblemModelCompatibleDataset:
        """Build dataset with EXACT problem model compatibility using a job_id."""
        logger.info(f"Building EXACT problem model dataset for job {job_id}")

        try:
            raw_data = await self._validate_and_retrieve_raw_data(job_id)

            # Extract session_id from the data returned by the function
            session_id = UUID(raw_data["session_id"])

            mapped_entities = await self._map_entities_with_validation(raw_data)
            relationships = await self._build_and_validate_relationships(
                mapped_entities, raw_data
            )
            dataset = self._create_validated_dataset(
                session_id, mapped_entities, relationships, raw_data
            )
            self._validate_final_dataset_integrity(dataset)
            self._log_dataset_statistics(dataset)

            logger.info(
                f"Successfully built validated dataset: {len(dataset.exams)} exams, "
                f"{len(dataset.students)} students, {len(dataset.rooms)} rooms"
            )

            return dataset

        except Exception as e:
            logger.error(
                f"Error building exact problem model dataset for job {job_id}: {e}"
            )
            raise

    # --- MODIFICATION END ---

    def _log_dataset_statistics(self, dataset: ProblemModelCompatibleDataset):
        """Log detailed dataset statistics"""
        stats = {
            "exams_count": len(dataset.exams),
            "rooms_count": len(dataset.rooms),
            "students_count": len(dataset.students),
            "invigilators_count": len(dataset.invigilators),
            "total_registrations": len(dataset.course_registrations),
            "student_exam_mappings": len(dataset.student_exam_mappings),
            "days_count": len(dataset.days),
            "locks_count": len(dataset.locks),
            "constraints_defined": "rules" in dataset.constraints,
            "slot_generation_mode": dataset.slot_generation_mode,
        }
        logger.info(f"Dataset Statistics: {stats}")

    # --- MODIFICATION START ---
    async def _validate_and_retrieve_raw_data(self, job_id: UUID) -> Dict[str, Any]:
        """
        Validate and retrieve raw data by calling the job-centric PostgreSQL function.
        """
        logger.info(
            f"Executing get_scheduling_dataset PostgreSQL function for job {job_id}"
        )
        try:
            # Call the updated database function that only requires a job_id
            query = text("SELECT exam_system.get_scheduling_dataset(:p_job_id)")
            result = await self.session.execute(query, {"p_job_id": job_id})
            raw_data = result.scalar_one_or_none()

            if not raw_data:
                raise ValueError(
                    f"PostgreSQL function returned no data for job {job_id}."
                )

            if not isinstance(raw_data, dict):
                raw_data = json.loads(raw_data)

            if not raw_data or not isinstance(raw_data, dict):
                raise ValueError("Invalid raw data structure from PostgreSQL function")

            critical_components = [
                "exams",
                "rooms",
                "students",
                "exam_days",
                "session_id",
            ]
            missing_components = [
                comp for comp in critical_components if not raw_data.get(comp)
            ]

            if missing_components:
                raise ValueError(
                    f"Missing critical data components from PG function for job {job_id}: {missing_components}"
                )

            logger.info(
                f"Retrieved valid raw data for job {job_id}: {len(raw_data.get('exams', []))} exams"
            )
            return raw_data

        except Exception as e:
            logger.error(f"Failed to retrieve raw data for job {job_id}: {e}")
            raise

    # --- MODIFICATION END ---

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

        # Map instructors by extracting them from the nested exam data
        all_instructors_data = {}  # Use dict to deduplicate by instructor ID
        for exam_data in raw_data.get("exams", []):
            for instructor_info in exam_data.get("instructors", []):
                instructor_id = str(instructor_info["id"])
                if instructor_id not in all_instructors_data:
                    all_instructors_data[instructor_id] = instructor_info

        instructors = [
            self.mapper.map_instructor_to_problem_model(instr)
            for instr in all_instructors_data.values()
        ]
        mapped_entities["instructors"] = instructors

        if len(exams) > 0 and len(invigilators) == 0:
            logger.warning(
                "No valid invigilators were mapped from the provided staff data."
            )

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
                # The 'students' field is now a dictionary {id: type}
                exam_students = exam.get("students", {})
                has_students = len(exam_students) > 0

                if has_students:
                    valid_exams.append(exam)
                else:
                    phantom_exams.append(
                        {
                            "id": exam.get("id", "unknown"),
                            "course_code": exam.get("course_code", "Unknown"),
                        }
                    )
                    logger.warning(
                        f"👻 PHANTOM EXAM: {exam.get('id', 'unknown')} - {exam.get('course_code')}"
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

    async def _build_and_validate_relationships(
        self, mapped_entities: Dict[str, List[Dict]], raw_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build and validate all relationships between entities with comprehensive error handling"""
        logger.info("Building and validating entity relationships...")

        try:
            relationships = {}

            exams = mapped_entities.get("exams", [])
            raw_registrations = raw_data.get("course_registrations", [])
            raw_student_exam_mappings = raw_data.get("student_exam_mappings", {})

            student_exam_mappings = {
                str(student_id): {str(exam_id) for exam_id in exam_ids}
                for student_id, exam_ids in raw_student_exam_mappings.items()
            }

            filtered_exams = await self.validate_and_filter_phantom_exams(
                exams, student_exam_mappings
            )

            mapped_entities["exams"] = filtered_exams
            relationships["student_exam_mappings"] = student_exam_mappings

            course_registrations = self._build_course_registrations(raw_registrations)
            relationships["course_registrations"] = course_registrations

            populated_exams = self._populate_exam_students(
                filtered_exams, student_exam_mappings
            )
            mapped_entities["exams"] = populated_exams

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
        raw_data: Dict[str, Any],
    ) -> ProblemModelCompatibleDataset:
        """Create final validated dataset with all entities and relationships"""
        logger.info("Creating final validated dataset...")

        try:
            dataset = ProblemModelCompatibleDataset(session_id=session_id)

            dataset.exams = mapped_entities.get("exams", [])
            dataset.rooms = mapped_entities.get("rooms", [])
            dataset.students = mapped_entities.get("students", [])
            dataset.invigilators = mapped_entities.get("invigilators", [])
            dataset.instructors = mapped_entities.get("instructors", [])
            dataset.staff = mapped_entities.get("staff", [])

            dataset.course_registrations = relationships.get("course_registrations", [])
            dataset.student_exam_mappings = relationships.get(
                "student_exam_mappings", defaultdict(set)
            )

            # Pass through HITL, config, and slot mode data directly from raw source
            dataset.days = raw_data.get("exam_days", [])
            dataset.constraints = raw_data.get("constraints", {})
            dataset.locks = raw_data.get("locks", [])
            dataset.slot_generation_mode = raw_data.get("slot_generation_mode", "fixed")
            dataset.exam_period_start = date.fromisoformat(
                raw_data["exam_period_start"]
            )
            dataset.exam_period_end = date.fromisoformat(raw_data["exam_period_end"])

            dataset.metadata = {
                "created_at": datetime.now().isoformat(),
                "total_exams": len(dataset.exams),
                "total_students": len(dataset.students),
                "total_rooms": len(dataset.rooms),
                "total_days": len(dataset.days),
                "dataset_version": "1.1-hitl",
            }

            logger.info(
                f"Created dataset with {len(dataset.exams)} exams, {len(dataset.students)} students, "
                f"{len(dataset.rooms)} rooms, {len(dataset.days)} days"
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
                    # Ensure registration_type is carried over
                    "registration_type": reg.get("registration_type", "normal"),
                }
                registrations.append(registration)
            except Exception as e:
                logger.warning(f"Failed to process registration: {e}")
                continue

        return registrations

    def _validate_relationship_integrity(
        self, mapped_entities: Dict[str, List[Dict]], relationships: Dict[str, Any]
    ) -> None:
        """Validate the integrity of all relationships"""
        issues = []

        student_exam_mappings = relationships.get("student_exam_mappings", {})
        exams = mapped_entities.get("exams", [])
        students = mapped_entities.get("students", [])

        student_ids = {str(student["id"]) for student in students}
        for student_id in student_exam_mappings.keys():
            if student_id not in student_ids:
                issues.append(
                    f"Student {student_id} in mappings but not in student list"
                )

        exam_ids = {str(exam["id"]) for exam in exams}
        for student_id, exam_set in student_exam_mappings.items():
            for exam_id in exam_set:
                if exam_id not in exam_ids:
                    issues.append(f"Exam {exam_id} in mappings but not in exam list")

        if issues:
            logger.warning(f"Relationship integrity issues found: {issues}")

    def _validate_final_dataset_integrity(
        self, dataset: ProblemModelCompatibleDataset
    ) -> None:
        """Enhanced dataset validation with phantom exam handling - FIXED VERSION"""
        logger.info("🔍 Performing comprehensive dataset integrity validation...")

        integrity_issues = []
        warnings = []

        if len(dataset.exams) == 0:
            integrity_issues.append("No exams in dataset")
        if len(dataset.rooms) == 0:
            integrity_issues.append("No rooms in dataset")
        if not dataset.days:
            integrity_issues.append(
                "No exam days defined in dataset. The database function may have failed to generate them."
            )

        phantom_exams = []
        valid_exams = []

        for exam in dataset.exams:
            # The 'students' field is now a dictionary
            exam_students = exam.get("students", {})
            student_count = len(exam_students) if isinstance(exam_students, dict) else 0

            if student_count > 0:
                valid_exams.append(exam)
            else:
                phantom_exams.append(
                    {
                        "id": exam.get("id"),
                        "course_code": exam.get("course_code", "Unknown"),
                    }
                )

        if phantom_exams:
            phantom_count = len(phantom_exams)
            logger.warning(f"🚨 Removing {phantom_count} phantom exams from dataset")

            for phantom in phantom_exams:
                logger.warning(
                    f"  👻 Removing phantom exam: {phantom['course_code']} (ID: {phantom['id']})"
                )

            dataset.exams = valid_exams
            warnings.append(f"Removed {phantom_count} phantom exams")

        if len(dataset.exams) == 0 and len(phantom_exams) > 0:
            integrity_issues.append("No valid exams remaining after phantom removal")

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

        logger.info(
            f"📊 INPUT DATA: {len(exams)} exams, {len(registrations)} registrations"
        )

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

        raw_stats = {
            "exams": len(raw_data.get("exams", [])),
            "students": len(raw_data.get("students", [])),
            "rooms": len(raw_data.get("rooms", [])),
            "registrations": len(raw_data.get("course_registrations", [])),
        }

        mapped_stats = {
            "exams": len(mapped_entities.get("exams", [])),
            "students": len(mapped_entities.get("students", [])),
            "rooms": len(mapped_entities.get("rooms", [])),
            "invigilators": len(mapped_entities.get("invigilators", [])),
        }

        for entity_type in ["exams", "students", "rooms"]:
            raw_count = raw_stats.get(entity_type, 0)
            mapped_count = mapped_stats.get(entity_type, 0)

            if mapped_count < raw_count:
                loss_percentage = ((raw_count - mapped_count) / raw_count) * 100
                validation_report["warnings"].append(
                    f"{entity_type.upper()} DATA LOSS: {raw_count} → {mapped_count} ({loss_percentage:.1f}% lost)"
                )

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

        students_with_exams = set(mappings.keys())
        all_student_ids = set()

        exams_with_students = set()
        for student_id, exam_set in mappings.items():
            exams_with_students.update(exam_set)

        exams_without_students = exam_ids - exams_with_students

        stats["students_without_exams"] = all_student_ids - students_with_exams
        stats["exams_without_students"] = exams_without_students

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

        if len(mappings) < 10:
            logger.warning(f"Very few student-exam mappings created: {len(mappings)}")

    def _populate_exam_students(
        self, exams: List[Dict], student_exam_mappings: Dict[str, Set[str]]
    ) -> List[Dict]:
        """Populate exam student lists with enhanced validation"""
        # This function now primarily serves to merge data from student_exam_mappings
        # (which lacks registration_type) with the already-populated student data from the mapper.

        for exam in exams:
            exam_id_str = str(exam["id"])
            # 'students' is already a dict: {student_id: registration_type}
            students_with_type = exam.get("students", {})

            # Iterate through the untyped mappings and add any missing students with a 'normal' type.
            for student_id_str, exam_ids in student_exam_mappings.items():
                if exam_id_str in exam_ids:
                    student_uuid = UUID(student_id_str)
                    if student_uuid not in students_with_type:
                        students_with_type[student_uuid] = "normal"

            exam["students"] = students_with_type
            exam["actual_student_count"] = len(students_with_type)
            if len(students_with_type) > exam["expected_students"]:
                exam["expected_students"] = len(students_with_type)

        return exams
