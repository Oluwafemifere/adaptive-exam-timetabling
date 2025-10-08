# app/models/constraints.py
import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    String,
    Text,
    Boolean,
    ForeignKey,
    Double,
    CheckConstraint,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .users import User, SystemConfiguration


class ConstraintConfiguration(Base):
    __tablename__ = "constraint_configurations"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    creator: Mapped[Optional["User"]] = relationship()
    rule_settings: Mapped[List["ConfigurationRuleSetting"]] = relationship(
        back_populates="configuration", cascade="all, delete-orphan"
    )
    # FIXED: The back_populates value now correctly matches the property name
    # in the SystemConfiguration model.
    system_configurations: Mapped[List["SystemConfiguration"]] = relationship(
        back_populates="constraint_configuration"
    )


class ConstraintRule(Base):
    __tablename__ = "constraint_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="Other")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    parameters: Mapped[List["ConstraintParameter"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )
    configuration_settings: Mapped[List["ConfigurationRuleSetting"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(type.in_(["hard", "soft"]), name="constraint_rules_type_check"),
    )


class ConstraintParameter(Base):
    __tablename__ = "constraint_parameters"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("constraint_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    data_type: Mapped[str] = mapped_column(String(50), nullable=False)
    default_value: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    validation_rules: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    rule: Mapped["ConstraintRule"] = relationship(back_populates="parameters")

    __table_args__ = (
        UniqueConstraint(
            "rule_id", "key", name="constraint_parameters_rule_id_key_key"
        ),
        CheckConstraint(
            data_type.in_(["integer", "float", "boolean", "string"]),
            name="constraint_parameters_data_type_check",
        ),
    )


class ConfigurationRuleSetting(Base):
    __tablename__ = "configuration_rule_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    configuration_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("constraint_configurations.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("constraint_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    weight: Mapped[float] = mapped_column(Double, default=1.0, nullable=False)
    parameter_overrides: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    configuration: Mapped["ConstraintConfiguration"] = relationship(
        back_populates="rule_settings"
    )
    rule: Mapped["ConstraintRule"] = relationship(
        back_populates="configuration_settings"
    )

    __table_args__ = (
        UniqueConstraint(
            "configuration_id",
            "rule_id",
            name="configuration_rule_settings_configuration_id_rule_id_key",
        ),
    )
