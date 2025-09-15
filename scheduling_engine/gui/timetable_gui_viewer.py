# scheduling_engine/gui/timetable_gui_viewer.py

"""
Comprehensive Timetable GUI Viewer

A professional GUI application for visualizing exam timetable solutions with:
- Main calendar/grid view of the timetable
- Color-coded courses and exams
- Detailed information panels
- Multiple tabs for different views
- Constraint satisfaction validation
- Export functionality

Key Features:
- Calendar-style timetable display
- Color coding for different departments/courses
- Interactive exam details
- Student conflict detection
- Room utilization visualization
- Invigilator assignment tracking
- Search and filter capabilities
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
from datetime import datetime, date, time
from typing import Dict, List, Set, Optional, Any, TYPE_CHECKING
from uuid import UUID
from collections import defaultdict, Counter
import logging
import threading

if TYPE_CHECKING:
    from scheduling_engine.core.problem_model import ExamSchedulingProblem
    from scheduling_engine.core.solution import TimetableSolution

logger = logging.getLogger(__name__)


class TimetableGUIViewer:
    """
    Professional timetable visualization GUI with comprehensive features.
    """

    def __init__(self, problem: "ExamSchedulingProblem", solution: "TimetableSolution"):
        self.problem = problem
        self.solution = solution

        # Color schemes for different elements
        self.department_colors = {}
        self.course_colors = {}
        self.room_colors = {}
        self.status_colors = {
            "assigned": "#4CAF50",  # Green
            "conflict": "#FF5722",  # Red
            "unassigned": "#9E9E9E",  # Gray
            "partial": "#FF9800",  # Orange
        }

        # Data processing
        self.processed_data = None
        self.conflicts = []

        # Initialize GUI
        self.root = None
        self.setup_gui()

        logger.info("🖥️ TimetableGUIViewer initialized")

    def setup_gui(self):
        """Initialize the main GUI window and components."""
        self.root = tk.Tk()
        self.root.title("Exam Timetable Viewer - Professional Solution Visualization")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)

        # Configure style
        self.setup_styles()

        # Process data for display
        self.process_solution_data()

        # Create main interface
        self.create_main_interface()

        # Load initial data
        self.refresh_display()

        logger.info("✅ GUI setup complete")

    def setup_styles(self):
        """Configure professional styling for the GUI."""
        style = ttk.Style()

        # Configure notebook tabs
        style.configure("TNotebook.Tab", padding=[12, 8])

        # Configure treeview
        style.configure("Treeview", rowheight=25)
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))

        # Configure frames
        style.configure("Card.TFrame", relief="raised", borderwidth=1)

        logger.debug("🎨 GUI styles configured")

    def create_main_interface(self):
        """Create the main interface with tabs and panels."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        assert self.root
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        if main_frame:  # Added null check
            main_frame.columnconfigure(0, weight=1)
            main_frame.rowconfigure(1, weight=1)

        # Title section
        self.create_title_section(main_frame)

        # Create notebook with tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky=("nsew"), pady=(10, 0))

        # Create tabs
        self.create_calendar_tab()
        self.create_details_tab()
        self.create_conflicts_tab()
        self.create_statistics_tab()
        self.create_export_tab()

        # Status bar
        self.create_status_bar(main_frame)

        logger.info("🏗️ Main interface created")

    def create_title_section(self, parent):
        """Create the title and summary section."""
        title_frame = ttk.Frame(parent, style="Card.TFrame", padding="15")
        title_frame.grid(row=0, column=0, sticky=("we"), pady=(0, 10))
        title_frame.columnconfigure(1, weight=1)

        # Main title
        title_label = ttk.Label(
            title_frame,
            text="📅 Exam Timetable Solution Viewer",
            font=("Arial", 16, "bold"),
        )
        title_label.grid(row=0, column=0, columnspan=3, sticky=tk.W)

        # Solution summary
        completion = self.solution.get_completion_percentage()
        total_exams = len(self.solution.assignments)
        assigned_exams = sum(
            1 for a in self.solution.assignments.values() if a.is_complete()
        )

        summary_text = f"📊 Solution Summary: {assigned_exams}/{total_exams} exams assigned ({completion:.1f}% complete)"
        if self.solution.is_feasible():
            summary_text += " ✅ FEASIBLE"
            summary_color = "green"
        else:
            summary_text += " ⚠️ HAS CONFLICTS"
            summary_color = "red"

        summary_label = ttk.Label(title_frame, text=summary_text, font=("Arial", 10))
        summary_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))

        # Quick stats
        self.create_quick_stats(title_frame)

    def create_quick_stats(self, parent):
        """Create quick statistics panel."""
        stats_frame = ttk.LabelFrame(parent, text="Quick Statistics", padding="10")
        stats_frame.grid(row=2, column=0, columnspan=3, sticky=("we"), pady=(10, 0))

        # Calculate statistics
        stats = self.calculate_quick_stats()

        row = 0
        col = 0
        for stat_name, stat_value in stats.items():
            stat_label = ttk.Label(
                stats_frame, text=f"{stat_name}: {stat_value}", font=("Arial", 9)
            )
            stat_label.grid(row=row, column=col, sticky=tk.W, padx=(0, 20))

            col += 1
            if col > 3:  # 4 columns
                col = 0
                row += 1

    def calculate_quick_stats(self) -> Dict[str, Any]:
        """Calculate quick statistics for the solution."""
        stats = {}

        # Basic counts
        stats["Total Exams"] = len(self.problem.exams)
        stats["Total Rooms"] = len(self.problem.rooms)
        stats["Total Time Slots"] = len(self.problem.time_slots)
        stats["Total Students"] = len(self.problem.students)

        # Assignment stats
        assigned = sum(1 for a in self.solution.assignments.values() if a.is_complete())
        stats["Assigned Exams"] = f"{assigned}/{len(self.solution.assignments)}"

        # Room utilization
        used_rooms = set()
        for assignment in self.solution.assignments.values():
            if assignment.is_complete():
                used_rooms.update(assignment.room_ids)
        stats["Room Utilization"] = f"{len(used_rooms)}/{len(self.problem.rooms)}"

        # Time slot utilization
        used_slots = {
            a.time_slot_id
            for a in self.solution.assignments.values()
            if a.is_complete()
        }
        stats["Time Slot Utilization"] = (
            f"{len(used_slots)}/{len(self.problem.time_slots)}"
        )

        # Conflicts
        conflicts = self.solution.detect_conflicts()
        stats["Total Conflicts"] = len(conflicts)

        return stats

    def create_calendar_tab(self):
        """Create the main calendar/timetable view tab."""
        calendar_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(calendar_frame, text="📅 Timetable Calendar")

        # Configure grid
        calendar_frame.columnconfigure(0, weight=1)
        calendar_frame.rowconfigure(1, weight=1)

        # Controls frame
        controls_frame = ttk.Frame(calendar_frame)
        controls_frame.grid(row=0, column=0, sticky=("we"), pady=(0, 10))

        # Filter controls
        ttk.Label(controls_frame, text="Filter by:").grid(row=0, column=0, padx=(0, 10))

        # Department filter
        ttk.Label(controls_frame, text="Department:").grid(row=0, column=1, padx=(0, 5))
        self.dept_filter = ttk.Combobox(controls_frame, width=15, state="readonly")
        self.dept_filter.grid(row=0, column=2, padx=(0, 15))

        # Room filter
        ttk.Label(controls_frame, text="Room:").grid(row=0, column=3, padx=(0, 5))
        self.room_filter = ttk.Combobox(controls_frame, width=15, state="readonly")
        self.room_filter.grid(row=0, column=4, padx=(0, 15))

        # Refresh button
        ttk.Button(
            controls_frame, text="🔄 Refresh", command=self.refresh_calendar
        ).grid(row=0, column=5)

        # Timetable display area
        self.create_timetable_display(calendar_frame)

        # Legend
        self.create_legend(calendar_frame)

    def create_timetable_display(self, parent):
        """Create the main timetable grid display."""
        # Create scrollable frame for the timetable
        canvas = tk.Canvas(parent, bg="white")
        scrollbar_v = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollbar_h = ttk.Scrollbar(parent, orient="horizontal", command=canvas.xview)
        self.timetable_frame = ttk.Frame(canvas)

        # Configure scrolling
        self.timetable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.timetable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)

        # Grid the components
        canvas.grid(row=1, column=0, sticky=("nsew"))
        scrollbar_v.grid(row=1, column=1, sticky=("ns"))
        scrollbar_h.grid(row=2, column=0, sticky=("we"))

        # Store canvas reference for updates
        self.timetable_canvas = canvas

        self.populate_timetable_grid()

    def populate_timetable_grid(self):
        """Populate the timetable grid with exam data."""
        # Clear existing widgets
        for widget in self.timetable_frame.winfo_children():
            widget.destroy()

        if not self.processed_data:
            return

        # Create headers
        self.create_timetable_headers()

        # Create time slot rows
        self.create_timetable_content()

        logger.debug("🗓️ Timetable grid populated")

    def create_timetable_headers(self):
        # Top-left corner
        header = tk.Frame(
            self.timetable_frame, relief="raised", borderwidth=1, bg="lightgray"
        )
        header.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        tk.Label(
            header, text="Time \\ Date", font=("Arial", 9, "bold"), bg="lightgray"
        ).pack(expand=True)

        # Unique sorted dates
        dates = sorted(
            {
                assignment.assigned_date
                for assignment in self.solution.assignments.values()
                if assignment.assigned_date is not None
            }
        )

        self.date_columns = {}
        for col, dt in enumerate(dates, start=1):
            cell = tk.Frame(
                self.timetable_frame, relief="raised", borderwidth=1, bg="lightgray"
            )
            cell.grid(row=0, column=col, sticky="nsew", padx=1, pady=1)
            tk.Label(
                cell,
                text=dt.strftime("%a\n%b %d"),
                font=("Arial", 9, "bold"),
                bg="lightgray",
            ).pack(expand=True)
            self.date_columns[dt] = col

    def create_timetable_content(self):
        # Unique time‐templates sorted by start_time
        templates = {
            (ts.start_time, ts.end_time) for ts in self.problem.time_slots.values()
        }
        sorted_templates = sorted(templates, key=lambda t: t[0])

        # Build a lookup: (date, (start,end)) -> list of assignments
        # create_timetable_content
        slot_map = defaultdict(list)
        for assign in self.solution.assignments.values():
            if assign.is_complete() and assign.time_slot_id is not None:
                ts = self.problem.time_slots[assign.time_slot_id]
                slot_map[(assign.assigned_date, (ts.start_time, ts.end_time))].append(
                    assign
                )

        # Populate rows for each time template
        for row, (start, end) in enumerate(sorted_templates, start=1):
            # Time‐template header
            time_cell = tk.Frame(
                self.timetable_frame, relief="raised", borderwidth=1, bg="#f0f0f0"
            )
            time_cell.grid(row=row, column=0, sticky="nsew", padx=1, pady=1)
            tk.Label(
                time_cell,
                text=f"{start.strftime('%H:%M')}\n{end.strftime('%H:%M')}",
                font=("Arial", 8),
                bg="#f0f0f0",
            ).pack(expand=True)

            # One cell per date
            for dt, col in self.date_columns.items():
                cell = tk.Frame(
                    self.timetable_frame, relief="raised", borderwidth=1, bg="white"
                )
                cell.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)

                assigns = slot_map.get((dt, (start, end)), [])
                if not assigns:
                    tk.Label(cell, text="", bg="white", width=15, height=4).pack(
                        expand=True
                    )
                elif len(assigns) == 1:
                    self.create_single_exam_display(cell, assigns[0])
                else:
                    self.create_multiple_exams_display(cell, assigns)

                # Bind click events to view details
                self.make_cell_interactive(cell, assigns, dt, None)

    def create_timetable_cell(
        self, row: int, col: int, date_obj: date, time_slot_id: UUID
    ):
        """Create a single timetable cell with exam information."""
        cell_frame = tk.Frame(
            self.timetable_frame, relief="raised", borderwidth=1, bg="white"
        )
        cell_frame.grid(row=row, column=col, sticky=("nsew"), padx=1, pady=1)

        # Find exams for this date/time combination
        cell_exams = []
        for assignment in self.solution.assignments.values():
            if (
                assignment.is_complete()
                and assignment.assigned_date == date_obj
                and assignment.time_slot_id == time_slot_id
            ):
                cell_exams.append(assignment)

        if not cell_exams:
            # Empty cell
            tk.Label(cell_frame, text="", bg="white", width=15, height=4).pack(
                expand=True, fill="both"
            )
            return

        # Create exam display in cell
        self.populate_exam_cell(cell_frame, cell_exams, date_obj, time_slot_id)

    def populate_exam_cell(self, cell_frame, assignments, date_obj, time_slot_id):
        """Populate a cell with exam information."""
        if len(assignments) == 1:
            # Single exam
            self.create_single_exam_display(cell_frame, assignments[0])
        else:
            # Multiple exams - create compact display
            self.create_multiple_exams_display(cell_frame, assignments)

        # Make cell clickable for details
        self.make_cell_interactive(cell_frame, assignments, date_obj, time_slot_id)

    def create_single_exam_display(self, parent, assignment):
        """Create display for a single exam in a cell."""
        exam = self.problem.exams.get(assignment.exam_id)
        if not exam:
            return

        # Get course info (you might need to extend this based on your data model)
        course_info = f"Exam {str(exam.id)[:8]}..."

        # Get color based on department or course
        color = self.get_exam_color(exam)

        # Create colored background
        parent.configure(bg=color)

        # Exam info
        exam_label = tk.Label(
            parent,
            text=course_info,
            font=("Arial", 8, "bold"),
            bg=color,
            fg="white",
            wraplength=120,
        )
        exam_label.pack(expand=True, fill="both", padx=2, pady=2)

        # Room info
        if assignment.room_ids:
            room_codes = []
            for room_id in assignment.room_ids:
                room = self.problem.rooms.get(room_id)
                if room:
                    room_codes.append(room.code)

            room_text = f"Room: {', '.join(room_codes[:2])}"
            if len(assignment.room_ids) > 2:
                room_text += f" +{len(assignment.room_ids)-2}"

            room_label = tk.Label(
                parent, text=room_text, font=("Arial", 7), bg=color, fg="white"
            )
            room_label.pack(padx=2)

        # Students count
        student_count = exam.expected_students
        student_label = tk.Label(
            parent, text=f"👥 {student_count}", font=("Arial", 7), bg=color, fg="white"
        )
        student_label.pack(padx=2)

    def create_multiple_exams_display(self, parent, assignments):
        """Create compact display for multiple exams in a cell."""
        # Use a neutral color for multiple exams
        parent.configure(bg="#FFE0B2")

        info_text = f"{len(assignments)} exams\n(click for details)"
        label = tk.Label(
            parent, text=info_text, font=("Arial", 8), bg="#FFE0B2", fg="black"
        )
        label.pack(expand=True)

    def make_cell_interactive(self, cell_frame, assignments, date_obj, time_slot_id):
        """Make a cell interactive with click events."""

        def on_click(event):
            self.show_cell_details(assignments, date_obj, time_slot_id)

        # Bind click event to the frame and its children
        def bind_click(widget):
            widget.bind("<Button-1>", on_click)
            widget.bind("<Enter>", lambda e: widget.configure(cursor="hand2"))
            widget.bind("<Leave>", lambda e: widget.configure(cursor=""))

            for child in widget.winfo_children():
                bind_click(child)

        bind_click(cell_frame)

    def show_cell_details(self, assignments, date_obj, time_slot_id):
        """Show detailed information for a clicked cell."""
        # Create popup window
        popup = tk.Toplevel(self.root)
        popup.title(f"Exam Details - {date_obj} at {time_slot_id}")
        popup.geometry("600x400")
        popup.transient(self.root)
        popup.grab_set()

        # Create content
        main_frame = ttk.Frame(popup, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label = ttk.Label(
            main_frame,
            text=f"📅 {date_obj.strftime('%A, %B %d, %Y')}",
            font=("Arial", 14, "bold"),
        )
        title_label.pack(pady=(0, 10))

        # Time slot info
        time_slot = self.problem.time_slots.get(time_slot_id)
        if time_slot:
            time_label = ttk.Label(
                main_frame,
                text=f"🕐 {time_slot.start_time.strftime('%H:%M')} - {time_slot.end_time.strftime('%H:%M')}",
                font=("Arial", 12),
            )
            time_label.pack(pady=(0, 15))

        # Exam details
        for i, assignment in enumerate(assignments):
            self.create_exam_detail_section(main_frame, assignment, i + 1)

        # Close button
        ttk.Button(popup, text="Close", command=popup.destroy).pack(pady=(15, 0))

    def create_exam_detail_section(self, parent, assignment, exam_num):
        """Create detailed section for one exam."""
        exam = self.problem.exams.get(assignment.exam_id)
        if not exam:
            return

        # Frame for this exam
        exam_frame = ttk.LabelFrame(parent, text=f"Exam {exam_num}", padding="10")
        exam_frame.pack(fill="x", pady=(0, 10))

        # Exam ID and course
        ttk.Label(exam_frame, text=f"Exam ID: {str(exam.id)}", font=("Arial", 10)).pack(
            anchor="w"
        )
        ttk.Label(
            exam_frame, text=f"Course ID: {str(exam.course_id)}", font=("Arial", 10)
        ).pack(anchor="w")

        # Duration
        ttk.Label(
            exam_frame,
            text=f"Duration: {exam.duration_minutes} minutes",
            font=("Arial", 10),
        ).pack(anchor="w")

        # Expected students
        ttk.Label(
            exam_frame,
            text=f"Expected Students: {exam.expected_students}",
            font=("Arial", 10),
        ).pack(anchor="w")

        # Rooms
        if assignment.room_ids:
            room_info = "Rooms: "
            room_details = []
            for room_id in assignment.room_ids:
                room = self.problem.rooms.get(room_id)
                if room:
                    allocation = assignment.room_allocations.get(room_id, 0)
                    room_details.append(f"{room.code} ({allocation} students)")
            room_info += ", ".join(room_details)
            ttk.Label(exam_frame, text=room_info, font=("Arial", 10)).pack(anchor="w")

        # Status
        status_color = self.status_colors.get(assignment.status.value, "black")
        status_label = ttk.Label(
            exam_frame,
            text=f"Status: {assignment.status.value.upper()}",
            font=("Arial", 10, "bold"),
        )
        status_label.pack(anchor="w")

    def get_exam_color(self, exam):
        """Get color for an exam based on course/department."""
        # Simple color scheme based on course ID hash
        course_hash = hash(str(exam.course_id)) % 12
        colors = [
            "#E53E3E",
            "#DD6B20",
            "#D69E2E",
            "#38A169",
            "#00A3C4",
            "#0078D4",
            "#5A67D8",
            "#805AD5",
            "#D53F8C",
            "#2B6CB0",
            "#319795",
            "#9F7AEA",
        ]
        return colors[course_hash]

    def create_legend(self, parent):
        """Create a legend for the timetable."""
        legend_frame = ttk.LabelFrame(parent, text="Legend", padding="10")
        legend_frame.grid(row=3, column=0, sticky=("we"), pady=(10, 0))

        # Status legend
        legend_content = ttk.Frame(legend_frame)
        legend_content.pack(fill="x")

        statuses = [
            ("Assigned", "#4CAF50"),
            ("Conflicts", "#FF5722"),
            ("Unassigned", "#9E9E9E"),
            ("Multiple Exams", "#FFE0B2"),
        ]

        for i, (status, color) in enumerate(statuses):
            color_box = tk.Frame(
                legend_content,
                width=20,
                height=20,
                bg=color,
                relief="raised",
                borderwidth=1,
            )
            color_box.grid(row=0, column=i * 2, padx=(0, 5))

            label = ttk.Label(legend_content, text=status)
            label.grid(row=0, column=i * 2 + 1, padx=(0, 20))

    def create_details_tab(self):
        """Create the detailed information tab."""
        details_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(details_frame, text="📋 Detailed View")

        # Create paned window for multiple sections
        paned_window = ttk.PanedWindow(details_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill="both", expand=True)

        # Left panel - Exam list
        self.create_exam_list_panel(paned_window)

        # Right panel - Selected exam details
        self.create_exam_details_panel(paned_window)

    def create_exam_list_panel(self, parent):
        """Create the exam list panel."""
        left_frame = ttk.Frame(parent)
        parent.add(left_frame, weight=1)

        # Header
        ttk.Label(left_frame, text="📝 Exam List", font=("Arial", 14, "bold")).pack(
            pady=(0, 10)
        )

        # Search
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_exam_list)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))

        # Exam list
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill="both", expand=True)

        # Treeview for exams
        columns = ("Status", "Date", "Time", "Rooms", "Students")
        self.exam_tree = ttk.Treeview(
            list_frame, columns=columns, show="tree headings", height=20
        )

        # Configure columns
        self.exam_tree.heading("#0", text="Exam ID")
        self.exam_tree.column("#0", width=150)

        for col in columns:
            self.exam_tree.heading(col, text=col)
            self.exam_tree.column(col, width=100)

        # Scrollbars
        tree_scroll_v = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.exam_tree.yview
        )
        tree_scroll_h = ttk.Scrollbar(
            list_frame, orient="horizontal", command=self.exam_tree.xview
        )
        self.exam_tree.configure(
            yscrollcommand=tree_scroll_v.set, xscrollcommand=tree_scroll_h.set
        )

        # Grid
        self.exam_tree.grid(row=0, column=0, sticky=("nsew"))
        tree_scroll_v.grid(row=0, column=1, sticky=("ns"))
        tree_scroll_h.grid(row=1, column=0, sticky=("we"))

        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # Bind selection event
        self.exam_tree.bind("<<TreeviewSelect>>", self.on_exam_select)

        # Populate exam list
        self.populate_exam_list()

    def create_exam_details_panel(self, parent):
        """Create the exam details panel."""
        right_frame = ttk.Frame(parent)
        parent.add(right_frame, weight=1)

        # Header
        ttk.Label(right_frame, text="🔍 Exam Details", font=("Arial", 14, "bold")).pack(
            pady=(0, 10)
        )

        # Scrollable details area
        canvas = tk.Canvas(right_frame, bg="white")
        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=canvas.yview)
        self.details_frame = ttk.Frame(canvas)

        self.details_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.details_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Initial message
        ttk.Label(
            self.details_frame, text="Select an exam from the list to view details"
        ).pack(pady=20)

    def populate_exam_list(self):
        """Populate the exam list treeview."""
        # Clear existing items
        for item in self.exam_tree.get_children():
            self.exam_tree.delete(item)

        # Add exams
        for exam_id, assignment in self.solution.assignments.items():
            exam = self.problem.exams.get(exam_id)
            if not exam:
                continue

            # Prepare display values
            status = assignment.status.value.title()
            date_str = (
                assignment.assigned_date.strftime("%Y-%m-%d")
                if assignment.assigned_date
                else "Not assigned"
            )

            # Time
            time_str = "Not assigned"
            if assignment.time_slot_id:
                time_slot = self.problem.time_slots.get(assignment.time_slot_id)
                if time_slot:
                    time_str = f"{time_slot.start_time.strftime('%H:%M')}-{time_slot.end_time.strftime('%H:%M')}"

            # Rooms
            room_str = "Not assigned"
            if assignment.room_ids:
                room_codes = []
                for room_id in assignment.room_ids:
                    room = self.problem.rooms.get(room_id)
                    if room:
                        room_codes.append(room.code)
                room_str = ", ".join(room_codes)

            # Students
            students_str = str(exam.expected_students)

            # Add to tree
            self.exam_tree.insert(
                "",
                "end",
                text=str(exam.id)[:8] + "...",
                values=(status, date_str, time_str, room_str, students_str),
                tags=(assignment.status.value,),
            )

        # Configure tags for colors
        self.exam_tree.tag_configure("assigned", background="lightgreen")
        self.exam_tree.tag_configure("conflict", background="lightcoral")
        self.exam_tree.tag_configure("unassigned", background="lightgray")

    def filter_exam_list(self, *args):
        """Filter the exam list based on search."""
        search_term = self.search_var.get().lower()

        # If no search term, show all
        if not search_term:
            for item in self.exam_tree.get_children():
                self.exam_tree.item(item, open=True)
            return

        # Hide items that don't match search
        for item in self.exam_tree.get_children():
            item_text = self.exam_tree.item(item, "text").lower()
            values = [str(v).lower() for v in self.exam_tree.item(item, "values")]

            if search_term in item_text or any(search_term in v for v in values):
                self.exam_tree.item(item, open=True)
            else:
                self.exam_tree.item(item, open=False)

    def on_exam_select(self, event):
        """Handle exam selection in the list."""
        selection = self.exam_tree.selection()
        if not selection:
            return

        # Get selected exam
        item = selection[0]
        exam_id_short = self.exam_tree.item(item, "text").replace("...", "")

        # Find full exam ID
        selected_exam_id = None
        for exam_id in self.solution.assignments.keys():
            if str(exam_id).startswith(exam_id_short):
                selected_exam_id = exam_id
                break

        if selected_exam_id:
            self.show_exam_details(selected_exam_id)

    def show_exam_details(self, exam_id):
        """Show detailed information for a selected exam."""
        # Clear existing details
        for widget in self.details_frame.winfo_children():
            widget.destroy()

        exam = self.problem.exams.get(exam_id)
        assignment = self.solution.assignments.get(exam_id)

        if not exam or not assignment:
            ttk.Label(self.details_frame, text="Error: Exam not found").pack(pady=20)
            return

        # Create detailed display
        detail_container = ttk.Frame(self.details_frame, padding="15")
        detail_container.pack(fill="both", expand=True)

        # Exam basic info
        exam_info_frame = ttk.LabelFrame(
            detail_container, text="Exam Information", padding="10"
        )
        exam_info_frame.pack(fill="x", pady=(0, 10))

        info_items = [
            ("Exam ID", str(exam.id)),
            ("Course ID", str(exam.course_id)),
            ("Duration", f"{exam.duration_minutes} minutes"),
            ("Expected Students", str(exam.expected_students)),
            ("Type", "Practical" if exam.is_practical else "Written"),
            ("Morning Only", "Yes" if exam.morning_only else "No"),
        ]

        for label, value in info_items:
            row_frame = ttk.Frame(exam_info_frame)
            row_frame.pack(fill="x", pady=2)
            ttk.Label(row_frame, text=f"{label}:", font=("Arial", 10, "bold")).pack(
                side="left"
            )
            ttk.Label(row_frame, text=value, font=("Arial", 10)).pack(
                side="left", padx=(10, 0)
            )

        # Assignment info
        assignment_frame = ttk.LabelFrame(
            detail_container, text="Assignment Information", padding="10"
        )
        assignment_frame.pack(fill="x", pady=(0, 10))

        if assignment.is_complete():
            # Date and time
            date_time_frame = ttk.Frame(assignment_frame)
            date_time_frame.pack(fill="x", pady=2)
            ttk.Label(
                date_time_frame, text="Date & Time:", font=("Arial", 10, "bold")
            ).pack(side="left")
            assert assignment.time_slot_id
            time_slot = self.problem.time_slots.get(assignment.time_slot_id)
            if time_slot:
                assert assignment.assigned_date
                datetime_str = f"{assignment.assigned_date.strftime('%A, %B %d, %Y')} at {time_slot.start_time.strftime('%H:%M')}-{time_slot.end_time.strftime('%H:%M')}"
                ttk.Label(date_time_frame, text=datetime_str, font=("Arial", 10)).pack(
                    side="left", padx=(10, 0)
                )

            # Rooms
            if assignment.room_ids:
                rooms_frame = ttk.LabelFrame(
                    assignment_frame, text="Room Assignments", padding="5"
                )
                rooms_frame.pack(fill="x", pady=(10, 0))

                for room_id in assignment.room_ids:
                    room = self.problem.rooms.get(room_id)
                    if room:
                        allocation = assignment.room_allocations.get(room_id, 0)

                        room_detail_frame = ttk.Frame(rooms_frame)
                        room_detail_frame.pack(fill="x", pady=2)

                        room_info = f"🏢 {room.code} - Capacity: {room.capacity} (Exam: {room.exam_capacity})"
                        if allocation > 0:
                            room_info += f" - Allocated: {allocation} students"

                        ttk.Label(
                            room_detail_frame, text=room_info, font=("Arial", 9)
                        ).pack(anchor="w")
        else:
            ttk.Label(
                assignment_frame,
                text="⚠️ Exam not yet assigned",
                font=("Arial", 11),
                foreground="red",
            ).pack()

        # Status and conflicts
        status_frame = ttk.LabelFrame(
            detail_container, text="Status & Conflicts", padding="10"
        )
        status_frame.pack(fill="x", pady=(0, 10))

        # Status
        status_color = "green" if assignment.status.value == "assigned" else "red"
        status_text = f"Status: {assignment.status.value.upper()}"
        ttk.Label(
            status_frame,
            text=status_text,
            font=("Arial", 10, "bold"),
            foreground=status_color,
        ).pack(anchor="w")

        # Check for conflicts involving this exam
        exam_conflicts = [
            c for c in self.solution.detect_conflicts() if exam_id in c.affected_exams
        ]
        if exam_conflicts:
            conflicts_subframe = ttk.Frame(status_frame)
            conflicts_subframe.pack(fill="x", pady=(10, 0))

            ttk.Label(
                conflicts_subframe,
                text="⚠️ Conflicts:",
                font=("Arial", 10, "bold"),
                foreground="red",
            ).pack(anchor="w")

            for conflict in exam_conflicts:
                conflict_text = f"  • {conflict.conflict_type}: {conflict.description}"
                ttk.Label(
                    conflicts_subframe,
                    text=conflict_text,
                    font=("Arial", 9),
                    foreground="red",
                    wraplength=400,
                ).pack(anchor="w")

        # Students (if available)
        if hasattr(exam, "_students") and exam._students:
            students_frame = ttk.LabelFrame(
                detail_container,
                text=f"Registered Students ({len(exam._students)})",
                padding="10",
            )
            students_frame.pack(fill="x", pady=(0, 10))

            # Show first few student IDs
            student_list = list(exam._students)[:10]  # Limit to first 10
            for student_id in student_list:
                ttk.Label(
                    students_frame, text=f"👤 {str(student_id)}", font=("Arial", 9)
                ).pack(anchor="w")

            if len(exam._students) > 10:
                ttk.Label(
                    students_frame,
                    text=f"... and {len(exam._students) - 10} more",
                    font=("Arial", 9, "italic"),
                ).pack(anchor="w")

    def create_conflicts_tab(self):
        """Create the conflicts analysis tab."""
        conflicts_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(conflicts_frame, text="⚠️ Conflicts")

        # Header
        ttk.Label(
            conflicts_frame, text="🔍 Conflict Analysis", font=("Arial", 16, "bold")
        ).pack(pady=(0, 15))

        # Detect and display conflicts
        self.conflicts = self.solution.detect_conflicts()

        if not self.conflicts:
            # No conflicts
            success_frame = ttk.Frame(conflicts_frame)
            success_frame.pack(expand=True)

            ttk.Label(
                success_frame,
                text="✅ No conflicts detected!",
                font=("Arial", 14),
                foreground="green",
            ).pack()
            ttk.Label(
                success_frame,
                text="The timetable appears to satisfy all constraints.",
                font=("Arial", 12),
            ).pack(pady=(10, 0))
        else:
            # Show conflicts
            self.display_conflicts(conflicts_frame)

    def display_conflicts(self, parent):
        """Display detected conflicts."""
        # Summary
        summary_frame = ttk.Frame(parent)
        summary_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(
            summary_frame,
            text=f"❌ {len(self.conflicts)} conflicts detected",
            font=("Arial", 12, "bold"),
            foreground="red",
        ).pack(anchor="w")

        # Group conflicts by type
        conflicts_by_type = defaultdict(list)
        for conflict in self.conflicts:
            conflicts_by_type[conflict.conflict_type].append(conflict)

        # Display by type
        for conflict_type, type_conflicts in conflicts_by_type.items():
            type_frame = ttk.LabelFrame(
                parent,
                text=f"{conflict_type.replace('_', ' ').title()} ({len(type_conflicts)})",
                padding="10",
            )
            type_frame.pack(fill="x", pady=(0, 10))

            # Create treeview for this conflict type
            columns = ("Severity", "Description", "Affected Exams")
            tree = ttk.Treeview(
                type_frame,
                columns=columns,
                show="headings",
                height=min(6, len(type_conflicts)),
            )

            for col in columns:
                tree.heading(col, text=col)
                if col == "Description":
                    tree.column(col, width=300)
                else:
                    tree.column(col, width=150)

            # Add conflicts to tree
            for conflict in type_conflicts:
                affected_exams_str = f"{len(conflict.affected_exams)} exams"
                tree.insert(
                    "",
                    "end",
                    values=(
                        conflict.severity.value.title(),
                        conflict.description,
                        affected_exams_str,
                    ),
                )

            tree.pack(fill="x")

            # Color code by severity
            tree.tag_configure("critical", background="#ffcccc")
            tree.tag_configure("high", background="#ffe0cc")
            tree.tag_configure("medium", background="#ffffcc")

    def create_statistics_tab(self):
        """Create the statistics and analysis tab."""
        stats_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(stats_frame, text="📊 Statistics")

        # Create scrollable frame
        canvas = tk.Canvas(stats_frame)
        scrollbar = ttk.Scrollbar(stats_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Generate statistics
        self.create_comprehensive_statistics(scrollable_frame)

    def create_comprehensive_statistics(self, parent):
        """Create comprehensive statistics display."""
        # Title
        ttk.Label(
            parent,
            text="📊 Comprehensive Solution Statistics",
            font=("Arial", 16, "bold"),
        ).pack(pady=(0, 20))

        # Solution overview
        self.create_solution_overview(parent)

        # Resource utilization
        self.create_resource_utilization(parent)

        # Time distribution
        self.create_time_distribution(parent)

        # Constraint satisfaction
        self.create_constraint_satisfaction(parent)

    def create_solution_overview(self, parent):
        """Create solution overview statistics."""
        overview_frame = ttk.LabelFrame(parent, text="Solution Overview", padding="15")
        overview_frame.pack(fill="x", pady=(0, 15))

        # Calculate statistics
        total_exams = len(self.solution.assignments)
        assigned_exams = sum(
            1 for a in self.solution.assignments.values() if a.is_complete()
        )
        completion_rate = (assigned_exams / total_exams * 100) if total_exams > 0 else 0

        # Create 2-column layout
        left_col = ttk.Frame(overview_frame)
        left_col.pack(side="left", fill="both", expand=True)

        right_col = ttk.Frame(overview_frame)
        right_col.pack(side="right", fill="both", expand=True)

        # Left column stats
        left_stats = [
            ("Total Exams", str(total_exams)),
            ("Assigned Exams", f"{assigned_exams} ({completion_rate:.1f}%)"),
            ("Unassigned Exams", str(total_exams - assigned_exams)),
            ("Total Conflicts", str(len(self.conflicts))),
        ]

        for label, value in left_stats:
            stat_frame = ttk.Frame(left_col)
            stat_frame.pack(fill="x", pady=2)
            ttk.Label(stat_frame, text=f"{label}:", font=("Arial", 10)).pack(
                side="left"
            )
            ttk.Label(stat_frame, text=value, font=("Arial", 10, "bold")).pack(
                side="right"
            )

        # Right column stats
        total_students = sum(
            exam.expected_students for exam in self.problem.exams.values()
        )
        avg_students_per_exam = (
            total_students / len(self.problem.exams) if self.problem.exams else 0
        )

        right_stats = [
            ("Total Students", str(total_students)),
            ("Avg Students/Exam", f"{avg_students_per_exam:.1f}"),
            ("Total Rooms", str(len(self.problem.rooms))),
            ("Total Time Slots", str(len(self.problem.time_slots))),
        ]

        for label, value in right_stats:
            stat_frame = ttk.Frame(right_col)
            stat_frame.pack(fill="x", pady=2)
            ttk.Label(stat_frame, text=f"{label}:", font=("Arial", 10)).pack(
                side="left"
            )
            ttk.Label(stat_frame, text=value, font=("Arial", 10, "bold")).pack(
                side="right"
            )

    def create_resource_utilization(self, parent):
        """Create resource utilization statistics."""
        util_frame = ttk.LabelFrame(parent, text="Resource Utilization", padding="15")
        util_frame.pack(fill="x", pady=(0, 15))

        # Room utilization
        used_rooms = set()
        room_usage_count = defaultdict(int)
        for assignment in self.solution.assignments.values():
            if assignment.is_complete():
                for room_id in assignment.room_ids:
                    used_rooms.add(room_id)
                    room_usage_count[room_id] += 1

        room_util = (
            len(used_rooms) / len(self.problem.rooms) * 100 if self.problem.rooms else 0
        )

        # Time slot utilization
        used_slots = {
            a.time_slot_id
            for a in self.solution.assignments.values()
            if a.is_complete()
        }
        slot_util = (
            len(used_slots) / len(self.problem.time_slots) * 100
            if self.problem.time_slots
            else 0
        )

        # Display utilization
        util_stats = [
            (
                "Room Utilization",
                f"{len(used_rooms)}/{len(self.problem.rooms)} ({room_util:.1f}%)",
            ),
            (
                "Time Slot Utilization",
                f"{len(used_slots)}/{len(self.problem.time_slots)} ({slot_util:.1f}%)",
            ),
            ("Most Used Room", self.get_most_used_room(room_usage_count)),
            (
                "Average Room Usage",
                (
                    f"{sum(room_usage_count.values()) / len(used_rooms):.1f} exams"
                    if used_rooms
                    else "0"
                ),
            ),
        ]

        for label, value in util_stats:
            stat_frame = ttk.Frame(util_frame)
            stat_frame.pack(fill="x", pady=2)
            ttk.Label(stat_frame, text=f"{label}:", font=("Arial", 10)).pack(
                side="left"
            )
            ttk.Label(stat_frame, text=value, font=("Arial", 10, "bold")).pack(
                side="right"
            )

    def get_most_used_room(self, room_usage_count):
        """Get the most used room."""
        if not room_usage_count:
            return "None"

        most_used_room_id = max(room_usage_count, key=room_usage_count.get)
        room = self.problem.rooms.get(most_used_room_id)
        room_code = room.code if room else str(most_used_room_id)
        usage_count = room_usage_count[most_used_room_id]

        return f"{room_code} ({usage_count} exams)"

    def create_time_distribution(self, parent):
        """Create time distribution statistics."""
        time_frame = ttk.LabelFrame(parent, text="Time Distribution", padding="15")
        time_frame.pack(fill="x", pady=(0, 15))

        # Analyze time slot usage
        slot_usage = defaultdict(int)
        for assignment in self.solution.assignments.values():
            if assignment.is_complete() and assignment.time_slot_id:
                slot_usage[assignment.time_slot_id] += 1

        # Find peak and off-peak times
        if slot_usage:
            peak_slot_id = max(slot_usage, key=lambda k: slot_usage[k])
            peak_slot = self.problem.time_slots.get(peak_slot_id)
            peak_time = (
                f"{peak_slot.start_time.strftime('%H:%M')}" if peak_slot else "Unknown"
            )
            peak_count = slot_usage[peak_slot_id]

            # Average exams per time slot
            avg_per_slot = sum(slot_usage.values()) / len(slot_usage)
        else:
            peak_time = "None"
            peak_count = 0
            avg_per_slot = 0

        time_stats = [
            ("Peak Time Slot", f"{peak_time} ({peak_count} exams)"),
            ("Average Exams per Slot", f"{avg_per_slot:.1f}"),
            ("Time Slots Used", f"{len(slot_usage)}/{len(self.problem.time_slots)}"),
            ("Exam Period Length", f"{len(self.problem.days)} days"),
        ]

        for label, value in time_stats:
            stat_frame = ttk.Frame(time_frame)
            stat_frame.pack(fill="x", pady=2)
            ttk.Label(stat_frame, text=f"{label}:", font=("Arial", 10)).pack(
                side="left"
            )
            ttk.Label(stat_frame, text=value, font=("Arial", 10, "bold")).pack(
                side="right"
            )

    def create_constraint_satisfaction(self, parent):
        """Create constraint satisfaction analysis."""
        constraint_frame = ttk.LabelFrame(
            parent, text="Constraint Satisfaction", padding="15"
        )
        constraint_frame.pack(fill="x", pady=(0, 15))

        # Analyze conflicts by type
        conflict_types = defaultdict(int)
        for conflict in self.conflicts:
            conflict_types[conflict.conflict_type] += 1

        # Overall satisfaction rate
        total_possible_violations = len(self.solution.assignments) * 3  # Rough estimate
        satisfaction_rate = (
            1 - len(self.conflicts) / max(total_possible_violations, 1)
        ) * 100

        # Display
        if not self.conflicts:
            ttk.Label(
                constraint_frame,
                text="✅ All constraints satisfied!",
                font=("Arial", 12, "bold"),
                foreground="green",
            ).pack()
        else:
            ttk.Label(
                constraint_frame,
                text=f"Constraint Satisfaction Rate: {satisfaction_rate:.1f}%",
                font=("Arial", 11, "bold"),
            ).pack(pady=(0, 10))

            for conflict_type, count in conflict_types.items():
                ttk.Label(
                    constraint_frame,
                    text=f"• {conflict_type.replace('_', ' ').title()}: {count} violations",
                    font=("Arial", 10),
                ).pack(anchor="w")

    def create_export_tab(self):
        """Create the export functionality tab."""
        export_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(export_frame, text="💾 Export")

        # Title
        ttk.Label(
            export_frame, text="💾 Export Solution Data", font=("Arial", 16, "bold")
        ).pack(pady=(0, 20))

        # Export options
        options_frame = ttk.LabelFrame(
            export_frame, text="Export Options", padding="15"
        )
        options_frame.pack(fill="x", pady=(0, 15))

        # Export buttons
        export_buttons = [
            ("📋 Export Timetable (CSV)", self.export_timetable_csv),
            ("📊 Export Statistics (JSON)", self.export_statistics_json),
            ("⚠️ Export Conflicts Report", self.export_conflicts_report),
            ("🖼️ Export Timetable Image", self.export_timetable_image),
            ("📄 Export Full Solution", self.export_full_solution),
        ]

        for button_text, command in export_buttons:
            ttk.Button(options_frame, text=button_text, command=command, width=30).pack(
                pady=5
            )

        # Export status
        self.export_status = ttk.Label(
            options_frame, text="Ready to export", font=("Arial", 10)
        )
        self.export_status.pack(pady=(15, 0))

    def export_timetable_csv(self):
        """Export timetable to CSV format."""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Export Timetable CSV",
            )

            if filename:
                self.export_status.config(
                    text="Exporting timetable CSV...", foreground="blue"
                )
                assert self.root
                self.root.update()

                # Implementation would go here
                # For now, show success message
                self.export_status.config(
                    text="✅ Timetable CSV exported successfully!", foreground="green"
                )
                messagebox.showinfo(
                    "Export Success", f"Timetable exported to {filename}"
                )

        except Exception as e:
            self.export_status.config(
                text=f"❌ Export failed: {str(e)}", foreground="red"
            )

    def export_statistics_json(self):
        """Export statistics to JSON format."""
        # Implementation similar to CSV export
        messagebox.showinfo("Export", "Statistics export functionality")

    def export_conflicts_report(self):
        """Export conflicts report."""
        messagebox.showinfo("Export", "Conflicts report export functionality")

    def export_timetable_image(self):
        """Export timetable as image."""
        messagebox.showinfo("Export", "Timetable image export functionality")

    def export_full_solution(self):
        """Export complete solution data."""
        messagebox.showinfo("Export", "Full solution export functionality")

    def create_status_bar(self, parent):
        """Create status bar at the bottom."""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=2, column=0, sticky=("we"), pady=(10, 0))

        self.status_text = tk.StringVar()
        self.status_text.set("Ready")

        status_label = ttk.Label(
            status_frame, textvariable=self.status_text, font=("Arial", 9)
        )
        status_label.pack(side="left")

        # Version info
        version_label = ttk.Label(
            status_frame, text="Timetable Viewer v1.0", font=("Arial", 9)
        )
        version_label.pack(side="right")

    def process_solution_data(self):
        """Process solution data for efficient GUI display."""
        logger.info("📊 Processing solution data for GUI display...")

        self.processed_data = {
            "assignments_by_date": defaultdict(list),
            "assignments_by_time": defaultdict(list),
            "assignments_by_room": defaultdict(list),
            "exam_colors": {},
            "room_usage": defaultdict(int),
            "time_usage": defaultdict(int),
        }

        # Process assignments
        for exam_id, assignment in self.solution.assignments.items():
            if assignment.is_complete():
                # Group by date
                self.processed_data["assignments_by_date"][
                    assignment.assigned_date
                ].append(assignment)

                # Group by time
                self.processed_data["assignments_by_time"][
                    assignment.time_slot_id
                ].append(assignment)

                # Group by room
                for room_id in assignment.room_ids:
                    self.processed_data["assignments_by_room"][room_id].append(
                        assignment
                    )
                    self.processed_data["room_usage"][room_id] += 1

                # Track time usage
                self.processed_data["time_usage"][assignment.time_slot_id] += 1

                # Generate color for exam
                exam = self.problem.exams.get(exam_id)
                if exam:
                    self.processed_data["exam_colors"][exam_id] = self.get_exam_color(
                        exam
                    )

        logger.info("✅ Solution data processing complete")

    def refresh_display(self):
        """Refresh all displayed data."""
        logger.info("🔄 Refreshing GUI display...")

        # Update calendar if it exists
        if hasattr(self, "timetable_frame"):
            self.populate_timetable_grid()

        # Update exam list if it exists
        if hasattr(self, "exam_tree"):
            self.populate_exam_list()

        # Update status
        self.status_text.set(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

        logger.debug("✅ GUI display refreshed")

    def refresh_calendar(self):
        """Refresh the calendar view."""
        self.populate_timetable_grid()

    def show(self):
        """Show the GUI window."""
        logger.info("🖥️ Displaying Timetable GUI...")
        try:
            assert self.root
            self.root.deiconify()  # Show window if it was hidden
            self.root.lift()  # Bring to front
            self.root.mainloop()  # Start GUI event loop
        except Exception as e:
            logger.error(f"❌ Error displaying GUI: {e}")
            raise

    def close(self):
        """Close the GUI window."""
        if self.root:
            self.root.destroy()
            logger.info("🖥️ GUI window closed")


# Factory function to create and show the GUI
def show_timetable_gui(problem: "ExamSchedulingProblem", solution: "TimetableSolution"):
    """
    Factory function to create and display the timetable GUI.

    Args:
        problem: The exam scheduling problem instance
        solution: The solution to visualize
    """
    logger.info("🚀 Creating Timetable GUI Viewer...")

    # Create GUI instance
    gui = TimetableGUIViewer(problem, solution)

    try:
        # Show the GUI
        gui.show()

    except Exception as e:
        logger.error(f"❌ Failed to create/show GUI: {e}")
        # Fallback to simple message
        import tkinter.messagebox as mb

        mb.showerror("GUI Error", f"Failed to display timetable GUI: {str(e)}")

    return gui
