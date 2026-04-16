from uuid import uuid4

import asyncpg
import pytest

from repositories import note_repository

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_insert_and_find_by_id(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    note_id = uuid4()
    user_id = test_user["id"]

    created = await note_repository.insert(
        db_conn, note_id=note_id, user_id=user_id, topic="Python", content="変数とは", summary="要約"
    )

    assert created["id"] == note_id
    assert created["user_id"] == user_id
    assert created["topic"] == "Python"
    assert created["content"] == "変数とは"
    assert created["summary"] == "要約"
    assert created["status"] == "active"

    found = await note_repository.find_by_id(db_conn, note_id=note_id, user_id=user_id)
    assert found is not None
    assert found["id"] == note_id
    assert found["topic"] == "Python"


async def test_find_by_id_returns_none_for_nonexistent(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    result = await note_repository.find_by_id(db_conn, note_id=uuid4(), user_id=test_user["id"])
    assert result is None


async def test_find_by_id_returns_none_for_other_user(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    note_id = uuid4()
    await note_repository.insert(
        db_conn, note_id=note_id, user_id=test_user["id"], topic="Topic", content="Content", summary="Summary"
    )

    result = await note_repository.find_by_id(db_conn, note_id=note_id, user_id="other-user-id")
    assert result is None


async def test_find_by_user_id(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    user_id = test_user["id"]
    await note_repository.insert(db_conn, note_id=uuid4(), user_id=user_id, topic="A", content="a", summary="sa")
    await note_repository.insert(db_conn, note_id=uuid4(), user_id=user_id, topic="B", content="b", summary="sb")

    notes = await note_repository.find_by_user_id(db_conn, user_id=user_id)
    assert len(notes) == 2
    # created_at DESC なので B が先
    assert notes[0]["topic"] == "B"
    assert notes[1]["topic"] == "A"


async def test_find_by_user_id_includes_archived(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    user_id = test_user["id"]
    note_id = uuid4()
    await note_repository.insert(db_conn, note_id=note_id, user_id=user_id, topic="Archived", content="c", summary="s")
    await note_repository.update(db_conn, note_id=note_id, user_id=user_id, status="archived")

    notes = await note_repository.find_by_user_id(db_conn, user_id=user_id)
    assert len(notes) == 1
    assert notes[0]["status"] == "archived"


async def test_find_by_user_id_returns_empty_for_no_notes(
    db_conn: asyncpg.Connection, test_user: dict[str, str]
) -> None:
    notes = await note_repository.find_by_user_id(db_conn, user_id=test_user["id"])
    assert notes == []


async def test_update_topic(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    note_id = uuid4()
    user_id = test_user["id"]
    await note_repository.insert(db_conn, note_id=note_id, user_id=user_id, topic="Old", content="c", summary="s")

    updated = await note_repository.update(db_conn, note_id=note_id, user_id=user_id, topic="New")
    assert updated is not None
    assert updated["topic"] == "New"
    assert updated["content"] == "c"


async def test_update_multiple_fields(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    note_id = uuid4()
    user_id = test_user["id"]
    await note_repository.insert(db_conn, note_id=note_id, user_id=user_id, topic="T", content="C", summary="S")

    updated = await note_repository.update(
        db_conn, note_id=note_id, user_id=user_id, content="New Content", summary="New Summary", status="archived"
    )
    assert updated is not None
    assert updated["content"] == "New Content"
    assert updated["summary"] == "New Summary"
    assert updated["status"] == "archived"


async def test_update_returns_none_for_nonexistent(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    result = await note_repository.update(db_conn, note_id=uuid4(), user_id=test_user["id"], topic="X")
    assert result is None


async def test_delete(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    note_id = uuid4()
    user_id = test_user["id"]
    await note_repository.insert(db_conn, note_id=note_id, user_id=user_id, topic="T", content="C", summary="S")

    deleted = await note_repository.delete(db_conn, note_id=note_id, user_id=user_id)
    assert deleted is True

    found = await note_repository.find_by_id(db_conn, note_id=note_id, user_id=user_id)
    assert found is None


async def test_delete_returns_false_for_nonexistent(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    result = await note_repository.delete(db_conn, note_id=uuid4(), user_id=test_user["id"])
    assert result is False


async def test_delete_cascades_related_records(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    note_id = uuid4()
    user_id = test_user["id"]
    await note_repository.insert(db_conn, note_id=note_id, user_id=user_id, topic="T", content="C", summary="S")

    await db_conn.execute(
        """
        INSERT INTO feedbacks (id, note_id, understanding_level, strength, improvements)
        VALUES ($1, $2, 'high', 'Good', 'None')
        """,
        uuid4(),
        note_id,
    )
    await db_conn.execute(
        """
        INSERT INTO review_schedules (id, note_id, next_review_at)
        VALUES ($1, $2, NOW() + INTERVAL '1 day')
        """,
        uuid4(),
        note_id,
    )

    deleted = await note_repository.delete(db_conn, note_id=note_id, user_id=user_id)
    assert deleted is True

    # 関連レコードも削除されていることを確認
    feedback_count = await db_conn.fetchval("SELECT COUNT(*) FROM feedbacks WHERE note_id = $1", note_id)
    assert feedback_count == 0
    schedule_count = await db_conn.fetchval("SELECT COUNT(*) FROM review_schedules WHERE note_id = $1", note_id)
    assert schedule_count == 0
