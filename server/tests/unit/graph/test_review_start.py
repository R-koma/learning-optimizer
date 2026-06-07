from typing import cast
from unittest.mock import AsyncMock, patch
from uuid import UUID

from langchain_core.messages import AIMessage, SystemMessage

from graph.prompts.review import build_focus_section
from graph.state import LearningState

SESSION_ID = UUID("00000000-0000-0000-0000-000000000002")
NOTE_ID = UUID("00000000-0000-0000-0000-000000000001")


def _make_state(**overrides: object) -> LearningState:
    base: dict[str, object] = {
        "user_id": "user-abc",
        "dialogue_session_id": SESSION_ID,
        "note_id": NOTE_ID,
        "messages": [],
        "topic": "二分探索",
        "turn_count": 0,
        "should_generate_note": False,
        "session_type": "review",
        "note_content": "二分探索のノート本文",
        "note_summary": "二分探索の要約",
    }
    base.update(overrides)
    return cast(LearningState, base)


class TestBuildFocusSection:
    def test_returns_section_when_improvements_present(self) -> None:
        section = build_focus_section("計算量の見積もりが曖昧でした")
        assert "重点確認項目" in section
        assert "計算量の見積もりが曖昧でした" in section

    def test_returns_empty_for_none(self) -> None:
        assert build_focus_section(None) == ""

    def test_returns_empty_for_blank(self) -> None:
        assert build_focus_section("   ") == ""


class TestReviewStart:
    async def test_uses_review_system_prompt(self) -> None:
        mock_llm = AsyncMock(return_value=AIMessage(content="覚えていることを教えてください"))
        with patch("graph.nodes.review_start.invoke_dialogue_llm", mock_llm):
            from graph.nodes.review_start import review_start

            await review_start(_make_state())

        _state, messages, node_name = mock_llm.call_args.args
        assert node_name == "review_start"
        assert isinstance(messages[0], SystemMessage)
        assert "復習パートナー" in messages[0].content

    async def test_prior_improvements_injected_into_prompt(self) -> None:
        mock_llm = AsyncMock(return_value=AIMessage(content="覚えていることを教えてください"))
        with patch("graph.nodes.review_start.invoke_dialogue_llm", mock_llm):
            from graph.nodes.review_start import review_start

            await review_start(_make_state(prior_improvements="計算量の見積もりが曖昧でした"))

        _state, messages, _node_name = mock_llm.call_args.args
        assert "重点確認項目" in messages[0].content
        assert "計算量の見積もりが曖昧でした" in messages[0].content

    async def test_no_prior_improvements_omits_focus_section(self) -> None:
        mock_llm = AsyncMock(return_value=AIMessage(content="覚えていることを教えてください"))
        with patch("graph.nodes.review_start.invoke_dialogue_llm", mock_llm):
            from graph.nodes.review_start import review_start

            await review_start(_make_state())

        _state, messages, _node_name = mock_llm.call_args.args
        assert "重点確認項目" not in messages[0].content
