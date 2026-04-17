from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import asyncpg
import pytest
from freezegun import freeze_time

from repositories import note_repository, review_schedule_repository

pytestmark = pytest.mark.asyncio(loop_scope="session")

PAST_TIME = "2026-04-16 10:00:00"
FUTURE_REVIEW = datetime(2026, 4, 17, 10, 0, 0, tzinfo=UTC)


async def _create_test_note(conn: asyncpg.Connection, user_id: str) -> dict[str, Any]:
    note_id = uuid4()
    return await note_repository.insert(
        conn,
        note_id=note_id,
        user_id=user_id,
        topic="テストトピック",
        content="テスト内容",
        summary="テスト要約",
    )


# -----------------------------------------------------------
# insert
# -----------------------------------------------------------


async def test_insert_creates_pending_schedule(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    note = await _create_test_note(db_conn, test_user["id"])
    next_review = datetime(2026, 4, 20, 0, 0, 0, tzinfo=UTC)

    schedule = await review_schedule_repository.insert(db_conn, note_id=note["id"], next_review_at=next_review)

    assert schedule["note_id"] == note["id"]
    assert schedule["status"] == "pending"
    assert schedule["review_count"] == 0
    assert schedule["next_review_at"].replace(tzinfo=UTC) == next_review


# -----------------------------------------------------------
# find_pending_by_user_id - 時刻条件テスト
# -----------------------------------------------------------


@freeze_time(PAST_TIME)
async def test_find_pending_includes_past_schedule(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    """next_review_at が過去のスケジュールは一覧に含まれる"""
    note = await _create_test_note(db_conn, test_user["id"])
    past_review = datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC)  # 現在時刻より過去

    await review_schedule_repository.insert(db_conn, note_id=note["id"], next_review_at=past_review)

    results = await review_schedule_repository.find_pending_by_user_id(db_conn, user_id=test_user["id"])
    note_ids = [r["note_id"] for r in results]
    assert note["id"] in note_ids


@freeze_time(PAST_TIME)
async def test_find_pending_excludes_future_schedule(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    """next_review_at が未来のスケジュールは一覧に含まれない"""
    note = await _create_test_note(db_conn, test_user["id"])
    future_review = datetime(2099, 12, 31, 0, 0, 0, tzinfo=UTC)  # DBのNOW()に依存するため遠い未来を使用

    await review_schedule_repository.insert(db_conn, note_id=note["id"], next_review_at=future_review)

    results = await review_schedule_repository.find_pending_by_user_id(db_conn, user_id=test_user["id"])
    note_ids = [r["note_id"] for r in results]
    assert note["id"] not in note_ids


@freeze_time(PAST_TIME)
async def test_find_pending_excludes_completed_schedule(
    db_conn: asyncpg.Connection, test_user: dict[str, str]
) -> None:
    """status='completed' のスケジュールは一覧に含まれない"""
    note = await _create_test_note(db_conn, test_user["id"])
    past_review = datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC)

    schedule = await review_schedule_repository.insert(db_conn, note_id=note["id"], next_review_at=past_review)
    # mark_completed で status を completed に変更
    await review_schedule_repository.mark_completed(
        db_conn,
        schedule_id=schedule["id"],
        user_id=test_user["id"],
        next_review_at=FUTURE_REVIEW,
    )

    results = await review_schedule_repository.find_pending_by_user_id(db_conn, user_id=test_user["id"])
    note_ids = [r["note_id"] for r in results]
    assert note["id"] not in note_ids


@freeze_time(PAST_TIME)
async def test_find_pending_returns_note_topic_and_summary(
    db_conn: asyncpg.Connection, test_user: dict[str, str]
) -> None:
    """結果に note_topic と note_summary が含まれる"""
    note = await _create_test_note(db_conn, test_user["id"])
    past_review = datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC)

    await review_schedule_repository.insert(db_conn, note_id=note["id"], next_review_at=past_review)

    results = await review_schedule_repository.find_pending_by_user_id(db_conn, user_id=test_user["id"])
    matched = [r for r in results if r["note_id"] == note["id"]]
    assert len(matched) == 1
    assert matched[0]["note_topic"] == "テストトピック"
    assert matched[0]["note_summary"] == "テスト要約"


# -----------------------------------------------------------
# mark_completed
# -----------------------------------------------------------


@freeze_time(PAST_TIME)
async def test_mark_completed_updates_status(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    """mark_completed 後に status='completed' になる"""
    note = await _create_test_note(db_conn, test_user["id"])
    past_review = datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC)

    schedule = await review_schedule_repository.insert(db_conn, note_id=note["id"], next_review_at=past_review)

    updated = await review_schedule_repository.mark_completed(
        db_conn,
        schedule_id=schedule["id"],
        user_id=test_user["id"],
        next_review_at=FUTURE_REVIEW,
    )

    assert updated is not None
    assert updated["status"] == "completed"
    assert updated["review_count"] == 1
    assert updated["next_review_at"].replace(tzinfo=UTC) == FUTURE_REVIEW


async def test_mark_completed_rejects_other_user(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    """別ユーザーのスケジュールを mark_completed しても None を返す"""
    note = await _create_test_note(db_conn, test_user["id"])
    next_review = datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC)

    schedule = await review_schedule_repository.insert(db_conn, note_id=note["id"], next_review_at=next_review)

    result = await review_schedule_repository.mark_completed(
        db_conn,
        schedule_id=schedule["id"],
        user_id="other-user-999",
        next_review_at=FUTURE_REVIEW,
    )

    assert result is None


# -----------------------------------------------------------
# update_schedule
# -----------------------------------------------------------


async def test_update_schedule_updates_review_count_and_next_review(
    db_conn: asyncpg.Connection, test_user: dict[str, str]
) -> None:
    """update_schedule が review_count と next_review_at を更新する"""
    note = await _create_test_note(db_conn, test_user["id"])
    initial_review = datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC)

    await review_schedule_repository.insert(db_conn, note_id=note["id"], next_review_at=initial_review)

    new_review = datetime(2026, 4, 23, 10, 0, 0, tzinfo=UTC)
    updated = await review_schedule_repository.update_schedule(
        db_conn,
        note_id=note["id"],
        review_count=3,
        next_review_at=new_review,
    )

    assert updated is not None
    assert updated["review_count"] == 3
    assert updated["next_review_at"].replace(tzinfo=UTC) == new_review
    assert updated["status"] == "pending"


async def test_update_schedule_returns_none_for_nonexistent_note(
    db_conn: asyncpg.Connection, test_user: dict[str, str]
) -> None:
    """存在しない note_id で update_schedule を呼ぶと None を返す"""
    result = await review_schedule_repository.update_schedule(
        db_conn,
        note_id=uuid4(),
        review_count=1,
        next_review_at=FUTURE_REVIEW,
    )
    assert result is None
