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


async def find_by_id(
    conn: asyncpg.Connection,
    session_id: UUID,
    user_id: str,
) -> dict[str, Any] | None:
    query = """--sql
    SELECT id, user_id, session_type, status, note_id, started_at, ended_at
    FROM dialogue_sessions
    WHERE id = $1 AND user_id = $2
    """
    record = await conn.fetchrow(query, str(session_id), user_id)
    return dict(record) if record else None


async def reset_stuck_generations(conn: asyncpg.Connection) -> int:
    query = """--sql
    UPDATE dialogue_sessions
    SET status = 'failed'
    WHERE status = 'generate_note'
    """
    result = await conn.execute(query)
    return int(result.split(" ")[1])
