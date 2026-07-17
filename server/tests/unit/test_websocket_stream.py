import json
from typing import Any
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessageChunk

from api.websocket.chat import _stream_ai_response
from graph.llm import INTERNAL_LLM_TAG


class _FakeGraph:
    def __init__(self, events: list[tuple[Any, dict[str, Any]]]) -> None:
        self._events = events

    async def astream(self, input: Any, config: Any, stream_mode: str) -> Any:
        for event in self._events:
            yield event


async def test_internal_llm_chunks_are_not_streamed_to_client() -> None:
    events: list[tuple[Any, dict[str, Any]]] = [
        (AIMessageChunk(content="表示する"), {"langgraph_node": "learning_dialogue", "tags": []}),
        (
            AIMessageChunk(content='{"response_mode": "expand"}'),
            {"langgraph_node": "learning_dialogue", "tags": [INTERNAL_LLM_TAG]},
        ),
        (AIMessageChunk(content="チャンク"), {"langgraph_node": "learning_dialogue"}),
    ]
    websocket = AsyncMock()

    content = await _stream_ai_response(_FakeGraph(events), None, {}, websocket)

    assert content == "表示するチャンク"
    sent = [json.loads(call.args[0]) for call in websocket.send_text.call_args_list]
    chunk_contents = [m["content"] for m in sent if m.get("type") == "assistant_message_chunk"]
    assert chunk_contents == ["表示する", "チャンク"]


async def test_non_streaming_nodes_are_filtered() -> None:
    events: list[tuple[Any, dict[str, Any]]] = [
        (AIMessageChunk(content="分析結果"), {"langgraph_node": "generate_feedback", "tags": []}),
    ]
    websocket = AsyncMock()

    content = await _stream_ai_response(_FakeGraph(events), None, {}, websocket)

    assert content == ""
    sent = [json.loads(call.args[0]) for call in websocket.send_text.call_args_list]
    assert [m["type"] for m in sent] == ["assistant_message_end"]
