#C:\Users\fresh\OneDrive\Dokumen\thesis\proj\CODE\adaptive-exam-timetabling\backend\app\services\export\csv_exporter.py
import csv
import io
from typing import List, Dict, Any

class CSVExporter:
    """Exports data to CSV format."""

    def __init__(self, fieldnames: List[str]):
        self.fieldnames = fieldnames

    def export(self, rows: List[Dict[str, Any]]) -> bytes:
        """Return CSV bytes for the given rows."""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=self.fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in self.fieldnames})
        return output.getvalue().encode("utf-8")
