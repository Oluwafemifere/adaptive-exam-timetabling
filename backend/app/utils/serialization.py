# app/utils/serialization.py
import json
import uuid
from datetime import datetime, date
from typing import Any


class UUIDEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle UUID and datetime objects"""

    def default(self, o: Any) -> Any:  # use parameter name `o` to match base signature
        if isinstance(o, uuid.UUID):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, date):
            return o.isoformat()
        return super().default(o)


def serialize_for_json(obj: Any) -> Any:
    """Recursively convert objects to JSON-serializable format"""
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if hasattr(obj, "__dict__"):
        return {
            k: serialize_for_json(v)
            for k, v in obj.__dict__.items()
            if not k.startswith("_")
        }
    if isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, tuple):
        return [serialize_for_json(item) for item in obj]
    if isinstance(obj, set):
        return [serialize_for_json(item) for item in obj]
    return obj


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """Safely serialize objects to JSON string"""
    return json.dumps(obj, cls=UUIDEncoder, **kwargs)


def safe_json_loads(json_str: str) -> Any:
    """Safely deserialize JSON string"""
    return json.loads(json_str)


# Monkey patch for global JSONEncoder.default (optional)
def patch_json_encoder():
    """Monkey patch the default JSON encoder to handle UUIDs"""
    _old_default = json.JSONEncoder.default

    def _new_default(self, o: Any) -> Any:  # use `o` to match JSONEncoder.default
        if isinstance(o, uuid.UUID):
            return str(o)
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return _old_default(self, o)

    # assignment triggers a type check warning. Silence it explicitly.
    json.JSONEncoder.default = _new_default  # type: ignore[assignment]
