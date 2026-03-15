from uuid import UUID

import asyncpg


async def find_by_note_id(conn: asyncpg.Connection, note_id: UUID, user_id: str) -> list[dict]:
    query = """--sql
    SELECT f.id, f.note_id, f.dialogue_session_id, f.understanding_level, f.strength, f.improvements, f.created_at
    FROM feedbacks f
    JOIN notes n ON n.id = f.note_id
    WHERE f.note_id = $1 AND n.user_id = $2
    ORDER BY f.created_at ASC
  """

    records = await conn.fetch(query, note_id, user_id)
    return [dict(r) for r in records]


async def insert(
    conn: asyncpg.Connection,
    note_id: UUID,
    dialogue_session_id: UUID,
    understanding_level: str,
    strength: str,
    improvements: str,
) -> dict:
    query = """--sql
    INSERT INTO feedbacks (id, note_id, dialogue_session_id, understanding_level, strength, improvements)
    VALUES (gen_random_uuid(), $1, $2, $3, $4, $5)
    RETURNING *
    """
    record = await conn.fetchrow(query, note_id, dialogue_session_id, understanding_level, strength, improvements)
    return dict(record)
