import asyncpg
from asyncpg.pool import PoolConnectionProxy

from core.config import DATABASE_URL

# リポジトリ層が受け取るコネクション型。
# FastAPI の DI や pool.acquire() 経由では PoolConnectionProxy が、
# 直接 Connection を扱う箇所では Connection が渡るため、両方を許容する。
DBConnection = asyncpg.Connection | PoolConnectionProxy

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
