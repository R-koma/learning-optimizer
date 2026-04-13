from typing import Any
from uuid import UUID

import asyncpg


async def create(
    conn: asyncpg.Connection,
    session_id: UUID,
    user_id: str,
    session_type: str,
) -> dict[str, Any]:
    query = """--sql
    INSERT INTO dialogue_sessions (id, user_id, session_type, status)
    VALUES ($1, $2, $3, 'in_progress')
    RETURNING *
    """
    record = await conn.fetchrow(query, str(session_id), user_id, session_type)
    return dict(record)


async def update_note_id(
    conn: asyncpg.Connection,
    session_id: UUID,
    note_id: UUID,
) -> dict[str, Any] | None:
    query = """--sql
    UPDATE dialogue_sessions
    SET note_id = $2, status = 'completed', ended_at = NOW()
    WHERE id = $1
    RETURNING *
    """
    record = await conn.fetchrow(query, str(session_id), str(note_id))
    return dict(record) if record else None


async def update_status(
    conn: asyncpg.Connection,
    session_id: UUID,
    status: str,
) -> dict[str, Any] | None:
    query = """--sql
    UPDATE dialogue_sessions
    SET status = $2
    WHERE id = $1
    RETURNING *
    """
    record = await conn.fetchrow(query, str(session_id), status)
    return dict(record) if record else None
