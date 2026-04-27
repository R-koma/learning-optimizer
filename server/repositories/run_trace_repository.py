import json
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

import asyncpg


async def insert_trace_event(
    conn: asyncpg.Connection,
    *,
    dialogue_session_id: UUID,
    user_id: str,
    trace_id: UUID,
    span_id: UUID,
    parent_span_id: UUID | None,
    event_type: Literal["node", "llm"],
    node_name: str | None,
    model_name: str | None,
    status: Literal["success", "failed"],
    started_at: datetime,
    ended_at: datetime,
    latency_ms: int,
    input_tokens: int | None,
    output_tokens: int | None,
    total_tokens: int | None,
    dialogue_turn_count: int | None,
    error_type: str | None,
    error_message: str | None,
    metadata: dict[str, Any],
) -> None:
    query = """--sql
    INSERT INTO run_traces (
        dialogue_session_id, user_id, trace_id, span_id, parent_span_id,
        event_type, node_name, model_name, status,
        started_at, ended_at, latency_ms,
        input_tokens, output_tokens, total_tokens,
        dialogue_turn_count, error_type, error_message, metadata
    ) VALUES (
        $1, $2, $3, $4, $5,
        $6, $7, $8, $9,
        $10, $11, $12,
        $13, $14, $15,
        $16, $17, $18, $19::jsonb
    )
    """
    await conn.execute(
        query,
        str(dialogue_session_id),
        user_id,
        str(trace_id),
        str(span_id),
        str(parent_span_id) if parent_span_id is not None else None,
        event_type,
        node_name,
        model_name,
        status,
        started_at,
        ended_at,
        latency_ms,
        input_tokens,
        output_tokens,
        total_tokens,
        dialogue_turn_count,
        error_type,
        error_message,
        json.dumps(metadata),
    )


async def list_by_session(
    conn: asyncpg.Connection,
    dialogue_session_id: UUID,
) -> list[dict[str, Any]]:
    query = """--sql
    SELECT *
    FROM run_traces
    WHERE dialogue_session_id = $1
    ORDER BY started_at ASC
    """
    records = await conn.fetch(query, str(dialogue_session_id))
    return [dict(record) for record in records]


async def summarize_recent(
    conn: asyncpg.Connection,
    since: datetime,
) -> dict[str, Any]:
    """直近期間の主要指標を集計する。

    返り値の指標:
      - success_rate: event_type='node' の成功率 (0.0-1.0 or None)
      - p95_latency_ms: 全 trace の latency_ms P95 (int or None)
      - tokens_per_session: session ごとの total_tokens 合計の平均 (float or None)
      - avg_dialogue_turn_count: session ごとの最終 turn_count の平均 (float or None)
      - note_generation_failure_rate: generate_note ノードの failed 比率 (0.0-1.0 or None)
    """
    node_query = """--sql
    SELECT
        COUNT(*) FILTER (WHERE status = 'success')::float
            / NULLIF(COUNT(*), 0) AS success_rate
    FROM run_traces
    WHERE event_type = 'node' AND created_at >= $1
    """
    node_row = await conn.fetchrow(node_query, since)

    p95_query = """--sql
    SELECT
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95
    FROM run_traces
    WHERE created_at >= $1
    """
    p95_row = await conn.fetchrow(p95_query, since)

    tokens_query = """--sql
    SELECT AVG(session_total)::float AS tokens_per_session
    FROM (
        SELECT dialogue_session_id, SUM(total_tokens) AS session_total
        FROM run_traces
        WHERE created_at >= $1 AND total_tokens IS NOT NULL
        GROUP BY dialogue_session_id
    ) t
    """
    tokens_row = await conn.fetchrow(tokens_query, since)

    turns_query = """--sql
    SELECT AVG(max_turn)::float AS avg_dialogue_turn_count
    FROM (
        SELECT dialogue_session_id, MAX(dialogue_turn_count) AS max_turn
        FROM run_traces
        WHERE created_at >= $1 AND dialogue_turn_count IS NOT NULL
        GROUP BY dialogue_session_id
    ) t
    """
    turns_row = await conn.fetchrow(turns_query, since)

    note_failure_query = """--sql
    SELECT
        COUNT(*) FILTER (WHERE status = 'failed')::float
            / NULLIF(COUNT(*), 0) AS note_failure_rate
    FROM run_traces
    WHERE event_type = 'node'
      AND node_name = 'generate_note'
      AND created_at >= $1
    """
    note_row = await conn.fetchrow(note_failure_query, since)

    p95_value = p95_row["p95"] if p95_row else None
    return {
        "success_rate": node_row["success_rate"] if node_row else None,
        "p95_latency_ms": int(p95_value) if p95_value is not None else None,
        "tokens_per_session": tokens_row["tokens_per_session"] if tokens_row else None,
        "avg_dialogue_turn_count": turns_row["avg_dialogue_turn_count"] if turns_row else None,
        "note_generation_failure_rate": note_row["note_failure_rate"] if note_row else None,
    }
