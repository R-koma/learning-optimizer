import uuid

import asyncpg
import pytest

from repositories import feedback_repository

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _insert_dialogue_session(conn: asyncpg.Connection, user_id: str) -> uuid.UUID:
    session_id = uuid.uuid4()
    await conn.execute(
        """--sql
        INSERT INTO dialogue_sessions (id, user_id, session_type, status)
        VALUES ($1, $2, 'review', 'completed')
        """,
        session_id,
        user_id,
    )
    return session_id


async def _insert_note(conn: asyncpg.Connection, user_id: str) -> uuid.UUID:
    note_id = uuid.uuid4()
    await conn.execute(
        """--sql
        INSERT INTO notes (id, user_id, topic, content, summary, status)
        VALUES ($1, $2, '統計学', 'original content', 'original summary', 'active')
        """,
        note_id,
        user_id,
    )
    return note_id


class TestUpsertForNote:
    async def test_inserts_when_no_existing_feedback(
        self, db_conn: asyncpg.Connection, test_user: dict[str, str]
    ) -> None:
        note_id = await _insert_note(db_conn, test_user["id"])
        session_id = await _insert_dialogue_session(db_conn, test_user["id"])

        result = await feedback_repository.upsert_for_note(
            conn=db_conn,
            note_id=note_id,
            dialogue_session_id=session_id,
            understanding_level="medium",
            strength="基礎理解OK",
            improvements="応用が弱い",
        )

        assert result["note_id"] == note_id
        assert result["understanding_level"] == "medium"

        rows = await db_conn.fetch("SELECT * FROM feedbacks WHERE note_id = $1", note_id)
        assert len(rows) == 1

    async def test_updates_existing_row_keeping_count_to_one(
        self, db_conn: asyncpg.Connection, test_user: dict[str, str]
    ) -> None:
        note_id = await _insert_note(db_conn, test_user["id"])
        session1 = await _insert_dialogue_session(db_conn, test_user["id"])
        session2 = await _insert_dialogue_session(db_conn, test_user["id"])

        await feedback_repository.upsert_for_note(
            conn=db_conn,
            note_id=note_id,
            dialogue_session_id=session1,
            understanding_level="low",
            strength="s1",
            improvements="i1",
        )
        await feedback_repository.upsert_for_note(
            conn=db_conn,
            note_id=note_id,
            dialogue_session_id=session2,
            understanding_level="high",
            strength="s2",
            improvements="i2",
        )

        rows = await db_conn.fetch("SELECT * FROM feedbacks WHERE note_id = $1", note_id)
        assert len(rows) == 1
        assert rows[0]["understanding_level"] == "high"
        assert rows[0]["strength"] == "s2"
        assert rows[0]["improvements"] == "i2"
        assert rows[0]["dialogue_session_id"] == session2
