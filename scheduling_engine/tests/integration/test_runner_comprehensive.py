# scheduling_engine/tests/integration/test_runner_comprehensive.py

"""
Comprehensive Test Runner for Constraint Integration Tests

Features:
- Runs comprehensive constraint integration tests
- Supports different test configurations
- Generates detailed reports with metrics
- Handles test failures and provides recommendations
- Integrates with pytest for CI/CD compatibility
"""
import io
import sys

import asyncio
import logging
import pytest
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """Setup logging configuration for test runner"""

    # Create logs directory
    logs_dir = Path("test_logs")
    logs_dir.mkdir(exist_ok=True)

    handlers: List[logging.Handler] = [logging.StreamHandler()]

    if log_file:
        handlers.append(
            logging.FileHandler(logs_dir / log_file, mode="w", encoding="utf-8")
        )
    else:
        # Default log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        handlers.append(
            logging.FileHandler(
                logs_dir / f"test_run_{timestamp}.log", mode="w", encoding="utf-8"
            )
        )

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

    # Set specific logger levels
    logging.getLogger("faker").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def run_comprehensive_tests(args=None):
    """Run comprehensive constraint integration tests"""
    if args is None:
        args = []

    print(" Running Comprehensive Constraint Integration Tests...")

    # Default pytest arguments for comprehensive testing
    pytest_args = [
        "scheduling_engine/tests/integration/test_comprehensive_constraint_integration.py::test_complete_constraint_system",
        "-v",
        "--tb=long",  # Detailed traceback for debugging
        "--asyncio-mode=auto",
        "--capture=no",  # Show all output including logs
    ]

    # Add custom arguments
    pytest_args.extend(args)

    print(f"Command: pytest {' '.join(pytest_args)}")
    print("-" * 60)

    # Run pytest
    exit_code = pytest.main(pytest_args)

    return exit_code == 0


def run_specific_test_category(category: str):
    """Run specific test category"""

    category_tests = {
        "registry": "test_constraint_registry_comprehensive",
        "model": "test_model_building_all_configurations",
        "solver": "test_solver_execution_with_presolve_logs",
        "performance": "test_performance_and_scalability",
    }

    if category not in category_tests:
        print(f" Unknown test category: {category}")
        print(f"Available categories: {list(category_tests.keys())}")
        return False

    test_method = category_tests[category]

    print(f" Running {category} tests ({test_method})...")

    # Create a temporary test file for the specific category
    test_code = f"""
import pytest
from test_comprehensive_constraint_integration import ComprehensiveConstraintTester, TestConfiguration

@pytest.mark.asyncio
async def test_{category}_only():
    config = TestConfiguration()
    tester = ComprehensiveConstraintTester(config)
    
    result = getattr(tester, '{test_method}')()
    
    assert result.success, f"Test failed: {{result.error_message}}"
    
    print(f" {category} test completed successfully")
    print(f"Duration: {{result.duration:.2f}}s")
    
    return result
    """

    temp_test_file = Path("temp_test.py")
    try:
        with open(temp_test_file, "w") as f:
            f.write(test_code)

        # Run the specific test
        exit_code = pytest.main([str(temp_test_file), "-v", "--tb=short"])
        return exit_code == 0

    finally:
        # Clean up
        if temp_test_file.exists():
            temp_test_file.unlink()


def create_test_report(test_results: Dict[str, Any], output_file: Optional[str] = None):
    """Create a formatted test report"""

    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"test_logs/test_report_{timestamp}.json"

    # Ensure output directory exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Add metadata to the report
    report = {
        "generated_at": datetime.now().isoformat(),
        "test_framework": "pytest + comprehensive_constraint_tester",
        "summary": test_results,
    }

    # Save report
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f" Test report saved to: {output_path}")
    return output_path


def validate_environment():
    """Validate that the test environment is properly set up"""
    print(" Validating test environment...")

    # Check required modules
    required_modules = [
        "scheduling_engine.core.problem_model",
        "scheduling_engine.cp_sat.model_builder",
        "scheduling_engine.constraints.constraint_manager",
        "faker",
        "pytest",
        "ortools",
    ]

    missing_modules = []

    for module_name in required_modules:
        try:
            __import__(module_name)
            print(f" {module_name}")
        except ImportError as e:
            print(f" {module_name}: {e}")
            missing_modules.append(module_name)

    if missing_modules:
        print(f" Missing modules: {missing_modules}")
        print("Please install missing dependencies before running tests")
        return False

    # Check file structure
    required_files = [
        "scheduling_engine/tests/integration/test_comprehensive_constraint_integration.py",
        "scheduling_engine/core/__init__.py",
        "scheduling_engine/cp_sat/__init__.py",
        "scheduling_engine/constraints/__init__.py",
    ]

    missing_files = []

    for file_path in required_files:
        if not Path(file_path).exists():
            print(f" Missing file: {file_path}")
            missing_files.append(file_path)
        else:
            print(f" {file_path}")

    if missing_files:
        print(f" Missing files: {missing_files}")
        return False

    print(" Environment validation passed")
    return True


def main():
    """Main entry point for comprehensive test runner"""

    parser = argparse.ArgumentParser(
        description="Run comprehensive constraint integration tests",
        epilog="""
Examples:
  python test_runner_comprehensive.py                    # Run all tests
  python test_runner_comprehensive.py --category solver  # Run solver tests only
  python test_runner_comprehensive.py --validate         # Validate environment
  python test_runner_comprehensive.py --quick            # Quick test (reduced data)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--category",
        choices=["registry", "model", "solver", "performance"],
        help="Run specific test category only",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level (default: INFO)",
    )

    parser.add_argument(
        "--log-file",
        type=str,
        help="Custom log file name (default: timestamped)",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate test environment and exit",
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick tests with reduced data size",
    )

    parser.add_argument(
        "--no-solver-logs",
        action="store_true",
        help="Disable detailed solver presolve logs",
    )

    parser.add_argument(
        "--max-time",
        type=int,
        default=30,
        help="Maximum solver time in seconds (default: 30)",
    )

    parser.add_argument(
        "--output-report",
        type=str,
        help="Output file for test report (JSON format)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output with detailed logs",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level, args.log_file)

    try:
        # Validate environment if requested
        if args.validate:
            success = validate_environment()
            sys.exit(0 if success else 1)

        # Validate environment before running tests
        if not validate_environment():
            print(" Environment validation failed")
            sys.exit(1)

        success = False

        if args.category:
            # Run specific category
            print(f" Running {args.category} tests...")
            success = run_specific_test_category(args.category)
        else:
            # Run comprehensive tests
            print(" Running comprehensive tests...")

            # Build pytest arguments based on options
            pytest_args = []

            if args.verbose:
                pytest_args.extend(["-vv", "-s"])

            if args.quick:
                pytest_args.extend(["-m", "not slow"])

            if args.log_level == "DEBUG":
                pytest_args.append("--log-cli-level=DEBUG")

            # Set environment variables for test configuration
            import os

            if args.max_time:
                os.environ["TEST_MAX_SOLVER_TIME"] = str(args.max_time)
            if args.no_solver_logs:
                os.environ["TEST_DISABLE_SOLVER_LOGS"] = "1"
            if args.quick:
                os.environ["TEST_QUICK_MODE"] = "1"

            success = run_comprehensive_tests(pytest_args)

        # Generate summary
        if success:
            print("\n All tests completed successfully!")

            # Look for generated test report
            report_files = list(
                Path("test_logs").glob("comprehensive_test_report*.json")
            )
            if report_files:
                latest_report = max(report_files, key=lambda p: p.stat().st_mtime)
                print(f" Detailed report: {latest_report}")

                # Copy to custom output if specified
                if args.output_report:
                    import shutil

                    shutil.copy(latest_report, args.output_report)
                    print(f" Report copied to: {args.output_report}")

            sys.exit(0)
        else:
            print("\n Some tests failed!")
            print("Check the logs above for detailed error information")

            # Look for error logs
            log_files = list(Path("test_logs").glob("*.log"))
            if log_files:
                latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
                print(f" Check detailed logs: {latest_log}")

            sys.exit(1)

    except KeyboardInterrupt:
        print("\n Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
