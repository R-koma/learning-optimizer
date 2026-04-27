import uuid
from typing import Any

import pytest

from observability import llm as llm_module
from observability import tracing
from observability.llm import _extract_token_usage, measured_ainvoke
from observability.tracing import TraceContext

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
def stub_save_trace(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    captured: list[dict[str, Any]] = []

    async def _capture(**kwargs: Any) -> None:
        captured.append(kwargs)

    monkeypatch.setattr(llm_module, "_save_trace_safely", _capture)
    monkeypatch.setattr(tracing, "_save_trace_safely", _capture)
    return captured


def _make_context() -> TraceContext:
    sid = uuid.uuid4()
    return TraceContext(
        dialogue_session_id=sid,
        user_id="test-user-001",
        trace_id=sid,
        parent_span_id=None,
        dialogue_turn_count=1,
    )


class _FakeResponseWithUsage:
    def __init__(self) -> None:
        self.usage_metadata = {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}


class _FakeResponseWithoutUsage:
    pass


class _FakeRunnable:
    def __init__(self, response: Any) -> None:
        self._response = response

    async def ainvoke(self, _messages: Any) -> Any:
        return self._response


class _FailingRunnable:
    async def ainvoke(self, _messages: Any) -> Any:
        raise ValueError("upstream failure")


def test_extract_token_usage_from_usage_metadata() -> None:
    response = _FakeResponseWithUsage()
    assert _extract_token_usage(response) == (10, 20, 30)


def test_extract_token_usage_from_response_metadata() -> None:
    response = type(
        "R",
        (),
        {"response_metadata": {"token_usage": {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12}}},
    )()
    assert _extract_token_usage(response) == (5, 7, 12)


def test_extract_token_usage_returns_none_when_absent() -> None:
    assert _extract_token_usage(_FakeResponseWithoutUsage()) == (None, None, None)


async def test_measured_ainvoke_records_success_and_token_usage(
    stub_save_trace: list[dict[str, Any]],
) -> None:
    runnable = _FakeRunnable(_FakeResponseWithUsage())
    response = await measured_ainvoke(
        runnable=runnable,
        messages=["dummy"],
        context=_make_context(),
        node_name="learning_start",
    )

    assert isinstance(response, _FakeResponseWithUsage)
    assert len(stub_save_trace) == 1
    saved = stub_save_trace[0]
    assert saved["status"] == "success"
    assert saved["event_type"] == "llm"
    assert saved["node_name"] == "learning_start"
    assert saved["model_name"] == "gpt-4.1-nano"
    assert saved["input_tokens"] == 10
    assert saved["output_tokens"] == 20
    assert saved["total_tokens"] == 30


async def test_measured_ainvoke_handles_missing_token_usage(
    stub_save_trace: list[dict[str, Any]],
) -> None:
    runnable = _FakeRunnable(_FakeResponseWithoutUsage())
    await measured_ainvoke(
        runnable=runnable,
        messages=["dummy"],
        context=_make_context(),
        node_name="generate_note",
    )

    assert len(stub_save_trace) == 1
    saved = stub_save_trace[0]
    assert saved["status"] == "success"
    assert saved["input_tokens"] is None
    assert saved["output_tokens"] is None
    assert saved["total_tokens"] is None


async def test_measured_ainvoke_propagates_exception(stub_save_trace: list[dict[str, Any]]) -> None:
    with pytest.raises(ValueError, match="upstream failure"):
        await measured_ainvoke(
            runnable=_FailingRunnable(),
            messages=["dummy"],
            context=_make_context(),
            node_name="generate_feedback",
        )

    assert len(stub_save_trace) == 1
    saved = stub_save_trace[0]
    assert saved["status"] == "failed"
    assert saved["event_type"] == "llm"
    assert saved["error_type"] == "ValueError"
    assert saved["error_message"] == "upstream failure"
