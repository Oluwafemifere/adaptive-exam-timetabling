# backend/app/schemas/dashboard.py
"""Pydantic schemas for dashboard-specific data structures."""

from pydantic import BaseModel, Field
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

    type: str
    # FIX: Renamed fields to match the database function's actual JSON output.
    name: str = Field(..., alias="item")
    issue: str = Field(..., alias="reason")
    value: int = Field(..., alias="issue_count")


class DashboardAnalytics(BaseModel):
    """High-level analytics data for the dashboard."""

    kpis: DashboardKpis
    conflict_hotspots: List[ConflictHotspot]
    top_bottlenecks: List[TopBottleneck]
