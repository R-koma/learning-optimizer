from uuid import UUID

import asyncpg


async def find_by_user_id(conn: asyncpg.Connection, user_id: str) -> list[dict]:
    query = """--sql
    SELECT id, user_id, topic, content, summary, status, created_at, updated_at From notes
    WHERE user_id = $1 AND status = 'active'
    ORDER BY created_at DESC
  """

    records = await conn.fetch(query, user_id)
    return [dict(r) for r in records]


async def find_by_id(conn: asyncpg.Connection, note_id: UUID, user_id: str) -> dict | None:
    query = """--sql
    SELECT id, user_id, topic, content, summary, status, created_at, updated_at
    FROM notes
    WHERE id = $1 AND user_id = $2
  """

    record = await conn.fetchrow(query, note_id, user_id)
    return dict(record) if record else None


async def insert(
    conn: asyncpg.Connection,
    note_id: UUID,
    user_id: str,
    topic: str,
    content: str,
    summary: str,
) -> dict:
    query = """--sql
        INSERT INTO notes (id, user_id, topic, content, summary, status)
        VALUES ($1, $2, $3, $4, $5, 'active')
        RETURNING id, user_id, topic, content, summary, status, created_at, updated_at
    """
    record = await conn.fetchrow(query, note_id, user_id, topic, content, summary)
    return dict(record)


async def update(
    conn: asyncpg.Connection,
    note_id: UUID,
    user_id: str,
    topic: str | None = None,
    content: str | None = None,
    summary: str | None = None,
    status: str | None = None,
) -> dict | None:
    query = """--sql
    UPDATE notes
    SET topic = COALESCE($3, topic),
        content = COALESCE($4, content),
        summary = COALESCE($5, summary),
        status = COALESCE($6, status),
        updated_at = NOW()
    WHERE id = $1 AND user_id = $2
    RETURNING id, user_id, topic, content, summary, status, created_at, updated_at
  """

    record = await conn.fetchrow(query, note_id, user_id, topic, content, summary, status)
    return dict(record) if record else None


async def delete(conn: asyncpg.Connection, note_id: UUID, user_id: str) -> bool:
    query = """--sql
    DELETE FROM notes WHERE id = $1 AND user_id = $2
  """

    result = await conn.execute(query, note_id, user_id)

    deleted_count = int(result.split(" ")[1])
    return deleted_count > 0
