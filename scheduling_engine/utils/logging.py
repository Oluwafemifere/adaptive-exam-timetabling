# scheduling_engine/utils/logging.py

"""
Enhanced logging utilities for the scheduling engine with structured logging,
performance tracking, and constraint programming specific metrics.

Based on best practices for optimization algorithm logging and informed by
the Genetic-based Constraint Programming research paper requirements.
"""

import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Callable
from enum import Enum
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager
import threading
from collections import defaultdict, deque
import statistics


class LogLevel(Enum):
    """Enhanced log levels for scheduling operations"""

    TRACE = "TRACE"  # Detailed execution traces
    DEBUG = "DEBUG"  # Debug information
    INFO = "INFO"  # General information
    NOTICE = "NOTICE"  # Notable events
    WARN = "WARN"  # Warning conditions
    ERROR = "ERROR"  # Error conditions
    FATAL = "FATAL"  # Fatal errors


class SchedulingPhase(Enum):
    """Phases of the scheduling process for context logging"""

    INITIALIZATION = "initialization"
    DATA_PREPARATION = "data_preparation"
    PARTITIONING = "partitioning"
    CP_SAT_SOLVING = "cp_sat_solving"
    GA_OPTIMIZATION = "ga_optimization"
    SOLUTION_INTEGRATION = "solution_integration"
    VALIDATION = "validation"
    FINALIZATION = "finalization"


@dataclass
class LogEntry:
    """Structured log entry for scheduling operations"""

    timestamp: datetime
    level: LogLevel
    phase: Optional[SchedulingPhase]
    component: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Union[int, float]] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    partition_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "phase": self.phase.value if self.phase else None,
            "component": self.component,
            "message": self.message,
            "context": self.context,
            "performance_metrics": self.performance_metrics,
            "correlation_id": self.correlation_id,
            "partition_id": self.partition_id,
        }


@dataclass
class CPSATLogMetrics:
    """Metrics extracted from CP-SAT solver logs"""

    branches: int = 0
    conflicts: int = 0
    propagations: int = 0
    restarts: int = 0
    binary_clauses: int = 0
    search_time_seconds: float = 0.0
    presolve_time_seconds: float = 0.0
    best_objective: Optional[float] = None
    lower_bound: Optional[float] = None
    gap: Optional[float] = None
    variables_fixed: int = 0
    constraints_removed: int = 0


@dataclass
class GALogMetrics:
    """Metrics for Genetic Algorithm evolution tracking"""

    generation: int = 0
    population_size: int = 0
    best_fitness: float = 0.0
    average_fitness: float = 0.0
    worst_fitness: float = 0.0
    diversity_score: float = 0.0
    convergence_rate: float = 0.0
    mutation_rate: float = 0.0
    crossover_rate: float = 0.0
    selection_pressure: float = 0.0
    elite_count: int = 0


class SchedulingLogger:
    """
    Advanced logger for scheduling operations with structured logging,
    performance tracking, and optimization-specific features.
    """

    def __init__(
        self,
        name: str = "scheduling_engine",
        level: LogLevel = LogLevel.INFO,
        correlation_id: Optional[str] = None,
        partition_id: Optional[str] = None,
        enable_performance_tracking: bool = True,
        enable_cpsat_parsing: bool = True,
        max_log_entries: int = 10000,
    ):
        self.name = name
        self.level = level
        self.correlation_id = correlation_id
        self.partition_id = partition_id
        self.enable_performance_tracking = enable_performance_tracking
        self.enable_cpsat_parsing = enable_cpsat_parsing

        # Initialize Python logger
        self._setup_python_logger()

        # Performance tracking
        self._phase_timers: Dict[SchedulingPhase, float] = {}
        self._operation_timers: Dict[str, List[float]] = defaultdict(list)
        self._performance_counters: Dict[str, int] = defaultdict(int)

        # Log storage for analysis
        self._log_entries: deque = deque(maxlen=max_log_entries)
        self._cpsat_metrics: List[CPSATLogMetrics] = []
        self._ga_metrics: List[GALogMetrics] = []

        # Thread safety
        self._lock = threading.Lock()

        # CP-SAT log parsing state
        self._cpsat_log_buffer: List[str] = []

    def _setup_python_logger(self):
        """Setup the underlying Python logger with appropriate handlers"""
        self._logger = logging.getLogger(self.name)
        self._logger.setLevel(getattr(logging, self.level.value))

        if not self._logger.handlers:
            # Console handler with structured format
            console_handler = logging.StreamHandler()
            console_handler.setLevel(getattr(logging, self.level.value))

            # Custom formatter for structured logging
            formatter = StructuredFormatter()
            console_handler.setFormatter(formatter)

            self._logger.addHandler(console_handler)

    def _log(
        self,
        level: LogLevel,
        message: str,
        phase: Optional[SchedulingPhase] = None,
        component: str = "core",
        context: Optional[Dict[str, Any]] = None,
        performance_metrics: Optional[Dict[str, Union[int, float]]] = None,
    ):
        """Core logging method with structured data"""
        with self._lock:
            entry = LogEntry(
                timestamp=datetime.now(),
                level=level,
                phase=phase,
                component=component,
                message=message,
                context=context or {},
                performance_metrics=performance_metrics or {},
                correlation_id=self.correlation_id,
                partition_id=self.partition_id,
            )

            # Store entry for analysis
            self._log_entries.append(entry)

            # Log to Python logger
            python_level = getattr(logging, level.value)
            self._logger.log(python_level, json.dumps(entry.to_dict(), indent=2))

    # Convenience methods for different log levels
    def trace(self, message: str, **kwargs):
        """Log trace level message"""
        self._log(LogLevel.TRACE, message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug level message"""
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info level message"""
        self._log(LogLevel.INFO, message, **kwargs)

    def notice(self, message: str, **kwargs):
        """Log notice level message"""
        self._log(LogLevel.NOTICE, message, **kwargs)

    def warn(self, message: str, **kwargs):
        """Log warning message"""
        self._log(LogLevel.WARN, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log(LogLevel.ERROR, message, **kwargs)

    def fatal(self, message: str, **kwargs):
        """Log fatal error message"""
        self._log(LogLevel.FATAL, message, **kwargs)

    # Phase-aware logging methods
    def log_phase_start(
        self, phase: SchedulingPhase, context: Optional[Dict[str, Any]] = None
    ):
        """Log the start of a scheduling phase"""
        self._phase_timers[phase] = time.time()
        self.info(f"Starting {phase.value} phase", phase=phase, context=context or {})

    def log_phase_end(
        self, phase: SchedulingPhase, context: Optional[Dict[str, Any]] = None
    ):
        """Log the end of a scheduling phase"""
        if phase in self._phase_timers:
            duration = time.time() - self._phase_timers[phase]
            self.info(
                f"Completed {phase.value} phase",
                phase=phase,
                context=context or {},
                performance_metrics={"duration_seconds": duration},
            )
            del self._phase_timers[phase]
        else:
            self.warn(f"Phase {phase.value} ended without corresponding start")

    @contextmanager
    def phase_context(
        self, phase: SchedulingPhase, context: Optional[Dict[str, Any]] = None
    ):
        """Context manager for automatic phase timing"""
        self.log_phase_start(phase, context)
        try:
            yield
        finally:
            self.log_phase_end(phase, context)

    @contextmanager
    def operation_timer(self, operation_name: str):
        """Context manager for timing specific operations"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            with self._lock:
                self._operation_timers[operation_name].append(duration)

            self.debug(
                f"Operation {operation_name} completed",
                performance_metrics={"duration_seconds": duration},
            )

    def increment_counter(self, counter_name: str, value: int = 1):
        """Increment a performance counter"""
        with self._lock:
            self._performance_counters[counter_name] += value

    # CP-SAT specific logging methods
    def log_cpsat_start(self, model_info: Dict[str, Any]):
        """Log CP-SAT solver start with model information"""
        self.info(
            "Starting CP-SAT solver",
            phase=SchedulingPhase.CP_SAT_SOLVING,
            component="cp_sat",
            context={
                "variables": model_info.get("variables", 0),
                "constraints": model_info.get("constraints", 0),
                "boolean_variables": model_info.get("boolean_variables", 0),
                "integer_variables": model_info.get("integer_variables", 0),
            },
        )

    def parse_cpsat_log_line(self, log_line: str):
        """Parse a line from CP-SAT solver log"""
        if not self.enable_cpsat_parsing:
            return

        self._cpsat_log_buffer.append(log_line)

        # Extract metrics from common CP-SAT log patterns
        metrics = CPSATLogMetrics()

        # Parse solver progress lines
        if "CpSolverResponse summary:" in log_line:
            self._extract_cpsat_summary(log_line, metrics)
        elif "branches:" in log_line.lower():
            self._extract_branch_metrics(log_line, metrics)
        elif "presolve" in log_line.lower():
            self._extract_presolve_metrics(log_line, metrics)

        if any(asdict(metrics).values()):  # If any metrics were extracted
            with self._lock:
                self._cpsat_metrics.append(metrics)

    def _extract_cpsat_summary(self, log_line: str, metrics: CPSATLogMetrics):
        """Extract metrics from CP-SAT summary line"""
        # Implementation would parse specific CP-SAT output format
        # This is a simplified version
        if "objective:" in log_line.lower():
            try:
                obj_str = log_line.split("objective:")[1].split()[0]
                metrics.best_objective = float(obj_str)
            except (IndexError, ValueError):
                pass

    def _extract_branch_metrics(self, log_line: str, metrics: CPSATLogMetrics):
        """Extract branching metrics from CP-SAT log"""
        try:
            if "branches:" in log_line:
                branch_str = log_line.split("branches:")[1].split()[0]
                metrics.branches = int(branch_str.replace(",", ""))
        except (IndexError, ValueError):
            pass

    def _extract_presolve_metrics(self, log_line: str, metrics: CPSATLogMetrics):
        """Extract presolve metrics from CP-SAT log"""
        try:
            if "presolve" in log_line.lower() and "s" in log_line:
                # Extract presolve time
                parts = log_line.split()
                for i, part in enumerate(parts):
                    if "s" in part and "presolve" in parts[i - 1 : i + 2]:
                        time_str = part.replace("s", "")
                        metrics.presolve_time_seconds = float(time_str)
                        break
        except (IndexError, ValueError):
            pass

    # Genetic Algorithm specific logging methods
    def log_ga_generation(self, metrics: GALogMetrics):
        """Log genetic algorithm generation metrics"""
        with self._lock:
            self._ga_metrics.append(metrics)

        self.info(
            f"GA Generation {metrics.generation} completed",
            phase=SchedulingPhase.GA_OPTIMIZATION,
            component="genetic_algorithm",
            context={
                "generation": metrics.generation,
                "population_size": metrics.population_size,
            },
            performance_metrics={
                "best_fitness": metrics.best_fitness,
                "average_fitness": metrics.average_fitness,
                "diversity_score": metrics.diversity_score,
            },
        )

    def log_ga_convergence(
        self, generation: int, stagnation_count: int, threshold: float
    ):
        """Log genetic algorithm convergence information"""
        self.info(
            f"GA convergence check at generation {generation}",
            phase=SchedulingPhase.GA_OPTIMIZATION,
            component="genetic_algorithm",
            context={
                "generation": generation,
                "stagnation_count": stagnation_count,
                "convergence_threshold": threshold,
            },
        )

    # Solution quality and validation logging
    def log_solution_quality(self, solution_metrics: Dict[str, Any]):
        """Log solution quality metrics"""
        self.info(
            "Solution quality assessment",
            phase=SchedulingPhase.VALIDATION,
            component="solution_validator",
            context=solution_metrics,
        )

    def log_constraint_violations(self, violations: List[Dict[str, Any]]):
        """Log constraint violations found during validation"""
        if violations:
            self.warn(
                f"Found {len(violations)} constraint violations",
                phase=SchedulingPhase.VALIDATION,
                component="constraint_validator",
                context={"violations": violations},
            )
        else:
            self.info(
                "No constraint violations found",
                phase=SchedulingPhase.VALIDATION,
                component="constraint_validator",
            )

    # Performance analysis methods
    def get_phase_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all phases"""
        summary = {}

        # Analyze log entries for phase durations
        phase_durations = defaultdict(list)

        with self._lock:
            for entry in self._log_entries:
                if entry.phase and "duration_seconds" in entry.performance_metrics:
                    phase_durations[entry.phase].append(
                        entry.performance_metrics["duration_seconds"]
                    )

        for phase, durations in phase_durations.items():
            if durations:
                summary[phase.value] = {
                    "total_time": sum(durations),
                    "average_time": statistics.mean(durations),
                    "min_time": min(durations),
                    "max_time": max(durations),
                    "count": len(durations),
                }

        return summary

    def get_operation_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for timed operations"""
        summary = {}

        with self._lock:
            for operation, durations in self._operation_timers.items():
                if durations:
                    summary[operation] = {
                        "total_time": sum(durations),
                        "average_time": statistics.mean(durations),
                        "min_time": min(durations),
                        "max_time": max(durations),
                        "count": len(durations),
                        "calls_per_second": (
                            len(durations) / sum(durations) if sum(durations) > 0 else 0
                        ),
                    }

        return summary

    def get_cpsat_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of CP-SAT solver metrics"""
        if not self._cpsat_metrics:
            return {}

        with self._lock:
            metrics = self._cpsat_metrics[-1]  # Latest metrics

        return {
            "branches": metrics.branches,
            "conflicts": metrics.conflicts,
            "propagations": metrics.propagations,
            "search_time": metrics.search_time_seconds,
            "presolve_time": metrics.presolve_time_seconds,
            "best_objective": metrics.best_objective,
            "lower_bound": metrics.lower_bound,
            "gap": metrics.gap,
        }

    def get_ga_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of genetic algorithm metrics"""
        if not self._ga_metrics:
            return {}

        with self._lock:
            latest_metrics = self._ga_metrics[-1]
            all_best_fitness = [m.best_fitness for m in self._ga_metrics]

        return {
            "generations": len(self._ga_metrics),
            "final_best_fitness": latest_metrics.best_fitness,
            "final_diversity": latest_metrics.diversity_score,
            "fitness_improvement": (
                all_best_fitness[-1] - all_best_fitness[0]
                if len(all_best_fitness) > 1
                else 0
            ),
            "convergence_rate": latest_metrics.convergence_rate,
        }

    def export_logs(self, filepath: str, format: str = "json"):
        """Export logs to file in specified format"""
        with self._lock:
            log_data = [entry.to_dict() for entry in self._log_entries]

        if format.lower() == "json":
            with open(filepath, "w") as f:
                json.dump(log_data, f, indent=2)
        elif format.lower() == "csv":
            import csv

            if log_data:
                with open(filepath, "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=log_data[0].keys())
                    writer.writeheader()
                    writer.writerows(log_data)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def clear_logs(self):
        """Clear stored logs (useful for memory management)"""
        with self._lock:
            self._log_entries.clear()
            self._cpsat_metrics.clear()
            self._ga_metrics.clear()
            self._operation_timers.clear()
            self._performance_counters.clear()


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging output"""

    def format(self, record):
        """Format log record with structured information"""
        try:
            # Parse JSON message if it's structured
            log_data = json.loads(record.getMessage())

            # Create readable format
            timestamp = log_data.get("timestamp", "")
            level = log_data.get("level", "INFO")
            phase = log_data.get("phase", "")
            component = log_data.get("component", "")
            message = log_data.get("message", "")

            # Build formatted string
            parts = [f"[{timestamp}]", f"[{level}]"]

            if phase:
                parts.append(f"[{phase}]")
            if component:
                parts.append(f"[{component}]")

            parts.append(message)

            # Add performance metrics if present
            perf_metrics = log_data.get("performance_metrics", {})
            if perf_metrics:
                metrics_str = " | ".join(f"{k}={v}" for k, v in perf_metrics.items())
                parts.append(f"| {metrics_str}")

            return " ".join(parts)

        except (json.JSONDecodeError, KeyError):
            # Fallback to standard formatting
            return super().format(record)


# Global logger instance
_default_logger: Optional[SchedulingLogger] = None


def get_logger(
    name: str = "scheduling_engine",
    correlation_id: Optional[str] = None,
    partition_id: Optional[str] = None,
) -> SchedulingLogger:
    """Get or create a scheduling logger instance"""
    global _default_logger

    if _default_logger is None or _default_logger.name != name:
        _default_logger = SchedulingLogger(
            name=name, correlation_id=correlation_id, partition_id=partition_id
        )

    return _default_logger


def setup_logging(
    level: LogLevel = LogLevel.INFO,
    enable_performance_tracking: bool = True,
    enable_cpsat_parsing: bool = True,
):
    """Setup global logging configuration"""
    global _default_logger
    _default_logger = SchedulingLogger(
        level=level,
        enable_performance_tracking=enable_performance_tracking,
        enable_cpsat_parsing=enable_cpsat_parsing,
    )


# Decorator for automatic operation timing
def log_operation(operation_name: str, logger: Optional[SchedulingLogger] = None):
    """Decorator to automatically log and time function operations"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            log = logger or get_logger()
            with log.operation_timer(operation_name):
                return func(*args, **kwargs)

        return wrapper

    return decorator
