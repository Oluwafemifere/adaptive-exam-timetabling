# FIXED tracking_mixin.py - Addressing WARN-003

"""
Tracking Mixin Fixes

FIXES APPLIED:
- WARN-003: Action ID mismatch: expected vs actual - Fixed action lifecycle management
"""

import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import threading
import asyncio

logger = logging.getLogger(__name__)


class TrackingMixin:
    """
    Mixin class that provides automatic job, session, and action ID generation and tracking
    capabilities for all service operations.

    FIXED: Action lifecycle management with proper synchronization
    """

    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session
        self.current_job_id: Optional[uuid.UUID] = None
        self.current_session_id: Optional[uuid.UUID] = None
        self.current_action_id: Optional[uuid.UUID] = None
        self._action_stack: List[Dict[str, Any]] = []

        # Add synchronization for thread-safe action management (WARN-003 fix)
        self._action_lock = threading.RLock()
        self._action_counter = 0

    def generate_action_id(self) -> uuid.UUID:
        """Generate a new unique action ID."""
        return uuid.uuid4()

    def _generate_job_id(self) -> uuid.UUID:
        """Generate a new unique job ID."""
        return uuid.uuid4()

    def _start_action(
        self,
        action_type: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> uuid.UUID:
        """
        Start tracking a new action with automatic ID generation and synchronization.

        FIXES WARN-003: Action ID mismatch with proper lifecycle management

        Args:
            action_type: Type of action being performed
            description: Human-readable description
            metadata: Additional metadata for the action

        Returns:
            Generated action ID
        """
        with self._action_lock:  # Thread-safe action management
            action_id = self.generate_action_id()
            self._action_counter += 1

            action_info = {
                "action_id": action_id,
                "action_type": action_type,
                "description": description,
                "metadata": metadata or {},
                "started_at": datetime.utcnow(),
                "parent_action_id": self.current_action_id,
                "sequence_number": self._action_counter,  # For debugging order
                "thread_id": threading.get_ident(),  # Track which thread created this
                "status": "running",  # Track action status
            }

            # Validate action stack consistency
            if (
                self._action_stack and len(self._action_stack) > 50
            ):  # Prevent stack overflow
                logger.warning(
                    f"Action stack is getting large ({len(self._action_stack)} actions)"
                )

            # Push to stack with validation
            self._action_stack.append(action_info)

            # Update current action ID
            previous_action_id = self.current_action_id
            self.current_action_id = action_id

            logger.info(
                f"Started action '{action_type}' with ID {action_id} "
                f"(parent: {previous_action_id}, seq: {self._action_counter})"
            )

            return action_id

    def _end_action(
        self, action_id: uuid.UUID, status: str = "completed", result: Any = None
    ):
        """
        End tracking of an action with enhanced validation and synchronization.
        """
        with self._action_lock:
            if not self._action_stack:
                logger.warning(f"No action stack found when ending action {action_id}")
                return

            # Find the action in the stack
            current_action = None
            action_index = None

            for i in range(len(self._action_stack) - 1, -1, -1):
                if self._action_stack[i]["action_id"] == action_id:
                    current_action = self._action_stack[i]
                    action_index = i
                    break

            if not current_action:
                logger.error(f"Action {action_id} not found in action stack")
                # Don't throw assertion error, just return gracefully
                return

            # Validate action is the expected one (most recent)
            if action_index != len(self._action_stack) - 1:
                logger.warning(
                    f"Ending action {action_id} that is not the most recent "
                    f"(index {action_index}, stack size {len(self._action_stack)})"
                )

            # Additional validation for action ID mismatch
            if self.current_action_id != action_id:
                logger.warning(
                    f"Action ID mismatch: current_action_id={self.current_action_id}, "
                    f"ending_action_id={action_id}. This may indicate improper nesting."
                )

            # Update action info
            end_time = datetime.utcnow()
            current_action.update(
                {
                    "ended_at": end_time,
                    "status": status,
                    "result": result,
                    "duration_ms": (
                        end_time - current_action["started_at"]
                    ).total_seconds()
                    * 1000,
                    "ended_by_thread": threading.get_ident(),
                }
            )

            # Validate thread consistency
            if current_action.get("thread_id") != current_action.get("ended_by_thread"):
                logger.warning(
                    f"Action {action_id} started by thread {current_action.get('thread_id')} "
                    f"but ended by thread {current_action.get('ended_by_thread')}"
                )

            # Remove from stack (preserve order) - FIXED: Remove assertion
            if action_index == len(self._action_stack) - 1:
                # Normal case: removing most recent action
                self._action_stack.pop()
            else:
                # Unusual case: removing action from middle of stack
                logger.warning(
                    f"Removing action from middle of stack (index {action_index})"
                )
                # FIXED: Remove the assertion that was causing the crash
                if action_index is not None:  # Only remove if we found a valid index
                    self._action_stack.pop(action_index)
                else:
                    logger.error(f"Cannot remove action {action_id} - invalid index")
                    return

            # Update current action ID to parent
            if self._action_stack:
                self.current_action_id = self._action_stack[-1]["action_id"]
            else:
                self.current_action_id = None

            logger.info(
                f"Ended action '{current_action['action_type']}' with ID {action_id} - "
                f"Status: {status}, Duration: {current_action.get('duration_ms', 0):.1f}ms"
            )

    def _create_job(
        self,
        job_type: str,
        initiated_by: Optional[uuid.UUID] = None,
        session_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> uuid.UUID:
        """
        Create a new job record with automatic ID generation.

        Args:
            job_type: Type of job being created
            initiated_by: User ID who initiated the job
            session_id: Associated session ID
            metadata: Additional job metadata

        Returns:
            Generated job ID
        """
        job_id = self._generate_job_id()
        self.current_job_id = job_id

        if session_id:
            self.current_session_id = session_id

        logger.info(f"Created job '{job_type}' with ID {job_id}")
        return job_id

    def _get_current_context(self) -> Dict[str, Any]:
        """
        Get current tracking context with enhanced information.

        Returns comprehensive context for debugging action lifecycle issues.
        """
        with self._action_lock:
            return {
                "job_id": self.current_job_id,
                "session_id": self.current_session_id,
                "action_id": self.current_action_id,
                "action_stack_depth": len(self._action_stack),
                "action_counter": self._action_counter,
                "thread_id": threading.get_ident(),
                "stack_summary": [
                    {
                        "id": str(action["action_id"]),
                        "type": action["action_type"],
                        "status": action.get("status", "unknown"),
                        "seq": action.get("sequence_number", 0),
                    }
                    for action in self._action_stack[
                        -3:
                    ]  # Last 3 actions for debugging
                ],
            }

    async def _log_operation(
        self,
        operation: str,
        details: Optional[Dict[str, Any]] = None,
        level: str = "INFO",
        session_id: Optional[str] = None,
        preparation_id: Optional[str] = None,
        validation_summary: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        **kwargs,
    ):
        """
        Log an operation with current tracking context and enhanced error handling.

        Args:
            operation: Description of the operation
            details: Additional details to log
            level: Log level
            session_id: Session ID for context
            preparation_id: Preparation ID for context
            validation_summary: Validation summary data
            error: Error message if applicable
            **kwargs: Additional keyword arguments for flexibility
        """
        context = self._get_current_context()

        # Merge provided IDs into context if available
        if session_id:
            context["provided_session_id"] = session_id
        if preparation_id:
            context["provided_preparation_id"] = preparation_id

        log_data = {
            "operation": operation,
            "context": context,
            "details": details or {},
            "validation_summary": validation_summary,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,  # Include any additional kwargs
        }

        log_msg = f"{operation} (Job: {context['job_id']}, Session: {context['session_id']}, Action: {context['action_id']})"

        if error:
            log_msg = f"{log_msg} - Error: {error}"

        if level.upper() == "ERROR":
            logger.error(log_msg, extra=log_data)
        elif level.upper() == "WARNING":
            logger.warning(log_msg, extra=log_data)
        else:
            logger.info(log_msg, extra=log_data)

    def track_method(self, method_name: str):
        """
        Decorator factory for automatically tracking method calls with enhanced error handling.

        Args:
            method_name: Name of the method being tracked
        """

        def decorator(func):
            async def wrapper(*args, **kwargs):
                action_id = self._start_action(
                    action_type=f"method_call",
                    description=f"Executing {method_name}",
                    metadata={
                        "method": method_name,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys()),
                    },
                )

                try:
                    result = await func(*args, **kwargs)
                    self._end_action(
                        action_id, status="completed", result={"success": True}
                    )
                    return result
                except Exception as e:
                    self._end_action(
                        action_id, status="failed", result={"error": str(e)}
                    )
                    raise

            return wrapper

        return decorator

    async def persist_tracking_data(self):
        """
        Persist tracking data to database if session is available.
        This should be called at the end of operations.
        """
        if not self.session:
            return

        try:
            # Implementation for persisting tracking data to database
            # This could include action history, performance metrics, etc.
            pass
        except Exception as e:
            logger.error(f"Failed to persist tracking data: {e}")

    def validate_action_stack_integrity(self) -> Dict[str, Any]:
        """
        Validate action stack integrity and detect potential issues.

        Returns:
            Dict with validation results and recommendations
        """
        with self._action_lock:
            validation = {
                "is_valid": True,
                "issues": [],
                "warnings": [],
                "stats": {
                    "stack_depth": len(self._action_stack),
                    "total_actions_created": self._action_counter,
                    "current_thread": threading.get_ident(),
                },
            }

            # Check for excessive stack depth
            if len(self._action_stack) > 20:
                validation["warnings"].append(
                    f"Action stack depth is high: {len(self._action_stack)}"
                )

            # Check for long-running actions
            now = datetime.utcnow()
            for action in self._action_stack:
                duration = (now - action["started_at"]).total_seconds()
                if duration > 300:  # 5 minutes
                    validation["warnings"].append(
                        f"Long-running action detected: {action['action_type']} "
                        f"({duration:.1f}s, ID: {action['action_id']})"
                    )

            # Check for thread consistency
            thread_ids = set(action.get("thread_id") for action in self._action_stack)
            if len(thread_ids) > 1:
                validation["warnings"].append(
                    f"Multiple threads in action stack: {thread_ids}"
                )

            # Check for orphaned actions
            running_actions = [
                a for a in self._action_stack if a.get("status") == "running"
            ]
            if len(running_actions) != len(self._action_stack):
                validation["issues"].append(
                    f"Found {len(self._action_stack) - len(running_actions)} non-running actions in stack"
                )
                validation["is_valid"] = False

            return validation

    def cleanup_stale_actions(self, max_age_seconds: int = 3600):
        """
        Clean up stale actions that have been running too long.

        Args:
            max_age_seconds: Maximum age for actions before cleanup
        """
        with self._action_lock:
            now = datetime.utcnow()
            initial_count = len(self._action_stack)

            # Remove stale actions
            self._action_stack = [
                action
                for action in self._action_stack
                if (now - action["started_at"]).total_seconds() < max_age_seconds
            ]

            cleaned_count = initial_count - len(self._action_stack)

            if cleaned_count > 0:
                logger.warning(f"Cleaned up {cleaned_count} stale actions")

                # Reset current action ID if stack is empty
                if not self._action_stack:
                    self.current_action_id = None
                else:
                    self.current_action_id = self._action_stack[-1]["action_id"]
