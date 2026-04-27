from datetime import datetime
from typing import Any

from core.database import get_pool
from repositories import run_trace_repository


async def summarize_recent(since: datetime) -> dict[str, Any]:
    """直近期間の主要指標を集計する。

    `uv run python -c "..."` から開発者が呼び出す想定の薄いラッパー。
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await run_trace_repository.summarize_recent(conn, since)
