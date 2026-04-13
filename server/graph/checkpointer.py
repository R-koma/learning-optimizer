from contextlib import AbstractAsyncContextManager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from core.config import DATABASE_URL


def get_checkpointer() -> AbstractAsyncContextManager[AsyncPostgresSaver]:
    """async with で使うコンテキストマネージャを返す"""
    if DATABASE_URL is None:
        raise RuntimeError("DATABASE_URL is not set")
    return AsyncPostgresSaver.from_conn_string(DATABASE_URL)
