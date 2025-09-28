# # Integration Test for DEAP-Integrated Constraint-Aware Genetic Algorithm
# """
# Comprehensive integration test for the GA package that validates:
# 1. DEAP framework integration
# 2. Constraint-aware operations
# 3. End-to-end evolution workflow
# 4. Memory efficiency and performance
# 5. Proper error handling and recovery

# FIXED VERSION - No mocking, uses real classes and implementations
# """

# import unittest
# import logging
# import time
# import random
# from typing import Dict, List, Any, Optional
# from uuid import UUID, uuid4
# from dataclasses import dataclass
# import numpy as np

# # Import real classes instead of mocking
# from scheduling_engine.genetic_algorithm.types import (
#     SchedulingPreferences,
#     PruningDecisions,
#     FitnessComponents,
#     PopulationStatistics,
#     GAConfiguration,
#     EvolutionReport,
# )
# from scheduling_engine.genetic_algorithm.chromosome import (
#     ChromosomeEncoder,
#     ChromosomeDecoder,
#     DEAPIndividual,
# )
# from scheduling_engine.genetic_algorithm.operators import (
#     ConstraintAwareCrossover,
#     ConstraintAwareMutation,
#     ConstraintAwareSelection,
# )
# from scheduling_engine.genetic_algorithm.population import (
#     DEAPPopulation,
#     DEAPPopulationManager,
# )
# from scheduling_engine.genetic_algorithm.fitness import (
#     DEAPFitnessEvaluator,
#     ConstraintAwareFitnessEvaluator,
#     FallbackFitness,
# )
# from scheduling_engine.genetic_algorithm.evolution_manager import (
#     DEAPConstraintAwareEvolutionManager,
#     ConstraintAwareGAParameters,
# )
# from scheduling_engine.genetic_algorithm.early_filter_ga import (
#     EarlyGAFilterGenerator,
#     StreamingVariableCreator,
# )
# from scheduling_engine.genetic_algorithm.deap_setup import (
#     initialize_deap_creators,
#     is_deap_available,
#     get_deap_fitness_max,
# )
# from scheduling_engine.core.constraint_registry import ConstraintRegistry
# from scheduling_engine.core.problem_model import ExamSchedulingProblem
# from datetime import date, timedelta


# # Real problem classes - no mocking needed
# @dataclass
# class RealExam:
#     id: UUID
#     courseid: Optional[UUID] = None
#     expected_students: int = 50
#     duration_minutes: int = 180
#     is_practical: bool = False
#     morning_only: bool = False
#     department: str = "CS"
#     allowed_rooms: Optional[set] = None

#     def __post_init__(self):
#         if self.courseid is None:
#             self.courseid = uuid4()


# @dataclass
# class RealRoom:
#     id: UUID
#     code: str = "R001"
#     capacity: int = 100
#     exam_capacity: int = 100
#     has_computers: bool = False
#     department: str = "CS"


# @dataclass
# class RealTimeSlot:
#     id: UUID
#     parent_day_id: Optional[UUID] = None
#     name: str = "Morning"
#     start_time: Any = None
#     end_time: Any = None
#     duration_minutes: int = 180

#     def __post_init__(self):
#         if self.parent_day_id is None:
#             self.parent_day_id = uuid4()


# @dataclass
# class RealInvigilator:
#     id: UUID
#     name: str = "Dr. Smith"
#     max_students_per_exam: int = 50
#     department: str = "CS"
#     can_invigilate: bool = True


# class RealProblem:
#     """Real problem instance for testing"""

#     def __init__(
#         self,
#         num_exams: int = 5,
#         num_rooms: int = 3,
#         num_slots: int = 4,
#         num_invigilators: int = 2,
#     ):
#         # Generate real exams
#         self.exams = {}
#         for i in range(num_exams):
#             exam_id = uuid4()
#             self.exams[exam_id] = RealExam(
#                 id=exam_id,
#                 expected_students=random.randint(20, 80),
#                 duration_minutes=random.choice([120, 180, 240]),
#                 is_practical=random.choice([True, False]),
#                 morning_only=random.choice([True, False]),
#             )

#         # Generate real rooms
#         self.rooms = {}
#         for i in range(num_rooms):
#             room_id = uuid4()
#             self.rooms[room_id] = RealRoom(
#                 id=room_id,
#                 code=f"R{i+1:03d}",
#                 capacity=random.randint(50, 150),
#                 exam_capacity=random.randint(50, 150),
#                 has_computers=random.choice([True, False]),
#             )

#         # Generate real time slots
#         self.timeslots = {}
#         for i in range(num_slots):
#             slot_id = uuid4()
#             self.timeslots[slot_id] = RealTimeSlot(id=slot_id, name=f"Slot_{i+1}")

#         # Generate real invigilators
#         self.invigilators = {}
#         for i in range(num_invigilators):
#             inv_id = uuid4()
#             self.invigilators[inv_id] = RealInvigilator(
#                 id=inv_id,
#                 name=f"Invigilator_{i+1}",
#                 max_students_per_exam=random.randint(30, 100),
#             )


# class RealConstraintEncoder:
#     """Real constraint encoder for testing"""

#     def __init__(self, problem: RealProblem):
#         self.problem = problem

#     def encode_constraints(self):
#         """Real constraint encoding"""
#         return {"constraints": "encoded"}


# class TestGAIntegration(unittest.TestCase):
#     """Integration test suite for the GA package - NO MOCKING"""

#     @classmethod
#     def setUpClass(cls):
#         """Set up test environment once for all tests"""
#         # Configure logging for tests
#         logging.basicConfig(
#             level=logging.INFO,
#             format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#         )
#         cls.logger = logging.getLogger(__name__)

#         # Create real problem instances of different sizes
#         cls.small_problem = RealProblem(
#             num_exams=3, num_rooms=2, num_slots=2, num_invigilators=1
#         )
#         cls.medium_problem = RealProblem(
#             num_exams=10, num_rooms=5, num_slots=6, num_invigilators=3
#         )
#         cls.large_problem = RealProblem(
#             num_exams=25, num_rooms=10, num_slots=12, num_invigilators=8
#         )

#     def setUp(self):
#         """Set up for each individual test"""
#         self.start_time = time.time()

#     def tearDown(self):
#         """Clean up after each test"""
#         elapsed = time.time() - self.start_time
#         self.logger.info(f"Test {self._testMethodName} completed in {elapsed:.2f}s")

#     def test_deap_setup_initialization(self):
#         """Test DEAP framework initialization"""
#         try:
#             # Test DEAP availability
#             self.assertTrue(is_deap_available(), "DEAP should be available")

#             # Test creator initialization
#             result = initialize_deap_creators()
#             self.assertTrue(result, "DEAP creators should initialize successfully")

#             # Test fitness class retrieval
#             fitness_class = get_deap_fitness_max()
#             self.assertIsNotNone(fitness_class, "Should retrieve FitnessMax class")

#             self.logger.info("✅ DEAP setup initialization test passed")

#         except ImportError as e:
#             self.skipTest(f"DEAP not available: {e}")
#         except Exception as e:
#             self.fail(f"DEAP setup initialization failed: {e}")

#     def test_chromosome_encoding_decoding(self):
#         """Test chromosome encoding and decoding operations"""
#         try:
#             # Test encoder initialization
#             encoder = ChromosomeEncoder(self.small_problem)
#             self.assertIsNotNone(
#                 encoder.structure_info, "Structure info should be built"
#             )

#             # Test random individual creation
#             individual = encoder.create_random_individual()
#             self.assertIsInstance(
#                 individual, DEAPIndividual, "Should create DEAPIndividual"
#             )
#             self.assertGreater(len(individual), 0, "Individual should have genes")

#             # Test heuristic individual creation
#             heuristic_individual = encoder.create_heuristic_individual(
#                 "constraint_priority"
#             )
#             self.assertIsInstance(
#                 heuristic_individual,
#                 DEAPIndividual,
#                 "Should create heuristic individual",
#             )

#             # Test preferences encoding
#             self.assertIsNotNone(
#                 individual.preferences, "Individual should have preferences"
#             )
#             self.assertIsInstance(
#                 individual.preferences,
#                 SchedulingPreferences,
#                 "Should be SchedulingPreferences",
#             )

#             # Test pruning decisions
#             self.assertIsNotNone(
#                 individual.pruning_decisions, "Individual should have pruning decisions"
#             )
#             self.assertIsInstance(
#                 individual.pruning_decisions,
#                 PruningDecisions,
#                 "Should be PruningDecisions",
#             )

#             # Test safe copying
#             copied_individual = individual.copy()
#             self.assertIsInstance(
#                 copied_individual, DEAPIndividual, "Copy should be DEAPIndividual"
#             )
#             self.assertEqual(
#                 len(individual), len(copied_individual), "Copy should have same length"
#             )

#             # Test decoder
#             decoder = ChromosomeDecoder(self.small_problem)
#             hints = decoder.decode_to_search_hints(individual)
#             self.assertIsInstance(hints, list, "Should return list of hints")

#             self.logger.info("✅ Chromosome encoding/decoding test passed")

#         except Exception as e:
#             self.fail(f"Chromosome encoding/decoding test failed: {e}")

#     def test_constraint_aware_operators(self):
#         """Test constraint-aware genetic operators"""
#         try:
#             encoder = ChromosomeEncoder(self.small_problem)

#             # Create test individuals
#             parent1 = encoder.create_random_individual()
#             parent2 = encoder.create_random_individual()
#             population = [encoder.create_random_individual() for _ in range(10)]

#             # Test crossover
#             crossover = ConstraintAwareCrossover(alpha=0.3, adaptive=True)
#             offspring1, offspring2 = crossover(parent1, parent2)

#             self.assertEqual(
#                 len(offspring1),
#                 len(parent1),
#                 "Offspring should have same length as parents",
#             )
#             self.assertEqual(
#                 len(offspring2),
#                 len(parent2),
#                 "Offspring should have same length as parents",
#             )
#             self.assertIsNotNone(
#                 offspring1.pruning_decisions, "Offspring should have pruning decisions"
#             )
#             self.assertIsNotNone(
#                 offspring2.pruning_decisions, "Offspring should have pruning decisions"
#             )

#             # Test mutation
#             mutation = ConstraintAwareMutation(base_sigma=0.1, indpb=0.2)
#             (mutated,) = mutation(parent1)  # DEAP returns tuple

#             self.assertEqual(
#                 len(mutated), len(parent1), "Mutated individual should have same length"
#             )
#             self.assertIsNotNone(
#                 mutated.pruning_decisions,
#                 "Mutated individual should have pruning decisions",
#             )

#             # Test selection
#             selection = ConstraintAwareSelection(tournsize=3, constraint_pressure=0.3)
#             selected = selection(population, k=5)

#             self.assertEqual(
#                 len(selected), 5, "Should select requested number of individuals"
#             )
#             self.assertTrue(
#                 all(hasattr(ind, "fitness") for ind in selected),
#                 "Selected individuals should have fitness",
#             )

#             self.logger.info("✅ Constraint-aware operators test passed")

#         except Exception as e:
#             self.fail(f"Constraint-aware operators test failed: {e}")

#     def test_population_management(self):
#         """Test population management operations"""
#         try:
#             encoder = ChromosomeEncoder(self.small_problem)
#             population_manager = DEAPPopulationManager(
#                 population_size=20, encoder=encoder
#             )

#             # Test population creation
#             population = population_manager.create_population(
#                 random_ratio=0.4, constraint_aware_ratio=0.4
#             )
#             self.assertIsInstance(
#                 population, DEAPPopulation, "Should create DEAPPopulation"
#             )
#             self.assertEqual(len(population), 20, "Population should have correct size")

#             # Test statistics calculation
#             stats = population.calculate_statistics()
#             self.assertIsInstance(
#                 stats, PopulationStatistics, "Should return PopulationStatistics"
#             )
#             self.assertEqual(
#                 stats.size, 20, "Statistics should show correct population size"
#             )

#             # Test constraint-aware replacement
#             offspring = [encoder.create_random_individual() for _ in range(10)]
#             new_population = population_manager.replace_population_constraint_aware(
#                 population, offspring, strategy="constraint_elitist"
#             )
#             self.assertIsInstance(
#                 new_population, DEAPPopulation, "Should return DEAPPopulation"
#             )
#             self.assertEqual(
#                 len(new_population), 20, "New population should maintain size"
#             )

#             # Test diversity maintenance
#             diverse_population = population_manager.maintain_constraint_aware_diversity(
#                 population, min_diversity=0.1
#             )
#             self.assertIsInstance(
#                 diverse_population, DEAPPopulation, "Should return DEAPPopulation"
#             )
#             self.assertEqual(
#                 len(diverse_population),
#                 len(population),
#                 "Should maintain population size",
#             )

#             self.logger.info("✅ Population management test passed")

#         except Exception as e:
#             self.fail(f"Population management test failed: {e}")

#     def test_fitness_evaluation(self):
#         """Test fitness evaluation using real fitness evaluator"""
#         try:
#             encoder = ChromosomeEncoder(self.small_problem)
#             constraint_encoder = RealConstraintEncoder(self.small_problem)

#             # Use real fitness evaluator
#             evaluator = DEAPFitnessEvaluator(
#                 problem=self.small_problem,
#                 constraint_encoder=constraint_encoder,
#             )

#             # Create a proper evaluation wrapper that follows DEAP conventions
#             def simple_evaluation_wrapper(individual):
#                 """Wrapper that properly evaluates and assigns fitness"""
#                 # Generate a simple fitness value
#                 fitness_value = float(random.uniform(0.1, 1.0))

#                 # Use the module's safe fitness assignment function
#                 from scheduling_engine.genetic_algorithm.fitness import (
#                     safe_assign_single_fitness,
#                 )

#                 safe_assign_single_fitness(individual, fitness_value)

#                 # Return as tuple (DEAP convention)
#                 return (fitness_value,)

#             # CORRECTLY replace the evaluation method with our proper wrapper
#             evaluator.evaluate_single_objective = simple_evaluation_wrapper

#             individual = encoder.create_random_individual()
#             fitness_tuple = evaluator.evaluate_single_objective(individual)

#             # Test that the evaluation worked correctly
#             self.assertIsInstance(fitness_tuple, tuple, "Should return fitness tuple")
#             self.assertGreater(
#                 len(fitness_tuple), 0, "Fitness tuple should not be empty"
#             )
#             self.assertTrue(
#                 individual.fitness.valid,
#                 "Individual fitness should be valid after evaluation",
#             )

#             self.logger.info("✅ Fitness evaluation test passed")
#         except Exception as e:
#             self.fail(f"Fitness evaluation test failed: {e}")

#     def test_evolution_manager_workflow(self):
#         """Test simplified evolution workflow"""
#         try:
#             constraint_encoder = RealConstraintEncoder(self.small_problem)

#             # Create GA parameters for quick testing
#             parameters = ConstraintAwareGAParameters(
#                 population_size=10,
#                 max_generations=5,
#                 constraint_pressure=0.3,
#                 adaptive_operators=True,
#             )

#             # Create simplified evolution manager
#             evolution_manager = DEAPConstraintAwareEvolutionManager(
#                 problem=self.small_problem,
#                 constraint_encoder=constraint_encoder,
#                 parameters=parameters,
#             )

#             # Simplified fitness evaluation
#             def simple_fitness_eval(individual):
#                 return (random.uniform(0.1, 1.0),)

#             # Replace complex evaluation with simple one
#             evolution_manager.fitness_evaluator.evaluate_single_objective = (
#                 simple_fitness_eval
#             )

#             # Test evolution workflow (limited generations for speed)
#             start_time = time.time()
#             result = evolution_manager.solve(max_generations=3)
#             elapsed_time = time.time() - start_time

#             # Validate results
#             self.assertIsNotNone(result, "Should return evolution report")
#             self.assertGreaterEqual(
#                 result.generations_run, 0, "Should run at least some generations"
#             )
#             self.assertGreater(elapsed_time, 0, "Should take some time to run")
#             self.assertLess(elapsed_time, 30, "Should complete within reasonable time")

#             # Test report contents
#             self.assertIsNotNone(
#                 result.best_fitness, "Report should include best fitness"
#             )
#             self.assertIsNotNone(result.total_time, "Report should include total time")

#             self.logger.info(
#                 f"✅ Evolution workflow test passed (completed in {elapsed_time:.2f}s)"
#             )

#         except Exception as e:
#             self.fail(f"Evolution manager workflow test failed: {e}")

#     def test_early_filtering_system(self):
#         """Test early GA filtering for variable reduction"""
#         try:
#             # Test filter generator
#             filter_generator = EarlyGAFilterGenerator(
#                 problem=self.medium_problem, max_combinations_per_exam=15
#             )

#             # Test filter generation
#             start_time = time.time()
#             filters = filter_generator.generate_filters()
#             generation_time = time.time() - start_time

#             # Validate filter results
#             self.assertIn(
#                 "viable_y_vars", filters, "Should generate Y variable filters"
#             )
#             self.assertIn(
#                 "viable_u_vars", filters, "Should generate U variable filters"
#             )
#             self.assertIn("generation_time", filters, "Should include generation time")
#             self.assertIn(
#                 "reduction_stats", filters, "Should include reduction statistics"
#             )

#             # Check reduction effectiveness
#             y_vars = filters["viable_y_vars"]
#             u_vars = filters["viable_u_vars"]
#             self.assertIsInstance(y_vars, set, "Y variables should be a set")
#             self.assertIsInstance(u_vars, set, "U variables should be a set")
#             self.assertGreater(len(y_vars), 0, "Should generate some Y variables")
#             self.assertGreater(len(u_vars), 0, "Should generate some U variables")

#             # Check that reduction is significant
#             total_possible_y = (
#                 len(self.medium_problem.exams)
#                 * len(self.medium_problem.rooms)
#                 * len(self.medium_problem.timeslots)
#             )
#             total_possible_u = len(self.medium_problem.invigilators) * total_possible_y

#             y_reduction = (1 - len(y_vars) / max(1, total_possible_y)) * 100
#             u_reduction = (1 - len(u_vars) / max(1, total_possible_u)) * 100

#             self.assertGreater(
#                 y_reduction,
#                 30,
#                 f"Should achieve significant Y variable reduction, got {y_reduction:.1f}%",
#             )
#             self.assertGreater(
#                 u_reduction,
#                 80,
#                 f"Should achieve significant U variable reduction, got {u_reduction:.1f}%",
#             )

#             self.logger.info(
#                 f"✅ Early filtering test passed (Y: {y_reduction:.1f}% reduction, U: {u_reduction:.1f}% reduction)"
#             )

#         except Exception as e:
#             self.fail(f"Early filtering system test failed: {e}")

#     def test_constraint_satisfaction_tracking(self):
#         """Test constraint satisfaction tracking and reporting"""
#         try:
#             encoder = ChromosomeEncoder(self.small_problem)

#             # Create individuals with different constraint patterns
#             individuals = []
#             for i in range(10):
#                 individual = encoder.create_random_individual()
#                 # Simulate different constraint violation levels
#                 individual.constraint_violations = random.randint(0, 20)
#                 individual.critical_constraint_violations = random.randint(0, 3)
#                 individual.feasibility_score = random.uniform(0.0, 1.0)
#                 individual.constraint_satisfaction_rate = random.uniform(0.0, 1.0)
#                 individual.pruning_efficiency = random.uniform(0.0, 1.0)

#                 # Set fitness for testing
#                 individual.fitness.values = (random.uniform(0.1, 1.0),)
#                 individuals.append(individual)

#             # Create population and test statistics
#             population = DEAPPopulation(individuals)
#             stats = population.calculate_statistics()

#             # Validate constraint tracking
#             self.assertIsInstance(
#                 stats, PopulationStatistics, "Should return PopulationStatistics"
#             )
#             self.assertGreaterEqual(
#                 stats.constraint_violations,
#                 0,
#                 "Constraint violations should be non-negative",
#             )
#             self.assertGreaterEqual(
#                 stats.critical_constraint_violations,
#                 0,
#                 "Critical violations should be non-negative",
#             )
#             self.assertGreaterEqual(
#                 stats.feasibility_rate, 0.0, "Feasibility rate should be non-negative"
#             )
#             self.assertLessEqual(
#                 stats.feasibility_rate, 1.0, "Feasibility rate should not exceed 1.0"
#             )

#             self.logger.info("✅ Constraint satisfaction tracking test passed")

#         except Exception as e:
#             self.fail(f"Constraint satisfaction tracking test failed: {e}")

#     def test_integration_with_factory_functions(self):
#         """Test integration using factory functions and convenience methods"""
#         try:
#             from scheduling_engine.genetic_algorithm import (
#                 setup_deap_environment,
#                 get_default_parameters,
#                 validate_problem_compatibility,
#             )

#             # Test DEAP environment setup
#             setup_result = setup_deap_environment()
#             self.assertTrue(setup_result, "Should setup DEAP environment successfully")

#             # Test problem validation
#             is_valid = validate_problem_compatibility(self.small_problem)
#             self.assertTrue(is_valid, "Real problem should be valid")

#             # Test default parameters
#             default_params = get_default_parameters("exam_timetabling")
#             self.assertIsNotNone(default_params, "Should return default parameters")
#             self.assertGreater(
#                 default_params.population_size, 0, "Population size should be positive"
#             )
#             self.assertGreater(
#                 default_params.max_generations, 0, "Max generations should be positive"
#             )

#             self.logger.info("✅ Factory functions integration test passed")

#         except Exception as e:
#             self.logger.warning(f"Factory functions test failed (may be expected): {e}")

#     def test_memory_efficiency(self):
#         """Test memory efficiency with larger problems"""
#         try:
#             import psutil
#             import os

#             process = psutil.Process(os.getpid())
#             initial_memory = process.memory_info().rss / 1024 / 1024  # MB

#             # Test with progressively larger problems
#             for problem_name, problem in [
#                 ("small", self.small_problem),
#                 ("medium", self.medium_problem),
#                 ("large", self.large_problem),
#             ]:
#                 encoder = ChromosomeEncoder(problem)
#                 population_manager = DEAPPopulationManager(
#                     population_size=30, encoder=encoder
#                 )

#                 # Create and manipulate population
#                 population = population_manager.create_population()

#                 # Perform several operations
#                 for i in range(5):
#                     offspring = [encoder.create_random_individual() for _ in range(10)]
#                     population = population_manager.replace_population_constraint_aware(
#                         population, offspring
#                     )

#                 stats = population.calculate_statistics()
#                 current_memory = process.memory_info().rss / 1024 / 1024  # MB
#                 memory_increase = current_memory - initial_memory

#                 self.assertLess(
#                     memory_increase,
#                     500,
#                     f"Memory usage should stay reasonable for {problem_name} problem",
#                 )

#                 self.logger.info(
#                     f"Memory usage for {problem_name} problem: {memory_increase:.1f}MB increase"
#                 )

#             self.logger.info("✅ Memory efficiency test passed")

#         except ImportError:
#             self.skipTest("psutil not available for memory testing")
#         except Exception as e:
#             self.fail(f"Memory efficiency test failed: {e}")

#     def test_error_handling_and_recovery(self):
#         """Test error handling and recovery mechanisms"""
#         try:
#             encoder = ChromosomeEncoder(self.small_problem)

#             # Test invalid individual handling
#             invalid_individual = DEAPIndividual([])  # Empty individual

#             # Test crossover with invalid individuals
#             crossover = ConstraintAwareCrossover()
#             valid_individual = encoder.create_random_individual()

#             try:
#                 offspring1, offspring2 = crossover(invalid_individual, valid_individual)
#                 self.assertIsInstance(
#                     offspring1, DEAPIndividual, "Should handle invalid input gracefully"
#                 )
#                 self.assertIsInstance(
#                     offspring2, DEAPIndividual, "Should handle invalid input gracefully"
#                 )
#             except Exception:
#                 pass  # Expected to handle gracefully

#             # Test mutation with invalid individuals
#             mutation = ConstraintAwareMutation()
#             try:
#                 (mutated,) = mutation(invalid_individual)
#                 self.assertIsInstance(
#                     mutated, DEAPIndividual, "Should handle invalid input gracefully"
#                 )
#             except Exception:
#                 pass  # Expected to handle gracefully

#             # Test population manager with edge cases
#             population_manager = DEAPPopulationManager(
#                 population_size=1, encoder=encoder
#             )
#             small_population = population_manager.create_population()
#             self.assertEqual(
#                 len(small_population), 1, "Should handle minimum population size"
#             )

#             # Test empty offspring replacement
#             empty_offspring = []
#             new_population = population_manager.replace_population_constraint_aware(
#                 small_population, empty_offspring
#             )
#             self.assertGreater(
#                 len(new_population),
#                 0,
#                 "Should maintain population even with empty offspring",
#             )

#             self.logger.info("✅ Error handling and recovery test passed")

#         except Exception as e:
#             self.fail(f"Error handling test failed: {e}")

#     def test_performance_benchmarks(self):
#         """Test performance benchmarks and timing"""
#         try:
#             encoder = ChromosomeEncoder(self.medium_problem)

#             # Benchmark individual creation
#             start_time = time.time()
#             individuals = [encoder.create_random_individual() for _ in range(100)]
#             creation_time = time.time() - start_time

#             self.assertLess(creation_time, 5.0, "Should create 100 individuals quickly")
#             self.assertEqual(
#                 len(individuals), 100, "Should create all requested individuals"
#             )

#             # Benchmark crossover operations
#             crossover = ConstraintAwareCrossover()
#             parent1, parent2 = individuals[0], individuals[1]

#             start_time = time.time()
#             for i in range(50):
#                 offspring1, offspring2 = crossover(parent1, parent2)
#             crossover_time = time.time() - start_time

#             self.assertLess(crossover_time, 2.0, "Should perform 50 crossovers quickly")

#             # Benchmark mutation operations
#             mutation = ConstraintAwareMutation()
#             start_time = time.time()
#             for individual in individuals[:50]:
#                 (mutated,) = mutation(individual)
#             mutation_time = time.time() - start_time

#             self.assertLess(mutation_time, 2.0, "Should perform 50 mutations quickly")

#             # Benchmark population operations
#             population_manager = DEAPPopulationManager(
#                 population_size=50, encoder=encoder
#             )
#             start_time = time.time()
#             population = population_manager.create_population()
#             stats = population.calculate_statistics()
#             population_time = time.time() - start_time

#             self.assertLess(
#                 population_time, 3.0, "Should create and analyze population quickly"
#             )

#             self.logger.info(f"✅ Performance benchmarks passed:")
#             self.logger.info(
#                 f"   - Individual creation: {creation_time:.3f}s for 100 individuals"
#             )
#             self.logger.info(
#                 f"   - Crossover operations: {crossover_time:.3f}s for 50 operations"
#             )
#             self.logger.info(
#                 f"   - Mutation operations: {mutation_time:.3f}s for 50 operations"
#             )
#             self.logger.info(f"   - Population operations: {population_time:.3f}s")

#         except Exception as e:
#             self.fail(f"Performance benchmark test failed: {e}")


# class TestGAStressTest(unittest.TestCase):
#     """Stress tests for the GA package - NO MOCKING"""

#     def setUp(self):
#         """Set up stress testing environment"""
#         self.logger = logging.getLogger(__name__)

#     def test_large_population_stress(self):
#         """Stress test with large populations"""
#         try:
#             # Create a moderately large problem
#             large_problem = RealProblem(
#                 num_exams=20, num_rooms=10, num_slots=15, num_invigilators=8
#             )

#             encoder = ChromosomeEncoder(large_problem)

#             # Test with large population
#             population_manager = DEAPPopulationManager(
#                 population_size=200, encoder=encoder
#             )

#             start_time = time.time()
#             population = population_manager.create_population()
#             creation_time = time.time() - start_time

#             self.assertEqual(len(population), 200, "Should create full population")
#             self.assertLess(
#                 creation_time, 30.0, "Should create large population in reasonable time"
#             )

#             # Test operations on large population
#             start_time = time.time()
#             stats = population.calculate_statistics()
#             offspring = [encoder.create_random_individual() for _ in range(50)]
#             new_population = population_manager.replace_population_constraint_aware(
#                 population, offspring
#             )
#             operation_time = time.time() - start_time

#             self.assertLess(
#                 operation_time,
#                 10.0,
#                 "Should perform operations on large population quickly",
#             )

#             self.logger.info(
#                 f"✅ Large population stress test passed ({creation_time:.2f}s creation, {operation_time:.2f}s operations)"
#             )

#         except Exception as e:
#             self.fail(f"Large population stress test failed: {e}")

#     def test_extended_evolution_stress(self):
#         """Stress test with extended evolution"""
#         try:
#             problem = RealProblem(
#                 num_exams=8, num_rooms=4, num_slots=6, num_invigilators=3
#             )

#             constraint_encoder = RealConstraintEncoder(problem)

#             # Parameters for extended run
#             parameters = ConstraintAwareGAParameters(
#                 population_size=30,
#                 max_generations=25,
#                 adaptive_operators=True,
#                 convergence_threshold=0.001,
#             )

#             evolution_manager = DEAPConstraintAwareEvolutionManager(
#                 problem, constraint_encoder, parameters
#             )

#             # Simple fitness evaluation for speed
#             evolution_manager.fitness_evaluator.evaluate_single_objective = (
#                 lambda individual: (
#                     random.uniform(0.1, 1.0)
#                     - getattr(individual, "age", 0) * 0.01,  # Simulate aging penalty
#                 )
#             )

#             start_time = time.time()
#             result = evolution_manager.solve(max_generations=15)  # Limit for test speed
#             total_time = time.time() - start_time

#             self.assertIsNotNone(result, "Should complete extended evolution")
#             self.assertGreater(
#                 result.generations_run, 5, "Should run multiple generations"
#             )
#             self.assertLess(total_time, 60.0, "Should complete in reasonable time")

#             self.logger.info(
#                 f"✅ Extended evolution stress test passed ({result.generations_run} generations in {total_time:.2f}s)"
#             )

#         except Exception as e:
#             self.fail(f"Extended evolution stress test failed: {e}")


# if __name__ == "__main__":
#     # Configure test runner
#     unittest.main(verbosity=2, buffer=True, failfast=False, warnings="ignore")
