from io import BytesIO
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

class PDFGenerator:
    """Generates simple tabular PDFs."""

    def __init__(self, title: str = "Report"):
        self.title = title

    def generate(self, rows: List[Dict[str, Any]], columns: List[str]) -> bytes:
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        p.setFont("Helvetica-Bold", 16)
        p.drawString(40, height - 40, self.title)
        p.setFont("Helvetica", 10)
        y = height - 60
        # Header
        for idx, col in enumerate(columns):
            p.drawString(40 + idx*100, y, col)
        y -= 20
        # Rows
        for row in rows:
            for idx, col in enumerate(columns):
                text = str(row.get(col, ""))
                p.drawString(40 + idx*100, y, text)
            y -= 15
            if y < 40:
                p.showPage()
                y = height - 40
        p.save()
        buffer.seek(0)
        return buffer.read()
