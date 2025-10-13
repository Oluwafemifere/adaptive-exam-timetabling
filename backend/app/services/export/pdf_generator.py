# C:\Users\fresh\OneDrive\Dokumen\thesis\proj\CODE\adaptive-exam-timetabling\backend\app\services\export\pdf_generator.py
import io
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime
import jinja2
from weasyprint import HTML
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# --- START OF FIX ---
# A dedicated HTML template for the timetable view. In a real application,
# this would be in a separate .html file.
TIMETABLE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        @page {
            size: landscape;
            margin: 0.5in;
        }
        body {
            font-family: 'Helvetica', 'Arial', sans-serif;
            color: #333;
        }
        h1 {
            font-size: 20pt;
            text-align: center;
            margin-bottom: 20px;
        }
        .timetable {
            display: grid;
            grid-template-columns: 120px repeat(11, 1fr); /* Date column + 11 hours (8am to 7pm) */
            grid-auto-rows: minmax(60px, auto);
            border: 1px solid #ddd;
        }
        .header {
            font-weight: bold;
            text-align: center;
            padding: 10px;
            border-bottom: 1px solid #ddd;
            border-right: 1px solid #ddd;
            background-color: #f8f9fa;
        }
        .group-header {
            grid-column: 1 / -1;
            font-size: 14pt;
            font-weight: bold;
            padding: 15px 10px;
            background-color: #e9ecef;
            border-top: 2px solid #333;
            border-bottom: 1px solid #ddd;
            /* Explicitly place the group header in its calculated row */
            grid-row: var(--row);
        }
        .date-cell {
            padding: 10px;
            font-weight: bold;
            border-right: 1px solid #ddd;
            border-bottom: 1px solid #ddd;
            /* Explicitly place the date cell in column 1 of its calculated row range */
            grid-column: 1;
            grid-row-start: var(--row-start);
            grid-row-end: span var(--row-span);
        }
        .event-cell {
            grid-column-start: var(--start-col);
            grid-column-end: var(--end-col);
            grid-row-start: var(--row);
            margin: 2px;
            padding: 5px;
            border-radius: 4px;
            background-color: var(--bg-color);
            color: #fff;
            font-size: 9pt;
            overflow: hidden;
        }
        .event-cell b {
            font-size: 10pt;
        }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    <div class="timetable">
        <!-- Time Headers (occupy row 1) -->
        <div class="header"></div>
        {% for hour in range(8, 19) %}
        <div class="header">{{ hour }}:00</div>
        {% endfor %}

        {% set colors = ['#6495ED', '#4682B4', '#B0C4DE', '#ADD8E6', '#87CEEB', '#87CEFA', '#00BFFF', '#1E90FF'] %}
        {% set color_map = {} %}
        {% set color_idx = [0] %}

        {# Use a mutable list as a global row counter, starting after the header row #}
        {% set current_row = [2] %}

        {% for group, events_by_date in grouped_data.items() %}
            {# Place the group header and increment the row counter #}
            <div class="group-header" style="--row: {{ current_row[0] }};">{{ group }}</div>
            {% if current_row.append(current_row.pop() + 1) %}{% endif %}

            {% if color_map.get(group) is none %}
                {% if color_idx.append(color_idx.pop() + 1) %}{% endif %}
                {% if color_map.update({group: colors[color_idx[0] % colors|length]}) %}{% endif %}
            {% endif %}
            
            {% for date, events in events_by_date.items() %}
                {# Place the date cell, specifying its start row and span #}
                <div class="date-cell" style="
                    --row-start: {{ current_row[0] }};
                    --row-span: {{ events|length }};
                ">{{ date }}</div>

                {# Place each event in its own calculated row #}
                {% for event in events %}
                <div class="event-cell" style="
                    --start-col: {{ event.start_col }}; 
                    --end-col: {{ event.end_col }};
                    --row: {{ current_row[0] + loop.index0 }};
                    --bg-color: {{ color_map[group] }};
                ">
                    <b>{{ event.course_code }}</b><br>
                    {{ event.course_title }}<br>
                    {{ event.start_time }} - {{ event.end_time }}
                </div>
                {% endfor %}

                {# After processing all events for a date, advance the main row counter #}
                {% if current_row.append(current_row.pop() + events|length) %}{% endif %}
            {% endfor %}
        {% endfor %}
    </div>
</body>
</html>
"""
# --- END OF FIX ---


class PDFGenerator:
    """Generates visually appealing PDFs for timetables and simple tabular reports."""

    def __init__(self, title: str = "Report"):
        self.title = title
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FunctionLoader(lambda name: TIMETABLE_TEMPLATE)
        )

    def _generate_timetable_view(self, rows: List[Dict[str, Any]]) -> bytes:
        """Generates a PDF with a modern, grid-based timetable layout using HTML and CSS."""

        # Group data by faculty/department and then by date
        grouped_data = defaultdict(lambda: defaultdict(list))
        for row in rows:
            group_key = f"{row.get('faculty_name', 'Uncategorized')} => {row.get('department_name', '')}"
            date_key = datetime.strptime(row["date"], "%Y-%m-%d").strftime("%d-%B-%Y")
            grouped_data[group_key][date_key].append(row)

        # Process events to calculate their grid position
        for group, events_by_date in grouped_data.items():
            for date, events in events_by_date.items():
                for event in events:
                    start_time = datetime.strptime(
                        event["start_time"], "%H:%M:%S"
                    ).time()
                    end_time = datetime.strptime(event["end_time"], "%H:%M:%S").time()

                    # Calculate grid column based on time (8am = col 2, 7pm = col 12)
                    event["start_col"] = (
                        2 + (start_time.hour - 8) + (start_time.minute / 60)
                    )
                    event["end_col"] = 2 + (end_time.hour - 8) + (end_time.minute / 60)

        # Render the HTML template
        template = self.jinja_env.get_template("timetable.html")
        html_str = template.render(title=self.title, grouped_data=grouped_data)

        # Generate PDF from HTML
        assert html_str is not None
        pdf_bytes = HTML(string=html_str).write_pdf()
        return pdf_bytes or b""

    def _generate_table_view(
        self, rows: List[Dict[str, Any]], columns: List[str]
    ) -> bytes:
        """Generates a simple tabular PDF for generic reports (backward compatibility)."""
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        p.setFont("Helvetica-Bold", 16)
        p.drawString(40, height - 40, self.title)
        p.setFont("Helvetica", 10)
        y = height - 60
        for idx, col in enumerate(columns):
            p.drawString(40 + idx * 100, y, col)
        y -= 20
        for row in rows:
            for idx, col in enumerate(columns):
                p.drawString(40 + idx * 100, y, str(row.get(col, "")))
            y -= 15
            if y < 40:
                p.showPage()
                y = height - 40
        p.save()
        buffer.seek(0)
        return buffer.getvalue()

    def generate(
        self,
        rows: List[Dict[str, Any]],
        columns: List[str],
        template: str = "table",
    ) -> bytes:
        """
        Delegates PDF generation to the appropriate method based on the template.
        """
        if template == "timetable" and rows:
            return self._generate_timetable_view(rows)
        else:
            return self._generate_table_view(rows, columns)
