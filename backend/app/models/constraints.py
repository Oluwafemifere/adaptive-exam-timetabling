# app/models/constraints.py
import uuid
from sqlalchemy import String, Text, Boolean, Numeric, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import Base, TimestampMixin
from .users import SystemConfiguration 

class ConstraintCategory(Base, TimestampMixin):
    __tablename__ = "constraint_categories"

    id: Mapped[uuid.UUID]     = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str]         = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enforcement_layer: Mapped[str | None] = mapped_column(String, nullable=True)

    rules: Mapped[list["ConstraintRule"]] = relationship(back_populates="category")

class ConstraintRule(Base, TimestampMixin):
    __tablename__ = "constraint_rules"

    id: Mapped[uuid.UUID]     = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str]         = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str]         = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    constraint_type: Mapped[str] = mapped_column(String, nullable=False)
    constraint_definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("constraint_categories.id"), nullable=False)
    default_weight: Mapped[Numeric] = mapped_column(Numeric, default=1.0, nullable=False)
    is_active: Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
    is_configurable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped["ConstraintCategory"] = relationship(back_populates="rules")
    configurations: Mapped[list["ConfigurationConstraint"]] = relationship(back_populates="rule")

class ConfigurationConstraint(Base, TimestampMixin):
    __tablename__ = "configuration_constraints"

    id: Mapped[uuid.UUID]     = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    configuration_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("system_configurations.id"), nullable=False
    )
    constraint_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("constraint_rules.id"), nullable=False
    )
    custom_parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    weight: Mapped[Numeric]  = mapped_column(Numeric, default=1.0, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    rule: Mapped["ConstraintRule"]           = relationship(back_populates="configurations")
    configuration: Mapped["SystemConfiguration"] = relationship(back_populates="constraints")
