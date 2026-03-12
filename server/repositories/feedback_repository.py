from uuid import UUID

import asyncpg


async def find_by_note_id(conn: asyncpg.Connection, note_id: UUID, user_id: str) -> list[asyncpg.Record]:
    query = """--sql
    SELECT id, note_id, dialogue_session_id, understanding_level, strengths, improvements, created_at
    FROM feedbacks f
    JOIN notes n ON n.id = f.note_id
    WHERE f.note_id = $1 AND n.user_id = $2
    ORDER BY f.created_at ASC
  """

    return await conn.fetch(query, note_id, user_id)
