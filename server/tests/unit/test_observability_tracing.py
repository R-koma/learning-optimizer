import uuid
from typing import Any

import pytest

from observability import tracing
from observability.tracing import build_trace_context, measured_node

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
def stub_save_trace(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """`_save_trace_safely` を monkeypatch し、呼び出し記録を返す。"""
    captured: list[dict[str, Any]] = []

    async def _capture(**kwargs: Any) -> None:
        captured.append(kwargs)

    monkeypatch.setattr(tracing, "_save_trace_safely", _capture)
    return captured


def _make_state(session_id_value: Any) -> dict[str, Any]:
    return {
        "user_id": "test-user-001",
        "dialogue_session_id": session_id_value,
        "turn_count": 1,
    }


def test_build_trace_context_accepts_uuid() -> None:
    sid = uuid.uuid4()
    ctx = build_trace_context(_make_state(sid))  # type: ignore[arg-type]
    assert ctx.dialogue_session_id == sid
    assert ctx.trace_id == sid
    assert ctx.user_id == "test-user-001"
    assert ctx.dialogue_turn_count == 1
    assert ctx.parent_span_id is None


def test_build_trace_context_normalizes_string() -> None:
    sid = uuid.uuid4()
    ctx = build_trace_context(_make_state(str(sid)))  # type: ignore[arg-type]
    assert ctx.dialogue_session_id == sid
    assert ctx.trace_id == sid


async def test_measured_node_preserves_return_value(stub_save_trace: list[dict[str, Any]]) -> None:
    async def handler(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": ["ok"], "turn_count": state["turn_count"] + 1}

    wrapped = measured_node("learning_start", handler)  # type: ignore[arg-type]
    result = await wrapped(_make_state(uuid.uuid4()))  # type: ignore[arg-type]

    assert result == {"messages": ["ok"], "turn_count": 2}
    assert len(stub_save_trace) == 1
    saved = stub_save_trace[0]
    assert saved["status"] == "success"
    assert saved["event_type"] == "node"
    assert saved["node_name"] == "learning_start"
    assert saved["latency_ms"] >= 0


async def test_measured_node_propagates_exception_and_records_failed(
    stub_save_trace: list[dict[str, Any]],
) -> None:
    async def handler(state: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("boom")

    wrapped = measured_node("generate_note", handler)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="boom"):
        await wrapped(_make_state(uuid.uuid4()))  # type: ignore[arg-type]

    assert len(stub_save_trace) == 1
    saved = stub_save_trace[0]
    assert saved["status"] == "failed"
    assert saved["event_type"] == "node"
    assert saved["node_name"] == "generate_note"
    assert saved["error_type"] == "RuntimeError"
    assert saved["error_message"] == "boom"
