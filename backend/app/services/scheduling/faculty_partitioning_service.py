# backend/app/services/scheduling/faculty_partitioning_service.py

"""
Faculty Partitioning Service for exam scheduling system.
Implements faculty-based problem decomposition for efficiency and scalability.
Analyzes course registrations by faculty, detects dependencies, and creates
optimal partition strategies.
"""

from typing import Dict, List, Optional, Set, Any, Tuple, Union, Collection
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import networkx as nx
import numpy as np
from itertools import combinations
from networkx.algorithms import community

# Import data retrieval services
from ...services.data_retrieval import (
    AcademicData,
    SchedulingData,
    InfrastructureData,
    ConstraintData,
)

logger = logging.getLogger(__name__)


class PartitionStrategy(Enum):
    """Partition strategies"""

    INDEPENDENT = "independent"
    LOOSELY_COUPLED = "loosely_coupled"
    HIERARCHICAL = "hierarchical"
    HYBRID = "hybrid"


class DependencyType(Enum):
    """Types of dependencies between faculties"""

    SHARED_STUDENTS = "shared_students"
    SHARED_COURSES = "shared_courses"
    SHARED_ROOMS = "shared_rooms"
    SHARED_STAFF = "shared_staff"
    TIME_CONSTRAINTS = "time_constraints"
    RESOURCE_CONSTRAINTS = "resource_constraints"


@dataclass
class PartitionNode:
    """Represents a partition node (faculty or department)"""

    node_id: UUID
    node_type: str  # 'faculty' or 'department'
    name: str
    code: str
    parent_id: Optional[UUID] = None
    courses: List[UUID] = field(default_factory=list)
    students: Set[str] = field(default_factory=set)
    staff: List[UUID] = field(default_factory=list)
    rooms: List[UUID] = field(default_factory=list)
    exam_count: int = 0
    estimated_complexity: float = 0.0


@dataclass
class PartitionDependency:
    """Represents dependency between partitions"""

    dependency_id: UUID
    source_partition: UUID
    target_partition: UUID
    dependency_type: DependencyType
    strength: float  # 0.0 to 1.0
    shared_entities: List[str] = field(default_factory=list)
    resolution_strategy: Optional[str] = None
    coordination_required: bool = True


@dataclass
class PartitionGroup:
    """Represents a group of partitions"""

    group_id: UUID
    name: str
    strategy: PartitionStrategy
    partitions: List[PartitionNode] = field(default_factory=list)
    dependencies: List[PartitionDependency] = field(default_factory=list)
    coordination_requirements: Dict[str, Any] = field(default_factory=dict)
    estimated_runtime: float = 0.0
    load_balance_score: float = 0.0


@dataclass
class PartitioningResult:
    """Result of faculty partitioning analysis"""

    partitioning_id: UUID
    session_id: UUID
    strategy_used: PartitionStrategy
    partition_groups: List[PartitionGroup]
    dependency_graph: Dict[str, Any]
    coordination_plan: Dict[str, Any]
    performance_estimates: Dict[str, Any]
    recommendations: List[str]
    partitioning_timestamp: datetime
    analysis_duration: float


class FacultyPartitioningService:
    """
    Advanced faculty partitioning service that analyzes academic structure
    and creates optimal partitioning strategies for distributed scheduling.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

        # Initialize data retrieval services
        self.academic_data = AcademicData(session)
        self.scheduling_data = SchedulingData(session)
        self.infrastructure_data = InfrastructureData(session)
        self.constraint_data = ConstraintData(session)

        # Partitioning state
        self.academic_structure: Dict[str, Any] = {}
        self.dependency_graph: nx.DiGraph = nx.DiGraph()
        self.partition_cache: Dict[UUID, PartitioningResult] = {}

        # Configuration
        self.min_partition_size = 5  # Minimum exams per partition
        self.max_partition_size = 200  # Maximum exams per partition
        self.dependency_threshold = 0.3  # Minimum dependency strength to consider

    async def initialize(self, session_id: UUID) -> None:
        """Initialize partitioning service for session"""
        try:
            logger.info(
                f"Initializing Faculty Partitioning Service for session {session_id}"
            )

            # Load academic structure
            await self._load_academic_structure(session_id)

            # Build dependency graph
            await self._build_dependency_graph(session_id)

            # Analyze partition characteristics
            await self._analyze_partition_characteristics(session_id)

            logger.info("Faculty Partitioning Service initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing faculty partitioning service: {e}")
            raise

    async def _load_academic_structure(self, session_id: UUID) -> None:
        """Load academic structure data"""
        try:
            # Get all faculties with departments
            faculties = await self.academic_data.get_all_faculties()

            # Get scheduling data for the session
            scheduling_data = (
                await self.scheduling_data.get_scheduling_data_for_session(session_id)
            )

            # Build academic structure
            self.academic_structure = {
                "session_id": session_id,
                "faculties": {},
                "departments": {},
                "courses_by_faculty": defaultdict(list),
                "courses_by_department": defaultdict(list),
                "students_by_faculty": defaultdict(set),
                "students_by_department": defaultdict(set),
                "exams": scheduling_data.get("exams", []),
                "course_registrations": scheduling_data.get("course_registrations", []),
            }

            # Process faculties
            for faculty in faculties:
                faculty_id = UUID(faculty["id"])
                self.academic_structure["faculties"][faculty_id] = {
                    "id": faculty_id,
                    "name": faculty["name"],
                    "code": faculty["code"],
                    "departments": [],
                }

                # Get departments for faculty
                departments = await self.academic_data.get_departments_by_faculty(
                    faculty_id
                )
                for dept in departments:
                    dept_id = UUID(dept["id"])
                    self.academic_structure["departments"][dept_id] = {
                        "id": dept_id,
                        "name": dept["name"],
                        "code": dept["code"],
                        "faculty_id": faculty_id,
                    }
                    self.academic_structure["faculties"][faculty_id][
                        "departments"
                    ].append(dept_id)

            # Map courses and students to faculties/departments
            await self._map_courses_and_students()

            logger.info(
                f"Loaded academic structure: {len(self.academic_structure['faculties'])} faculties, "
                f"{len(self.academic_structure['departments'])} departments"
            )

        except Exception as e:
            logger.error(f"Error loading academic structure: {e}")
            raise

    async def _map_courses_and_students(self) -> None:
        """Map courses and students to faculties and departments"""
        try:
            # Map courses from exams
            for exam in self.academic_structure["exams"]:
                course_id = UUID(exam["course_id"])
                department_name = exam.get("department_name", "")

                # Find department ID from name
                dept_id = None
                for dept_uuid, dept_info in self.academic_structure[
                    "departments"
                ].items():
                    if dept_info["name"] == department_name:
                        dept_id = dept_uuid
                        break

                if dept_id:
                    self.academic_structure["courses_by_department"][dept_id].append(
                        course_id
                    )

                    # Map to faculty
                    faculty_id = self.academic_structure["departments"][dept_id][
                        "faculty_id"
                    ]
                    self.academic_structure["courses_by_faculty"][faculty_id].append(
                        course_id
                    )

            # Map students from registrations
            for reg in self.academic_structure["course_registrations"]:
                student_id = reg["student_id"]
                course_id = UUID(reg["course_id"])

                # Find department and faculty for this course
                for dept_id, courses in self.academic_structure[
                    "courses_by_department"
                ].items():
                    if course_id in courses:
                        self.academic_structure["students_by_department"][dept_id].add(
                            student_id
                        )

                        faculty_id = self.academic_structure["departments"][dept_id][
                            "faculty_id"
                        ]
                        self.academic_structure["students_by_faculty"][faculty_id].add(
                            student_id
                        )
                        break

        except Exception as e:
            logger.error(f"Error mapping courses and students: {e}")

    async def _build_dependency_graph(self, session_id: UUID) -> None:
        """Build dependency graph between faculties"""
        try:
            self.dependency_graph = nx.DiGraph()

            # Add faculty nodes
            for faculty_id, faculty_info in self.academic_structure[
                "faculties"
            ].items():
                self.dependency_graph.add_node(str(faculty_id), **faculty_info)

            # Analyze dependencies between faculties
            faculty_pairs = list(
                combinations(self.academic_structure["faculties"].keys(), 2)
            )

            for faculty1_id, faculty2_id in faculty_pairs:
                dependencies = await self._analyze_faculty_dependencies(
                    faculty1_id, faculty2_id
                )

                for dep_type, strength in dependencies.items():
                    if strength >= self.dependency_threshold:
                        # Add edge with dependency information
                        if not self.dependency_graph.has_edge(
                            str(faculty1_id), str(faculty2_id)
                        ):
                            self.dependency_graph.add_edge(
                                str(faculty1_id), str(faculty2_id), dependencies={}
                            )

                        edge_data = self.dependency_graph[str(faculty1_id)][
                            str(faculty2_id)
                        ]
                        edge_data["dependencies"][dep_type.value] = strength
                        edge_data["total_strength"] = sum(
                            edge_data["dependencies"].values()
                        )

            logger.info(
                f"Built dependency graph: {self.dependency_graph.number_of_nodes()} nodes, "
                f"{self.dependency_graph.number_of_edges()} edges"
            )

        except Exception as e:
            logger.error(f"Error building dependency graph: {e}")

    async def _analyze_faculty_dependencies(
        self, faculty1_id: UUID, faculty2_id: UUID
    ) -> Dict[DependencyType, float]:
        """Analyze dependencies between two faculties"""
        try:
            dependencies = {}

            # Shared students analysis
            students1 = self.academic_structure["students_by_faculty"].get(
                faculty1_id, set()
            )
            students2 = self.academic_structure["students_by_faculty"].get(
                faculty2_id, set()
            )
            shared_students = students1.intersection(students2)

            if students1 and students2:
                shared_ratio = len(shared_students) / min(
                    len(students1), len(students2)
                )
                dependencies[DependencyType.SHARED_STUDENTS] = min(shared_ratio, 1.0)

            # Shared courses analysis (cross-registration)
            courses1 = set(
                self.academic_structure["courses_by_faculty"].get(faculty1_id, [])
            )
            courses2 = set(
                self.academic_structure["courses_by_faculty"].get(faculty2_id, [])
            )

            # Check for students taking courses from both faculties
            cross_enrollment = 0
            total_enrollments = 0

            for reg in self.academic_structure["course_registrations"]:
                course_id = UUID(reg["course_id"])
                student_id = reg["student_id"]

                if course_id in courses1 or course_id in courses2:
                    total_enrollments += 1

                    # Check if student is also registered in the other faculty
                    other_faculty_courses = (
                        courses2 if course_id in courses1 else courses1
                    )
                    student_other_courses = [
                        r
                        for r in self.academic_structure["course_registrations"]
                        if r["student_id"] == student_id
                        and UUID(r["course_id"]) in other_faculty_courses
                    ]

                    if student_other_courses:
                        cross_enrollment += 1

            if total_enrollments > 0:
                cross_enrollment_ratio = cross_enrollment / total_enrollments
                dependencies[DependencyType.SHARED_COURSES] = cross_enrollment_ratio

            # Resource sharing analysis (simplified)
            # This would be enhanced with actual room and staff sharing data
            dependencies[DependencyType.SHARED_ROOMS] = 0.1  # Default low sharing
            dependencies[DependencyType.SHARED_STAFF] = 0.1  # Default low sharing

            return dependencies

        except Exception as e:
            logger.error(f"Error analyzing faculty dependencies: {e}")
            return {}

    async def _analyze_partition_characteristics(self, session_id: UUID) -> None:
        """Analyze characteristics of potential partitions"""
        try:
            # Calculate complexity metrics for each faculty
            for faculty_id, faculty_info in self.academic_structure[
                "faculties"
            ].items():
                courses = self.academic_structure["courses_by_faculty"].get(
                    faculty_id, []
                )
                students = self.academic_structure["students_by_faculty"].get(
                    faculty_id, set()
                )

                # Count exams for this faculty
                exam_count = len(
                    [
                        exam
                        for exam in self.academic_structure["exams"]
                        if UUID(exam["course_id"]) in courses
                    ]
                )

                # Estimate complexity based on various factors
                complexity = self._calculate_partition_complexity(
                    len(courses), len(students), exam_count
                )

                faculty_info.update(
                    {
                        "course_count": len(courses),
                        "student_count": len(students),
                        "exam_count": exam_count,
                        "complexity": complexity,
                    }
                )

            logger.info("Completed partition characteristics analysis")

        except Exception as e:
            logger.error(f"Error analyzing partition characteristics: {e}")

    def _calculate_partition_complexity(
        self, course_count: int, student_count: int, exam_count: int
    ) -> float:
        """Calculate complexity score for a partition"""
        try:
            # Base complexity from problem size
            size_complexity = (
                (exam_count * 0.1) + (student_count * 0.01) + (course_count * 0.05)
            )

            # Interaction complexity (student-course interactions)
            if course_count > 0 and student_count > 0:
                interaction_density = min(student_count * course_count * 0.0001, 1.0)
            else:
                interaction_density = 0.0

            # Resource complexity (simplified)
            resource_complexity = min(exam_count * 0.02, 0.5)

            total_complexity = (
                size_complexity + interaction_density + resource_complexity
            )

            return min(total_complexity, 10.0)  # Cap at 10.0

        except Exception as e:
            logger.error(f"Error calculating partition complexity: {e}")
            return 1.0

    async def create_partitioning_strategy(
        self,
        session_id: UUID,
        strategy_type: PartitionStrategy = PartitionStrategy.HYBRID,
        max_partitions: Optional[int] = None,
        balance_workload: bool = True,
    ) -> PartitioningResult:
        """Create optimal partitioning strategy for the session"""
        try:
            start_time = datetime.now()
            logger.info(
                f"Creating partitioning strategy {strategy_type.value} for session {session_id}"
            )

            # Determine optimal number of partitions if not specified
            if max_partitions is None:
                max_partitions = await self._determine_optimal_partition_count(
                    session_id
                )

            # Create partitions based on strategy
            partition_groups = []

            if strategy_type == PartitionStrategy.INDEPENDENT:
                partition_groups = await self._create_independent_partitions(
                    max_partitions
                )
            elif strategy_type == PartitionStrategy.LOOSELY_COUPLED:
                partition_groups = await self._create_loosely_coupled_partitions(
                    max_partitions
                )
            elif strategy_type == PartitionStrategy.HIERARCHICAL:
                partition_groups = await self._create_hierarchical_partitions(
                    max_partitions
                )
            elif strategy_type == PartitionStrategy.HYBRID:
                partition_groups = await self._create_hybrid_partitions(max_partitions)

            # Balance workload if requested
            if balance_workload:
                partition_groups = await self._balance_partition_workload(
                    partition_groups
                )

            # Create coordination plan
            coordination_plan = await self._create_coordination_plan(partition_groups)

            # Calculate performance estimates
            performance_estimates = await self._estimate_partition_performance(
                partition_groups
            )

            # Generate recommendations
            recommendations = await self._generate_partitioning_recommendations(
                partition_groups, coordination_plan, performance_estimates
            )

            end_time = datetime.now()
            analysis_duration = (end_time - start_time).total_seconds()

            # Create result
            result = PartitioningResult(
                partitioning_id=uuid4(),
                session_id=session_id,
                strategy_used=strategy_type,
                partition_groups=partition_groups,
                dependency_graph=dict(nx.node_link_data(self.dependency_graph)),
                coordination_plan=coordination_plan,
                performance_estimates=performance_estimates,
                recommendations=recommendations,
                partitioning_timestamp=start_time,
                analysis_duration=analysis_duration,
            )

            # Cache result
            self.partition_cache[result.partitioning_id] = result

            logger.info(
                f"Created partitioning strategy with {len(partition_groups)} groups "
                f"in {analysis_duration:.2f} seconds"
            )

            return result

        except Exception as e:
            logger.error(f"Error creating partitioning strategy: {e}")
            raise

    async def _determine_optimal_partition_count(self, session_id: UUID) -> int:
        """Determine optimal number of partitions"""
        try:
            # Count total exams and faculties
            total_exams = len(self.academic_structure["exams"])
            total_faculties = len(self.academic_structure["faculties"])

            # Heuristic for optimal partition count
            if total_exams <= 50:
                return min(2, total_faculties)
            elif total_exams <= 200:
                return min(4, total_faculties)
            elif total_exams <= 500:
                return min(6, total_faculties)
            else:
                return min(8, total_faculties)

        except Exception as e:
            logger.error(f"Error determining optimal partition count: {e}")
            return 4

    async def _create_independent_partitions(
        self, max_partitions: int
    ) -> List[PartitionGroup]:
        """Create independent partitions with minimal dependencies"""
        try:
            partition_groups = []

            # Sort faculties by complexity (ascending)
            sorted_faculties = sorted(
                self.academic_structure["faculties"].items(),
                key=lambda x: x[1].get("complexity", 0),
            )

            # Group faculties into partitions
            faculties_per_partition = max(1, len(sorted_faculties) // max_partitions)

            for i in range(0, len(sorted_faculties), faculties_per_partition):
                partition_faculties = sorted_faculties[i : i + faculties_per_partition]

                # Create partition nodes
                partition_nodes = []
                for faculty_id, faculty_info in partition_faculties:
                    node = PartitionNode(
                        node_id=faculty_id,
                        node_type="faculty",
                        name=faculty_info["name"],
                        code=faculty_info["code"],
                        courses=self.academic_structure["courses_by_faculty"].get(
                            faculty_id, []
                        ),
                        students=self.academic_structure["students_by_faculty"].get(
                            faculty_id, set()
                        ),
                        exam_count=faculty_info.get("exam_count", 0),
                        estimated_complexity=faculty_info.get("complexity", 0),
                    )
                    partition_nodes.append(node)

                # Create partition group
                group = PartitionGroup(
                    group_id=uuid4(),
                    name=f"Independent Partition {i // faculties_per_partition + 1}",
                    strategy=PartitionStrategy.INDEPENDENT,
                    partitions=partition_nodes,
                    dependencies=[],  # Independent partitions have no dependencies
                    coordination_requirements={"type": "minimal"},
                )

                partition_groups.append(group)

            return partition_groups

        except Exception as e:
            logger.error(f"Error creating independent partitions: {e}")
            return []

    async def _create_loosely_coupled_partitions(
        self, max_partitions: int
    ) -> List[PartitionGroup]:
        """Create loosely coupled partitions with managed dependencies"""
        try:
            # Use community detection on dependency graph
            communities = self._detect_faculty_communities()

            partition_groups = []
            group_id = 1

            for community in communities[:max_partitions]:
                # Create partition nodes for community
                partition_nodes = []
                dependencies = []

                for faculty_id_str in community:
                    faculty_id = UUID(faculty_id_str)
                    faculty_info = self.academic_structure["faculties"][faculty_id]

                    node = PartitionNode(
                        node_id=faculty_id,
                        node_type="faculty",
                        name=faculty_info["name"],
                        code=faculty_info["code"],
                        courses=self.academic_structure["courses_by_faculty"].get(
                            faculty_id, []
                        ),
                        students=self.academic_structure["students_by_faculty"].get(
                            faculty_id, set()
                        ),
                        exam_count=faculty_info.get("exam_count", 0),
                        estimated_complexity=faculty_info.get("complexity", 0),
                    )
                    partition_nodes.append(node)

                # Find dependencies with other partitions
                dependencies = await self._find_inter_partition_dependencies(
                    community, communities, group_id
                )

                # Create partition group
                group = PartitionGroup(
                    group_id=uuid4(),
                    name=f"Coupled Partition {group_id}",
                    strategy=PartitionStrategy.LOOSELY_COUPLED,
                    partitions=partition_nodes,
                    dependencies=dependencies,
                    coordination_requirements={
                        "type": "managed",
                        "dependency_count": len(dependencies),
                    },
                )

                partition_groups.append(group)
                group_id += 1

            return partition_groups

        except Exception as e:
            logger.error(f"Error creating loosely coupled partitions: {e}")
            return []

    def _detect_faculty_communities(self) -> List[List[str]]:
        """Detect communities in faculty dependency graph"""
        try:
            if self.dependency_graph.number_of_nodes() == 0:
                return []

            # Convert to undirected graph for community detection
            undirected = self.dependency_graph.to_undirected()

            # Use simple greedy modularity for community detection
            communities = list(
                nx.algorithms.community.greedy_modularity_communities(undirected)
            )

            # Convert to list of lists
            return [list(community) for community in communities]

        except Exception as e:
            logger.error(f"Error detecting faculty communities: {e}")
            # Fallback: each faculty is its own community
            return [
                [str(faculty_id)]
                for faculty_id in self.academic_structure["faculties"].keys()
            ]

    async def _find_inter_partition_dependencies(
        self,
        current_community: List[str],
        all_communities: List[List[str]],
        current_group_id: int,
    ) -> List[PartitionDependency]:
        """Find dependencies between partitions"""
        try:
            dependencies = []

            for other_community in all_communities:
                if other_community == current_community:
                    continue

                # Calculate dependency strength between communities
                total_strength = 0.0
                shared_entities: List[str] = []

                for faculty1_str in current_community:
                    for faculty2_str in other_community:
                        if self.dependency_graph.has_edge(faculty1_str, faculty2_str):
                            edge_data = self.dependency_graph[faculty1_str][
                                faculty2_str
                            ]
                            edge_strength = edge_data.get("total_strength", 0.0)
                            total_strength += edge_strength

                if total_strength >= self.dependency_threshold:
                    dependency = PartitionDependency(
                        dependency_id=uuid4(),
                        source_partition=uuid4(),  # Would be actual partition ID
                        target_partition=uuid4(),  # Would be actual partition ID
                        dependency_type=DependencyType.SHARED_STUDENTS,  # Simplified
                        strength=min(total_strength, 1.0),
                        shared_entities=shared_entities,
                        coordination_required=total_strength > 0.5,
                    )
                    dependencies.append(dependency)

            return dependencies

        except Exception as e:
            logger.error(f"Error finding inter-partition dependencies: {e}")
            return []

    async def _create_hierarchical_partitions(
        self, max_partitions: int
    ) -> List[PartitionGroup]:
        """Create hierarchical partitions based on faculty-department structure"""
        try:
            partition_groups = []

            # Create faculty-level partitions first
            for faculty_id, faculty_info in self.academic_structure[
                "faculties"
            ].items():
                departments = faculty_info["departments"]

                if len(departments) <= 1:
                    # Small faculty - single partition
                    node = PartitionNode(
                        node_id=faculty_id,
                        node_type="faculty",
                        name=faculty_info["name"],
                        code=faculty_info["code"],
                        courses=self.academic_structure["courses_by_faculty"].get(
                            faculty_id, []
                        ),
                        students=self.academic_structure["students_by_faculty"].get(
                            faculty_id, set()
                        ),
                        exam_count=faculty_info.get("exam_count", 0),
                        estimated_complexity=faculty_info.get("complexity", 0),
                    )

                    group = PartitionGroup(
                        group_id=uuid4(),
                        name=f"Faculty: {faculty_info['name']}",
                        strategy=PartitionStrategy.HIERARCHICAL,
                        partitions=[node],
                        coordination_requirements={
                            "type": "hierarchical",
                            "level": "faculty",
                        },
                    )
                    partition_groups.append(group)

                else:
                    # Large faculty - create department-level partitions
                    for dept_id in departments:
                        dept_info = self.academic_structure["departments"][dept_id]

                        node = PartitionNode(
                            node_id=dept_id,
                            node_type="department",
                            name=dept_info["name"],
                            code=dept_info["code"],
                            parent_id=faculty_id,
                            courses=self.academic_structure[
                                "courses_by_department"
                            ].get(dept_id, []),
                            students=self.academic_structure[
                                "students_by_department"
                            ].get(dept_id, set()),
                            estimated_complexity=0.5,  # Departments typically smaller
                        )

                        group = PartitionGroup(
                            group_id=uuid4(),
                            name=f"Dept: {dept_info['name']}",
                            strategy=PartitionStrategy.HIERARCHICAL,
                            partitions=[node],
                            coordination_requirements={
                                "type": "hierarchical",
                                "level": "department",
                                "parent_faculty": str(faculty_id),
                            },
                        )
                        partition_groups.append(group)

            # Limit to max_partitions by merging smallest partitions if necessary
            if len(partition_groups) > max_partitions:
                partition_groups = await self._merge_smallest_partitions(
                    partition_groups, max_partitions
                )

            return partition_groups

        except Exception as e:
            logger.error(f"Error creating hierarchical partitions: {e}")
            return []

    async def _create_hybrid_partitions(
        self, max_partitions: int
    ) -> List[PartitionGroup]:
        """Create hybrid partitions combining multiple strategies"""
        try:
            # Start with hierarchical partitions
            hierarchical_partitions = await self._create_hierarchical_partitions(
                max_partitions * 2
            )

            # Apply community detection to find coupling opportunities
            communities = self._detect_faculty_communities()

            # Merge partitions based on community structure
            hybrid_groups: List[PartitionGroup] = []
            used_partitions = set()

            for community in communities:
                if len(hybrid_groups) >= max_partitions:
                    break

                # Find partitions that belong to this community
                community_faculty_ids = {UUID(fid) for fid in community}
                matching_partitions = []

                for partition_group in hierarchical_partitions:
                    if partition_group.group_id in used_partitions:
                        continue

                    # Check if any partition nodes belong to this community
                    for node in partition_group.partitions:
                        if (
                            node.node_type == "faculty"
                            and node.node_id in community_faculty_ids
                        ) or (
                            node.node_type == "department"
                            and node.parent_id in community_faculty_ids
                        ):
                            matching_partitions.append(partition_group)
                            used_partitions.add(partition_group.group_id)
                            break

                if matching_partitions:
                    # Merge matching partitions into hybrid group
                    all_nodes = []
                    all_dependencies = []

                    for partition_group in matching_partitions:
                        all_nodes.extend(partition_group.partitions)
                        all_dependencies.extend(partition_group.dependencies)

                    hybrid_group = PartitionGroup(
                        group_id=uuid4(),
                        name=f"Hybrid Partition {len(hybrid_groups) + 1}",
                        strategy=PartitionStrategy.HYBRID,
                        partitions=all_nodes,
                        dependencies=all_dependencies,
                        coordination_requirements={
                            "type": "hybrid",
                            "hierarchical_levels": len(
                                set(node.node_type for node in all_nodes)
                            ),
                            "community_based": True,
                        },
                    )
                    hybrid_groups.append(hybrid_group)

            # Add remaining partitions as independent groups
            for partition_group in hierarchical_partitions:
                if (
                    partition_group.group_id not in used_partitions
                    and len(hybrid_groups) < max_partitions
                ):
                    partition_group.strategy = PartitionStrategy.HYBRID
                    partition_group.coordination_requirements["type"] = "hybrid"
                    hybrid_groups.append(partition_group)

            return hybrid_groups[:max_partitions]

        except Exception as e:
            logger.error(f"Error creating hybrid partitions: {e}")
            return []

    async def _balance_partition_workload(
        self, partition_groups: List[PartitionGroup]
    ) -> List[PartitionGroup]:
        """Balance workload across partitions"""
        try:
            # Calculate current load for each partition
            for group in partition_groups:
                total_exams = sum(node.exam_count for node in group.partitions)
                total_complexity = sum(
                    node.estimated_complexity for node in group.partitions
                )
                group.estimated_runtime = total_exams * 0.1 + total_complexity

            # Calculate load balance score
            if partition_groups:
                avg_load = sum(g.estimated_runtime for g in partition_groups) / len(
                    partition_groups
                )
                for group in partition_groups:
                    group.load_balance_score = 1.0 - abs(
                        group.estimated_runtime - avg_load
                    ) / max(avg_load, 1.0)

            # Identify imbalanced partitions
            if partition_groups:
                avg_load = sum(g.estimated_runtime for g in partition_groups) / len(
                    partition_groups
                )
                overloaded_groups = [
                    g for g in partition_groups if g.load_balance_score < 0.7
                ]
                underloaded_groups = [
                    g for g in partition_groups if g.estimated_runtime < avg_load * 0.5
                ]
            else:
                overloaded_groups = []
                underloaded_groups = []

            # Attempt to rebalance by moving nodes
            for overloaded_group in overloaded_groups:
                if underloaded_groups:
                    # Find smallest node to move
                    smallest_node = min(
                        overloaded_group.partitions,
                        key=lambda n: n.estimated_complexity,
                    )

                    # Find best destination
                    best_destination = min(
                        underloaded_groups, key=lambda g: g.estimated_runtime
                    )

                    # Move node if it improves balance
                    if (
                        overloaded_group.estimated_runtime
                        - smallest_node.estimated_complexity
                        > best_destination.estimated_runtime
                        + smallest_node.estimated_complexity
                    ):

                        overloaded_group.partitions.remove(smallest_node)
                        best_destination.partitions.append(smallest_node)

                        # Update runtime estimates
                        overloaded_group.estimated_runtime -= (
                            smallest_node.estimated_complexity
                        )
                        best_destination.estimated_runtime += (
                            smallest_node.estimated_complexity
                        )

            return partition_groups

        except Exception as e:
            logger.error(f"Error balancing partition workload: {e}")
            return partition_groups

    async def _merge_smallest_partitions(
        self, partition_groups: List[PartitionGroup], target_count: int
    ) -> List[PartitionGroup]:
        """Merge smallest partitions to reach target count"""
        try:
            # Sort by estimated runtime (smallest first)
            sorted_groups = sorted(partition_groups, key=lambda g: g.estimated_runtime)

            while len(sorted_groups) > target_count:
                # Merge two smallest groups
                group1 = sorted_groups.pop(0)
                group2 = sorted_groups.pop(0)

                merged_group = PartitionGroup(
                    group_id=uuid4(),
                    name=f"Merged: {group1.name} + {group2.name}",
                    strategy=PartitionStrategy.HYBRID,
                    partitions=group1.partitions + group2.partitions,
                    dependencies=group1.dependencies + group2.dependencies,
                    coordination_requirements={
                        "type": "merged",
                        "original_groups": [str(group1.group_id), str(group2.group_id)],
                    },
                    estimated_runtime=group1.estimated_runtime
                    + group2.estimated_runtime,
                )

                # Insert back in sorted order
                inserted = False
                for i, existing_group in enumerate(sorted_groups):
                    if (
                        merged_group.estimated_runtime
                        <= existing_group.estimated_runtime
                    ):
                        sorted_groups.insert(i, merged_group)
                        inserted = True
                        break

                if not inserted:
                    sorted_groups.append(merged_group)

            return sorted_groups

        except Exception as e:
            logger.error(f"Error merging smallest partitions: {e}")
            return partition_groups[:target_count]

    async def _create_coordination_plan(
        self, partition_groups: List[PartitionGroup]
    ) -> Dict[str, Any]:
        """Create coordination plan for partition groups"""
        try:
            coordination_plan: Dict[str, Any] = {
                "strategy": "distributed",
                "coordination_phases": [],
                "dependency_resolution": {},
                "resource_sharing": {},
                "synchronization_points": [],
            }

            # Phase 1: Independent optimization
            coordination_plan["coordination_phases"].append(
                {
                    "phase": "independent_optimization",
                    "description": "Each partition optimizes independently",
                    "duration_estimate": (
                        max(g.estimated_runtime for g in partition_groups)
                        if partition_groups
                        else 0
                    ),
                    "parallel_execution": True,
                }
            )

            # Phase 2: Dependency resolution
            total_dependencies = sum(len(g.dependencies) for g in partition_groups)
            if total_dependencies > 0:
                coordination_plan["coordination_phases"].append(
                    {
                        "phase": "dependency_resolution",
                        "description": "Resolve inter-partition dependencies",
                        "duration_estimate": total_dependencies * 0.5,
                        "parallel_execution": False,
                    }
                )

            # Phase 3: Solution integration
            coordination_plan["coordination_phases"].append(
                {
                    "phase": "solution_integration",
                    "description": "Integrate partition solutions",
                    "duration_estimate": len(partition_groups) * 0.1,
                    "parallel_execution": False,
                }
            )

            # Dependency resolution strategies
            for group in partition_groups:
                for dependency in group.dependencies:
                    coordination_plan["dependency_resolution"][
                        str(dependency.dependency_id)
                    ] = {
                        "strategy": await self._get_dependency_resolution_strategy(
                            dependency
                        ),
                        "priority": "high" if dependency.strength > 0.7 else "medium",
                    }

            # Resource sharing plan
            coordination_plan["resource_sharing"] = {
                "shared_rooms": await self._identify_shared_resources(
                    "rooms", partition_groups
                ),
                "shared_staff": await self._identify_shared_resources(
                    "staff", partition_groups
                ),
                "conflict_resolution": "round_robin",  # or 'priority_based'
            }

            # Synchronization points
            sync_points: List[Dict[str, str]] = [
                {"point": "pre_optimization", "description": "Validate partition data"},
                {"point": "post_independent", "description": "Check for conflicts"},
                {
                    "point": "post_resolution",
                    "description": "Validate integrated solution",
                },
            ]
            coordination_plan["synchronization_points"] = sync_points

            return coordination_plan
        except Exception as e:
            logger.error(f"Failed to create coordination plan: {e}")
            raise

    async def _get_dependency_resolution_strategy(
        self, dependency: PartitionDependency
    ) -> str:
        """Get resolution strategy for a dependency"""
        try:
            if dependency.dependency_type == DependencyType.SHARED_STUDENTS:
                if dependency.strength > 0.8:
                    return "sequential_optimization"
                else:
                    return "conflict_checking"
            elif dependency.dependency_type in [
                DependencyType.SHARED_ROOMS,
                DependencyType.SHARED_STAFF,
            ]:
                return "resource_allocation"
            else:
                return "post_hoc_validation"

        except Exception as e:
            logger.error(f"Error getting dependency resolution strategy: {e}")
            return "default"

    async def _identify_shared_resources(
        self, resource_type: str, partition_groups: List[PartitionGroup]
    ) -> List[Dict[str, Any]]:
        """Identify shared resources between partitions"""
        try:
            # This would identify actual shared resources
            # For now, return simplified structure
            return [
                {
                    "resource_id": "shared_resource_1",
                    "resource_type": resource_type,
                    "sharing_partitions": ["partition_1", "partition_2"],
                    "allocation_strategy": "time_based",
                }
            ]

        except Exception as e:
            logger.error(f"Error identifying shared resources: {e}")
            return []

    async def _estimate_partition_performance(
        self, partition_groups: List[PartitionGroup]
    ) -> Dict[str, Any]:
        """Estimate performance characteristics of partitioning"""
        try:
            # Calculate total runtime estimates
            sequential_runtime = sum(g.estimated_runtime for g in partition_groups)
            parallel_runtime = (
                max(g.estimated_runtime for g in partition_groups)
                if partition_groups
                else 0
            )

            # Calculate speedup
            speedup = (
                sequential_runtime / max(parallel_runtime, 1.0)
                if parallel_runtime > 0
                else 1.0
            )

            # Calculate efficiency
            efficiency = speedup / len(partition_groups) if partition_groups else 0.0

            # Calculate load balance
            if partition_groups:
                avg_load = sum(g.estimated_runtime for g in partition_groups) / len(
                    partition_groups
                )
                load_variance = sum(
                    (g.estimated_runtime - avg_load) ** 2 for g in partition_groups
                ) / len(partition_groups)
                load_balance = 1.0 / (1.0 + load_variance / max(avg_load, 1.0))
            else:
                load_balance = 0.0

            return {
                "sequential_runtime_estimate": round(sequential_runtime, 2),
                "parallel_runtime_estimate": round(parallel_runtime, 2),
                "speedup_factor": round(speedup, 2),
                "efficiency": round(efficiency, 3),
                "load_balance_score": round(load_balance, 3),
                "partition_count": len(partition_groups),
                "total_dependencies": sum(
                    len(g.dependencies) for g in partition_groups
                ),
                "coordination_overhead_estimate": round(
                    sum(len(g.dependencies) for g in partition_groups) * 0.1, 2
                ),
            }

        except Exception as e:
            logger.error(f"Error estimating partition performance: {e}")
            return {}

    async def _generate_partitioning_recommendations(
        self,
        partition_groups: List[PartitionGroup],
        coordination_plan: Dict[str, Any],
        performance_estimates: Dict[str, Any],
    ) -> List[str]:
        """Generate recommendations for the partitioning strategy"""
        try:
            recommendations = []

            # Performance recommendations
            speedup = performance_estimates.get("speedup_factor", 1.0)
            if speedup < 2.0:
                recommendations.append(
                    "Low speedup factor - consider reducing partition count or improving load balance"
                )

            efficiency = performance_estimates.get("efficiency", 0.0)
            if efficiency < 0.6:
                recommendations.append(
                    "Low efficiency - partitions may be too granular or dependencies too strong"
                )

            load_balance = performance_estimates.get("load_balance_score", 0.0)
            if load_balance < 0.7:
                recommendations.append(
                    "Poor load balance - consider redistributing courses or merging small partitions"
                )

            # Dependency recommendations
            total_dependencies = performance_estimates.get("total_dependencies", 0)
            if total_dependencies > len(partition_groups) * 2:
                recommendations.append(
                    "High dependency count - consider different partitioning strategy or merge related partitions"
                )

            # Strategy-specific recommendations
            strategies = set(g.strategy for g in partition_groups)
            if len(strategies) > 1:
                recommendations.append(
                    "Mixed strategies detected - ensure coordination plan handles different partition types"
                )

            # Size recommendations
            small_partitions = [
                g
                for g in partition_groups
                if sum(n.exam_count for n in g.partitions) < self.min_partition_size
            ]
            if small_partitions:
                recommendations.append(
                    f"{len(small_partitions)} partitions are below minimum size - consider merging"
                )

            large_partitions = [
                g
                for g in partition_groups
                if sum(n.exam_count for n in g.partitions) > self.max_partition_size
            ]
            if large_partitions:
                recommendations.append(
                    f"{len(large_partitions)} partitions exceed maximum size - consider splitting"
                )

            return recommendations

        except Exception as e:
            logger.error(f"Error generating partitioning recommendations: {e}")
            return []

    async def get_partition_details(
        self, partitioning_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a partitioning result"""
        try:
            if partitioning_id not in self.partition_cache:
                return None

            result = self.partition_cache[partitioning_id]

            return {
                "partitioning_id": str(result.partitioning_id),
                "session_id": str(result.session_id),
                "strategy": result.strategy_used.value,
                "created_at": result.partitioning_timestamp.isoformat(),
                "analysis_duration": result.analysis_duration,
                "partition_groups": [
                    {
                        "group_id": str(group.group_id),
                        "name": group.name,
                        "strategy": group.strategy.value,
                        "partition_count": len(group.partitions),
                        "total_exams": sum(
                            node.exam_count for node in group.partitions
                        ),
                        "total_students": len(
                            set().union(*(node.students for node in group.partitions))
                        ),
                        "estimated_runtime": group.estimated_runtime,
                        "load_balance_score": group.load_balance_score,
                        "dependency_count": len(group.dependencies),
                        "coordination_type": group.coordination_requirements.get(
                            "type", "unknown"
                        ),
                    }
                    for group in result.partition_groups
                ],
                "performance_estimates": result.performance_estimates,
                "recommendations": result.recommendations,
            }

        except Exception as e:
            logger.error(f"Error getting partition details: {e}")
            return None

    async def validate_partitioning(self, partitioning_id: UUID) -> Dict[str, Any]:
        """Validate a partitioning result"""
        try:
            if partitioning_id not in self.partition_cache:
                return {"valid": False, "errors": ["Partitioning not found"]}

            result = self.partition_cache[partitioning_id]
            errors = []
            warnings = []

            # Check partition coverage
            all_faculties = set(self.academic_structure["faculties"].keys())
            covered_faculties = set()

            for group in result.partition_groups:
                for node in group.partitions:
                    if node.node_type == "faculty":
                        covered_faculties.add(node.node_id)
                    elif node.node_type == "department" and node.parent_id:
                        covered_faculties.add(node.parent_id)

            missing_faculties = all_faculties - covered_faculties
            if missing_faculties:
                errors.append(
                    f"Missing coverage for faculties: {[str(fid) for fid in missing_faculties]}"
                )

            # Check for overlapping partitions
            all_nodes = []
            for group in result.partition_groups:
                all_nodes.extend(group.partitions)

            node_ids = [node.node_id for node in all_nodes]
            if len(node_ids) != len(set(node_ids)):
                errors.append("Overlapping partitions detected")

            # Check partition sizes
            for group in result.partition_groups:
                total_exams = sum(node.exam_count for node in group.partitions)
                if total_exams < self.min_partition_size:
                    warnings.append(
                        f"Partition '{group.name}' is below minimum size ({total_exams})"
                    )
                elif total_exams > self.max_partition_size:
                    warnings.append(
                        f"Partition '{group.name}' exceeds maximum size ({total_exams})"
                    )

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "coverage_percentage": len(covered_faculties)
                / max(len(all_faculties), 1)
                * 100,
            }

        except Exception as e:
            logger.error(f"Error validating partitioning: {e}")
            return {"valid": False, "errors": [str(e)]}

    def clear_cache(self) -> None:
        """Clear partitioning caches"""
        try:
            self.partition_cache.clear()
            self.academic_structure.clear()
            self.dependency_graph.clear()

            logger.info("Faculty partitioning caches cleared")

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
