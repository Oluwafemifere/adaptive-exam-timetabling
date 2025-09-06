# scheduling_engine/utils/performance.py

"""
Performance monitoring and optimization utilities for the scheduling engine.
Provides comprehensive metrics collection, analysis, and optimization guidance
based on the Genetic-based Constraint Programming research paper.
"""

import time
import psutil
import gc
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import statistics
from contextlib import contextmanager
import json


class PerformanceMetricType(Enum):
    """Types of performance metrics tracked"""

    TIMING = "timing"
    MEMORY = "memory"
    CPU = "cpu"
    ALGORITHM = "algorithm"
    QUALITY = "quality"
    THROUGHPUT = "throughput"
    CONVERGENCE = "convergence"


class OptimizationStage(Enum):
    """Stages of optimization for performance tracking"""

    MODEL_BUILDING = "model_building"
    CPSAT_SOLVING = "cpsat_solving"
    GA_EVOLUTION = "ga_evolution"
    HYBRID_COORDINATION = "hybrid_coordination"
    SOLUTION_EXTRACTION = "solution_extraction"
    VALIDATION = "validation"


@dataclass
class PerformanceMetric:
    """Individual performance metric with metadata"""

    name: str
    value: Union[int, float, str]
    metric_type: PerformanceMetricType
    timestamp: datetime
    stage: Optional[OptimizationStage] = None
    partition_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimingMetrics:
    """Comprehensive timing metrics for operations"""

    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    cpu_time: Optional[float] = None
    wall_time: Optional[float] = None
    operation_count: int = 0

    def finalize(self):
        """Finalize timing measurements"""
        if self.end_time is None:
            self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.wall_time = self.duration


@dataclass
class MemoryMetrics:
    """Memory usage metrics"""

    rss_mb: float  # Resident Set Size in MB
    vms_mb: float  # Virtual Memory Size in MB
    percent: float  # Memory percentage
    available_mb: float  # Available memory in MB
    peak_usage_mb: Optional[float] = None
    gc_collections: int = 0


@dataclass
class CPUMetrics:
    """CPU utilization metrics"""

    cpu_percent: float
    user_time: float
    system_time: float
    idle_time: float
    load_average: Optional[Tuple[float, float, float]] = None
    core_count: int = 0


@dataclass
class AlgorithmMetrics:
    """Algorithm-specific performance metrics"""

    # CP-SAT metrics
    branches: int = 0
    conflicts: int = 0
    propagations: int = 0
    restarts: int = 0
    presolve_reductions: int = 0

    # GA metrics
    generations: int = 0
    population_size: int = 0
    fitness_evaluations: int = 0
    crossover_operations: int = 0
    mutation_operations: int = 0
    selection_operations: int = 0

    # Hybrid metrics
    cpsat_to_ga_conversions: int = 0
    solution_repairs: int = 0
    incremental_optimizations: int = 0


@dataclass
class QualityMetrics:
    """Solution quality and convergence metrics"""

    objective_value: Optional[float] = None
    best_known_value: Optional[float] = None
    optimality_gap: Optional[float] = None
    constraint_violations: int = 0
    solution_feasibility: bool = False

    # Convergence metrics
    fitness_improvement_rate: float = 0.0
    stagnation_count: int = 0
    diversity_score: float = 0.0
    convergence_rate: float = 0.0

    # Multi-objective metrics (if applicable)
    pareto_rank: Optional[int] = None
    hypervolume: Optional[float] = None


@dataclass
class ThroughputMetrics:
    """System throughput and efficiency metrics"""

    problems_solved_per_hour: float = 0.0
    solutions_generated_per_second: float = 0.0
    constraints_processed_per_second: float = 0.0
    variables_processed_per_second: float = 0.0
    partition_processing_rate: float = 0.0


class PerformanceProfiler:
    """
    Advanced performance profiler for scheduling algorithms with support
    for hybrid CP-SAT + GA optimization tracking.
    """

    def __init__(
        self,
        name: str = "scheduling_performance",
        enable_system_monitoring: bool = True,
        enable_algorithm_tracking: bool = True,
        sample_interval: float = 1.0,  # seconds
        max_samples: int = 10000,
    ):
        self.name = name
        self.enable_system_monitoring = enable_system_monitoring
        self.enable_algorithm_tracking = enable_algorithm_tracking
        self.sample_interval = sample_interval

        # Storage for metrics
        self._metrics: deque = deque(maxlen=max_samples)
        self._timing_data: Dict[str, List[TimingMetrics]] = defaultdict(list)
        self._algorithm_data: Dict[OptimizationStage, AlgorithmMetrics] = {}
        self._quality_history: List[QualityMetrics] = []

        # Performance counters
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = defaultdict(float)

        # System monitoring
        self._system_monitor_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_stop_event = threading.Event()

        # Thread safety
        self._lock = threading.Lock()

        # Baseline measurements
        self._baseline_metrics: Optional[Dict[str, Any]] = None

        if enable_system_monitoring:
            self._start_system_monitoring()

    def _start_system_monitoring(self):
        """Start background system monitoring thread"""
        if not self._system_monitor_active:
            self._system_monitor_active = True
            self._monitor_thread = threading.Thread(
                target=self._system_monitor_loop, daemon=True
            )
            self._monitor_thread.start()

    def _system_monitor_loop(self):
        """Background loop for system metrics collection"""
        while not self._monitor_stop_event.wait(self.sample_interval):
            try:
                self._collect_system_metrics()
            except Exception:
                # Log error but continue monitoring
                pass

    def _collect_system_metrics(self):
        """Collect current system metrics"""
        process = psutil.Process()
        system_memory = psutil.virtual_memory()

        # Memory metrics
        memory_info = process.memory_info()
        memory_metrics = MemoryMetrics(
            rss_mb=memory_info.rss / (1024 * 1024),
            vms_mb=memory_info.vms / (1024 * 1024),
            percent=process.memory_percent(),
            available_mb=system_memory.available / (1024 * 1024),
            gc_collections=sum(
                gc.get_stats()[i]["collections"] for i in range(len(gc.get_stats()))
            ),
        )

        # CPU metrics
        cpu_percent = process.cpu_percent()
        cpu_times = process.cpu_times()
        cpu_metrics = CPUMetrics(
            cpu_percent=cpu_percent,
            user_time=cpu_times.user,
            system_time=cpu_times.system,
            idle_time=0.0,  # Not available at process level
            load_average=psutil.getloadavg() if hasattr(psutil, "getloadavg") else None,
            core_count=psutil.cpu_count() or 0,
        )

        # Store metrics
        with self._lock:
            self._record_metric(
                "memory_rss_mb",
                memory_metrics.rss_mb,
                PerformanceMetricType.MEMORY,
                metadata={"memory_metrics": memory_metrics.__dict__},
            )
            self._record_metric(
                "cpu_percent",
                cpu_metrics.cpu_percent,
                PerformanceMetricType.CPU,
                metadata={"cpu_metrics": cpu_metrics.__dict__},
            )

    def _record_metric(
        self,
        name: str,
        value: Union[int, float, str],
        metric_type: PerformanceMetricType,
        stage: Optional[OptimizationStage] = None,
        partition_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record a performance metric"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            metric_type=metric_type,
            timestamp=datetime.now(),
            stage=stage,
            partition_id=partition_id,
            metadata=metadata or {},
        )

        self._metrics.append(metric)

    @contextmanager
    def time_operation(
        self,
        operation_name: str,
        stage: Optional[OptimizationStage] = None,
        partition_id: Optional[str] = None,
    ):
        """Context manager for timing operations with detailed metrics"""
        timing = TimingMetrics(start_time=time.time())

        # Record process CPU time at start
        process = psutil.Process()
        start_cpu_times = process.cpu_times()

        try:
            yield timing
        finally:
            timing.finalize()

            # Calculate CPU time used
            end_cpu_times = process.cpu_times()
            timing.cpu_time = (end_cpu_times.user - start_cpu_times.user) + (
                end_cpu_times.system - start_cpu_times.system
            )

            # Store timing data
            with self._lock:
                self._timing_data[operation_name].append(timing)

                # Record as metrics
                self._record_metric(
                    f"{operation_name}_duration",
                    timing.duration,  # type: ignore
                    PerformanceMetricType.TIMING,
                    stage=stage,
                    partition_id=partition_id,
                    metadata={
                        "operation": operation_name,
                        "cpu_time": timing.cpu_time,
                        "wall_time": timing.wall_time,
                    },
                )

    # Algorithm-specific tracking methods
    def track_cpsat_metrics(
        self,
        stage: OptimizationStage,
        branches: int = 0,
        conflicts: int = 0,
        propagations: int = 0,
        restarts: int = 0,
        presolve_reductions: int = 0,
    ):
        """Track CP-SAT solver specific metrics"""
        with self._lock:
            if stage not in self._algorithm_data:
                self._algorithm_data[stage] = AlgorithmMetrics()

            metrics = self._algorithm_data[stage]
            metrics.branches += branches
            metrics.conflicts += conflicts
            metrics.propagations += propagations
            metrics.restarts += restarts
            metrics.presolve_reductions += presolve_reductions

            # Record individual metrics
            self._record_metric(
                "cpsat_branches", branches, PerformanceMetricType.ALGORITHM, stage
            )
            self._record_metric(
                "cpsat_conflicts", conflicts, PerformanceMetricType.ALGORITHM, stage
            )
            self._record_metric(
                "cpsat_propagations",
                propagations,
                PerformanceMetricType.ALGORITHM,
                stage,
            )

    def track_ga_metrics(
        self,
        stage: OptimizationStage,
        generation: int = 0,
        population_size: int = 0,
        fitness_evaluations: int = 0,
        crossover_ops: int = 0,
        mutation_ops: int = 0,
        selection_ops: int = 0,
    ):
        """Track Genetic Algorithm specific metrics"""
        with self._lock:
            if stage not in self._algorithm_data:
                self._algorithm_data[stage] = AlgorithmMetrics()

            metrics = self._algorithm_data[stage]
            metrics.generations = generation
            metrics.population_size = population_size
            metrics.fitness_evaluations += fitness_evaluations
            metrics.crossover_operations += crossover_ops
            metrics.mutation_operations += mutation_ops
            metrics.selection_operations += selection_ops

            # Record individual metrics
            self._record_metric(
                "ga_generation", generation, PerformanceMetricType.ALGORITHM, stage
            )
            self._record_metric(
                "ga_fitness_evals",
                fitness_evaluations,
                PerformanceMetricType.ALGORITHM,
                stage,
            )
            self._record_metric(
                "ga_population_size",
                population_size,
                PerformanceMetricType.ALGORITHM,
                stage,
            )

    def track_solution_quality(
        self,
        objective_value: Optional[float] = None,
        best_known: Optional[float] = None,
        constraint_violations: int = 0,
        is_feasible: bool = True,
        fitness_improvement: float = 0.0,
        diversity_score: float = 0.0,
    ):
        """Track solution quality metrics"""
        optimality_gap = None
        if objective_value is not None and best_known is not None and best_known != 0:
            optimality_gap = abs(objective_value - best_known) / abs(best_known)

        quality = QualityMetrics(
            objective_value=objective_value,
            best_known_value=best_known,
            optimality_gap=optimality_gap,
            constraint_violations=constraint_violations,
            solution_feasibility=is_feasible,
            fitness_improvement_rate=fitness_improvement,
            diversity_score=diversity_score,
        )

        with self._lock:
            self._quality_history.append(quality)

            # Record as metrics - only record non-None values
            if objective_value is not None:
                self._record_metric(
                    "objective_value", objective_value, PerformanceMetricType.QUALITY
                )
            if optimality_gap is not None:
                self._record_metric(
                    "optimality_gap",
                    optimality_gap,
                    PerformanceMetricType.QUALITY,
                )
            self._record_metric(
                "constraint_violations",
                constraint_violations,
                PerformanceMetricType.QUALITY,
            )

    def track_throughput(
        self,
        problems_solved: int = 0,
        time_window_hours: float = 1.0,
        solutions_generated: int = 0,
        time_window_seconds: float = 1.0,
    ):
        """Track system throughput metrics"""
        throughput = ThroughputMetrics(
            problems_solved_per_hour=(
                problems_solved / time_window_hours if time_window_hours > 0 else 0
            ),
            solutions_generated_per_second=(
                solutions_generated / time_window_seconds
                if time_window_seconds > 0
                else 0
            ),
        )

        with self._lock:
            self._record_metric(
                "problems_per_hour",
                throughput.problems_solved_per_hour,
                PerformanceMetricType.THROUGHPUT,
            )
            self._record_metric(
                "solutions_per_second",
                throughput.solutions_generated_per_second,
                PerformanceMetricType.THROUGHPUT,
            )

    # Counter and gauge methods
    def increment_counter(self, name: str, value: int = 1):
        """Increment a performance counter"""
        with self._lock:
            self._counters[name] += value

    def set_gauge(self, name: str, value: float):
        """Set a performance gauge value"""
        with self._lock:
            self._gauges[name] = value

    def get_counter(self, name: str) -> int:
        """Get current counter value"""
        with self._lock:
            return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> float:
        """Get current gauge value"""
        with self._lock:
            return self._gauges.get(name, 0.0)

    # Analysis and reporting methods
    def get_timing_analysis(
        self, operation_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive timing analysis"""
        with self._lock:
            if operation_name:
                timings = self._timing_data.get(operation_name, [])
                operations = {operation_name: timings}
            else:
                operations = dict(self._timing_data)

        analysis = {}
        for op_name, timing_list in operations.items():
            if timing_list:
                durations = [t.duration for t in timing_list if t.duration is not None]
                cpu_times = [t.cpu_time for t in timing_list if t.cpu_time is not None]

                if durations:
                    analysis[op_name] = {
                        "count": len(durations),
                        "total_duration": sum(durations),
                        "average_duration": statistics.mean(durations),
                        "median_duration": statistics.median(durations),
                        "min_duration": min(durations),
                        "max_duration": max(durations),
                        "std_dev": (
                            statistics.stdev(durations) if len(durations) > 1 else 0
                        ),
                        "total_cpu_time": sum(cpu_times) if cpu_times else 0,
                        "cpu_efficiency": (
                            sum(cpu_times) / sum(durations)
                            if cpu_times and sum(durations) > 0
                            else 0
                        ),
                    }

        return analysis

    def get_algorithm_performance_summary(self) -> Dict[str, Any]:
        """Get summary of algorithm performance across all stages"""
        summary = {}

        with self._lock:
            for stage, metrics in self._algorithm_data.items():
                summary[stage.value] = {
                    # CP-SAT metrics
                    "cpsat": {
                        "branches": metrics.branches,
                        "conflicts": metrics.conflicts,
                        "propagations": metrics.propagations,
                        "restarts": metrics.restarts,
                        "presolve_reductions": metrics.presolve_reductions,
                    },
                    # GA metrics
                    "genetic_algorithm": {
                        "generations": metrics.generations,
                        "population_size": metrics.population_size,
                        "fitness_evaluations": metrics.fitness_evaluations,
                        "crossover_operations": metrics.crossover_operations,
                        "mutation_operations": metrics.mutation_operations,
                        "selection_operations": metrics.selection_operations,
                    },
                    # Hybrid metrics
                    "hybrid": {
                        "cpsat_to_ga_conversions": metrics.cpsat_to_ga_conversions,
                        "solution_repairs": metrics.solution_repairs,
                        "incremental_optimizations": metrics.incremental_optimizations,
                    },
                }

        return summary

    def get_quality_analysis(self) -> Dict[str, Any]:
        """Get solution quality analysis over time"""
        if not self._quality_history:
            return {}

        with self._lock:
            objective_values = [
                q.objective_value
                for q in self._quality_history
                if q.objective_value is not None
            ]
            gaps = [
                q.optimality_gap
                for q in self._quality_history
                if q.optimality_gap is not None
            ]
            violations = [q.constraint_violations for q in self._quality_history]
            diversity_scores = [q.diversity_score for q in self._quality_history]

        analysis = {
            "quality_trend": {
                "best_objective": min(objective_values) if objective_values else None,
                "worst_objective": max(objective_values) if objective_values else None,
                "average_objective": (
                    statistics.mean(objective_values) if objective_values else None
                ),
                "objective_improvement": (
                    (objective_values[0] - objective_values[-1])
                    / abs(objective_values[0])
                    if len(objective_values) > 1 and objective_values[0] != 0
                    else 0
                ),
            },
            "feasibility": {
                "total_violations": sum(violations),
                "average_violations": statistics.mean(violations) if violations else 0,
                "feasible_solutions": sum(
                    1 for q in self._quality_history if q.solution_feasibility
                ),
            },
            "convergence": {
                "average_gap": statistics.mean(gaps) if gaps else None,
                "final_gap": gaps[-1] if gaps else None,
                "average_diversity": (
                    statistics.mean(diversity_scores) if diversity_scores else 0
                ),
            },
        }

        return analysis

    def get_resource_utilization_summary(self) -> Dict[str, Any]:
        """Get system resource utilization summary"""
        memory_metrics = [m for m in self._metrics if m.name == "memory_rss_mb"]
        cpu_metrics = [m for m in self._metrics if m.name == "cpu_percent"]

        summary = {}

        if memory_metrics:
            memory_values = [float(m.value) for m in memory_metrics]
            summary["memory"] = {
                "peak_usage_mb": max(memory_values),
                "average_usage_mb": statistics.mean(memory_values),
                "min_usage_mb": min(memory_values),
                "samples": len(memory_values),
            }

        if cpu_metrics:
            cpu_values = [float(m.value) for m in cpu_metrics]
            summary["cpu"] = {
                "peak_usage_percent": max(cpu_values),
                "average_usage_percent": statistics.mean(cpu_values),
                "min_usage_percent": min(cpu_values),
                "samples": len(cpu_values),
            }

        return summary

    def get_performance_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks and optimization opportunities"""
        bottlenecks = []

        # Analyze timing data for slow operations
        timing_analysis = self.get_timing_analysis()
        for operation, stats in timing_analysis.items():
            if (
                stats["average_duration"] > 1.0
            ):  # Operations taking > 1 second on average
                bottlenecks.append(
                    {
                        "type": "slow_operation",
                        "operation": operation,
                        "average_duration": stats["average_duration"],
                        "total_time": stats["total_duration"],
                        "recommendation": f"Optimize {operation} - consuming {stats['total_duration']:.2f}s total",
                    }
                )

        # Analyze memory usage
        resource_summary = self.get_resource_utilization_summary()
        if "memory" in resource_summary:
            peak_memory = resource_summary["memory"]["peak_usage_mb"]
            if peak_memory > 1024:  # > 1GB peak usage
                bottlenecks.append(
                    {
                        "type": "high_memory_usage",
                        "peak_memory_mb": peak_memory,
                        "recommendation": f"High memory usage detected ({peak_memory:.0f}MB). Consider memory optimization.",
                    }
                )

        # Analyze algorithm efficiency
        algorithm_summary = self.get_algorithm_performance_summary()
        for stage, metrics in algorithm_summary.items():
            cpsat_data = metrics.get("cpsat", {})
            if cpsat_data.get("branches", 0) > 100000:
                bottlenecks.append(
                    {
                        "type": "excessive_branching",
                        "stage": stage,
                        "branches": cpsat_data["branches"],
                        "recommendation": f"High branching in {stage} ({cpsat_data['branches']} branches). Consider constraint strengthening.",
                    }
                )

        return bottlenecks

    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        return {
            "report_timestamp": datetime.now().isoformat(),
            "profiler_name": self.name,
            "timing_analysis": self.get_timing_analysis(),
            "algorithm_performance": self.get_algorithm_performance_summary(),
            "quality_analysis": self.get_quality_analysis(),
            "resource_utilization": self.get_resource_utilization_summary(),
            "bottlenecks": self.get_performance_bottlenecks(),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "total_metrics_collected": len(self._metrics),
        }

    def export_metrics(self, filepath: str, format: str = "json"):
        """Export collected metrics to file"""
        report = self.generate_performance_report()

        if format.lower() == "json":
            with open(filepath, "w") as f:
                json.dump(report, f, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def reset(self):
        """Reset all collected performance data"""
        with self._lock:
            self._metrics.clear()
            self._timing_data.clear()
            self._algorithm_data.clear()
            self._quality_history.clear()
            self._counters.clear()
            self._gauges.clear()

    def stop_monitoring(self):
        """Stop system monitoring and cleanup resources"""
        if self._system_monitor_active:
            self._monitor_stop_event.set()
            if self._monitor_thread:
                self._monitor_thread.join()
            self._system_monitor_active = False


# Global profiler instance
_default_profiler: Optional[PerformanceProfiler] = None


def get_profiler(name: str = "scheduling_performance") -> PerformanceProfiler:
    """Get or create a performance profiler instance"""
    global _default_profiler

    if _default_profiler is None or _default_profiler.name != name:
        _default_profiler = PerformanceProfiler(name=name)

    return _default_profiler


# Decorator for automatic performance tracking
def profile_performance(
    operation_name: Optional[str] = None,
    stage: Optional[OptimizationStage] = None,
    profiler: Optional[PerformanceProfiler] = None,
):
    """Decorator to automatically profile function performance"""

    def decorator(func):
        nonlocal operation_name
        name = operation_name or func.__name__

        def wrapper(*args, **kwargs):
            prof = profiler or get_profiler()
            with prof.time_operation(name, stage):
                return func(*args, **kwargs)

        return wrapper

    return decorator
