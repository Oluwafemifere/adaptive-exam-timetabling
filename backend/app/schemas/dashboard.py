# backend/app/schemas/dashboard.py
"""Pydantic schemas for dashboard-specific data structures."""

from pydantic import BaseModel
from typing import List


class DashboardKpis(BaseModel):
    """Defines the structure for the main KPI cards on the dashboard."""

    total_exams_scheduled: int
    unresolved_hard_conflicts: int
    total_soft_conflicts: int
    overall_room_utilization: float


class ConflictHotspot(BaseModel):
    """Defines the structure for a single conflict hotspot item."""

    timeslot: str
    conflict_count: int


class TopBottleneck(BaseModel):
    """Defines the structure for a single bottleneck item."""

    item: str
    reason: str
    issue_count: int
