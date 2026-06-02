from typing import Any
from uuid import UUID

from core.database import DBConnection


async def insert(
    conn: DBConnection, dialogue_session_id: UUID, role: str, content: str, message_order: int
) -> dict[str, Any]:
    query = """--sql
    INSERT INTO dialogue_messages (id, dialogue_session_id, role, content, message_order)
    VALUES (gen_random_uuid(), $1, $2, $3, $4)
    RETURNING *
    """
    record = await conn.fetchrow(query, str(dialogue_session_id), role, content, message_order)
    assert record is not None  # INSERT ... RETURNING は必ず1行返す
    return dict(record)


async def find_by_session_id(
    conn: DBConnection,
    dialogue_session_id: UUID,
) -> list[dict[str, Any]]:
    query = """--sql
    SELECT id, role, content, message_order, created_at
    FROM dialogue_messages
    WHERE dialogue_session_id = $1
    ORDER BY message_order ASC
    """
    records = await conn.fetch(query, str(dialogue_session_id))
    return [dict(r) for r in records]


async def get_max_message_order(conn: DBConnection, dialogue_session_id: UUID) -> int:
    query = """--sql
    SELECT COALESCE(MAX(message_order), 0)
    FROM dialogue_messages
    WHERE dialogue_session_id = $1
    """
    result = await conn.fetchval(query, str(dialogue_session_id))
    return int(result)


async def delete_last_n(conn: DBConnection, dialogue_session_id: UUID, n: int) -> int:
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
