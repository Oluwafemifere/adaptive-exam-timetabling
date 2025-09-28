# backend/app/models/base.py
import uuid
from datetime import datetime
from sqlalchemy import (
    DateTime,
    func,
    MetaData,
    Table,
    Column,
    ForeignKey,
)  # Added Table, Column, ForeignKey for association table
from sqlalchemy.orm import Mapped, mapped_column, declarative_base
from pydantic import ConfigDict

# Create MetaData with default schema
metadata = MetaData(schema="exam_system")

# Declarative base with schema-aware metadata
Base = declarative_base(metadata=metadata)


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""

    model_config = ConfigDict(from_attributes=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
