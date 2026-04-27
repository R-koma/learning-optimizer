import logging
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from core.database import get_pool
from graph.state import LearningState
from repositories import run_trace_repository

logger = logging.getLogger(__name__)

NodeHandler = Callable[[LearningState], Coroutine[Any, Any, dict[str, Any]]]


@dataclass(frozen=True)
class TraceContext:
    dialogue_session_id: UUID
    user_id: str
    trace_id: UUID
    parent_span_id: UUID | None
    dialogue_turn_count: int | None


def build_trace_context(state: LearningState) -> TraceContext:
    """LearningState から TraceContext を組み立てる。

    state["dialogue_session_id"] は型上 UUID だが、WebSocket 経由では str で
    流入することがあるため、str / UUID の両方を受けて UUID に正規化する。
    """
    sid_raw: Any = state["dialogue_session_id"]
    sid: UUID = sid_raw if isinstance(sid_raw, UUID) else UUID(str(sid_raw))
    return TraceContext(
        dialogue_session_id=sid,
        user_id=state["user_id"],
        trace_id=sid,
        parent_span_id=None,
        dialogue_turn_count=state.get("turn_count"),
    )


async def _save_trace_safely(
    *,
    dialogue_session_id: UUID,
    user_id: str,
    trace_id: UUID,
    span_id: UUID,
    parent_span_id: UUID | None,
    event_type: str,
    node_name: str | None,
    model_name: str | None,
    status: str,
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
    """trace event を DB に保存する。書き込み失敗は warning に留め、本体処理を止めない。"""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await run_trace_repository.insert_trace_event(
                conn,
                dialogue_session_id=dialogue_session_id,
                user_id=user_id,
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                event_type=event_type,  # type: ignore[arg-type]
                node_name=node_name,
                model_name=model_name,
                status=status,  # type: ignore[arg-type]
                started_at=started_at,
                ended_at=ended_at,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                dialogue_turn_count=dialogue_turn_count,
                error_type=error_type,
                error_message=error_message,
                metadata=metadata,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("failed to persist run_trace event: %s", exc)


def measured_node(node_name: str, handler: NodeHandler) -> NodeHandler:
    """LangGraph ノードを計測ラッパーで包む。

    - 開始/終了時刻と status を記録
    - 例外発生時は failed trace を保存して例外を再 raise（伝播は変えない）
    - 戻り値はそのまま返す
    - DB 書き込み失敗は warning ログのみ
    """

    async def wrapper(state: LearningState) -> dict[str, Any]:
        ctx = build_trace_context(state)
        span_id = uuid.uuid4()
        started_at = datetime.now(UTC)
        try:
            result = await handler(state)
        except Exception as exc:
            ended_at = datetime.now(UTC)
            latency_ms = int((ended_at - started_at).total_seconds() * 1000)
            await _save_trace_safely(
                dialogue_session_id=ctx.dialogue_session_id,
                user_id=ctx.user_id,
                trace_id=ctx.trace_id,
                span_id=span_id,
                parent_span_id=ctx.parent_span_id,
                event_type="node",
                node_name=node_name,
                model_name=None,
                status="failed",
                started_at=started_at,
                ended_at=ended_at,
                latency_ms=latency_ms,
                input_tokens=None,
                output_tokens=None,
                total_tokens=None,
                dialogue_turn_count=ctx.dialogue_turn_count,
                error_type=type(exc).__name__,
                error_message=str(exc),
                metadata={},
            )
            raise

        ended_at = datetime.now(UTC)
        latency_ms = int((ended_at - started_at).total_seconds() * 1000)
        await _save_trace_safely(
            dialogue_session_id=ctx.dialogue_session_id,
            user_id=ctx.user_id,
            trace_id=ctx.trace_id,
            span_id=span_id,
            parent_span_id=ctx.parent_span_id,
            event_type="node",
            node_name=node_name,
            model_name=None,
            status="success",
            started_at=started_at,
            ended_at=ended_at,
            latency_ms=latency_ms,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            dialogue_turn_count=ctx.dialogue_turn_count,
            error_type=None,
            error_message=None,
            metadata={},
        )
        return result

    return wrapper
