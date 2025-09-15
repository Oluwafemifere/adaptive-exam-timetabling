# FIXED Test Script to Verify Constraint System

# scheduling_engine\tests\integration\test_fixed.py

"""
FIXED Enhanced test script that properly validates all constraint configuration presets.

Key Fixes:
- Proper test flow that tests ALL configurations
- Better error handling and recovery
- Enhanced logging and debugging
- Fixed invigilator data setup
"""

import sys
import io

# Fix console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import logging
from datetime import date, timedelta, time
from uuid import uuid4


def setup_comprehensive_logging():
    """Setup detailed logging to track constraint activation"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("constraint_fix_test.log", mode="w", encoding="utf-8"),
        ],
    )

    # Set specific loggers to DEBUG for detailed tracking
    debug_loggers = [
        "scheduling_engine.core.constraint_registry",
        "scheduling_engine.cp_sat.model_builder",
        "scheduling_engine.constraints.constraint_manager",
        "scheduling_engine.constraints.base_constraint",
    ]

    for logger_name in debug_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

    return logging.getLogger(__name__)


logger = setup_comprehensive_logging()


def create_test_problem():
    """Create a realistic test problem with FIXED invigilator data"""
    logger.info("Creating enhanced test problem...")

    try:
        from ...core.problem_model import (
            ExamSchedulingProblem,
            Exam,
            TimeSlot,
            Room,
            Student,
            Staff,  # Import Staff for invigilators
        )
        from ...core.constraint_registry import ConstraintRegistry
    except ImportError as e:
        logger.error(f"Import failed: {e}")
        return None

    # Create problem
    exam_period_start = date.today() + timedelta(days=30)
    exam_period_end = exam_period_start + timedelta(days=10)

    problem = ExamSchedulingProblem(
        session_id=uuid4(),
        exam_period_start=exam_period_start,
        exam_period_end=exam_period_end,
    )

    # Add 5 exams
    for i in range(5):
        exam = Exam(
            id=uuid4(),
            course_id=uuid4(),
            duration_minutes=180,
            expected_students=50 + i * 10,
        )
        problem.add_exam(exam)

    # Add 3 time slots
    for i in range(3):
        slot = TimeSlot(
            id=uuid4(),
            name=f"Slot {i+1}",
            start_time=time(9, 0),
            end_time=time(12, 0),
            duration_minutes=180,
        )
        problem.add_time_slot(slot)

    # Add 2 rooms
    for i in range(2):
        room = Room(id=uuid4(), code=f"R{i+1}", capacity=100, exam_capacity=80)
        problem.add_room(room)

    # FIXED: Add invigilator/staff data to prevent warnings
    for i in range(3):
        staff = Staff(
            id=uuid4(),
            name=f"Staff Member {i+1}",
            department=f"Department {i+1}",
            can_invigilate=True,
            max_concurrent_exams=1,
        )
        problem.staff[staff.id] = staff

    logger.info(f"Added {len(problem.staff)} staff members for invigilator constraints")

    # Add students and registrations
    for i in range(100):
        student = Student(id=uuid4())
        problem.add_student(student)

        # Register for some courses
        exam_ids = list(problem.exams.keys())
        for j in range(min(3, len(exam_ids))):  # Each student takes up to 3 exams
            course_id = problem.exams[exam_ids[j]].course_id
            problem.register_student_course(student.id, course_id)

    # Populate exam students based on registrations
    problem.populate_exam_students()

    logger.info(
        f"Enhanced test problem created: {len(problem.exams)} exams, {len(problem.time_slots)} slots, "
        f"{len(problem.rooms)} rooms, {len(problem.students)} students, {len(problem.staff)} staff"
    )

    return problem


def test_constraint_configuration(problem, config_name):
    """FIXED: Test a specific constraint configuration with proper error handling"""
    logger.info(f"🧪 Testing {config_name.upper()} configuration...")

    try:
        from scheduling_engine.cp_sat.model_builder import CPSATModelBuilder

        # Create fresh builder for each test to avoid state issues
        builder = CPSATModelBuilder(problem)

        # Configure based on config name
        if config_name == "standard":
            builder.configure_standard()
        elif config_name == "with_conflicts":
            builder.configure_with_student_conflicts()
        elif config_name == "complete":
            builder.configure_complete()
        else:
            logger.error(f"❌ Unknown configuration: {config_name}")
            return False

        # Check active constraints after configuration
        active_constraints = problem.constraint_registry.get_active_constraints()
        logger.info(
            f"✅ Active constraints after {config_name} config: {len(active_constraints)}"
        )

        for constraint in sorted(active_constraints):
            logger.info(f"   • {constraint}")

        if not active_constraints:
            logger.error(
                f"❌ CRITICAL: No constraints active after {config_name} configuration!"
            )
            return False

        # FIXED: Try to build the model with proper error handling
        logger.info(f"🔨 Building model with {config_name} configuration...")

        try:
            model, shared_vars = builder.build()
            logger.info(f"✅ Model build SUCCESS for {config_name}")

            # Get build statistics
            build_stats = builder.get_build_statistics()
            registry_stats = build_stats.get("constraint_registry", {})
            logger.info(f"📊 Build results for {config_name}:")
            logger.info(
                f"   • Total registered: {registry_stats.get('total_registered', 0)}"
            )
            logger.info(f"   • Total active: {registry_stats.get('total_active', 0)}")
            logger.info(
                f"   • Active categories: {registry_stats.get('active_categories', [])}"
            )

            return True

        except Exception as build_error:
            logger.error(f"❌ Model build FAILED for {config_name}: {build_error}")
            logger.error(f"   Build error details: {str(build_error)}")
            return False

    except Exception as e:
        logger.error(f"❌ Configuration test FAILED for {config_name}: {e}")
        import traceback

        logger.debug(f"🐛 Traceback: {traceback.format_exc()}")
        return False


def main():
    """FIXED: Main test execution with proper flow control"""
    logger.info("🚀 Starting FIXED Enhanced Constraint Configuration Test")
    logger.info("=" * 80)

    # Create test problem
    problem = create_test_problem()
    if not problem:
        logger.error("❌ Failed to create test problem")
        return False

    # FIXED: Test all configurations properly
    configurations = ["standard", "with_conflicts", "complete"]
    results = {}

    logger.info(f"\n📋 Testing {len(configurations)} configurations...")

    for i, config in enumerate(configurations, 1):
        logger.info(f"\n{'='*60}")
        logger.info(
            f"🧪 TEST {i}/{len(configurations)}: {config.upper()} Configuration"
        )
        logger.info(f"{'='*60}")

        try:
            # FIXED: Create fresh problem instance for each test to avoid state pollution
            fresh_problem = create_test_problem()
            if not fresh_problem:
                logger.error(f"❌ Failed to create fresh problem for {config}")
                results[config] = False
                continue

            success = test_constraint_configuration(fresh_problem, config)
            results[config] = success

            if success:
                logger.info(f"✅ {config.upper()} configuration test PASSED")
            else:
                logger.error(f"❌ {config.upper()} configuration test FAILED")

        except Exception as config_error:
            logger.error(
                f"❌ Configuration {config} failed with exception: {config_error}"
            )
            results[config] = False

    # FIXED: Comprehensive summary
    logger.info(f"\n{'='*80}")
    logger.info("📊 FINAL TEST SUMMARY")
    logger.info(f"{'='*80}")

    passed = sum(results.values())
    total = len(results)

    logger.info(f"🎯 Configuration Results:")
    for config, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"   • {config.upper()}: {status}")

    logger.info(f"\n📈 Overall Results: {passed}/{total} configurations passed")

    if passed == total:
        logger.info(
            "🎉 ALL TESTS PASSED - Constraint configuration system is working correctly!"
        )
        return True
    else:
        logger.error(
            f"⚠️  {total - passed} TESTS FAILED - Some constraint configurations need fixes!"
        )
        logger.info("\n🔧 Next steps:")
        failed_configs = [config for config, success in results.items() if not success]
        for config in failed_configs:
            logger.info(f"   • Debug and fix {config} configuration")
        return False


if __name__ == "__main__":
    success = main()
    exit_code = 0 if success else 1
    logger.info(f"\n🏁 Test execution complete. Exit code: {exit_code}")
    sys.exit(exit_code)
