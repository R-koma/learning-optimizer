from datetime import datetime
from typing import Any
from uuid import UUID

from core.database import DBConnection


async def find_pending_by_user_id(conn: DBConnection, user_id: str) -> list[dict[str, Any]]:
    query = """--sql
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


async def find_upcoming_by_user_id(conn: DBConnection, user_id: str) -> list[dict[str, Any]]:
    """next_review_at が未来のスケジュール（＝今後の復習予定）をトピック付きで返す。
    カレンダーで未来日に復習予定を表示するために使う。期限到来済みは find_pending が担うため除外する。
    status はフィルタしない（復習完了後も次回予定が未来に再設定されるため、それも予定として含める）。
    """
    query = """--sql
      SELECT rs.id, rs.note_id, rs.review_count,
      rs.next_review_at, rs.last_reviewed_at, rs.status, rs.created_at, rs.updated_at, n.topic AS note_topic,
      n.summary AS note_summary
      FROM review_schedules rs
      JOIN notes n ON n.id = rs.note_id
      WHERE n.user_id = $1
        AND rs.next_review_at > NOW()
      ORDER BY rs.next_review_at ASC
    """

    records = await conn.fetch(query, user_id)
    return [dict(r) for r in records]


async def count_completed_today_by_user_id(conn: DBConnection, user_id: str, timezone: str) -> int:
    """指定タイムゾーンの暦日で「今日復習を完了した」スケジュール件数を返す。
    ダッシュボードの当日進捗バーで「完了 / 当日総数」を出すために使う。
    timestamptz をユーザーのタイムゾーンに変換して暦日比較するため、サーバーの稼働 TZ に依存しない。
    """
    query = """--sql
      SELECT COUNT(*)
      FROM review_schedules rs
      JOIN notes n ON n.id = rs.note_id
      WHERE n.user_id = $1
        AND rs.last_reviewed_at IS NOT NULL
        AND (rs.last_reviewed_at AT TIME ZONE $2)::date = (NOW() AT TIME ZONE $2)::date
    """

    count = await conn.fetchval(query, user_id, timezone)
    return int(count or 0)


async def mark_completed(
    conn: DBConnection, schedule_id: UUID, user_id: str, next_review_at: datetime
) -> dict[str, Any] | None:
    query = """--sql
      UPDATE review_schedules
      SET status = 'completed',
          review_count = review_count + 1,
          last_reviewed_at = NOW(),
          next_review_at = $3,
          updated_at = NOW()
      WHERE id = $1
        AND note_id IN (SELECT id FROM notes WHERE user_id = $2)
      RETURNING *
    """

    record = await conn.fetchrow(query, schedule_id, user_id, next_review_at)

    return dict(record) if record else None


async def insert(
    conn: DBConnection,
    note_id: UUID,
    next_review_at: datetime,
) -> dict[str, Any]:
    query = """--sql
    INSERT INTO review_schedules (id, note_id, next_review_at, status)
    VALUES (gen_random_uuid(), $1, $2, 'pending')
    RETURNING *
    """
    record = await conn.fetchrow(query, note_id, next_review_at)
    assert record is not None  # INSERT ... RETURNING は必ず1行返す
    return dict(record)


async def find_by_note_id(conn: DBConnection, note_id: UUID) -> dict[str, Any] | None:
    """ノートIDから復習スケジュールを取得する。"""
    query = """--sql
    SELECT id, note_id, review_count, next_review_at,
           last_reviewed_at, status, created_at, updated_at
    FROM review_schedules
    WHERE note_id = $1
    """
    record = await conn.fetchrow(query, note_id)
    return dict(record) if record else None


async def update_schedule(
    conn: DBConnection,
    note_id: UUID,
    review_count: int,
    next_review_at: datetime,
) -> dict[str, Any] | None:
    """復習完了後にスケジュールを更新する。"""
    query = """--sql
    UPDATE review_schedules
    SET review_count = $2,
        next_review_at = $3,
        last_reviewed_at = NOW(),
        status = 'pending',
        updated_at = NOW()
    WHERE note_id = $1
    RETURNING *
    """
    record = await conn.fetchrow(query, note_id, review_count, next_review_at)
    return dict(record) if record else None
