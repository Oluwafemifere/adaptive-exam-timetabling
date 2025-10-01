# backend/app/services/data_retrieval/__init__.py

"""
Data retrieval services package.

This package provides a unified service for retrieving pre-structured data
from the database by calling dedicated PostgreSQL functions. This offloads
complex data aggregation to the database layer.
"""

from .data_retrieval_service import DataRetrievalService

__all__ = [
    # Unified service for complex data retrieval via PSQL functions
    "DataRetrievalService",
]
