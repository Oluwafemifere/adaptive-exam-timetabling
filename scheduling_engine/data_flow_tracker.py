# data_flow_tracker.py

"""
Compact Data Flow Tracker - Logs summaries instead of full data snapshots
to avoid massive file sizes while maintaining detailed insights.
FIXED: Pylance warnings for optional frame access
"""

import json
import datetime
import functools
import threading
import hashlib
from typing import Any, Dict, List, Optional, Union
from types import FrameType
from uuid import UUID
import inspect


class DataFlowTracker:
    _lock = threading.RLock()
    _events = []
    _session_id = None
    _max_sample_size = 3  # Max items to sample from lists/dicts

    @classmethod
    def set_session(cls, session_id: UUID):
        """Set the current session ID for tracking"""
        cls._session_id = str(session_id)

    @classmethod
    def _get_data_summary(cls, data: Any) -> Dict[str, Any]:
        """Create a compact summary of data instead of full snapshot"""
        summary = {
            "type": type(data).__name__,
            "size": None,
            "sample": None,
            "hash": None,
            "structure": None,
        }

        try:
            # Handle different data types
            if isinstance(data, dict):
                summary["size"] = len(data)
                summary["structure"] = {
                    "keys": list(data.keys())[: cls._max_sample_size],
                    "total_keys": len(data.keys()),
                }
                # Sample a few key-value pairs
                sample_items = dict(list(data.items())[: cls._max_sample_size])
                summary["sample"] = cls._summarize_nested(sample_items)
                summary["hash"] = hashlib.md5(
                    str(sorted(data.keys())).encode()
                ).hexdigest()[:8]

            elif isinstance(data, list):
                summary["size"] = len(data)
                if data:
                    summary["sample"] = [
                        cls._summarize_nested(item)
                        for item in data[: cls._max_sample_size]
                    ]
                    summary["structure"] = {
                        "first_item_type": type(data[0]).__name__ if data else None,
                        "all_same_type": (
                            all(type(item) == type(data[0]) for item in data)
                            if data
                            else True
                        ),
                    }
                summary["hash"] = hashlib.md5(str(len(data)).encode()).hexdigest()[:8]

            elif hasattr(data, "__dict__"):  # Custom objects
                obj_dict = data.__dict__
                summary["type"] = (
                    f"{data.__class__.__module__}.{data.__class__.__name__}"
                )
                summary["structure"] = {
                    "attributes": list(obj_dict.keys())[: cls._max_sample_size],
                    "total_attributes": len(obj_dict.keys()),
                }
                sample_attrs = dict(list(obj_dict.items())[: cls._max_sample_size])
                summary["sample"] = cls._summarize_nested(sample_attrs)

            elif isinstance(data, (str, int, float, bool)):
                summary["sample"] = (
                    data if len(str(data)) < 100 else str(data)[:100] + "..."
                )
                summary["size"] = len(str(data))

            else:
                summary["sample"] = (
                    str(data)[:100] + "..." if len(str(data)) > 100 else str(data)
                )
                summary["size"] = len(str(data))

        except Exception as e:
            summary["error"] = f"Summary generation failed: {str(e)}"
            summary["sample"] = (
                str(data)[:50] + "..." if len(str(data)) > 50 else str(data)
            )

        return summary

    @classmethod
    def _summarize_nested(cls, obj: Any, depth: int = 0) -> Any:
        """Recursively summarize nested objects with depth limit"""
        if depth > 2:  # Prevent infinite recursion
            return f"<nested_{type(obj).__name__}>"

        if isinstance(obj, dict):
            if len(obj) <= cls._max_sample_size:
                return {k: cls._summarize_nested(v, depth + 1) for k, v in obj.items()}
            else:
                sample = dict(list(obj.items())[: cls._max_sample_size])
                return {
                    **{
                        k: cls._summarize_nested(v, depth + 1)
                        for k, v in sample.items()
                    },
                    f"... and {len(obj) - cls._max_sample_size} more items": "...",
                }
        elif isinstance(obj, list):
            if len(obj) <= cls._max_sample_size:
                return [cls._summarize_nested(item, depth + 1) for item in obj]
            else:
                return [
                    *[
                        cls._summarize_nested(item, depth + 1)
                        for item in obj[: cls._max_sample_size]
                    ],
                    f"... and {len(obj) - cls._max_sample_size} more items",
                ]
        elif isinstance(obj, (UUID, datetime.datetime, datetime.date)):
            return str(obj)
        elif hasattr(obj, "__dict__") and depth < 2:
            return cls._get_data_summary(obj)
        else:
            return str(obj)[:50] + "..." if len(str(obj)) > 50 else str(obj)

    @classmethod
    def _get_caller_info(cls) -> Dict[str, str]:
        """Safely get caller information with proper null checking"""
        try:
            # Get the frame that called log_event
            frame = inspect.currentframe()
            if frame is None:
                return {"function": "unknown", "filename": "unknown", "line": "unknown"}

            # Go up the stack to find the actual caller (skip log_event and _get_caller_info)
            caller_frame = frame.f_back
            if caller_frame is None:
                return {"function": "unknown", "filename": "unknown", "line": "unknown"}

            # Skip one more frame if it's a decorator wrapper
            if caller_frame.f_back is not None:
                caller_frame = caller_frame.f_back

            # Now get the info safely
            if caller_frame is not None and caller_frame.f_code is not None:
                return {
                    "function": caller_frame.f_code.co_name,
                    "filename": caller_frame.f_code.co_filename.split("/")[-1].split(
                        "\\"
                    )[
                        -1
                    ],  # Handle both / and \ separators
                    "line": str(caller_frame.f_lineno),
                }
            else:
                return {"function": "unknown", "filename": "unknown", "line": "unknown"}

        except Exception as e:
            return {
                "function": "error",
                "filename": f"caller_error_{str(e)}",
                "line": "unknown",
            }

    @classmethod
    def log_event(
        cls,
        stage: str,
        data: Any,
        context: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ):
        """Log a compact event with data summary"""
        with cls._lock:
            timestamp = datetime.datetime.utcnow().isoformat()

            # Get function call context safely
            caller_info = cls._get_caller_info()

            event = {
                "timestamp": timestamp,
                "session_id": cls._session_id,
                "stage": stage,
                "caller": caller_info,
                "data_summary": cls._get_data_summary(data),
                "context": context or {},
                "metadata": metadata or {},
            }

            cls._events.append(event)

    @classmethod
    def log_stats(
        cls, stage: str, stats: Dict[str, Any], context: Optional[Dict] = None
    ):
        """Log statistical information without data payload"""
        with cls._lock:
            timestamp = datetime.datetime.utcnow().isoformat()

            # Get caller info safely
            caller_info = cls._get_caller_info()

            event = {
                "timestamp": timestamp,
                "session_id": cls._session_id,
                "stage": f"{stage}_STATS",
                "caller": caller_info,
                "stats": stats,
                "context": context or {},
            }

            cls._events.append(event)

    @classmethod
    def export(cls, filename: str = "data_flow_compact_log.md"):
        """Export compact, readable log"""
        with cls._lock:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("# Data Flow Tracking Log\n\n")
                f.write(f"**Session ID:** {cls._session_id}\n")
                f.write(f"**Generated:** {datetime.datetime.utcnow().isoformat()}\n")
                f.write(f"**Total Events:** {len(cls._events)}\n\n")

                f.write("## Table of Contents\n\n")
                stages = list(set(event["stage"] for event in cls._events))
                for stage in sorted(stages):
                    f.write(f"- [{stage}](#{stage.lower().replace('_', '-')})\n")
                f.write("\n")

                for i, event in enumerate(cls._events, 1):
                    f.write(f"## {i}. {event['stage']} @ {event['timestamp']}\n\n")

                    # Caller information
                    caller = event.get("caller", {})
                    f.write(
                        f"**Called from:** `{caller.get('function', 'unknown')}()` "
                    )
                    f.write(
                        f"in `{caller.get('filename', 'unknown')}:{caller.get('line', '?')}`\n\n"
                    )

                    # Context
                    if event.get("context"):
                        f.write("**Context:**\n")
                        f.write("```json\n")
                        f.write(json.dumps(event["context"], indent=2, default=str))
                        f.write("\n```\n\n")

                    # Stats (if present)
                    if "stats" in event:
                        f.write("**Statistics:**\n")
                        f.write("```json\n")
                        f.write(json.dumps(event["stats"], indent=2, default=str))
                        f.write("\n```\n\n")

                    # Data summary
                    if "data_summary" in event:
                        summary = event["data_summary"]
                        f.write("**Data Summary:**\n")
                        f.write(f"- **Type:** {summary.get('type', 'unknown')}\n")
                        if summary.get("size") is not None:
                            f.write(f"- **Size:** {summary['size']} items\n")
                        if summary.get("hash"):
                            f.write(f"- **Hash:** {summary['hash']}\n")

                        if summary.get("structure"):
                            f.write("- **Structure:**\n")
                            f.write("  ```json\n")
                            f.write(
                                f"  {json.dumps(summary['structure'], indent=4, default=str)}\n"
                            )
                            f.write("  ```\n")

                        if summary.get("sample"):
                            f.write("- **Sample Data:**\n")
                            f.write("  ```json\n")
                            f.write(
                                f"  {json.dumps(summary['sample'], indent=4, default=str)}\n"
                            )
                            f.write("  ```\n")

                        if summary.get("error"):
                            f.write(f"- **Error:** {summary['error']}\n")

                    # Metadata
                    if event.get("metadata"):
                        f.write("**Metadata:**\n")
                        f.write("```json\n")
                        f.write(json.dumps(event["metadata"], indent=2, default=str))
                        f.write("\n```\n\n")

                    f.write("---\n\n")

    @classmethod
    def clear_events(cls):
        """Clear all logged events"""
        with cls._lock:
            cls._events.clear()


# Decorator for tracking with compact output
def track_data_flow(stage: str, include_stats: bool = False):
    """
    Decorator to track function output with compact summaries

    Args:
        stage: Name of the pipeline stage
        include_stats: Whether to log additional statistics
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.datetime.utcnow()

            try:
                result = func(*args, **kwargs)
                end_time = datetime.datetime.utcnow()

                # Build minimal context
                context = {
                    "function": func.__qualname__,
                    "execution_time_ms": int(
                        (end_time - start_time).total_seconds() * 1000
                    ),
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()),
                }

                # Log the result
                DataFlowTracker.log_event(stage, result, context)

                # Optionally log statistics
                if include_stats and hasattr(result, "__len__"):
                    try:
                        stats = {
                            "result_length": len(result),
                            "result_type": type(result).__name__,
                            "execution_successful": True,
                        }
                        DataFlowTracker.log_stats(stage, stats, context)
                    except:
                        pass  # Ignore stats errors

                return result

            except Exception as e:
                end_time = datetime.datetime.utcnow()
                context = {
                    "function": func.__qualname__,
                    "execution_time_ms": int(
                        (end_time - start_time).total_seconds() * 1000
                    ),
                    "error": str(e),
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()),
                }

                DataFlowTracker.log_event(f"{stage}_ERROR", {"error": str(e)}, context)
                raise

        return wrapper

    return decorator


# Async version of the decorator
def track_data_flow_async(stage: str, include_stats: bool = False):
    """Async version of track_data_flow decorator"""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = datetime.datetime.utcnow()

            try:
                result = await func(*args, **kwargs)
                end_time = datetime.datetime.utcnow()

                context = {
                    "function": func.__qualname__,
                    "execution_time_ms": int(
                        (end_time - start_time).total_seconds() * 1000
                    ),
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()),
                    "async": True,
                }

                DataFlowTracker.log_event(stage, result, context)

                if include_stats and hasattr(result, "__len__"):
                    try:
                        stats = {
                            "result_length": len(result),
                            "result_type": type(result).__name__,
                            "execution_successful": True,
                        }
                        DataFlowTracker.log_stats(stage, stats, context)
                    except:
                        pass

                return result

            except Exception as e:
                end_time = datetime.datetime.utcnow()
                context = {
                    "function": func.__qualname__,
                    "execution_time_ms": int(
                        (end_time - start_time).total_seconds() * 1000
                    ),
                    "error": str(e),
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()),
                    "async": True,
                }

                DataFlowTracker.log_event(f"{stage}_ERROR", {"error": str(e)}, context)
                raise

        return wrapper

    return decorator
