from uuid import uuid4

import asyncpg
import pytest

from repositories import dialogue_session_repository

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_create_persists_graph_version(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    session_id = uuid4()

    created = await dialogue_session_repository.create(
        conn=db_conn,
        session_id=session_id,
        user_id=test_user["id"],
        session_type="learning",
        graph_version=2,
    )

    assert created["graph_version"] == 2


async def test_find_by_id_returns_graph_version(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    session_id = uuid4()
    await dialogue_session_repository.create(
        conn=db_conn,
        session_id=session_id,
        user_id=test_user["id"],
        session_type="review",
        graph_version=2,
    )

    found = await dialogue_session_repository.find_by_id(db_conn, session_id, test_user["id"])

    assert found is not None
    assert found["graph_version"] == 2
