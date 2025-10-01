# backend/app/logging_config.py
import logging
from typing import Dict


# Define a custom filter to add extra context if needed
class RequestIdFilter(logging.Filter):
    def filter(self, record):
        # Provide a default request_id if not already set
        if not hasattr(record, "request_id"):
            record.request_id = "no-request-id"
        return True


LOGGING_CONFIG: Dict[str, any] = {  # type: ignore
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id_filter": {
            "()": RequestIdFilter,
        },
    },
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(asctime)s [%(name)s] [%(request_id)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(levelprefix)s %(asctime)s [%(name)s] [%(request_id)s] %(client_addr)s - "%(request_line)s" %(status_code)s',
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        # This formatter is key for tracebacks
        "detailed": {
            "format": "%(levelname)s %(asctime)s [%(name)s] [%(module)s:%(lineno)d] - %(message)s\n%(exc_text)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        # Handles general logs (INFO, DEBUG, etc.)
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",  # Use stdout for general logs
            "filters": ["request_id_filter"],
        },
        # Specifically for access logs
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "filters": ["request_id_filter"],
        },
        # Specifically for error logs with tracebacks
        "error": {
            "formatter": "detailed",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",  # Use stderr for errors
            "level": "ERROR",
            "filters": ["request_id_filter"],
        },
    },
    "loggers": {
        # Root logger: Catches all logs from your app and libraries
        "": {
            "handlers": ["default", "error"],
            "level": "INFO",
        },
        # Uvicorn access logs: Handled separately to use the access formatter
        "uvicorn.access": {
            "handlers": ["access"],
            "level": "INFO",
            "propagate": False,
        },
        # Your application's logger: Set to DEBUG for more verbosity
        "backend": {
            "handlers": ["default", "error"],
            "level": "DEBUG",
            "propagate": False,  # Prevent duplicating logs in the root logger
        },
    },
}
