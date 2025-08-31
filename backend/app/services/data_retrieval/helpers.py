# backend/app/services/data_retrieval/helpers.py
"""
Reusable helper functions for data retrieval services
"""
from datetime import date, datetime
from typing import List, Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def refresh_materialized_view(session: AsyncSession, view_name: str) -> None:
    """
    Refreshes a materialized view to ensure up-to-date data
    """
    await session.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}"))
    await session.commit()


async def batch_query_ids(
    session: AsyncSession, table_name: str, id_list: List[str]
) -> List[dict]:
    """
    Fetch rows by batching a large list of IDs to avoid query parameter limits
    """
    batch_size = 500
    results = []
    for i in range(0, len(id_list), batch_size):
        batch = id_list[i : i + batch_size]
        placeholders = ",".join([f":id_{j}" for j in range(len(batch))])
        stmt = text(f"SELECT * FROM {table_name} WHERE id IN ({placeholders})")
        params = {f"id_{j}": batch[j] for j in range(len(batch))}
        res = await session.execute(stmt, params)
        results.extend([dict(row) for row in res])
    return results


def iso_date_range(start: date, end: date) -> List[str]:
    """
    Returns a list of ISO-formatted dates between start and end inclusive
    """
    days = []
    current = start
    while current <= end:
        days.append(current.isoformat())
        current = current.fromordinal(current.toordinal() + 1)
    return days
