from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from core.config import DATABASE_URL


def get_checkpointer():
    """async with で使うコンテキストマネージャを返す"""
    return AsyncPostgresSaver.from_conn_string(DATABASE_URL)
