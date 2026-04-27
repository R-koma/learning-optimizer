import uuid
from datetime import UTC, datetime, timedelta

import asyncpg
import pytest

from repositories import run_trace_repository

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _insert_dialogue_session(conn: asyncpg.Connection, user_id: str) -> uuid.UUID:
    session_id = uuid.uuid4()
    await conn.execute(
        """--sql
        INSERT INTO dialogue_sessions (id, user_id, session_type, status)
        VALUES ($1, $2, 'learning', 'in_progress')
        """,
        session_id,
        user_id,
    )
    return session_id


async def test_insert_and_list_node_event(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    session_id = await _insert_dialogue_session(db_conn, test_user["id"])
    trace_id = session_id
    span_id = uuid.uuid4()
    started_at = datetime.now(UTC)
    ended_at = started_at + timedelta(milliseconds=120)

    await run_trace_repository.insert_trace_event(
        db_conn,
        dialogue_session_id=session_id,
        user_id=test_user["id"],
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=None,
        event_type="node",
        node_name="learning_start",
        model_name=None,
        status="success",
        started_at=started_at,
        ended_at=ended_at,
        latency_ms=120,
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        dialogue_turn_count=1,
        error_type=None,
        error_message=None,
        metadata={},
    )

    events = await run_trace_repository.list_by_session(db_conn, session_id)
    assert len(events) == 1
    assert events[0]["event_type"] == "node"
    assert events[0]["node_name"] == "learning_start"
    assert events[0]["status"] == "success"
    assert events[0]["latency_ms"] == 120
    assert events[0]["dialogue_turn_count"] == 1
    assert events[0]["input_tokens"] is None


async def test_insert_failed_event_with_error_fields(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    session_id = await _insert_dialogue_session(db_conn, test_user["id"])
    started_at = datetime.now(UTC)
    ended_at = started_at + timedelta(milliseconds=50)

    await run_trace_repository.insert_trace_event(
        db_conn,
        dialogue_session_id=session_id,
        user_id=test_user["id"],
        trace_id=session_id,
        span_id=uuid.uuid4(),
        parent_span_id=None,
        event_type="llm",
        node_name="generate_note",
        model_name="gpt-4.1-nano",
        status="failed",
        started_at=started_at,
        ended_at=ended_at,
        latency_ms=50,
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        dialogue_turn_count=None,
        error_type="RuntimeError",
        error_message="boom",
        metadata={},
    )

    events = await run_trace_repository.list_by_session(db_conn, session_id)
    assert len(events) == 1
    assert events[0]["status"] == "failed"
    assert events[0]["error_type"] == "RuntimeError"
    assert events[0]["error_message"] == "boom"


async def test_summarize_recent_returns_metrics(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    session_id = await _insert_dialogue_session(db_conn, test_user["id"])
    base_started = datetime.now(UTC)

    # node success x2
    for i, latency in enumerate([100, 200]):
        await run_trace_repository.insert_trace_event(
            db_conn,
            dialogue_session_id=session_id,
            user_id=test_user["id"],
            trace_id=session_id,
            span_id=uuid.uuid4(),
            parent_span_id=None,
            event_type="node",
            node_name="learning_start" if i == 0 else "generate_note",
            model_name=None,
            status="success",
            started_at=base_started,
            ended_at=base_started + timedelta(milliseconds=latency),
            latency_ms=latency,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            dialogue_turn_count=i + 1,
            error_type=None,
            error_message=None,
            metadata={},
        )

    # llm success with token usage
    await run_trace_repository.insert_trace_event(
        db_conn,
        dialogue_session_id=session_id,
        user_id=test_user["id"],
        trace_id=session_id,
        span_id=uuid.uuid4(),
        parent_span_id=None,
        event_type="llm",
        node_name="learning_start",
        model_name="gpt-4.1-nano",
        status="success",
        started_at=base_started,
        ended_at=base_started + timedelta(milliseconds=300),
        latency_ms=300,
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        dialogue_turn_count=1,
        error_type=None,
        error_message=None,
        metadata={},
    )

    since = base_started - timedelta(minutes=1)
    summary = await run_trace_repository.summarize_recent(db_conn, since)

    assert summary["success_rate"] == 1.0
    assert summary["p95_latency_ms"] is not None
    assert summary["p95_latency_ms"] > 0
    assert summary["tokens_per_session"] == 150.0
    assert summary["avg_dialogue_turn_count"] == 2.0
    # generate_note は failed が 0 件、success が 1 件 → failure_rate = 0.0
    assert summary["note_generation_failure_rate"] == 0.0


async def test_list_by_session_orders_by_started_at(db_conn: asyncpg.Connection, test_user: dict[str, str]) -> None:
    session_id = await _insert_dialogue_session(db_conn, test_user["id"])
    base = datetime.now(UTC)

    for i, offset_ms in enumerate([300, 100, 200]):
        ts = base + timedelta(milliseconds=offset_ms)
        await run_trace_repository.insert_trace_event(
            db_conn,
            dialogue_session_id=session_id,
            user_id=test_user["id"],
            trace_id=session_id,
            span_id=uuid.uuid4(),
            parent_span_id=None,
            event_type="node",
            node_name=f"node_{i}",
            model_name=None,
            status="success",
            started_at=ts,
            ended_at=ts + timedelta(milliseconds=10),
            latency_ms=10,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            dialogue_turn_count=None,
            error_type=None,
            error_message=None,
            metadata={},
        )

    events = await run_trace_repository.list_by_session(db_conn, session_id)
    assert [e["node_name"] for e in events] == ["node_1", "node_2", "node_0"]
