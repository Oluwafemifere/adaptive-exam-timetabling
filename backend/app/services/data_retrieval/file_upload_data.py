# backend/app/services/data_retrieval/file_upload_data.py

"""
Service for retrieving file upload data from the database
"""

from typing import Dict, List, cast, Optional
from uuid import UUID
from datetime import datetime as ddatetime
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.file_uploads import (
    FileUploadSession,
    UploadedFile,
)


class FileUploadData:
    """Service for retrieving file upload-related data"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # File Upload Sessions
    async def get_all_upload_sessions(self) -> List[Dict]:
        """Get all file upload sessions with file counts"""
        stmt = (
            select(FileUploadSession)
            .options(
                selectinload(FileUploadSession.uploader),
                selectinload(FileUploadSession.session),
                selectinload(FileUploadSession.uploaded_files),
            )
            .order_by(FileUploadSession.created_at.desc())
        )
        result = await self.session.execute(stmt)
        sessions = result.scalars().all()

        return [
            {
                "id": str(session.id),
                "upload_type": session.upload_type,
                "uploaded_by": str(session.uploaded_by),
                "uploader_email": session.uploader.email if session.uploader else None,
                "uploader_name": (
                    f"{session.uploader.first_name} {session.uploader.last_name}"
                    if session.uploader
                    else None
                ),
                "session_id": str(session.session_id) if session.session_id else None,
                "session_name": session.session.name if session.session else None,
                "status": session.status,
                "total_records": session.total_records,
                "processed_records": session.processed_records,
                "validation_errors": session.validation_errors,
                "file_count": len(session.uploaded_files),
                "completed_at": (
                    cast(ddatetime, session.completed_at).isoformat()
                    if session.completed_at
                    else None
                ),
                "created_at": (
                    cast(ddatetime, session.created_at).isoformat()
                    if session.created_at
                    else None
                ),
                "updated_at": (
                    cast(ddatetime, session.updated_at).isoformat()
                    if session.updated_at
                    else None
                ),
            }
            for session in sessions
        ]

    async def get_upload_sessions_by_user(self, user_id: UUID) -> List[Dict]:
        """Get upload sessions by user"""
        stmt = (
            select(FileUploadSession)
            .options(
                selectinload(FileUploadSession.session),
                selectinload(FileUploadSession.uploaded_files),
            )
            .where(FileUploadSession.uploaded_by == user_id)
            .order_by(FileUploadSession.created_at.desc())
        )
        result = await self.session.execute(stmt)
        sessions = result.scalars().all()

        return [
            {
                "id": str(session.id),
                "upload_type": session.upload_type,
                "session_name": session.session.name if session.session else None,
                "status": session.status,
                "total_records": session.total_records,
                "processed_records": session.processed_records,
                "file_count": len(session.uploaded_files),
                "completed_at": (
                    cast(ddatetime, session.completed_at).isoformat()
                    if session.completed_at
                    else None
                ),
                "created_at": (
                    cast(ddatetime, session.created_at).isoformat()
                    if session.created_at
                    else None
                ),
            }
            for session in sessions
        ]

    async def get_upload_sessions_by_type(self, upload_type: str) -> List[Dict]:
        """Get upload sessions by type"""
        stmt = (
            select(FileUploadSession)
            .options(
                selectinload(FileUploadSession.uploader),
                selectinload(FileUploadSession.session),
            )
            .where(FileUploadSession.upload_type == upload_type)
            .order_by(FileUploadSession.created_at.desc())
        )
        result = await self.session.execute(stmt)
        sessions = result.scalars().all()

        return [
            {
                "id": str(session.id),
                "uploaded_by": str(session.uploaded_by),
                "uploader_email": session.uploader.email if session.uploader else None,
                "session_name": session.session.name if session.session else None,
                "status": session.status,
                "total_records": session.total_records,
                "processed_records": session.processed_records,
                "validation_errors": session.validation_errors,
                "completed_at": (
                    cast(ddatetime, session.completed_at).isoformat()
                    if session.completed_at
                    else None
                ),
                "created_at": (
                    cast(ddatetime, session.created_at).isoformat()
                    if session.created_at
                    else None
                ),
            }
            for session in sessions
        ]

    async def get_upload_session_by_id(self, session_id: UUID) -> Optional[Dict]:
        """Get upload session by ID with complete information"""
        stmt = (
            select(FileUploadSession)
            .options(
                selectinload(FileUploadSession.uploader),
                selectinload(FileUploadSession.session),
                selectinload(FileUploadSession.uploaded_files),
            )
            .where(FileUploadSession.id == session_id)
        )
        result = await self.session.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            return None

        return {
            "id": str(session.id),
            "upload_type": session.upload_type,
            "uploaded_by": str(session.uploaded_by),
            "uploader_email": session.uploader.email if session.uploader else None,
            "uploader_name": (
                f"{session.uploader.first_name} {session.uploader.last_name}"
                if session.uploader
                else None
            ),
            "session_id": str(session.session_id) if session.session_id else None,
            "session_name": session.session.name if session.session else None,
            "status": session.status,
            "total_records": session.total_records,
            "processed_records": session.processed_records,
            "validation_errors": session.validation_errors,
            "uploaded_files": [
                {
                    "id": str(file.id),
                    "file_name": file.file_name,
                    "file_size": file.file_size,
                    "file_type": file.file_type,
                    "mime_type": file.mime_type,
                    "row_count": file.row_count,
                    "validation_status": file.validation_status,
                    "validation_errors": file.validation_errors,
                    "uploaded_at": (
                        cast(ddatetime, file.uploaded_at).isoformat()
                        if file.uploaded_at
                        else None
                    ),
                }
                for file in session.uploaded_files
            ],
            "completed_at": (
                cast(ddatetime, session.completed_at).isoformat()
                if session.completed_at
                else None
            ),
            "created_at": (
                cast(ddatetime, session.created_at).isoformat()
                if session.created_at
                else None
            ),
            "updated_at": (
                cast(ddatetime, session.updated_at).isoformat()
                if session.updated_at
                else None
            ),
        }

    async def get_active_upload_sessions(self) -> List[Dict]:
        """Get currently active upload sessions"""
        stmt = (
            select(FileUploadSession)
            .options(
                selectinload(FileUploadSession.uploader),
                selectinload(FileUploadSession.session),
            )
            .where(FileUploadSession.status == "processing")
            .order_by(FileUploadSession.created_at.asc())
        )
        result = await self.session.execute(stmt)
        sessions = result.scalars().all()

        return [
            {
                "id": str(session.id),
                "upload_type": session.upload_type,
                "uploader_email": session.uploader.email if session.uploader else None,
                "session_name": session.session.name if session.session else None,
                "total_records": session.total_records,
                "processed_records": session.processed_records,
                "progress_percentage": (
                    (session.processed_records / session.total_records * 100)
                    if session.total_records > 0
                    else 0
                ),
                "created_at": (
                    cast(ddatetime, session.created_at).isoformat()
                    if session.created_at
                    else None
                ),
            }
            for session in sessions
        ]

    # Uploaded Files
    async def get_all_uploaded_files(self, limit: int = 100) -> List[Dict]:
        """Get all uploaded files"""
        stmt = (
            select(UploadedFile)
            .options(selectinload(UploadedFile.upload_session))
            .order_by(UploadedFile.uploaded_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        files = result.scalars().all()

        return [
            {
                "id": str(file.id),
                "upload_session_id": str(file.upload_session_id),
                "upload_type": (
                    file.upload_session.upload_type if file.upload_session else None
                ),
                "file_name": file.file_name,
                "file_path": file.file_path,
                "file_size": file.file_size,
                "file_type": file.file_type,
                "mime_type": file.mime_type,
                "checksum": file.checksum,
                "row_count": file.row_count,
                "validation_status": file.validation_status,
                "validation_errors": file.validation_errors,
                "uploaded_at": (
                    cast(ddatetime, file.uploaded_at).isoformat()
                    if file.uploaded_at
                    else None
                ),
            }
            for file in files
        ]

    async def get_files_by_upload_session(self, upload_session_id: UUID) -> List[Dict]:
        """Get files by upload session"""
        stmt = (
            select(UploadedFile)
            .where(UploadedFile.upload_session_id == upload_session_id)
            .order_by(UploadedFile.uploaded_at.asc())
        )
        result = await self.session.execute(stmt)
        files = result.scalars().all()

        return [
            {
                "id": str(file.id),
                "file_name": file.file_name,
                "file_size": file.file_size,
                "file_type": file.file_type,
                "mime_type": file.mime_type,
                "row_count": file.row_count,
                "validation_status": file.validation_status,
                "validation_errors": file.validation_errors,
                "uploaded_at": (
                    cast(ddatetime, file.uploaded_at).isoformat()
                    if file.uploaded_at
                    else None
                ),
            }
            for file in files
        ]

    async def get_file_by_id(self, file_id: UUID) -> Optional[Dict]:
        """Get uploaded file by ID"""
        stmt = (
            select(UploadedFile)
            .options(
                selectinload(UploadedFile.upload_session).selectinload(
                    FileUploadSession.uploader
                )
            )
            .where(UploadedFile.id == file_id)
        )
        result = await self.session.execute(stmt)
        file = result.scalar_one_or_none()

        if not file:
            return None

        return {
            "id": str(file.id),
            "upload_session_id": str(file.upload_session_id),
            "upload_session": (
                {
                    "id": str(file.upload_session.id),
                    "upload_type": file.upload_session.upload_type,
                    "status": file.upload_session.status,
                    "uploader_email": (
                        file.upload_session.uploader.email
                        if file.upload_session.uploader
                        else None
                    ),
                }
                if file.upload_session
                else None
            ),
            "file_name": file.file_name,
            "file_path": file.file_path,
            "file_size": file.file_size,
            "file_type": file.file_type,
            "mime_type": file.mime_type,
            "checksum": file.checksum,
            "row_count": file.row_count,
            "validation_status": file.validation_status,
            "validation_errors": file.validation_errors,
            "uploaded_at": (
                cast(ddatetime, file.uploaded_at).isoformat()
                if file.uploaded_at
                else None
            ),
        }

    async def get_files_by_validation_status(
        self, validation_status: str
    ) -> List[Dict]:
        """Get files by validation status"""
        stmt = (
            select(UploadedFile)
            .options(selectinload(UploadedFile.upload_session))
            .where(UploadedFile.validation_status == validation_status)
            .order_by(UploadedFile.uploaded_at.desc())
        )
        result = await self.session.execute(stmt)
        files = result.scalars().all()

        return [
            {
                "id": str(file.id),
                "upload_session_id": str(file.upload_session_id),
                "upload_type": (
                    file.upload_session.upload_type if file.upload_session else None
                ),
                "file_name": file.file_name,
                "file_size": file.file_size,
                "row_count": file.row_count,
                "validation_errors": file.validation_errors,
                "uploaded_at": (
                    cast(ddatetime, file.uploaded_at).isoformat()
                    if file.uploaded_at
                    else None
                ),
            }
            for file in files
        ]

    # Statistics and analysis
    async def get_upload_statistics(self) -> Dict:
        """Get upload statistics"""
        # Total upload sessions
        total_sessions_stmt = select(func.count(FileUploadSession.id))
        total_sessions_result = await self.session.execute(total_sessions_stmt)
        total_sessions = total_sessions_result.scalar()

        # Sessions by status
        status_stmt = select(
            FileUploadSession.status, func.count(FileUploadSession.id).label("count")
        ).group_by(FileUploadSession.status)
        status_result = await self.session.execute(status_stmt)
        status_counts = {row.status: row.count for row in status_result}

        # Sessions by upload type
        type_stmt = select(
            FileUploadSession.upload_type,
            func.count(FileUploadSession.id).label("count"),
        ).group_by(FileUploadSession.upload_type)
        type_result = await self.session.execute(type_stmt)
        type_counts = {row.upload_type: row.count for row in type_result}

        # Total files and records
        file_stats_stmt = select(
            func.count(UploadedFile.id).label("total_files"),
            func.sum(UploadedFile.file_size).label("total_size"),
            func.sum(UploadedFile.row_count).label("total_records"),
        )
        file_stats_result = await self.session.execute(file_stats_stmt)
        file_stats = file_stats_result.first()

        # Validation statistics
        validation_stmt = select(
            UploadedFile.validation_status, func.count(UploadedFile.id).label("count")
        ).group_by(UploadedFile.validation_status)
        validation_result = await self.session.execute(validation_stmt)
        validation_counts = {
            row.validation_status: row.count for row in validation_result
        }

        # Handle potential None values
        total_files = file_stats.total_files if file_stats else 0
        total_size = (
            int(file_stats.total_size)
            if file_stats and file_stats.total_size is not None
            else 0
        )
        total_records = (
            int(file_stats.total_records)
            if file_stats and file_stats.total_records is not None
            else 0
        )

        return {
            "total_upload_sessions": total_sessions or 0,
            "status_breakdown": status_counts,
            "type_breakdown": type_counts,
            "total_files": total_files,
            "total_file_size_bytes": total_size,
            "total_records_processed": total_records,
            "validation_breakdown": validation_counts,
        }

    async def get_upload_activity_by_date(self, days: int = 30) -> List[Dict]:
        """Get upload activity for the last N days"""
        stmt = (
            select(
                func.date(FileUploadSession.created_at).label("upload_date"),
                func.count(FileUploadSession.id).label("session_count"),
                func.count(UploadedFile.id).label("file_count"),
            )
            .outerjoin(
                UploadedFile, UploadedFile.upload_session_id == FileUploadSession.id
            )
            .where(
                FileUploadSession.created_at
                >= func.now() - text(f"INTERVAL '{days} days'")
            )
            .group_by(func.date(FileUploadSession.created_at))
            .order_by(func.date(FileUploadSession.created_at).desc())
        )

        result = await self.session.execute(stmt)
        activity = result.all()

        return [
            {
                "date": row.upload_date.isoformat() if row.upload_date else None,
                "session_count": row.session_count,
                "file_count": row.file_count or 0,
            }
            for row in activity
        ]

    async def search_upload_sessions(
        self,
        search_term: str,
        upload_type: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[UUID] = None,
    ) -> List[Dict]:
        """Search upload sessions with multiple filters"""
        search_pattern = f"%{search_term}%"

        stmt = select(FileUploadSession).options(
            selectinload(FileUploadSession.uploader),
            selectinload(FileUploadSession.session),
        )

        # Apply search term if provided
        if search_term:
            stmt = stmt.join(
                UploadedFile, UploadedFile.upload_session_id == FileUploadSession.id
            ).where(UploadedFile.file_name.ilike(search_pattern))

        # Apply filters
        if upload_type:
            stmt = stmt.where(FileUploadSession.upload_type == upload_type)
        if status:
            stmt = stmt.where(FileUploadSession.status == status)
        if user_id:
            stmt = stmt.where(FileUploadSession.uploaded_by == user_id)

        stmt = stmt.distinct().order_by(FileUploadSession.created_at.desc())
        result = await self.session.execute(stmt)
        sessions = result.scalars().all()

        return [
            {
                "id": str(session.id),
                "upload_type": session.upload_type,
                "uploader_email": session.uploader.email if session.uploader else None,
                "session_name": session.session.name if session.session else None,
                "status": session.status,
                "total_records": session.total_records,
                "processed_records": session.processed_records,
                "created_at": (
                    cast(ddatetime, session.created_at).isoformat()
                    if session.created_at
                    else None
                ),
            }
            for session in sessions
        ]

    async def get_recent_uploads(self, limit: int = 20) -> List[Dict]:
        """Get recent upload sessions"""
        stmt = (
            select(FileUploadSession)
            .options(
                selectinload(FileUploadSession.uploader),
                selectinload(FileUploadSession.session),
            )
            .order_by(FileUploadSession.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        sessions = result.scalars().all()

        return [
            {
                "id": str(session.id),
                "upload_type": session.upload_type,
                "uploader_email": session.uploader.email if session.uploader else None,
                "session_name": session.session.name if session.session else None,
                "status": session.status,
                "total_records": session.total_records,
                "processed_records": session.processed_records,
                "created_at": (
                    cast(ddatetime, session.created_at).isoformat()
                    if session.created_at
                    else None
                ),
            }
            for session in sessions
        ]
