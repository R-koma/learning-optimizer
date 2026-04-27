import uuid
from datetime import UTC, datetime
from typing import Any

from observability.tracing import TraceContext, _save_trace_safely


def _extract_token_usage(response: Any) -> tuple[int | None, int | None, int | None]:
    """LangChain の応答から token 使用量を取り出す。

    取得経路の優先順位:
      1. response.usage_metadata (AIMessage の標準)
      2. response.response_metadata["token_usage"] (OpenAI 互換)

    structured output 経由の場合 Pydantic モデルが返り、これらが無い。その場合は全て None。
    """
    usage = getattr(response, "usage_metadata", None)
    if isinstance(usage, dict):
        return (
            usage.get("input_tokens"),
            usage.get("output_tokens"),
            usage.get("total_tokens"),
        )

    response_metadata = getattr(response, "response_metadata", None)
    if isinstance(response_metadata, dict):
        token_usage = response_metadata.get("token_usage")
        if isinstance(token_usage, dict):
            input_tokens = token_usage.get("prompt_tokens")
            output_tokens = token_usage.get("completion_tokens")
            total_tokens = token_usage.get("total_tokens")
            return (input_tokens, output_tokens, total_tokens)

    return (None, None, None)


async def measured_ainvoke(
    *,
    runnable: Any,
    messages: Any,
    context: TraceContext,
    node_name: str,
    model_name: str = "gpt-4.1-nano",
) -> Any:
    """LLM (もしくは structured output runnable) の `ainvoke` を計測ラッパーで包む。

    - 開始/終了時刻と status を記録
    - token usage が取れる場合のみ記録、取れない場合は None
    - 例外発生時は failed trace を保存して例外を再 raise（伝播は変えない）
    - DB 書き込み失敗は warning ログのみ
    - メッセージ本文・プロンプト本文は metadata に保存しない
    """
    span_id = uuid.uuid4()
    started_at = datetime.now(UTC)
    try:
        response = await runnable.ainvoke(messages)
    except Exception as exc:
        ended_at = datetime.now(UTC)
        latency_ms = int((ended_at - started_at).total_seconds() * 1000)
        await _save_trace_safely(
            dialogue_session_id=context.dialogue_session_id,
            user_id=context.user_id,
            trace_id=context.trace_id,
            span_id=span_id,
            parent_span_id=context.parent_span_id,
            event_type="llm",
            node_name=node_name,
            model_name=model_name,
            status="failed",
            started_at=started_at,
            ended_at=ended_at,
            latency_ms=latency_ms,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            dialogue_turn_count=context.dialogue_turn_count,
            error_type=type(exc).__name__,
            error_message=str(exc),
            metadata={},
        )
        raise

    ended_at = datetime.now(UTC)
    latency_ms = int((ended_at - started_at).total_seconds() * 1000)
    input_tokens, output_tokens, total_tokens = _extract_token_usage(response)
    await _save_trace_safely(
        dialogue_session_id=context.dialogue_session_id,
        user_id=context.user_id,
        trace_id=context.trace_id,
        span_id=span_id,
        parent_span_id=context.parent_span_id,
        event_type="llm",
        node_name=node_name,
        model_name=model_name,
        status="success",
        started_at=started_at,
        ended_at=ended_at,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        dialogue_turn_count=context.dialogue_turn_count,
        error_type=None,
        error_message=None,
        metadata={},
    )
    return response
