from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch
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
    "focus_aspects": "未指定",
}


async def _run(mock_invoke: AsyncMock) -> DialogueTurnAnalysis | None:
    mock_runnable = MagicMock(ainvoke=mock_invoke)
    mock_llm_structured = MagicMock()
    mock_llm_structured.with_structured_output.return_value.with_config.return_value = mock_runnable
    with patch("graph.nodes._turn_analysis.llm_structured", mock_llm_structured):
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
            has_misconception=False,
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
        analysis = DialogueTurnAnalysis(
            observations=[], has_misconception=False, response_mode="expand", selected_aspect="計算量"
        )
        mock_invoke = AsyncMock(return_value=analysis)
        await _run(mock_invoke)
        prompt = mock_invoke.call_args.args[0][0].content
        assert "二分探索" in prompt
        assert "- 前提条件: defined（定義済み）" in prompt
        assert "到達目標は exemplified" in prompt
        assert mock_invoke.call_args.kwargs["config"]["run_name"] == "turn-analysis"

    async def test_prompt_asks_for_the_misconception_check_before_the_mode(self) -> None:
        """誤りの判定を response_mode より前に置く順序を固定する。

        後ろに置くと深さだけでモードが決まり、誤りを一度も見ないまま deepen / expand に到達できる
        （capture した 12 ターンすべてで reinforce が選ばれなかったのがこの形）。
        """
        analysis = DialogueTurnAnalysis(
            observations=[], has_misconception=False, response_mode="expand", selected_aspect="計算量"
        )
        mock_invoke = AsyncMock(return_value=analysis)
        await _run(mock_invoke)
        prompt = str(mock_invoke.call_args.args[0][0].content)

        assert prompt.index("`has_misconception`") < prompt.index("`response_mode`")

    async def test_a_flagged_misconception_forces_reinforce(self) -> None:
        """訂正セクションがプロンプトに載る条件は response_mode == reinforce なので、揃っていないと届かない。"""
        analysis = DialogueTurnAnalysis(
            observations=[],
            has_misconception=True,
            error_summary="並行処理を仕組みそのものとして述べている",
            response_mode="deepen",
            selected_aspect="プロセスの管理",
        )
        result = await _run(AsyncMock(return_value=analysis))

        assert result is not None
        assert result.response_mode == "reinforce"
        assert result.error_summary == "並行処理を仕組みそのものとして述べている"

    async def test_a_clean_turn_keeps_the_chosen_mode(self) -> None:
        analysis = DialogueTurnAnalysis(
            observations=[], has_misconception=False, response_mode="expand", selected_aspect="計算量"
        )
        result = await _run(AsyncMock(return_value=analysis))

        assert result is not None
        assert result.response_mode == "expand"
