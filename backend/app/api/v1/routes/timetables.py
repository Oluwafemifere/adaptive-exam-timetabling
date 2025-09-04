# # app/api/v1/routes/timetables.py
# from fastapi import APIRouter, Depends
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.api.deps import db_session, current_user
# from app.models.users import User


# router = APIRouter()


# @router.post("/")
# async def create_timetable(
#     session_id: str,
#     db: AsyncSession = Depends(db_session),
#     user: User = Depends(current_user),
# ):
#     service = SchedulingService(db, user)
#     job = await service.start_timetable_job(session_id)
#     return job


# @router.get("/{timetable_id}")
# async def get_timetable(
#     timetable_id: str,
#     db: AsyncSession = Depends(db_session),
#     user: User = Depends(current_user),
# ):
#     service = SchedulingService(db, user)
#     timetable = await service.get_timetable(timetable_id)
#     return timetable
