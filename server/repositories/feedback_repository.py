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

    records = await conn.fetch(query, str(note_id), user_id)
    return [dict(r) for r in records]
