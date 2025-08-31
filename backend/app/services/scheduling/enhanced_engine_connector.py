# backend/app/services/scheduling/enhanced_engine_connector.py

"""
Enhanced scheduling engine connector with advanced data structures
and optimization-focused data retrieval for direct database integration.
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


@dataclass
class ProblemInstance:
    """Complete problem instance optimized for scheduling engines"""

    session_id: str
    exams: Dict[str, Dict[str, Any]]
    rooms: Dict[str, Dict[str, Any]]
    time_slots: Dict[str, Dict[str, Any]]
    staff: Dict[str, Dict[str, Any]]
    students: Dict[str, Dict[str, Any]]
    # Constraint matrices for fast lookups
    conflict_matrix: Set[Tuple[str, str]]  # Student conflicts
    room_compatibility: Dict[str, List[str]]  # Exam -> compatible rooms
    time_constraints: Dict[str, List[str]]  # Exam -> available time slots
    staff_constraints: Dict[str, Any]  # Staff availability data
    # Optimization hints and metrics
    problem_metrics: Dict[str, Any]
    optimization_hints: Dict[str, Any]


@dataclass
class OptimizationResult:
    """Result of optimization process"""

    success: bool
    solution: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    metrics: Optional[Dict[str, Any]] = None


class EnhancedSchedulingEngineConnector:
    """
    Enhanced connector that provides comprehensive data structures
    optimized for scheduling algorithms with caching and performance optimizations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        # Import base service here to avoid circular imports
        from app.services.data_retrieval.scheduling_data import SchedulingData

        self.base_service = SchedulingData(session)

        # Caching for frequently accessed data
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = 300  # 5 minutes

    async def get_complete_problem_instance(
        self, session_id: UUID, use_cache: bool = True, refresh_views: bool = False
    ) -> ProblemInstance:
        """
        Get complete problem instance with all optimization data structures.
        This is the main entry point for the scheduling engines.
        """
        cache_key = f"problem_instance_{session_id}"

        # Check cache first
        if use_cache and self._is_cache_valid(cache_key):
            logger.info(f"Returning cached problem instance for session {session_id}")
            return self._cache[cache_key]

        try:
            logger.info(f"Building complete problem instance for session {session_id}")

            # Refresh materialized views if requested
            if refresh_views:
                await self._refresh_optimization_views()

            # Get base scheduling data
            base_data = await self.base_service.get_scheduling_data_for_session(
                session_id
            )

            # Build optimization-specific data structures
            conflict_matrix = await self._build_comprehensive_conflict_matrix(
                session_id
            )
            room_compatibility = await self._build_enhanced_room_compatibility(
                session_id, base_data
            )
            time_constraints = await self._build_enhanced_time_constraints(
                session_id, base_data
            )
            staff_constraints = await self._build_comprehensive_staff_constraints(
                session_id
            )

            # Calculate problem metrics and optimization hints
            problem_metrics = await self._calculate_problem_metrics(
                base_data, conflict_matrix, room_compatibility, time_constraints
            )
            optimization_hints = await self._generate_optimization_hints(
                base_data,
                conflict_matrix,
                room_compatibility,
                time_constraints,
                problem_metrics,
            )

            # Build complete problem instance
            problem_instance = ProblemInstance(
                session_id=str(session_id),
                exams={exam["id"]: exam for exam in base_data["exams"]},
                rooms={room["id"]: room for room in base_data["rooms"]},
                time_slots={slot["id"]: slot for slot in base_data["time_slots"]},
                staff={staff["id"]: staff for staff in base_data["staff"]},
                students=await self._build_student_data_structure(session_id),
                conflict_matrix=conflict_matrix,
                room_compatibility=room_compatibility,
                time_constraints=time_constraints,
                staff_constraints=staff_constraints,
                problem_metrics=problem_metrics,
                optimization_hints=optimization_hints,
            )

            # Cache the result
            if use_cache:
                self._cache[cache_key] = problem_instance
                self._cache_timestamps[cache_key] = datetime.utcnow()

            logger.info(
                f"Problem instance built: {len(problem_instance.exams)} exams, "
                f"{len(problem_instance.rooms)} rooms, "
                f"{len(problem_instance.time_slots)} time slots, "
                f"{len(problem_instance.conflict_matrix)} conflicts"
            )

            return problem_instance

        except Exception as e:
            logger.error(
                f"Failed to build problem instance for session {session_id}: {e}"
            )
            raise

    async def _build_comprehensive_conflict_matrix(
        self, session_id: UUID
    ) -> Set[Tuple[str, str]]:
        """Build comprehensive student conflict matrix with additional conflict types"""

        # Get direct student conflicts (same students in multiple courses)
        stmt = """
        WITH student_courses AS (
            SELECT 
                cr.student_id,
                array_agg(DISTINCT e.id::text) as exam_ids
            FROM exam_system.course_registrations cr
            JOIN exam_system.exams e ON e.course_id = cr.course_id
            WHERE cr.session_id = :session_id
            AND e.session_id = :session_id
            AND e.status IN ('pending', 'scheduled', 'confirmed')
            GROUP BY cr.student_id
            HAVING COUNT(DISTINCT e.id) > 1
        )
        SELECT DISTINCT
            e1.exam_id as exam1_id,
            e2.exam_id as exam2_id,
            'student_conflict' as conflict_type
        FROM (
            SELECT unnest(exam_ids) as exam_id, student_id
            FROM student_courses
        ) e1
        JOIN (
            SELECT unnest(exam_ids) as exam_id, student_id  
            FROM student_courses
        ) e2 ON e1.student_id = e2.student_id AND e1.exam_id < e2.exam_id
        
        UNION
        
        -- Add carryover conflicts (students retaking courses)
        SELECT DISTINCT
            e1.id::text as exam1_id,
            e2.id::text as exam2_id,
            'carryover_conflict' as conflict_type
        FROM exam_system.exams e1
        JOIN exam_system.course_registrations cr1 ON cr1.course_id = e1.course_id
        JOIN exam_system.course_registrations cr2 ON cr2.student_id = cr1.student_id
        JOIN exam_system.exams e2 ON e2.course_id = cr2.course_id
        WHERE e1.session_id = :session_id
        AND e2.session_id = :session_id
        AND e1.id != e2.id
        AND cr1.registration_type = 'retake'
        AND cr2.registration_type = 'regular'
        """

        try:
            result = await self.session.execute(
                text(stmt), {"session_id": str(session_id)}
            )
            conflicts = set()

            for row in result.fetchall():
                conflicts.add((row.exam1_id, row.exam2_id))

            logger.info(f"Built conflict matrix with {len(conflicts)} conflict pairs")
            return conflicts

        except Exception as e:
            logger.error(f"Failed to build conflict matrix: {e}")
            return set()

    async def _build_enhanced_room_compatibility(
        self, session_id: UUID, base_data: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Build enhanced room compatibility with advanced requirements"""

        # Get detailed exam requirements
        stmt = """
        SELECT
            e.id as exam_id,
            e.expected_students,
            c.is_practical,
            c.morning_only,
            c.code as course_code,
            c.course_level,
            COALESCE(
                array_agg(DISTINCT unnest(COALESCE(s.special_needs, '{}')))
                FILTER (WHERE unnest(COALESCE(s.special_needs, '{}')) IS NOT NULL), 
                '{}'
            ) as special_needs,
            COUNT(DISTINCT cr.student_id) as registered_students
        FROM exam_system.exams e
        JOIN exam_system.courses c ON c.id = e.course_id
        JOIN exam_system.course_registrations cr ON cr.course_id = e.course_id
        LEFT JOIN exam_system.students s ON s.id = cr.student_id
        WHERE e.session_id = :session_id
        AND cr.session_id = :session_id
        AND e.status IN ('pending', 'scheduled', 'confirmed')
        GROUP BY e.id, c.id
        """

        try:
            exam_result = await self.session.execute(
                text(stmt), {"session_id": str(session_id)}
            )
            exam_requirements = {}

            for row in exam_result.fetchall():
                exam_requirements[str(row.exam_id)] = {
                    "expected_students": row.expected_students or 0,
                    "registered_students": row.registered_students or 0,
                    "is_practical": row.is_practical or False,
                    "morning_only": row.morning_only or False,
                    "course_code": row.course_code or "",
                    "course_level": row.course_level or 100,
                    "special_needs": row.special_needs or [],
                }

            # Get room capabilities
            rooms = {room["id"]: room for room in base_data.get("rooms", [])}

            # Build compatibility matrix with advanced logic
            compatibility = {}
            for exam_id, requirements in exam_requirements.items():
                compatible_rooms = []
                for room_id, room_data in rooms.items():
                    if self._is_room_compatible_enhanced(requirements, room_data):
                        compatible_rooms.append(room_id)

                # Sort by preference (capacity match, features, etc.)
                compatible_rooms = await self._sort_rooms_by_preference(
                    compatible_rooms, requirements, rooms
                )
                compatibility[exam_id] = compatible_rooms

                # Add fallback rooms for exams with no compatible rooms
                if not compatibility.get(exam_id):
                    fallback_rooms = await self._get_fallback_rooms(requirements, rooms)
                    compatibility[exam_id] = fallback_rooms
                    if fallback_rooms:
                        logger.warning(
                            f"Exam {exam_id} has no ideal rooms, using fallbacks: {fallback_rooms}"
                        )

            return compatibility

        except Exception as e:
            logger.error(f"Failed to build room compatibility: {e}")
            return {}

    def _is_room_compatible_enhanced(
        self, exam_requirements: Dict[str, Any], room_data: Dict[str, Any]
    ) -> bool:
        """Enhanced room compatibility checking"""

        # Basic capacity check with buffer
        required_capacity = max(
            exam_requirements.get("expected_students", 0),
            exam_requirements.get("registered_students", 0),
        )
        room_capacity = room_data.get("exam_capacity", room_data.get("capacity", 0))

        if room_capacity < required_capacity:
            return False

        # Practical course requirements
        if exam_requirements.get("is_practical", False):
            if not room_data.get("has_computers", False):
                return False

        # Special needs requirements
        special_needs = exam_requirements.get("special_needs", [])
        if "wheelchair_access" in special_needs:
            accessibility_features = room_data.get("accessibility_features", [])
            if "wheelchair_accessible" not in accessibility_features:
                return False

        # Course level preferences (higher level courses get better rooms)
        course_level = exam_requirements.get("course_level", 100)
        if course_level >= 400 and not room_data.get("has_projector", False):
            return False  # Graduate courses prefer rooms with projectors

        return True

    async def _sort_rooms_by_preference(
        self,
        compatible_rooms: List[str],
        requirements: Dict[str, Any],
        rooms: Dict[str, Dict[str, Any]],
    ) -> List[str]:
        """Sort rooms by preference for the given exam requirements"""

        def room_score(room_id: str) -> float:
            room_data = rooms.get(room_id, {})
            score = 0.0

            # Capacity utilization score (prefer rooms that will be well-utilized)
            required = requirements.get("expected_students", 0)
            capacity = room_data.get("exam_capacity", room_data.get("capacity", 1))

            if capacity > 0:
                utilization = required / capacity
                if 0.7 <= utilization <= 0.9:  # Sweet spot
                    score += 10.0
                elif utilization <= 1.0:
                    score += utilization * 5.0

            # Feature bonuses
            if room_data.get("has_projector", False):
                score += 2.0
            if room_data.get("has_ac", False):
                score += 1.0

            # Building preference (centrally located buildings)
            building_code = room_data.get("building_code", "")
            if building_code in ["MAIN", "CENTRAL", "ADMIN"]:
                score += 3.0

            return score

        return sorted(compatible_rooms, key=room_score, reverse=True)

    async def _get_fallback_rooms(
        self, requirements: Dict[str, Any], rooms: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """Get fallback rooms when no ideal match exists"""
        fallbacks = []
        required_capacity = requirements.get("expected_students", 0)

        # Find rooms with at least minimum capacity
        for room_id, room_data in rooms.items():
            capacity = room_data.get("exam_capacity", room_data.get("capacity", 0))
            if capacity >= required_capacity * 0.8:  # 80% of required capacity
                fallbacks.append(room_id)

        return fallbacks[:3]  # Limit to 3 fallback options

    async def _build_enhanced_time_constraints(
        self, session_id: UUID, base_data: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Build enhanced time constraints with preferences and restrictions"""

        # Categorize time slots
        time_slots = {slot["id"]: slot for slot in base_data.get("time_slots", [])}
        morning_slots = []
        afternoon_slots = []
        evening_slots = []

        for slot_id, slot_data in time_slots.items():
            start_time_str = slot_data.get("start_time", "09:00")
            try:
                start_hour = int(start_time_str.split(":")[0])
                # Add time category to slot data
                if start_hour < 12:
                    slot_data["time_category"] = "morning"
                    morning_slots.append(slot_id)
                elif start_hour < 17:
                    slot_data["time_category"] = "afternoon"
                    afternoon_slots.append(slot_id)
                else:
                    slot_data["time_category"] = "evening"
                    evening_slots.append(slot_id)
            except (ValueError, IndexError):
                slot_data["time_category"] = "unknown"
                morning_slots.append(slot_id)  # Default to morning

        # Get exam-specific constraints
        exam_time_constraints = {}
        for exam_data in base_data.get("exams", []):
            exam_id = exam_data["id"]
            available_slots = list(time_slots.keys())  # Start with all slots

            # Apply morning-only restriction
            if exam_data.get("morning_only", False):
                available_slots = [
                    slot_id for slot_id in available_slots if slot_id in morning_slots
                ]

            # Apply duration constraints
            exam_duration = exam_data.get("duration_minutes", 180)
            available_slots = [
                slot_id
                for slot_id in available_slots
                if time_slots[slot_id].get("duration_minutes", 180) >= exam_duration
            ]

            # Prefer certain time slots based on course level
            course_level = exam_data.get("course_level", 100)
            if course_level >= 400:  # Graduate courses prefer morning slots
                available_slots = sorted(
                    available_slots,
                    key=lambda s: (
                        0 if s in morning_slots else 1 if s in afternoon_slots else 2
                    ),
                )

            exam_time_constraints[exam_id] = available_slots

        return exam_time_constraints

    async def _build_comprehensive_staff_constraints(
        self, session_id: UUID
    ) -> Dict[str, Any]:
        """Build comprehensive staff constraints including preferences and patterns"""

        try:
            base_staff_data = await self.base_service._get_available_staff()
            staff_unavailability = await self.base_service._get_staff_unavailability(
                session_id
            )

            # Build unavailability lookup
            unavailable_by_staff = defaultdict(set)
            for unavail in staff_unavailability:
                staff_id = unavail["staff_id"]
                if unavail["time_slot_id"]:
                    unavailable_by_staff[staff_id].add(unavail["time_slot_id"])

            # Build individual staff constraints
            individual_constraints = {}
            for staff_member in base_staff_data:
                staff_id = staff_member["id"]
                individual_constraints[staff_id] = {
                    "staff_number": staff_member.get("staff_number", ""),
                    "department_id": staff_member.get("department_id"),
                    "staff_type": staff_member.get("staff_type", "administrative"),
                    "max_daily_sessions": staff_member.get("max_daily_sessions", 2),
                    "max_consecutive_sessions": staff_member.get(
                        "max_consecutive_sessions", 2
                    ),
                    "unavailable_slots": list(
                        unavailable_by_staff.get(staff_id, set())
                    ),
                    "can_be_chief": staff_member.get("staff_type") == "academic",
                    "preference_weight": self._calculate_staff_preference_weight(
                        staff_member
                    ),
                }

            # Calculate staff distribution metrics
            department_distribution: defaultdict[str, int] = defaultdict(int)
            type_distribution: defaultdict[str, int] = defaultdict(int)
            for staff_member in base_staff_data:
                if staff_member.get("department_id"):
                    department_distribution[staff_member["department_id"]] += 1
                type_distribution[staff_member.get("staff_type", "administrative")] += 1

            return {
                "individual_constraints": individual_constraints,
                "department_distribution": dict(department_distribution),
                "type_distribution": dict(type_distribution),
                "total_staff_count": len(base_staff_data),
                "academic_staff_count": type_distribution.get("academic", 0),
                "average_max_sessions": (
                    sum(s.get("max_daily_sessions", 2) for s in base_staff_data)
                    / max(1, len(base_staff_data))
                ),
            }

        except Exception as e:
            logger.error(f"Failed to build staff constraints: {e}")
            return {
                "individual_constraints": {},
                "department_distribution": {},
                "type_distribution": {},
                "total_staff_count": 0,
                "academic_staff_count": 0,
                "average_max_sessions": 2.0,
            }

    def _calculate_staff_preference_weight(self, staff_member: Dict[str, Any]) -> float:
        """Calculate preference weight for staff assignment"""
        weight = 1.0

        # Academic staff get higher preference for chief invigilator roles
        if staff_member.get("staff_type") == "academic":
            weight += 0.5

        # Staff with higher max sessions get slight preference
        max_sessions = staff_member.get("max_daily_sessions", 2)
        weight += (max_sessions - 1) * 0.1

        return weight

    async def _build_student_data_structure(
        self, session_id: UUID
    ) -> Dict[str, Dict[str, Any]]:
        """Build optimized student data structure"""

        stmt = """
        SELECT
            s.id as student_id,
            s.matric_number,
            s.current_level,
            s.special_needs,
            COALESCE(array_agg(DISTINCT e.id::text), '{}') as exam_ids,
            COUNT(DISTINCT e.id) as exam_count
        FROM exam_system.students s
        JOIN exam_system.course_registrations cr ON cr.student_id = s.id
        JOIN exam_system.exams e ON e.course_id = cr.course_id
        WHERE cr.session_id = :session_id
        AND e.session_id = :session_id
        AND e.status IN ('pending', 'scheduled', 'confirmed')
        GROUP BY s.id
        """

        try:
            result = await self.session.execute(
                text(stmt), {"session_id": str(session_id)}
            )
            students = {}

            for row in result.fetchall():
                students[str(row.student_id)] = {
                    "matric_number": row.matric_number or "",
                    "current_level": row.current_level or 100,
                    "special_needs": row.special_needs or [],
                    "exam_ids": row.exam_ids or [],
                    "exam_count": row.exam_count or 0,
                }

            return students

        except Exception as e:
            logger.error(f"Failed to build student data structure: {e}")
            return {}

    async def _calculate_problem_metrics(
        self,
        base_data: Dict[str, Any],
        conflict_matrix: Set[Tuple[str, str]],
        room_compatibility: Dict[str, List[str]],
        time_constraints: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """Calculate comprehensive problem complexity metrics"""

        num_exams = len(base_data.get("exams", []))
        num_rooms = len(base_data.get("rooms", []))
        num_timeslots = len(base_data.get("time_slots", []))

        # Constraint density metrics
        max_possible_conflicts = (num_exams * (num_exams - 1)) // 2
        conflict_density = len(conflict_matrix) / max(1, max_possible_conflicts)

        # Room availability metrics
        avg_compatible_rooms = sum(
            len(rooms) for rooms in room_compatibility.values()
        ) / max(1, len(room_compatibility))
        min_compatible_rooms = (
            min(len(rooms) for rooms in room_compatibility.values())
            if room_compatibility
            else 0
        )

        # Time availability metrics
        avg_available_slots = sum(
            len(slots) for slots in time_constraints.values()
        ) / max(1, len(time_constraints))
        min_available_slots = (
            min(len(slots) for slots in time_constraints.values())
            if time_constraints
            else 0
        )

        # Capacity utilization
        total_exam_demand = sum(
            exam.get("expected_students", 0) for exam in base_data.get("exams", [])
        )
        total_room_capacity = (
            sum(
                room.get("exam_capacity", room.get("capacity", 0))
                for room in base_data.get("rooms", [])
            )
            * num_timeslots
        )
        demand_to_capacity_ratio = total_exam_demand / max(1, total_room_capacity)

        # Complexity estimation
        complexity_score = (
            conflict_density * 0.4
            + (1 / max(1, avg_compatible_rooms)) * 0.3
            + (1 / max(1, avg_available_slots)) * 0.2
            + demand_to_capacity_ratio * 0.1
        )

        if complexity_score < 0.3:
            complexity_estimate = "EASY"
        elif complexity_score < 0.6:
            complexity_estimate = "MODERATE"
        elif complexity_score < 0.8:
            complexity_estimate = "HARD"
        else:
            complexity_estimate = "VERY_HARD"

        return {
            "num_exams": num_exams,
            "num_rooms": num_rooms,
            "num_timeslots": num_timeslots,
            "conflict_count": len(conflict_matrix),
            "conflict_density": conflict_density,
            "avg_compatible_rooms": avg_compatible_rooms,
            "min_compatible_rooms": min_compatible_rooms,
            "avg_available_slots": avg_available_slots,
            "min_available_slots": min_available_slots,
            "demand_to_capacity_ratio": demand_to_capacity_ratio,
            "complexity_score": complexity_score,
            "complexity_estimate": complexity_estimate,
            "search_space_size": num_exams * num_rooms * num_timeslots,
        }

    async def _generate_optimization_hints(
        self,
        base_data: Dict[str, Any],
        conflict_matrix: Set[Tuple[str, str]],
        room_compatibility: Dict[str, List[str]],
        time_constraints: Dict[str, List[str]],
        problem_metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate optimization hints and recommendations"""

        # Find problematic exams
        few_rooms_exams = [
            exam_id for exam_id, rooms in room_compatibility.items() if len(rooms) <= 2
        ]
        few_timeslots_exams = [
            exam_id for exam_id, slots in time_constraints.items() if len(slots) <= 2
        ]

        # Find highly conflicted exams
        conflict_count_by_exam: defaultdict[str, int] = defaultdict(int)
        for exam1, exam2 in conflict_matrix:
            conflict_count_by_exam[exam1] += 1
            conflict_count_by_exam[exam2] += 1

        high_conflict_exams = [
            exam_id
            for exam_id, count in conflict_count_by_exam.items()
            if count > len(base_data.get("exams", [])) * 0.1  # More than 10% of exams
        ]

        # Resource bottlenecks
        bottleneck_resources = {}
        demand_ratio = problem_metrics.get("demand_to_capacity_ratio", 0)
        if demand_ratio > 0.9:
            bottleneck_resources["room_capacity"] = "HIGH"
        elif demand_ratio > 0.7:
            bottleneck_resources["room_capacity"] = "MEDIUM"
        else:
            bottleneck_resources["room_capacity"] = "LOW"

        min_slots = problem_metrics.get("min_available_slots", 0)
        avg_slots = problem_metrics.get("avg_available_slots", 0)
        if min_slots <= 1:
            bottleneck_resources["time_slots"] = "HIGH"
        elif avg_slots <= 3:
            bottleneck_resources["time_slots"] = "MEDIUM"
        else:
            bottleneck_resources["time_slots"] = "LOW"

        num_exams = len(base_data.get("exams", []))
        return {
            "few_rooms_exams": few_rooms_exams,
            "few_timeslots_exams": few_timeslots_exams,
            "high_conflict_exams": high_conflict_exams,
            "bottleneck_resources": bottleneck_resources,
            "conflict_density": problem_metrics.get("conflict_density", 0),
            "recommended_algorithm_params": {
                "cpsat_time_limit": min(600, max(180, num_exams * 2)),
                "ga_generations": min(200, max(50, num_exams)),
                "ga_population_size": min(100, max(30, num_exams // 2)),
            },
        }

    async def get_optimization_statistics(self, session_id: UUID) -> Dict[str, Any]:
        """Get current optimization statistics for monitoring"""

        # Get current scheduling status
        stats_stmt = """
        SELECT
            COUNT(*) as total_exams,
            COUNT(CASE WHEN time_slot_id IS NOT NULL THEN 1 END) as scheduled_exams,
            COUNT(CASE WHEN status = 'confirmed' THEN 1 END) as confirmed_exams,
            AVG(expected_students) as avg_exam_size,
            MAX(expected_students) as largest_exam,
            MIN(expected_students) as smallest_exam
        FROM exam_system.exams
        WHERE session_id = :session_id
        """

        try:
            result = await self.session.execute(
                text(stats_stmt), {"session_id": str(session_id)}
            )
            stats = result.fetchone()

            if not stats or not stats.total_exams:
                return {
                    "scheduling_progress": {"completion_percentage": 0},
                    "resource_utilization": {"room_utilization_percentage": 0},
                    "exam_statistics": {
                        "avg_exam_size": 0,
                        "largest_exam": 0,
                        "smallest_exam": 0,
                    },
                }

            # Get room utilization
            room_util_stmt = """
            SELECT
                COUNT(DISTINCT er.room_id) as rooms_used,
                (SELECT COUNT(*) FROM exam_system.rooms WHERE is_active = true) as total_rooms,
                COALESCE(AVG(er.allocated_capacity::float / r.exam_capacity), 0) as avg_capacity_utilization
            FROM exam_system.exam_rooms er
            JOIN exam_system.exams e ON e.id = er.exam_id
            JOIN exam_system.rooms r ON r.id = er.room_id
            WHERE e.session_id = :session_id
            """

            room_result = await self.session.execute(
                text(room_util_stmt), {"session_id": str(session_id)}
            )
            room_stats = room_result.fetchone()

            return {
                "scheduling_progress": {
                    "total_exams": stats.total_exams or 0,
                    "scheduled_exams": stats.scheduled_exams or 0,
                    "confirmed_exams": stats.confirmed_exams or 0,
                    "completion_percentage": (
                        (stats.scheduled_exams or 0) / stats.total_exams * 100
                        if stats.total_exams and stats.total_exams > 0
                        else 0
                    ),
                },
                "exam_statistics": {
                    "avg_exam_size": float(stats.avg_exam_size or 0),
                    "largest_exam": stats.largest_exam or 0,
                    "smallest_exam": stats.smallest_exam or 0,
                },
                "resource_utilization": {
                    "rooms_used": room_stats.rooms_used or 0 if room_stats else 0,
                    "total_rooms": room_stats.total_rooms or 0 if room_stats else 0,
                    "room_utilization_percentage": (
                        (room_stats.rooms_used or 0)
                        / (room_stats.total_rooms or 1)
                        * 100
                        if room_stats and room_stats.total_rooms
                        else 0
                    ),
                    "avg_room_capacity_utilization": float(
                        room_stats.avg_capacity_utilization or 0 if room_stats else 0
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Failed to get optimization statistics: {e}")
            return {
                "scheduling_progress": {"completion_percentage": 0},
                "resource_utilization": {"room_utilization_percentage": 0},
                "exam_statistics": {
                    "avg_exam_size": 0,
                    "largest_exam": 0,
                    "smallest_exam": 0,
                },
            }

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self._cache or cache_key not in self._cache_timestamps:
            return False
        age = (datetime.utcnow() - self._cache_timestamps[cache_key]).total_seconds()
        return age < self._cache_ttl

    async def _refresh_optimization_views(self) -> None:
        """Refresh materialized views used for optimization"""
        views = [
            "exam_system.mv_student_exam_conflicts",
            "exam_system.mv_room_utilization_stats",
            "exam_system.mv_staff_availability_summary",
        ]

        for view_name in views:
            try:
                from app.services.data_retrieval.helpers import (
                    refresh_materialized_view,
                )

                await refresh_materialized_view(self.session, view_name)
                logger.debug(f"Refreshed materialized view: {view_name}")
            except Exception as e:
                logger.warning(f"Failed to refresh view {view_name}: {e}")

    async def clear_cache(self, pattern: Optional[str] = None) -> None:
        """Clear cache entries matching pattern"""
        if pattern is None:
            self._cache.clear()
            self._cache_timestamps.clear()
        else:
            keys_to_remove = [key for key in self._cache.keys() if pattern in key]
            for key in keys_to_remove:
                self._cache.pop(key, None)
                self._cache_timestamps.pop(key, None)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        current_time = datetime.utcnow()
        valid_entries = 0

        for key, timestamp in self._cache_timestamps.items():
            if (current_time - timestamp).total_seconds() < self._cache_ttl:
                valid_entries += 1

        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "cache_hit_rate": valid_entries / max(1, len(self._cache)),
            "cache_ttl_seconds": self._cache_ttl,
        }
