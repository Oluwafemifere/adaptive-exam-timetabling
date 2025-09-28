# backend/app/api/v1/routes/timetables.py
"""
API endpoints for retrieving and managing generated timetables.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_retrieval.unified_data_retrieval import UnifiedDataService
from ....services.export.reporting_service import ReportingService
from fastapi.responses import StreamingResponse
import io

router = APIRouter()


@router.get(
    "/versions/{version_id}",
    summary="Get a specific timetable version",
    description="Retrieves the full data for a generated timetable version, including all assignments.",
)
async def get_timetable_version(
    version_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
) -> Dict[str, Any]:
    """Get a fully structured timetable version by its ID."""
    try:
        service = UnifiedDataService(db)
        timetable = await service.get_full_timetable(version_id)
        if not timetable:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timetable version not found.",
            )
        return {
            "success": True,
            "message": "Timetable data retrieved successfully.",
            "data": timetable,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve timetable: {str(e)}",
        )


@router.get(
    "/versions/{version_id}/download/{file_format}",
    summary="Download timetable report",
    description="Generates and downloads a timetable report in PDF or CSV format.",
)
async def download_timetable_report(
    version_id: UUID,
    file_format: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Download a timetable version as a PDF or CSV file."""
    if file_format.lower() not in ["pdf", "csv"]:
        raise HTTPException(
            status_code=400, detail="Unsupported file format. Use 'pdf' or 'csv'."
        )

    try:
        service = ReportingService(db)
        report_bytes = await service.generate_full_timetable_report(
            version_id, file_format
        )

        if not report_bytes:
            raise HTTPException(
                status_code=404,
                detail="Could not generate report. Timetable version may not exist or has no data.",
            )

        media_type = "application/pdf" if file_format == "pdf" else "text/csv"
        filename = f"timetable_version_{version_id}.{file_format}"

        return StreamingResponse(
            io.BytesIO(report_bytes),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )
