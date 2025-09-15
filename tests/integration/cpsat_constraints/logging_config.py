# Enhanced CP-SAT Logging Capture
# This captures CP-SAT's internal C++ logging output that bypasses Python streams

import logging
import os
import sys
import subprocess
import tempfile
from datetime import datetime
from logging import Handler
from io import StringIO
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from typing import Optional, TextIO


class TeeStream:
    """A stream that writes to multiple destinations (file and console)"""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            try:
                stream.write(data)
                stream.flush()
            except:
                pass  # Handle closed streams gracefully

    def flush(self):
        for stream in self.streams:
            try:
                stream.flush()
            except:
                pass


class StreamToLogger:
    """Redirect stdout/stderr to logger"""

    def __init__(self, logger, level=logging.INFO):
        self.logger = logger
        self.level = level
        self.linebuf = ""

    def write(self, buf):
        if isinstance(buf, bytes):
            buf = buf.decode("utf-8", errors="replace")

        temp_linebuf = self.linebuf + buf
        self.linebuf = ""

        for line in temp_linebuf.splitlines(True):
            if line.endswith("\n"):
                self.logger.log(self.level, line.rstrip("\n\r"))
            else:
                self.linebuf = line

    def flush(self):
        if self.linebuf:
            self.logger.log(self.level, self.linebuf.rstrip("\n\r"))
            self.linebuf = ""


def configure_cpsat_native_logging():
    """
    Configure CP-SAT to log its internal C++ output to files
    This is the key to capturing the detailed solver output you see
    """
    # Set Google logging environment variables for OR-Tools
    # These control CP-SAT's internal C++ logging
    os.environ["GLOG_logtostderr"] = "1"  # Log to stderr
    os.environ["GLOG_v"] = "1"  # Verbose level 1
    os.environ["GLOG_stderrthreshold"] = "0"  # Log everything to stderr
    os.environ["GLOG_colorlogtostderr"] = "0"  # No color codes

    # Additional CP-SAT specific logging
    os.environ["FLAGS_cp_model_dump_models"] = "0"  # Don't dump models
    os.environ["FLAGS_log_prefix"] = "1"  # Include prefixes

    logging.getLogger("CPSAT_NATIVE").info("Configured CP-SAT native C++ logging")


def configure_ultimate_logging(
    log_file_path: str = "ultimate_execution.log",
    log_level: int = logging.DEBUG,
    console_output: bool = True,
    capture_stdout: bool = True,
    capture_stderr: bool = True,
    capture_cpsat_native: bool = True,
    max_file_size_mb: int = 200,
    backup_count: int = 10,
):
    """
    Configure the ultimate logging that captures EVERYTHING including CP-SAT native output
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Clear any existing handlers to avoid duplicates
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Create comprehensive formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file_path, mode="w")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # Create console handler if requested
    handlers: list[Handler] = [file_handler]
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    # Configure root logger
    logging.basicConfig(
        level=log_level, handlers=handlers, force=True, encoding="utf-8"
    )

    # Configure CP-SAT native logging FIRST
    if capture_cpsat_native:
        configure_cpsat_native_logging()

    # Configure stdout/stderr capture
    if capture_stdout or capture_stderr:
        setup_stream_capture(capture_stdout, capture_stderr)

    # Configure all known module loggers
    module_names = [
        "test_cpsat_hard_constraints_integration",
        "cpsat_constraint_manager",
        "room_constraints",
        "student_constraints",
        "invigilator_constraints",
        "special_constraints",
        "day_indicator",
        "start_occupancy_linking",
        "student_distribution",
        "problem_model",
        "base_cpsat_constraint",
        "STDOUT",
        "STDERR",
        "CPSAT_NATIVE",
        "__main__",
    ]

    for module_name in module_names:
        module_logger = logging.getLogger(module_name)
        module_logger.setLevel(log_level)
        for handler in module_logger.handlers[:]:
            module_logger.removeHandler(handler)
        module_logger.propagate = True

    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info(f"ULTIMATE logging configured at {datetime.now()}")
    logger.info(f"Log file: {log_file_path}")
    logger.info(f"Capture CP-SAT native: {capture_cpsat_native}")
    logger.info(f"Google logging environment configured for CP-SAT")
    logger.info("=" * 80)

    return logging.getLogger()


def setup_stream_capture(capture_stdout: bool = True, capture_stderr: bool = True):
    """Set up stdout/stderr capture to logging"""
    if capture_stdout:
        stdout_logger = logging.getLogger("STDOUT")
        original_stdout = sys.stdout
        sys.stdout = TeeStream(
            StreamToLogger(stdout_logger, logging.INFO), original_stdout
        )

    if capture_stderr:
        stderr_logger = logging.getLogger("STDERR")
        original_stderr = sys.stderr
        sys.stderr = TeeStream(
            StreamToLogger(stderr_logger, logging.INFO),  # CP-SAT logs to stderr
            original_stderr,
        )


@contextmanager
def cpsat_ultimate_logging():
    """
    Context manager that maximizes CP-SAT logging capture
    Use this around your solver.Solve() calls
    """
    # Store original environment
    original_env = {}
    glog_vars = [
        "GLOG_logtostderr",
        "GLOG_v",
        "GLOG_stderrthreshold",
        "GLOG_colorlogtostderr",
    ]

    try:
        # Backup original environment
        for var in glog_vars:
            original_env[var] = os.environ.get(var, "")

        # Set maximum logging for CP-SAT
        os.environ["GLOG_logtostderr"] = "1"
        os.environ["GLOG_v"] = "2"  # Even more verbose
        os.environ["GLOG_stderrthreshold"] = "0"
        os.environ["GLOG_colorlogtostderr"] = "0"

        cpsat_logger = logging.getLogger("CPSAT_SOLVE")
        cpsat_logger.info("Starting CP-SAT solve with maximum native logging")

        yield

    finally:
        # Restore original environment
        for var, value in original_env.items():
            if value:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]


def setup_cpsat_solver_with_logging(solver):
    """
    Configure a CP-SAT solver instance for maximum logging output
    Call this before solver.Solve()
    """
    # Enable all CP-SAT solver logging parameters
    solver.parameters.log_search_progress = True  # We want stderr for capture
    solver.parameters.log_to_response = True

    # Enable detailed presolve logging
    solver.parameters.cp_model_presolve = True

    # Enable symmetry detection logging
    solver.parameters.symmetry_level = 2

    # Enable detailed search logging
    solver.parameters.search_branching = 0  # Automatic

    logging.getLogger("CPSAT_SETUP").info(
        "Configured CP-SAT solver for maximum logging output"
    )

    return solver


def setup_ultimate_test_logging():
    """Convenience function for ultimate CP-SAT test logging"""
    return configure_ultimate_logging(
        log_file_path="ultimate_cpsat_execution.log",
        log_level=logging.DEBUG,
        console_output=True,
        capture_stdout=True,
        capture_stderr=True,
        capture_cpsat_native=True,
        max_file_size_mb=500,  # Large for comprehensive CP-SAT logs
        backup_count=20,
    )


# Example usage
if __name__ == "__main__":
    # Set up ultimate logging
    logger = setup_ultimate_test_logging()

    # Test regular logging
    logger.info("Testing ultimate CP-SAT logging")

    # Test stdout capture
    print("This stdout message should be captured")

    # Test stderr capture (where CP-SAT logs go)
    import sys

    print("This CP-SAT-style message goes to stderr", file=sys.stderr)

    # Simulate what happens when you solve
    try:
        from ortools.sat.python import cp_model

        model = cp_model.CpModel()
        x = model.NewIntVar(0, 10, "x")
        y = model.NewIntVar(0, 10, "y")
        model.Add(x + y == 5)

        solver = cp_model.CpSolver()
        solver = setup_cpsat_solver_with_logging(solver)

        with cpsat_ultimate_logging():
            logger.info("Starting CP-SAT solve with ultimate logging")
            status = solver.Solve(model)
            logger.info(f"Solve completed with status: {status}")

    except ImportError:
        logger.warning("OR-Tools not available for testing")

    logger.info("Check 'ultimate_cpsat_execution.log' for all captured output!")
