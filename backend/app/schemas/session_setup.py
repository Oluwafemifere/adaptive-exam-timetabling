# backend/app/schemas/session_setup.py
"""Pydantic schemas for the Exam Session Setup Wizard."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any
from uuid import UUID
from datetime import date, time


class TimeSlot(BaseModel):
    """Defines a single time slot for an exam day."""

    start_time: time
    end_time: time


class SessionSetupCreate(BaseModel):
    """Schema for creating a new exam session via the setup wizard."""

    session_name: str = Field(
        ..., min_length=5, description="The name of the exam session."
    )
    start_date: date
    end_date: date
    slot_generation_mode: str = Field(
        "flexible", description="The slot generation mode, e.g., 'dynamic'."
    )
    time_slots: List[TimeSlot] = Field(
        ..., min_length=1, description="A list of daily time slots."
    )


class SessionSetupSummary(BaseModel):
    """Schema for the response of the session setup summary and validation endpoint."""

    session_details: Dict[str, Any]
    data_summary: Dict[str, Any]
    validation_results: Dict[str, Any]
