from datetime import datetime
from uuid import UUID

import asyncpg


async def find_pending_by_user_id(conn: asyncpg.Connection, user_id: str) -> list[dict]:
    query = """
      SELECT rs.id, rs.note_id, rs.review_count,
      rs.next_review_at, rs.last_reviewed_at, rs.status, rs.created_at, rs.updated_at, n.topic AS note_topic,
      n.summary AS note_summary
      FROM review_schedules rs
      JOIN notes n ON n.id = rs.note_id
      WHERE n.user_id = $1
        AND rs.status IN ('pending', 'overdue')
        AND rs.next_review_at <= NOW()
      ORDER BY rs.next_review_at ASC
    """

    records = await conn.fetch(query, user_id)
    return [dict(r) for r in records]


async def mark_completed(
    conn: asyncpg.Connection, schedule_id: UUID, user_id: str, next_review_at: datetime
) -> dict | None:
    query = """--sql
      UPDATE review_schedules
      SET status = 'completed',
          review_count = review_count + 1,
          last_review_at = NOW(),
          next_review_at = $3,
          updated_at = NOW()
      WHERE id = $1
        AND note_id IN (SELECT id FROM notes WHERE user_id = $2)
      RETURNING *
    """

    record = await conn.fetchrow(query, schedule_id, user_id, next_review_at)

    return dict(record) if record else None
