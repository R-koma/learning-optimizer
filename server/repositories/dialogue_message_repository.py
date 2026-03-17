from uuid import UUID

import asyncpg


async def insert(
    conn: asyncpg.Connection, dialogue_session_id: UUID, role: str, content: str, message_order: int
) -> dict:
    query = """--sql
    INSERT INTO dialogue_messages (id, dialogue_session_id, role, content, message_order)
    VALUES (gen_random_uuid(), $1, $2, $3)
    RETURNING *
    """
    record = await conn.fetchrow(query, str(dialogue_session_id), role, content, message_order)
    return dict(record)
