# scheduling_engine/utils/__init__.py

"""
Utilities package for the scheduling engine.
Provides logging, performance monitoring, and validation utilities.
"""

from typing import Optional, Tuple

# Import main classes and functions for easy access
from .logging import (
    SchedulingLogger,
    LogLevel,
    SchedulingPhase,
    LogEntry,
    CPSATLogMetrics,
    GALogMetrics,
    get_logger,
    setup_logging,
    log_operation,
)

from .performance import (
    PerformanceProfiler,
    PerformanceMetricType,
    OptimizationStage,
    PerformanceMetric,
    TimingMetrics,
    MemoryMetrics,
    CPUMetrics,
    AlgorithmMetrics,
    QualityMetrics,
    ThroughputMetrics,
    get_profiler,
    profile_performance,
)

from .validation import (
    ComprehensiveSolutionValidator,
    ValidationLevel,
    ConstraintType,
    ViolationType,
    ConstraintViolation,
    ValidationResult,
    SolutionQualityAssessor,
    quick_validate,
    validate_with_report,
)

# Version information
__version__ = "1.0.0"

# Public API
__all__ = [
    # Logging utilities
    "SchedulingLogger",
    "LogLevel",
    "SchedulingPhase",
    "LogEntry",
    "CPSATLogMetrics",
    "GALogMetrics",
    "get_logger",
    "setup_logging",
    "log_operation",
    # Performance monitoring
    "PerformanceProfiler",
    "PerformanceMetricType",
    "OptimizationStage",
    "PerformanceMetric",
    "TimingMetrics",
    "MemoryMetrics",
    "CPUMetrics",
    "AlgorithmMetrics",
    "QualityMetrics",
    "ThroughputMetrics",
    "get_profiler",
    "profile_performance",
    # Solution validation
    "ComprehensiveSolutionValidator",
    "ValidationLevel",
    "ConstraintType",
    "ViolationType",
    "ConstraintViolation",
    "ValidationResult",
    "SolutionQualityAssessor",
    "quick_validate",
    "validate_with_report",
]

# Configuration for the utilities package
DEFAULT_LOG_LEVEL = LogLevel.INFO
DEFAULT_VALIDATION_LEVEL = ValidationLevel.STANDARD
DEFAULT_PERFORMANCE_MONITORING = True

# Initialize package-level logger
_package_logger = None


def get_package_logger():
    """Get the package-level logger instance"""
    global _package_logger
    if _package_logger is None:
        _package_logger = get_logger("scheduling_engine.utils")
    return _package_logger


# Utility functions for common operations
def configure_engine_utilities(
    log_level: LogLevel = DEFAULT_LOG_LEVEL,
    enable_performance_monitoring: bool = DEFAULT_PERFORMANCE_MONITORING,
    validation_level: ValidationLevel = DEFAULT_VALIDATION_LEVEL,
):
    """
    Configure all engine utilities with consistent settings.

    Args:
        log_level: Global logging level for all components
        enable_performance_monitoring: Whether to enable performance profiling
        validation_level: Default validation strictness level
    """
    # Setup logging
    setup_logging(
        level=log_level,
        enable_performance_tracking=enable_performance_monitoring,
        enable_cpsat_parsing=True,
    )

    # Initialize performance profiler if enabled
    if enable_performance_monitoring:
        profiler = get_profiler()
        logger = get_package_logger()
        logger.info(
            "Performance monitoring enabled",
            component="utils_package",
            context={"profiler_name": profiler.name},
        )

    # Log configuration
    logger = get_package_logger()
    logger.info(
        "Scheduling engine utilities configured",
        component="utils_package",
        context={
            "log_level": log_level.value,
            "performance_monitoring": enable_performance_monitoring,
            "validation_level": validation_level.value,
        },
    )


def create_integrated_monitoring_session(
    session_name: str, correlation_id: str, partition_id: Optional[str] = None
) -> Tuple[SchedulingLogger, PerformanceProfiler, ComprehensiveSolutionValidator]:
    """
    Create an integrated monitoring session with coordinated logging,
    performance tracking, and validation.

    Args:
        session_name: Name for the monitoring session
        correlation_id: Unique identifier for correlating across components
        partition_id: Optional partition identifier for distributed scheduling

    Returns:
        Tuple of (logger, profiler, validator) instances configured for the session
    """
    # Create coordinated logger
    logger = SchedulingLogger(
        name=f"{session_name}_logger",
        correlation_id=correlation_id,
        partition_id=partition_id,
        enable_performance_tracking=True,
        enable_cpsat_parsing=True,
    )

    # Create performance profiler
    profiler = PerformanceProfiler(
        name=f"{session_name}_profiler",
        enable_system_monitoring=True,
        enable_algorithm_tracking=True,
    )

    # Create solution validator
    validator = ComprehensiveSolutionValidator(
        validation_level=ValidationLevel.COMPREHENSIVE
    )

    # Log session creation
    logger.info(
        f"Integrated monitoring session '{session_name}' created",
        component="utils_package",
        context={
            "correlation_id": correlation_id,
            "partition_id": partition_id,
            "components": ["logger", "profiler", "validator"],
        },
    )

    return logger, profiler, validator


def export_session_data(
    logger: SchedulingLogger,
    profiler: PerformanceProfiler,
    output_dir: str,
    session_name: str = "session",
):
    """
    Export all monitoring data from a session to files.

    Args:
        logger: Logger instance to export from
        profiler: Profiler instance to export from
        output_dir: Directory to save export files
        session_name: Base name for export files
    """
    import os

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Export logs
    log_file = os.path.join(output_dir, f"{session_name}_logs.json")
    logger.export_logs(log_file, format="json")

    # Export performance metrics
    perf_file = os.path.join(output_dir, f"{session_name}_performance.json")
    profiler.export_metrics(perf_file, format="json")

    # Log export completion
    pkg_logger = get_package_logger()
    pkg_logger.info(
        f"Session data exported for '{session_name}'",
        component="utils_package",
        context={
            "output_directory": output_dir,
            "files_exported": ["logs", "performance"],
        },
    )


# Context managers for common monitoring patterns
from contextlib import contextmanager


@contextmanager
def monitored_operation(
    operation_name: str,
    phase: Optional[SchedulingPhase] = None,
    stage: Optional[OptimizationStage] = None,
    logger: Optional[SchedulingLogger] = None,
    profiler: Optional[PerformanceProfiler] = None,
):
    """
    Context manager for monitoring an operation with both logging and performance tracking.

    Args:
        operation_name: Name of the operation being monitored
        phase: Scheduling phase for logging context
        stage: Optimization stage for performance tracking
        logger: Logger instance (creates default if None)
        profiler: Profiler instance (creates default if None)
    """
    # Use default instances if not provided
    actual_logger = logger or get_logger()
    actual_profiler = profiler or get_profiler()

    # Start monitoring
    actual_logger.info(
        f"Starting monitored operation: {operation_name}",
        phase=phase,
        component="monitored_operation",
    )

    with actual_logger.operation_timer(operation_name):
        with actual_profiler.time_operation(operation_name, stage):
            try:
                yield {
                    "logger": actual_logger,
                    "profiler": actual_profiler,
                    "operation_name": operation_name,
                }
            except Exception as e:
                actual_logger.error(
                    f"Error in monitored operation: {operation_name}",
                    phase=phase,
                    component="monitored_operation",
                    context={"error": str(e), "error_type": type(e).__name__},
                )
                raise
            finally:
                actual_logger.info(
                    f"Completed monitored operation: {operation_name}",
                    phase=phase,
                    component="monitored_operation",
                )


# Helper functions for common validation patterns
def validate_solution_with_monitoring(
    solution_data: dict,
    logger: Optional[SchedulingLogger] = None,
    profiler: Optional[PerformanceProfiler] = None,
    validation_level: ValidationLevel = ValidationLevel.STANDARD,
) -> ValidationResult:
    """
    Validate a solution with integrated monitoring and logging.

    Args:
        solution_data: Solution data to validate
        logger: Logger instance for recording validation process
        profiler: Profiler instance for tracking performance
        validation_level: Level of validation strictness

    Returns:
        ValidationResult with comprehensive validation information
    """
    actual_logger = logger or get_logger()
    actual_profiler = profiler or get_profiler()

    validator = ComprehensiveSolutionValidator(validation_level)

    with monitored_operation(
        "solution_validation",
        SchedulingPhase.VALIDATION,
        OptimizationStage.VALIDATION,
        actual_logger,
        actual_profiler,
    ) as monitor:

        # Perform validation
        result = validator.validate_solution(
            solution_data, include_quality_assessment=True, detailed_logging=True
        )

        # Log validation results
        actual_logger.log_solution_quality(
            {
                "overall_score": result.quality_score,
                "is_valid": result.is_valid,
                "is_feasible": result.is_feasible,
                "total_violations": result.total_violations,
                "critical_violations": result.critical_violations,
            }
        )

        if result.violations:
            actual_logger.log_constraint_violations(
                [v.to_dict() for v in result.violations]
            )

        # Track quality metrics in profiler
        actual_profiler.track_solution_quality(
            objective_value=result.quality_score,
            constraint_violations=result.total_violations,
            is_feasible=result.is_feasible,
        )

        return result


# Package initialization message
def _initialize_package():
    """Initialize the utils package with default configuration"""
    try:
        configure_engine_utilities()
        logger = get_package_logger()
        logger.info(
            "Scheduling engine utils package initialized",
            component="utils_package",
            context={"version": __version__},
        )
    except Exception as e:
        # Fallback to basic logging if initialization fails
        import logging

        logging.basicConfig(level=logging.WARNING)
        logging.warning(f"Failed to initialize scheduling engine utils: {e}")


# Auto-initialize when package is imported
_initialize_package()
