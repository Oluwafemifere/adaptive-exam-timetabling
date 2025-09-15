# scheduling_engine/gui/__init__.py

"""
GUI module for timetable visualization

This module provides GUI components for visualizing exam timetable solutions,
including interactive calendar views, detailed information panels, and
comprehensive analysis tools.
"""

from .timetable_gui_viewer import TimetableGUIViewer, show_timetable_gui

__all__ = ["TimetableGUIViewer", "show_timetable_gui"]
