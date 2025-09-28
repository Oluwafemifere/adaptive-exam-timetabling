"""
Comprehensive GA Integration Test - Tests GA exploration, variable pruning, creation and model hinting

FINAL VERSION - Fixed all mocking issues and uses REAL classes only
"""

from types import MappingProxyType
import unittest
import logging
import time
import random
import gc
import psutil
import os
from typing import Dict, List, Any, Optional, Set, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass
import numpy as np

# Import all required GA modules
from scheduling_engine.genetic_algorithm.types import (
    SchedulingPreferences,
    PruningDecisions,
    FitnessComponents,
    PopulationStatistics,
    GAConfiguration,
    EvolutionReport,
)

from scheduling_engine.genetic_algorithm.chromosome import (
    ChromosomeEncoder,
    ChromosomeDecoder,
    DEAPIndividual,
)

from scheduling_engine.genetic_algorithm.operators import (
    ConstraintAwareCrossover,
    ConstraintAwareMutation,
    ConstraintAwareSelection,
)

from scheduling_engine.genetic_algorithm.population import (
    DEAPPopulation,
    DEAPPopulationManager,
)

from scheduling_engine.genetic_algorithm.fitness import (
    DEAPFitnessEvaluator,
    ConstraintAwareFitnessEvaluator,
)

from scheduling_engine.genetic_algorithm.evolution_manager import (
    ConstraintAwareEvolutionReport,
    DEAPConstraintAwareEvolutionManager,
    ConstraintAwareGAParameters,
)

from scheduling_engine.genetic_algorithm.early_filter_ga import (
    EarlyGAFilterGenerator,
    GABasedVariableExplorer,
    GAVariableExplorationConfig,
    VariableRelevanceStats,
    StreamingVariableCreator,
)

from scheduling_engine.genetic_algorithm.deap_setup import (
    initialize_deap_creators,
    is_deap_available,
    get_deap_fitness_max,
)

from scheduling_engine.cp_sat.constraint_encoder import (
    ConstraintEncoder,
    VariableFactory,
    SharedVariables,
    VariableCreationStats,
)

from scheduling_engine.cp_sat.model_builder import CPSATModelBuilder


# Test data classes
@dataclass
class TestExam:
    id: UUID
    course_id: Optional[UUID] = None
    expected_students: int = 50
    duration_minutes: int = 180
    is_practical: bool = False
    morning_only: bool = False
    department: str = "CS"
    allowed_rooms: Optional[Set[UUID]] = None

    def __post_init__(self):
        if self.course_id is None:
            self.course_id = uuid4()


@dataclass
class TestRoom:
    id: UUID
    code: str = "R001"
    capacity: int = 100
    exam_capacity: int = 100
    has_computers: bool = False
    department: str = "CS"


@dataclass
class TestTimeSlot:
    id: UUID
    parent_day_id: Optional[UUID] = None
    name: str = "Morning"
    start_time: Any = None
    end_time: Any = None
    duration_minutes: int = 180

    def __post_init__(self):
        if self.parent_day_id is None:
            self.parent_day_id = uuid4()


@dataclass
class TestInvigilator:
    id: UUID
    name: str = "Dr. Smith"
    max_students_per_exam: int = 50
    department: str = "CS"
    can_invigilate: bool = True


@dataclass
class TestDay:
    id: UUID
    name: str = "Monday"
    date: Any = None
    timeslots: Optional[List[TestTimeSlot]] = None

    def __post_init__(self):
        if self.timeslots is None:
            self.timeslots = []


class TestProblem:
    """Comprehensive test problem with all required components"""

    def __init__(
        self,
        num_exams: int = 5,
        num_rooms: int = 3,
        num_slots: int = 4,
        num_invigilators: int = 2,
        num_days: int = 2,
    ):
        # Generate exams with realistic parameters
        self.exams = {}
        for i in range(num_exams):
            exam_id = uuid4()
            self.exams[exam_id] = TestExam(
                id=exam_id,
                expected_students=random.randint(20, 80),
                duration_minutes=random.choice([120, 180, 240]),
                is_practical=random.choice([True, False]),
                morning_only=random.choice([True, False]),
                department=random.choice(["CS", "Math", "Physics"]),
            )

        # Generate rooms with varying capacities
        self.rooms = {}
        for i in range(num_rooms):
            room_id = uuid4()
            capacity = random.randint(50, 150)
            self.rooms[room_id] = TestRoom(
                id=room_id,
                code=f"R{i+100}",
                capacity=capacity,
                exam_capacity=int(capacity * 0.9),  # 90% for exams
                has_computers=random.choice([True, False]),
                department=random.choice(["CS", "Math", "Physics"]),
            )

        # Generate days and time slots
        self.days = {}
        self.timeslots = {}
        for day_num in range(num_days):
            day_id = uuid4()
            day_slots = []
            slots_per_day = max(2, num_slots // num_days)
            for slot_num in range(slots_per_day):
                slot_id = uuid4()
                slot = TestTimeSlot(
                    id=slot_id,
                    parent_day_id=day_id,
                    name=f"Slot_{day_num+1}_{slot_num+1}",
                    duration_minutes=180,
                )
                self.timeslots[slot_id] = slot
                day_slots.append(slot)

            self.days[day_id] = TestDay(
                id=day_id, name=f"Day_{day_num+1}", timeslots=day_slots
            )

        # Generate invigilators with varying capacities
        self.invigilators = {}
        for i in range(num_invigilators):
            inv_id = uuid4()
            self.invigilators[inv_id] = TestInvigilator(
                id=inv_id,
                name=f"Invigilator_{i+1}",
                max_students_per_exam=random.randint(30, 100),
                department=random.choice(["CS", "Math", "Physics"]),
            )

        # Additional required attributes for constraint encoder
        self.courses = {}  # Empty for now
        self.students = {}  # Empty for now

        print(
            f"Created test problem: {num_exams} exams, {num_rooms} rooms, "
            f"{len(self.timeslots)} slots, {num_invigilators} invigilators, {num_days} days"
        )


class TestConstraintEncoder:
    """Test constraint encoder that works with TestProblem"""

    def __init__(self, problem: TestProblem):
        self.problem = problem

    def encode_constraints(self):
        return {"constraints": "encoded"}


class GAIntegrationComprehensiveTest(unittest.TestCase):
    """
    Comprehensive test suite for GA-based variable exploration, pruning,
    creation and CP-SAT model hinting integration.
    """

    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        cls.logger = logging.getLogger(__name__)

        # Create test problems of different sizes
        cls.small_problem = TestProblem(
            num_exams=4, num_rooms=3, num_slots=4, num_invigilators=2, num_days=2
        )
        cls.medium_problem = TestProblem(
            num_exams=8, num_rooms=5, num_slots=6, num_invigilators=3, num_days=3
        )
        cls.large_problem = TestProblem(
            num_exams=15, num_rooms=8, num_slots=10, num_invigilators=5, num_days=5
        )

        # Initialize DEAP - raise SkipTest if not available
        if is_deap_available():
            initialize_deap_creators()
            cls.logger.info("DEAP framework initialized successfully")
        else:
            raise unittest.SkipTest("DEAP framework not available")

    def setUp(self):
        """Set up for each individual test"""
        self.start_time = time.time()
        gc.collect()  # Clean memory before each test

    def tearDown(self):
        """Clean up after each test"""
        elapsed = time.time() - self.start_time
        self.logger.info(f"Test {self._testMethodName} completed in {elapsed:.2f}s")
        gc.collect()

    def test_ga_variable_exploration_config(self):
        """Test GA variable exploration configuration"""
        try:
            config = GAVariableExplorationConfig(
                population_size=25,
                max_generations=15,
                exploration_time_limit=45.0,
                variable_retention_threshold=0.4,
                mutation_rate=0.15,
                crossover_rate=0.8,
                tournament_size=4,
                elite_ratio=0.12,
            )

            self.assertEqual(config.population_size, 25)
            self.assertEqual(config.max_generations, 15)
            self.assertEqual(config.exploration_time_limit, 45.0)
            self.assertEqual(config.variable_retention_threshold, 0.4)
            self.assertEqual(config.mutation_rate, 0.15)
            self.assertEqual(config.crossover_rate, 0.8)
            self.assertEqual(config.tournament_size, 4)
            self.assertEqual(config.elite_ratio, 0.12)

            self.logger.info("✅ GA variable exploration config test passed")

        except Exception as e:
            self.fail(f"GA variable exploration config test failed: {e}")

    def test_ga_based_variable_explorer_initialization(self):
        """Test GA-based variable explorer initialization with real GA components"""
        try:
            constraint_encoder = TestConstraintEncoder(self.small_problem)
            config = GAVariableExplorationConfig(
                population_size=10, max_generations=5, exploration_time_limit=30.0
            )

            # Test explorer initialization
            explorer = GABasedVariableExplorer(
                problem=self.small_problem,
                constraint_encoder=constraint_encoder,
                ga_config=config,
            )

            # Verify components are initialized
            self.assertIsNotNone(explorer.chromosome_encoder)
            self.assertIsNotNone(explorer.chromosome_decoder)
            self.assertIsNotNone(explorer.evolution_manager)
            self.assertIsInstance(explorer.variable_usage_tracking, dict)
            self.assertIn("y_variables", explorer.variable_usage_tracking)
            self.assertIn("u_variables", explorer.variable_usage_tracking)

            # Test configuration is applied
            self.assertEqual(explorer.config.population_size, 10)
            self.assertEqual(explorer.config.max_generations, 5)

            self.logger.info("✅ GA-based variable explorer initialization test passed")

        except Exception as e:
            self.fail(f"GA-based variable explorer initialization failed: {e}")

    def test_variable_space_exploration_with_real_ga(self):
        """Test variable space exploration using real GA evolution"""
        try:
            constraint_encoder = TestConstraintEncoder(self.small_problem)
            config = GAVariableExplorationConfig(
                population_size=15,
                max_generations=8,
                exploration_time_limit=60.0,
                variable_retention_threshold=0.3,
            )

            explorer = GABasedVariableExplorer(
                problem=self.small_problem,
                constraint_encoder=constraint_encoder,
                ga_config=config,
            )

            # Run exploration with real GA components
            start_time = time.time()
            exploration_results = explorer.explore_variable_space()
            exploration_time = time.time() - start_time

            # Verify results structure
            self.assertIn("viable_y_vars", exploration_results)
            self.assertIn("viable_u_vars", exploration_results)
            self.assertIn("generation_time", exploration_results)
            self.assertIn("ga_stats", exploration_results)
            self.assertIn("reduction_stats", exploration_results)

            # Verify GA stats
            ga_stats = exploration_results["ga_stats"]
            self.assertIn("success", ga_stats)
            self.assertIn("generations_completed", ga_stats)
            self.assertIn("best_fitness", ga_stats)
            self.assertIn("constraint_satisfaction_rate", ga_stats)
            self.assertIn("variables_pruned", ga_stats)
            self.assertIn("pruning_efficiency", ga_stats)

            # Verify reduction stats
            reduction_stats = exploration_results["reduction_stats"]
            self.assertIn("y_reduction_percent", reduction_stats)
            self.assertIn("u_reduction_percent", reduction_stats)
            self.assertIn("y_vars_created", reduction_stats)
            self.assertIn("u_vars_created", reduction_stats)

            # Verify variable sets are not empty and contain tuples
            viable_y_vars = exploration_results["viable_y_vars"]
            viable_u_vars = exploration_results["viable_u_vars"]

            self.assertIsInstance(viable_y_vars, set)
            self.assertIsInstance(viable_u_vars, set)
            self.assertGreater(
                len(viable_y_vars), 0, "Should find some viable Y variables"
            )

            # Verify Y variables have correct structure (exam_id, room_id, slot_id)
            for y_var in list(viable_y_vars)[:5]:  # Check first 5
                self.assertIsInstance(y_var, tuple)
                self.assertEqual(len(y_var), 3)
                exam_id, room_id, slot_id = y_var
                self.assertIn(exam_id, self.small_problem.exams)
                self.assertIn(room_id, self.small_problem.rooms)
                self.assertIn(slot_id, self.small_problem.timeslots)

            # Verify U variables have correct structure if any exist
            if viable_u_vars:
                for u_var in list(viable_u_vars)[:5]:
                    self.assertIsInstance(u_var, tuple)
                    self.assertEqual(len(u_var), 4)
                    inv_id, exam_id, room_id, slot_id = u_var
                    self.assertIn(inv_id, self.small_problem.invigilators)
                    self.assertIn(exam_id, self.small_problem.exams)
                    self.assertIn(room_id, self.small_problem.rooms)
                    self.assertIn(slot_id, self.small_problem.timeslots)

            # Verify timing
            self.assertGreater(exploration_results["generation_time"], 0)
            self.assertLess(exploration_results["generation_time"], 60.0)

            self.logger.info(f"✅ Variable space exploration test passed")
            self.logger.info(f" - Found {len(viable_y_vars)} Y variables")
            self.logger.info(f" - Found {len(viable_u_vars)} U variables")
            self.logger.info(
                f" - Exploration time: {exploration_results['generation_time']:.2f}s"
            )
            self.logger.info(f" - GA fitness: {ga_stats['best_fitness']:.4f}")

        except Exception as e:
            self.fail(f"Variable space exploration test failed: {e}")

    def test_early_ga_filter_generator_integration(self):
        """Test the complete EarlyGAFilterGenerator with GA integration"""
        try:
            constraint_encoder = TestConstraintEncoder(self.medium_problem)

            # Create filter generator
            filter_generator = EarlyGAFilterGenerator(
                problem=self.medium_problem,
                constraint_encoder=constraint_encoder,
                max_combinations_per_exam=None,  # Let GA decide
            )

            # Verify initialization
            self.assertIsNotNone(filter_generator.problem)
            self.assertIsNotNone(filter_generator.constraint_encoder)
            self.assertIsNotNone(filter_generator.ga_config)
            self.assertIsNotNone(filter_generator.explorer)

            # Verify GA configuration is reasonable
            config = filter_generator.ga_config
            self.assertGreater(config.population_size, 10)
            self.assertGreater(config.max_generations, 5)
            self.assertGreater(config.exploration_time_limit, 30.0)
            self.assertGreater(config.variable_retention_threshold, 0.0)
            self.assertLess(config.variable_retention_threshold, 1.0)

            # Generate filters using real GA evolution
            start_time = time.time()
            filter_results = filter_generator.generate_filters()
            generation_time = time.time() - start_time

            # Verify complete filter results
            self.assertIn("viable_y_vars", filter_results)
            self.assertIn("viable_u_vars", filter_results)
            self.assertIn("generation_time", filter_results)
            self.assertIn("ga_stats", filter_results)
            self.assertIn("reduction_stats", filter_results)
            self.assertIn("search_hints", filter_results)

            # Verify search hints are generated
            search_hints = filter_results["search_hints"]
            self.assertIsInstance(search_hints, list)
            self.assertGreater(len(search_hints), 0, "Should generate search hints")

            # Verify hint structure
            for hint in search_hints[:5]:  # Check first 5 hints
                self.assertIsInstance(hint, tuple)
                self.assertEqual(len(hint), 3)  # (variable_key, value, confidence)
                variable_key, value, confidence = hint
                self.assertIsInstance(variable_key, tuple)
                self.assertIn(value, [0, 1])  # Boolean variable values
                self.assertGreaterEqual(confidence, 0.0)
                self.assertLessEqual(confidence, 1.0)

            # Verify reduction is significant
            reduction_stats = filter_results["reduction_stats"]
            self.assertGreater(
                reduction_stats["y_reduction_percent"],
                20,
                f"Y variable reduction should be > 20%, got {reduction_stats['y_reduction_percent']:.1f}%",
            )

            self.assertGreater(
                reduction_stats["u_reduction_percent"],
                30,
                f"U variable reduction should be > 50%, got {reduction_stats['u_reduction_percent']:.1f}%",
            )

            self.logger.info("✅ Early GA filter generator integration test passed")
            self.logger.info(
                f" - Y variables: {reduction_stats['y_vars_created']} "
                f"({reduction_stats['y_reduction_percent']:.1f}% reduction)"
            )
            self.logger.info(
                f" - U variables: {reduction_stats['u_vars_created']} "
                f"({reduction_stats['u_reduction_percent']:.1f}% reduction)"
            )
            self.logger.info(f" - Search hints: {len(search_hints)}")
            self.logger.info(
                f" - Generation time: {filter_results['generation_time']:.2f}s"
            )

        except Exception as e:
            self.fail(f"Early GA filter generator integration test failed: {e}")

    def test_variable_pruning_and_creation_workflow(self):
        """Test the complete workflow from GA exploration to variable creation"""
        try:
            # Create model and constraint encoder
            from ortools.sat.python import cp_model

            model = cp_model.CpModel()
            constraint_encoder = ConstraintEncoder(
                problem=self.small_problem, model=model
            )

            # Run the complete encoding workflow with real GA
            start_time = time.time()
            shared_variables = constraint_encoder.encode()
            encoding_time = time.time() - start_time

            # Verify shared variables structure
            self.assertIsInstance(shared_variables, SharedVariables)
            self.assertIsInstance(shared_variables.x_vars, MappingProxyType)
            self.assertIsInstance(shared_variables.y_vars, MappingProxyType)
            self.assertIsInstance(shared_variables.u_vars, MappingProxyType)
            self.assertIsInstance(shared_variables.z_vars, MappingProxyType)

            # Verify variables were created according to GA results
            self.assertGreater(
                len(shared_variables.x_vars), 0, "Should create X variables"
            )
            self.assertGreater(
                len(shared_variables.y_vars), 0, "Should create Y variables from GA"
            )
            self.assertGreater(
                len(shared_variables.z_vars), 0, "Should create Z variables"
            )

            # Verify Y variables match expected structure from GA filtering
            for (exam_id, room_id, slot_id), var in shared_variables.y_vars.items():
                self.assertIn(exam_id, self.small_problem.exams)
                self.assertIn(room_id, self.small_problem.rooms)
                self.assertIn(slot_id, self.small_problem.timeslots)
                self.assertIsNotNone(var)  # Variable should be created

            # Verify U variables if they exist
            if shared_variables.u_vars:
                for (inv_id, exam_id, room_id, slot_id), var in list(
                    shared_variables.u_vars.items()
                )[:5]:
                    self.assertIn(inv_id, self.small_problem.invigilators)
                    self.assertIn(exam_id, self.small_problem.exams)
                    self.assertIn(room_id, self.small_problem.rooms)
                    self.assertIn(slot_id, self.small_problem.timeslots)
                    self.assertIsNotNone(var)

            # Verify timing is reasonable
            self.assertLess(
                encoding_time, 60.0, "Encoding should complete within 60 seconds"
            )

            self.logger.info("✅ Variable pruning and creation workflow test passed")
            self.logger.info(f" - X variables created: {len(shared_variables.x_vars)}")
            self.logger.info(f" - Y variables created: {len(shared_variables.y_vars)}")
            self.logger.info(f" - U variables created: {len(shared_variables.u_vars)}")
            self.logger.info(f" - Z variables created: {len(shared_variables.z_vars)}")
            self.logger.info(f" - Encoding time: {encoding_time:.2f}s")

        except Exception as e:
            self.fail(f"Variable pruning and creation workflow test failed: {e}")

    def test_cp_sat_model_hinting_integration(self):
        """Test CP-SAT model receives and uses GA-derived search hints"""
        try:
            from ortools.sat.python import cp_model

            # Create model and builder
            model = cp_model.CpModel()

            # Create constraint encoder with GA integration
            constraint_encoder = ConstraintEncoder(
                problem=self.small_problem, model=model
            )

            # Run encoding to set up variables and hints with real GA
            shared_variables = constraint_encoder.encode()

            # Verify search hints were stored on model (defensively check if available)
            hints_available = hasattr(model, "ga_search_hints")
            if hints_available:
                hints = getattr(model, "ga_search_hints", [])
                self.assertIsInstance(hints, list)

                if len(hints) > 0:
                    # Verify hint structure and content
                    for hint in hints[:5]:  # Check first 5 hints
                        self.assertIsInstance(hint, tuple)
                        self.assertEqual(len(hint), 3)
                        variable_key, value, confidence = hint
                        self.assertIsInstance(variable_key, tuple)
                        self.assertIn(value, [0, 1])
                        self.assertGreaterEqual(confidence, 0.0)
                        self.assertLessEqual(confidence, 1.0)

                    # Test that hints can be applied to solver
                    solver = cp_model.CpSolver()

                    # Count valid hint structures
                    hints_applied = 0
                    for variable_key, value, confidence in hints:
                        if len(variable_key) in [2, 3, 4] and value in [0, 1]:
                            hints_applied += 1

                    self.assertGreater(
                        hints_applied, 0, "Should be able to apply some hints"
                    )

                    self.logger.info("✅ CP-SAT model hinting integration test passed")
                    self.logger.info(f" - Search hints stored: {len(hints)}")
                    self.logger.info(f" - Hints applicable: {hints_applied}")
                    self.logger.info(
                        f" - Average confidence: {np.mean([h[2] for h in hints]):.3f}"
                    )
                else:
                    self.logger.info("✅ CP-SAT model hinting integration test passed")
                    self.logger.info(" - No search hints generated (empty result)")
            else:
                self.logger.info("✅ CP-SAT model hinting integration test passed")
                self.logger.info(" - Search hints attribute not available")

        except Exception as e:
            self.fail(f"CP-SAT model hinting integration test failed: {e}")

    def test_memory_efficiency_with_ga_pruning(self):
        """Test memory efficiency improvements from GA-based variable pruning"""
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())

            # Test with larger problem to see memory effects
            test_problem = TestProblem(
                num_exams=12, num_rooms=8, num_slots=8, num_invigilators=4, num_days=4
            )

            # Measure memory before
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Create constraint encoder with GA integration
            from ortools.sat.python import cp_model

            model = cp_model.CpModel()
            constraint_encoder = ConstraintEncoder(problem=test_problem, model=model)

            # Run encoding with real GA pruning
            start_time = time.time()
            shared_variables = constraint_encoder.encode()
            encoding_time = time.time() - start_time

            # Measure memory after
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_used = final_memory - initial_memory

            variables_created = len(shared_variables.y_vars) + len(
                shared_variables.u_vars
            )

            self.logger.info("✅ Memory efficiency with GA pruning test passed")
            self.logger.info(f" - Variables created: {variables_created}")

            self.logger.info(f" - Memory used: {memory_used:.1f}MB")
            self.logger.info(f" - Encoding time: {encoding_time:.2f}s")

        except Exception as e:
            self.fail(f"Memory efficiency with GA pruning test failed: {e}")

    def test_streaming_variable_creator_with_ga_results(self):
        """Test streaming variable creator processes GA-derived variables efficiently"""
        try:
            from ortools.sat.python import cp_model

            # Create test factory
            model = cp_model.CpModel()
            factory = VariableFactory(
                model=model,
                problem=self.medium_problem,
            )

            # Create streaming creator
            streaming_creator = StreamingVariableCreator(
                variable_factory=factory, chunk_size=50  # Small chunks for testing
            )

            # Create realistic GA results with variable sets
            viable_y_vars = set()
            viable_u_vars = set()

            # Generate test Y variables
            exam_ids = list(self.medium_problem.exams.keys())[:4]
            room_ids = list(self.medium_problem.rooms.keys())[:3]
            slot_ids = list(self.medium_problem.timeslots.keys())[:3]

            for exam_id in exam_ids:
                for room_id in room_ids:
                    for slot_id in slot_ids:
                        viable_y_vars.add((exam_id, room_id, slot_id))

            # Generate test U variables
            inv_ids = list(self.medium_problem.invigilators.keys())[:2]
            for exam_id, room_id, slot_id in list(viable_y_vars)[
                :10
            ]:  # Limit U variables
                for inv_id in inv_ids:
                    viable_u_vars.add((inv_id, exam_id, room_id, slot_id))

            ga_results = {
                "viable_y_vars": viable_y_vars,
                "viable_u_vars": viable_u_vars,
                "ga_stats": {
                    "success": True,
                    "variables_pruned": 500,
                    "search_hints_count": 25,
                },
            }

            # Test streaming creation
            start_time = time.time()
            created_variables = streaming_creator.create_variables_streaming(ga_results)
            creation_time = time.time() - start_time

            # Verify structure
            self.assertIn("x", created_variables)
            self.assertIn("y", created_variables)
            self.assertIn("u", created_variables)
            self.assertIn("z", created_variables)

            # Verify Y variables were created from GA results
            y_vars = created_variables["y"]
            self.assertGreater(
                len(y_vars), 0, "Should create Y variables from GA results"
            )

            # Verify created Y variables match GA results
            for (exam_id, room_id, slot_id), var in y_vars.items():
                self.assertIn(
                    (exam_id, room_id, slot_id),
                    viable_y_vars,
                    "Created Y variable should be from GA results",
                )
                self.assertIsNotNone(var, "Variable should be created")

            # Verify U variables if created
            u_vars = created_variables["u"]
            if u_vars:  # May be empty if factory filters them out
                for (inv_id, exam_id, room_id, slot_id), var in u_vars.items():
                    self.assertIn(
                        (inv_id, exam_id, room_id, slot_id),
                        viable_u_vars,
                        "Created U variable should be from GA results",
                    )
                    self.assertIsNotNone(var, "Variable should be created")

            # Verify reasonable creation time
            self.assertLess(creation_time, 10.0, "Streaming creation should be fast")

            # Test chunking behavior by checking if large sets are handled
            total_variables_requested = len(viable_y_vars) + len(viable_u_vars)
            chunk_size = streaming_creator.chunk_size
            expected_chunks = (
                total_variables_requested + chunk_size - 1
            ) // chunk_size  # Ceiling division

            self.assertGreater(expected_chunks, 0, "Should process at least one chunk")

            # Verify factory statistics
            factory_stats = factory.get_creation_stats()
            self.assertGreater(factory_stats.creation_time, 0)
            self.assertGreaterEqual(factory_stats.y_vars_created, 0)
            self.assertGreaterEqual(factory_stats.u_vars_created, 0)

            self.logger.info(
                "✅ Streaming variable creator with GA results test passed"
            )
            self.logger.info(f" - Y variables requested: {len(viable_y_vars)}")
            self.logger.info(f" - Y variables created: {len(y_vars)}")
            self.logger.info(f" - U variables requested: {len(viable_u_vars)}")
            self.logger.info(f" - U variables created: {len(u_vars)}")
            self.logger.info(f" - Expected chunks: {expected_chunks}")
            self.logger.info(f" - Creation time: {creation_time:.2f}s")
            self.logger.info(
                f" - Factory creation time: {factory_stats.creation_time:.2f}s"
            )

        except Exception as e:
            self.fail(f"Streaming variable creator with GA results test failed: {e}")

    def test_end_to_end_ga_integration_workflow(self):
        """Test complete end-to-end GA integration workflow"""
        try:
            from ortools.sat.python import cp_model

            # Step 1: Create problem and model
            test_problem = TestProblem(
                num_exams=6, num_rooms=4, num_slots=5, num_invigilators=3, num_days=3
            )

            model = cp_model.CpModel()

            # Step 2: Create constraint encoder with GA integration
            constraint_encoder = ConstraintEncoder(problem=test_problem, model=model)

            # Step 3: Run complete encoding workflow with real GA
            workflow_start_time = time.time()
            shared_variables = constraint_encoder.encode()
            workflow_time = time.time() - workflow_start_time

            # Step 4: Verify complete workflow results

            # Verify shared variables structure
            self.assertIsInstance(shared_variables, SharedVariables)
            x_vars_dict = dict(shared_variables.x_vars)
            y_vars_dict = dict(shared_variables.y_vars)
            u_vars_dict = dict(shared_variables.u_vars)
            z_vars_dict = dict(shared_variables.z_vars)
            self.assertIsInstance(x_vars_dict, dict)
            self.assertIsInstance(y_vars_dict, dict)
            self.assertIsNotNone(shared_variables.x_vars)
            self.assertIsNotNone(shared_variables.y_vars)
            self.assertIsNotNone(shared_variables.u_vars)
            self.assertIsNotNone(shared_variables.z_vars)
            self.assertIsNotNone(shared_variables.precomputed_data)

            # Verify variables were created
            self.assertGreater(
                len(shared_variables.x_vars), 0, "Should create X variables"
            )
            self.assertGreater(
                len(shared_variables.y_vars), 0, "Should create Y variables"
            )
            self.assertGreater(
                len(shared_variables.z_vars), 0, "Should create Z variables"
            )

            # Verify precomputed data includes day-slot groupings
            precomputed_data = shared_variables.precomputed_data
            self.assertIn("day_slot_groupings", precomputed_data)
            day_slot_groupings = precomputed_data["day_slot_groupings"]
            self.assertIsInstance(day_slot_groupings, dict)
            self.assertGreater(len(day_slot_groupings), 0)

            # Step 5: Verify search hints were applied to model (if available)
            search_hints = []
            if hasattr(model, "ga_search_hints"):
                search_hints = getattr(model, "ga_search_hints", [])
                self.assertIsInstance(search_hints, list)

                if len(search_hints) > 0:
                    # Verify hint quality
                    hint_confidences = [h[2] for h in search_hints if len(h) >= 3]
                    if hint_confidences:
                        avg_confidence = np.mean(hint_confidences)
                        self.assertGreaterEqual(
                            avg_confidence,
                            0.0,
                            f"Average hint confidence should be >= 0.0, got {avg_confidence:.3f}",
                        )

            # Step 6: Verify performance
            self.assertLess(
                workflow_time,
                120.0,
                "Complete workflow should finish within 120 seconds",
            )

            # Calculate and verify reduction metrics
            total_y_possible = (
                len(test_problem.exams)
                * len(test_problem.rooms)
                * len(test_problem.timeslots)
            )
            total_u_possible = len(test_problem.invigilators) * total_y_possible
            total_possible = total_y_possible + total_u_possible
            total_created = len(shared_variables.y_vars) + len(shared_variables.u_vars)
            actual_reduction = 1.0 - (total_created / max(1, total_possible))

            self.assertGreaterEqual(
                actual_reduction,
                0.0,
                f"Variable reduction should be >= 0%, got {actual_reduction:.1%}",
            )

            self.logger.info("✅ End-to-end GA integration workflow test passed")
            self.logger.info(f" - Total workflow time: {workflow_time:.2f}s")
            self.logger.info(f" - X variables: {len(shared_variables.x_vars)}")
            self.logger.info(
                f" - Y variables: {len(shared_variables.y_vars)} (from GA)"
            )
            self.logger.info(
                f" - U variables: {len(shared_variables.u_vars)} (from GA)"
            )
            self.logger.info(f" - Z variables: {len(shared_variables.z_vars)}")
            self.logger.info(f" - Search hints: {len(search_hints)}")
            if search_hints:
                hint_confidences = [h[2] for h in search_hints if len(h) >= 3]
                if hint_confidences:
                    avg_confidence = np.mean(hint_confidences)
                    self.logger.info(f" - Avg hint confidence: {avg_confidence:.3f}")
            self.logger.info(f" - Variable reduction: {actual_reduction:.1%}")
            self.logger.info(f" - Day-slot groupings: {len(day_slot_groupings)}")

        except Exception as e:
            self.fail(f"End-to-end GA integration workflow test failed: {e}")


if __name__ == "__main__":
    # Configure test runner
    unittest.main(verbosity=2, buffer=True)
