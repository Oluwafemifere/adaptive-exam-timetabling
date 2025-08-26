from typing import List, Dict, Any
from app.services.export.csv_exporter import CSVExporter
from app.services.export.pdf_generator import PDFGenerator

class ReportBuilder:
    """High-level service to produce CSV or PDF reports."""

    def build_csv(self, rows: List[Dict[str, Any]], columns: List[str]) -> bytes:
        exporter = CSVExporter(columns)
        return exporter.export(rows)

    def build_pdf(self, rows: List[Dict[str, Any]], columns: List[str], title: str) -> bytes:
        generator = PDFGenerator(title)
        return generator.generate(rows, columns)
