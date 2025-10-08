# app/models/base.py
from datetime import datetime
from sqlalchemy import DateTime, func, MetaData
from sqlalchemy.orm import Mapped, mapped_column, declarative_base

# Create MetaData with default schema
# This ensures that all tables created using this Base will be in the 'exam_system' schema
metadata = MetaData(schema="exam_system")

# Declarative base with schema-aware metadata
Base = declarative_base(metadata=metadata)


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""

    # Note: The DB schema uses 'timestamp without time zone'.
    # SQLAlchemy's default DateTime type corresponds to this.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
