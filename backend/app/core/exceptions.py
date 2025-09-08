# app/core/exceptions.py
"""Application-level exceptions used across services.

This module provides richer, structured exceptions that carry metadata useful
for service-level error handling, logging, and HTTP translation in routers.

Design goals:
- Each exception is serializable via ``to_dict`` for API responses and logs.
- Exceptions include an explicit ``code`` and ``status_code`` for consistent
  error handling across the application.
- Provide helpers to attach contextual data and to wrap underlying exceptions.
"""
from __future__ import annotations

from typing import Optional, Any, Dict, List
from datetime import datetime


class AppError(Exception):
    """Base application exception with structured metadata.

    Attributes
    ----------
    message
        Human readable message.
    code
        Machine friendly error code (snake_case).
    status_code
        Suggested HTTP status code for API responses.
    details
        Arbitrary extra data useful for debugging or UX.
    timestamp
        UTC ISO timestamp when the exception was created.
    cause
        Optional underlying exception instance or string.
    context
        Optional lightweight context dict (ids, phase names, counts).
    """

    code: str = "app_error"
    status_code: int = 500

    def __init__(
        self,
        message: str = "An application error occurred",
        *,
        details: Optional[Any] = None,
        cause: Optional[BaseException] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        self.cause = cause
        self.context = context or {}
        self.timestamp = datetime.utcnow().isoformat() + "Z"

    def __str__(self) -> str:
        base = f"{self.__class__.__name__}({self.code}): {self.message}"
        if self.context:
            base += f" | context={self.context}"
        if self.details is not None:
            base += f" | details={self.details}"
        if self.cause is not None:
            base += f" | cause={repr(self.cause)}"
        return base

    def to_dict(self) -> Dict[str, Any]:
        """Return a serializable representation suitable for API responses.

        Note: Do not include large or sensitive objects inside ``details`` or
        ``cause`` when sending to untrusted clients.
        """
        return {
            "error": {
                "type": self.__class__.__name__,
                "code": self.code,
                "message": self.message,
                "status_code": self.status_code,
                "details": self.details,
                "context": self.context,
                "timestamp": self.timestamp,
            }
        }

    def with_context(self, **ctx: Any) -> "AppError":
        """Return self after extending the context dict. Useful for chaining.

        Example:
        raise err.with_context(job_id=job_id)
        """
        self.context.update({k: v for k, v in ctx.items() if v is not None})
        return self

    @classmethod
    def from_exception(
        cls, exc: BaseException, message: Optional[str] = None
    ) -> "AppError":
        """Wrap a generic exception into an AppError preserving the cause."""
        return cls(message or str(exc), cause=exc)


class SchedulingError(AppError):
    """Generic scheduling/timetabling error.

    Use this as the base for solver and orchestration failures. Handlers may
    want to map this to a 500 status by default but subclasses can adjust it.
    """

    code = "scheduling_error"
    status_code = 500

    def __init__(
        self,
        message: str = "Scheduling engine error",
        *,
        phase: Optional[str] = None,
        solver: Optional[str] = None,
        details: Optional[Any] = None,
        cause: Optional[BaseException] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, details=details, cause=cause, context=context)
        if phase:
            self.context.setdefault("phase", phase)
        if solver:
            self.context.setdefault("solver", solver)


class InfeasibleProblemError(SchedulingError):
    """Raised when the solver cannot find any feasible solution.

    Carries solver-specific diagnostics where available so callers can
    present helpful guidance or attempt automatic relaxations.
    """

    code = "infeasible_problem"
    status_code = 422

    def __init__(
        self,
        message: str = "Problem found to be infeasible",
        *,
        solver: Optional[str] = None,
        phase: Optional[str] = None,
        infeasible_sets: Optional[List[Dict[str, Any]]] = None,
        suggestion: Optional[str] = None,
        details: Optional[Any] = None,
        cause: Optional[BaseException] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message,
            phase=phase,
            solver=solver,
            details=details,
            cause=cause,
            context=context,
        )
        self.infeasible_sets = infeasible_sets or []
        self.suggestion = suggestion
        # Add compact diagnostics to context for logs and monitoring
        if self.infeasible_sets:
            self.context.setdefault("infeasible_count", len(self.infeasible_sets))

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["error"].update(
            {
                "infeasible_sets": self.infeasible_sets,
                "suggestion": self.suggestion,
            }
        )
        return data


class JobNotFoundError(AppError):
    """Raised when a job record cannot be located in storage.

    Include the missing identifier to make logging and client messages clear.
    """

    code = "job_not_found"
    status_code = 404

    def __init__(
        self,
        job_id: Optional[str] = None,
        message: Optional[str] = None,
        *,
        details: Optional[Any] = None,
        cause: Optional[BaseException] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        msg = message or (
            f"Timetable job {job_id} not found" if job_id else "Job not found"
        )
        super().__init__(msg, details=details, cause=cause, context=context)
        if job_id is not None:
            self.context.setdefault("job_id", str(job_id))


class JobAccessDeniedError(AppError):
    """Raised when the current user is not permitted to access a job.

    Contains minimal identity information to avoid leaking sensitive data
    in logs or to clients while still being actionable.
    """

    code = "job_access_denied"
    status_code = 403

    def __init__(
        self,
        job_id: Optional[str] = None,
        user_id: Optional[str] = None,
        message: Optional[str] = None,
        *,
        required_roles: Optional[List[str]] = None,
        details: Optional[Any] = None,
        cause: Optional[BaseException] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        msg = message or "Access denied to requested job"
        super().__init__(msg, details=details, cause=cause, context=context)
        if job_id is not None:
            self.context.setdefault("job_id", str(job_id))
        if user_id is not None:
            # avoid storing PII beyond an opaque id
            self.context.setdefault("user_id", str(user_id))
        if required_roles:
            self.context.setdefault("required_roles", required_roles)


class DataProcessingError(AppError):
    """Raised during data processing, validation, or transformation operations.

    This covers CSV processing, data mapping, integrity checks, and bulk operations.
    """

    code = "data_processing_error"
    status_code = 422  # Unprocessable Entity

    def __init__(
        self,
        message: str = "Data processing error occurred",
        *,
        phase: Optional[str] = None,
        entity_type: Optional[str] = None,
        validation_errors: Optional[List[Dict[str, Any]]] = None,
        details: Optional[Any] = None,
        cause: Optional[BaseException] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, details=details, cause=cause, context=context)
        if phase:
            self.context.setdefault("phase", phase)
        if entity_type:
            self.context.setdefault("entity_type", entity_type)
        self.validation_errors = validation_errors or []

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["error"].update(
            {
                "validation_errors": self.validation_errors,
            }
        )
        return data


__all__ = [
    "AppError",
    "SchedulingError",
    "InfeasibleProblemError",
    "JobNotFoundError",
    "JobAccessDeniedError",
    "DataProcessingError",
]
