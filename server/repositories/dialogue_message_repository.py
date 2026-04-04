from uuid import UUID

import asyncpg


async def insert(
    conn: asyncpg.Connection, dialogue_session_id: UUID, role: str, content: str, message_order: int
) -> dict:
    query = """--sql
    INSERT INTO dialogue_messages (id, dialogue_session_id, role, content, message_order)
    VALUES (gen_random_uuid(), $1, $2, $3, $4)
    RETURNING *
    """
    record = await conn.fetchrow(query, str(dialogue_session_id), role, content, message_order)
    return dict(record)


async def delete_last_n(conn: asyncpg.Connection, dialogue_session_id: UUID, n: int) -> int:
    query = """--sql
    DELETE FROM dialogue_messages
    WHERE id IN (
        SELECT id FROM dialogue_messages
        WHERE dialogue_session_id = $1
        ORDER BY message_order DESC
        LIMIT $2
    )
    """
    result = await conn.execute(query, str(dialogue_session_id), n)
    return int(result.split()[-1])
