# C:\Users\fresh\OneDrive\Dokumen\thesis\proj\CODE\adaptive-exam-timetabling\backend\app\services\export\report_builder.py
from typing import List, Dict, Any, Literal, Optional

from .csv_exporter import CSVExporter
from .pdf_generator import PDFGenerator

# Define supported output formats using Literal for better type hinting
ReportFormat = Literal["csv", "pdf"]


class ReportBuilder:
    """
    A factory and builder for generating reports in various formats (e.g., CSV, PDF).

    This class acts as a high-level service that abstracts the details of
    specific file format generators. It can be easily extended to support
    new formats.
    """

    def __init__(self):
        """Initializes the ReportBuilder and registers available builders."""
        self._builders = {
            "csv": self._build_csv_internal,
            "pdf": self._build_pdf_internal,
        }

    def build(
        self,
        output_format: ReportFormat,
        rows: List[Dict[str, Any]],
        columns: List[str],
        title: str = "Report",
        template: Optional[str] = "table",
    ) -> bytes:
        """
        Builds a report in the specified format using the provided data.

        This is the primary factory method for generating reports.

        Args:
            output_format: The desired output format ('csv' or 'pdf').
            rows: A list of dictionaries, where each dictionary represents a row.
            columns: A list of strings representing the column headers and order.
            title: The title of the report (primarily used for PDFs).
            template: The template to use for the report, e.g., 'table' or 'timetable' (for PDFs).

        Returns:
            The generated report as bytes.

        Raises:
            ValueError: If the specified output_format is unsupported.
        """
        builder_func = self._builders.get(output_format.lower())
        if not builder_func:
            raise ValueError(f"Unsupported report format: {output_format}")

        return builder_func(rows=rows, columns=columns, title=title, template=template)

    def _build_csv_internal(
        self, rows: List[Dict[str, Any]], columns: List[str], **kwargs
    ) -> bytes:
        """Internal method to handle CSV generation."""
        exporter = CSVExporter(fieldnames=columns)
        return exporter.export(rows)

    def _build_pdf_internal(
        self,
        rows: List[Dict[str, Any]],
        columns: List[str],
        title: str,
        template: Optional[str],
        **kwargs,
    ) -> bytes:
        """Internal method to handle PDF generation."""
        generator = PDFGenerator(title=title)
        return generator.generate(
            rows=rows, columns=columns, template=template or "table"
        )

    # --- Convenience methods for backward compatibility ---

    def build_csv(self, rows: List[Dict[str, Any]], columns: List[str]) -> bytes:
        """
        Builds a CSV report.

        Note: This is a convenience method. The primary `build` method is preferred.
        """
        return self.build(output_format="csv", rows=rows, columns=columns)

    def build_pdf(
        self,
        rows: List[Dict[str, Any]],
        columns: List[str],
        title: str,
        template: str = "table",
    ) -> bytes:
        """
        Builds a PDF report.

        Note: This is a convenience method. The primary `build` method is preferred.

        Args:
            rows: A list of dictionaries representing the data rows.
            columns: A list of strings for the column headers.
            title: The title of the PDF document.
            template: The PDF template to use ('table' or 'timetable').
        """
        return self.build(
            output_format="pdf",
            rows=rows,
            columns=columns,
            title=title,
            template=template,
        )
