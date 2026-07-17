from typing import cast
from unittest.mock import AsyncMock, patch
from uuid import UUID

from graph.nodes._turn_analysis import analyze_dialogue_turn
from graph.output_schemas import AspectObservation, DialogueTurnAnalysis
from graph.state import LearningState

_STATE = cast(
    LearningState,
    {
        "user_id": "user-abc",
        "dialogue_session_id": UUID("00000000-0000-0000-0000-000000000002"),
        "note_id": UUID("00000000-0000-0000-0000-000000000001"),
        "messages": [],
        "topic": "二分探索",
        "turn_count": 2,
        "should_generate_note": False,
        "session_type": "learning",
    },
)

_PLAN_FIELDS = {
    "learning_goal": "未指定",
    "target_depth_label": "自分の言葉で説明できるレベル",
    "focus_aspects": "未指定",
}


async def _run(mock_invoke: AsyncMock) -> DialogueTurnAnalysis | None:
    with patch("graph.nodes._turn_analysis.measured_ainvoke", mock_invoke):
        return await analyze_dialogue_turn(
            _STATE,
            recent_messages="ユーザー: 二分探索は…",
            plan_fields=_PLAN_FIELDS,
            covered_aspects=[{"aspect": "前提条件", "reached_depth": "defined"}],
        )


class TestAnalyzeDialogueTurn:
    async def test_returns_analysis_on_success(self) -> None:
        analysis = DialogueTurnAnalysis(
            observations=[AspectObservation(aspect="計算量", reached_depth="defined")],
            response_mode="expand",
            selected_aspect="計算量",
        )
        result = await _run(AsyncMock(return_value=analysis))
        assert result is analysis

    async def test_returns_none_on_llm_failure(self) -> None:
        result = await _run(AsyncMock(side_effect=RuntimeError("llm down")))
        assert result is None

    async def test_returns_none_on_unexpected_payload(self) -> None:
        result = await _run(AsyncMock(return_value={"response_mode": "expand"}))
        assert result is None

    async def test_prompt_includes_coverage_and_topic(self) -> None:
        analysis = DialogueTurnAnalysis(observations=[], response_mode="expand", selected_aspect="計算量")
        mock_invoke = AsyncMock(return_value=analysis)
        await _run(mock_invoke)
        prompt = mock_invoke.call_args.kwargs["messages"][0].content
        assert "二分探索" in prompt
        assert "- 前提条件: defined（定義済み）" in prompt
        assert mock_invoke.call_args.kwargs["node_name"] == "turn_analysis"
