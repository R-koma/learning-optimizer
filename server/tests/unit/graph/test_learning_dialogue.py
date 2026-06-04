from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage

from graph.state import LearningState

SESSION_ID = UUID("00000000-0000-0000-0000-000000000002")
NOTE_ID = UUID("00000000-0000-0000-0000-000000000001")

_FAKE_PROMPT = MagicMock(return_value=("QUESTION_PROMPT", "dialogue"))


def _make_state(messages: list[Any], **overrides: object) -> LearningState:
    base: dict[str, object] = {
        "user_id": "user-abc",
        "dialogue_session_id": SESSION_ID,
        "note_id": NOTE_ID,
        "messages": messages,
        "topic": "二分探索",
        "turn_count": 2,
        "should_generate_note": False,
        "session_type": "learning",
    }
    base.update(overrides)
    return cast(LearningState, base)


class TestLearningDialogue:
    async def test_increments_turn_count(self) -> None:
        with (
            patch(
                "graph.nodes.learning_dialogue.invoke_dialogue_llm",
                AsyncMock(return_value=AIMessage(content="質問です")),
            ),
            patch("graph.nodes.learning_dialogue.build_question_prompt", _FAKE_PROMPT),
        ):
            from graph.nodes.learning_dialogue import learning_dialogue

            result = await learning_dialogue(_make_state([HumanMessage(content="hi")], turn_count=2))

        assert result["turn_count"] == 3

    async def test_should_generate_note_is_always_false(self) -> None:
        with (
            patch(
                "graph.nodes.learning_dialogue.invoke_dialogue_llm",
                AsyncMock(return_value=AIMessage(content="質問です")),
            ),
            patch("graph.nodes.learning_dialogue.build_question_prompt", _FAKE_PROMPT),
        ):
            from graph.nodes.learning_dialogue import learning_dialogue

            result = await learning_dialogue(_make_state([HumanMessage(content="hi")]))

        assert result["should_generate_note"] is False

    async def test_appends_response_message(self) -> None:
        response = AIMessage(content="次はどう考えますか？")
        with (
            patch("graph.nodes.learning_dialogue.invoke_dialogue_llm", AsyncMock(return_value=response)),
            patch("graph.nodes.learning_dialogue.build_question_prompt", _FAKE_PROMPT),
        ):
            from graph.nodes.learning_dialogue import learning_dialogue

            result = await learning_dialogue(_make_state([HumanMessage(content="hi")]))

        assert result["messages"] == [response]

    async def test_passes_only_recent_six_messages_to_question_prompt(self) -> None:
        messages = [HumanMessage(content=f"m{i}") for i in range(8)]
        mock_build = MagicMock(return_value=("QUESTION_PROMPT", "dialogue"))
        with (
            patch(
                "graph.nodes.learning_dialogue.invoke_dialogue_llm",
                AsyncMock(return_value=AIMessage(content="質問です")),
            ),
            patch("graph.nodes.learning_dialogue.build_question_prompt", mock_build),
        ):
            from graph.nodes.learning_dialogue import learning_dialogue

            await learning_dialogue(_make_state(messages))

        recent = mock_build.call_args.kwargs["recent_messages"]
        assert "m2" in recent and "m7" in recent  # 直近6件は含む
        assert "m0" not in recent and "m1" not in recent  # それより前は含まない
