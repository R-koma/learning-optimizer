import pytest
from langchain_core.messages import AIMessage, HumanMessage

from graph.output_schemas import DialogueTurnAnalysis
from graph.prompts import question
from graph.prompts.question import (
    MODE_DIALOGUE,
    MODE_HINT,
    MODE_UNKNOWN_A,
    MODE_UNKNOWN_B,
    MODE_UNKNOWN_C,
    build_question_prompt,
    classify_user_intent,
)
from graph.state import CoveredAspect

_PLAN_FIELDS = {
    "learning_goal": "未指定",
    "target_depth_label": "自分の言葉で説明できるレベル",
    "focus_aspects": "未指定",
}


class TestClassifyUserIntent:
    def test_empty_returns_dialogue(self) -> None:
        assert classify_user_intent([]) == "dialogue"

    def test_substantive_returns_dialogue(self) -> None:
        messages = [HumanMessage(content="ReAct は推論と行動を交互に行うエージェントです。")]
        assert classify_user_intent(messages) == "dialogue"

    def test_exhausted_keyword(self) -> None:
        messages = [
            HumanMessage(content="ReAct は推論と行動を交互に行うエージェントです。"),
            AIMessage(content="他に補足することはありますか？"),
            HumanMessage(content="以上です"),
        ]
        assert classify_user_intent(messages) == "exhausted"

    def test_unknown_a_when_no_prior_explanation(self) -> None:
        messages = [HumanMessage(content="わかりません")]
        assert classify_user_intent(messages) == "unknown_a"

    def test_unknown_b_when_prior_substantive_exists(self) -> None:
        messages = [
            HumanMessage(
                content="ReAct は推論と行動を交互に行うエージェントです。CoT との違いは複雑な行動を扱える点です。"
            ),
            AIMessage(content="トレードオフがある場面はありますか？"),
            HumanMessage(content="わかりません"),
        ]
        assert classify_user_intent(messages) == "unknown_b"

    def test_unknown_c_when_consecutive(self) -> None:
        messages = [
            HumanMessage(content="ReAct は推論と行動を組み合わせます。具体例として検索エージェントがあります。"),
            AIMessage(content="その仕組みは？"),
            HumanMessage(content="わかりません"),
            AIMessage(content="では別の角度から？"),
            HumanMessage(content="わからない"),
        ]
        assert classify_user_intent(messages) == "unknown_c"


class TestBuildQuestionPrompt:
    def _build(self, messages: list[object]) -> tuple[str, str]:
        prompt, intent = build_question_prompt(
            topic="ReAct",
            recent_messages="ユーザー: わかりません",
            plan_fields=_PLAN_FIELDS,
            messages=messages,
        )
        return prompt, intent

    def test_dialogue_includes_dialogue_section(self) -> None:
        prompt, intent = self._build([HumanMessage(content="ReAct は推論と行動を交互に行うエージェントです。")])
        assert intent == "dialogue"
        assert "応答モードの判定原則（最初にこれで分岐する）" in prompt
        assert MODE_DIALOGUE.splitlines()[0] in prompt

    def test_unknown_a_section(self) -> None:
        prompt, intent = self._build([HumanMessage(content="わかりません")])
        assert intent == "unknown_a"
        assert MODE_UNKNOWN_A.splitlines()[0] in prompt

    def test_unknown_b_section(self) -> None:
        prompt, intent = self._build(
            [
                HumanMessage(content="ReAct は推論と行動を組み合わせます。具体例として検索エージェントがあります。"),
                AIMessage(content="その仕組みは？"),
                HumanMessage(content="わかりません"),
            ]
        )
        assert intent == "unknown_b"
        assert MODE_UNKNOWN_B.splitlines()[0] in prompt

    def test_unknown_c_section(self) -> None:
        prompt, intent = self._build(
            [
                HumanMessage(content="ReAct は推論と行動を組み合わせます。具体例として検索エージェントがあります。"),
                HumanMessage(content="わかりません"),
                HumanMessage(content="わからない"),
            ]
        )
        assert intent == "unknown_c"
        assert MODE_UNKNOWN_C.splitlines()[0] in prompt

    def test_exhausted_section(self) -> None:
        prompt, intent = self._build(
            [
                HumanMessage(content="ReAct は推論と行動を組み合わせます。具体例として検索エージェントがあります。"),
                HumanMessage(content="以上です"),
            ]
        )
        assert intent == "exhausted"
        assert MODE_HINT.splitlines()[0] in prompt

    def test_plan_fields_are_interpolated(self) -> None:
        prompt, _ = self._build([HumanMessage(content="ReAct は推論と行動を交互に行うエージェントです。")])
        assert "自分の言葉で説明できるレベル" in prompt
        assert "ReAct" in prompt


_DIALOGUE_MESSAGES = [HumanMessage(content="ReAct は推論と行動を交互に行うエージェントです。")]


def _build_with(**kwargs: object) -> tuple[str, str]:
    prompt, intent = build_question_prompt(
        topic="ReAct",
        recent_messages="ユーザー: ReAct は…",
        plan_fields=_PLAN_FIELDS,
        messages=_DIALOGUE_MESSAGES,
        **kwargs,  # type: ignore[arg-type]
    )
    return prompt, intent


class TestCoverageSection:
    def test_covered_aspects_are_rendered(self) -> None:
        covered: list[CoveredAspect] = [{"aspect": "推論と行動の交互実行", "reached_depth": "defined"}]
        prompt, _ = _build_with(covered_aspects=covered)
        assert "## カバー済み観点と到達度（過去ターン累積）" in prompt
        assert "- 推論と行動の交互実行: defined（定義済み）" in prompt

    def test_empty_coverage_omits_section(self) -> None:
        prompt, _ = _build_with(covered_aspects=[])
        assert "## カバー済み観点と到達度" not in prompt

    def test_default_is_omitted(self) -> None:
        prompt, _ = _build_with()
        assert "## カバー済み観点と到達度" not in prompt


class TestPredecidedMode:
    def _analysis(self, mode: str, error_summary: str = "") -> DialogueTurnAnalysis:
        return DialogueTurnAnalysis(
            observations=[],
            response_mode=mode,  # type: ignore[arg-type]
            selected_aspect="ツール呼び出し",
            error_summary=error_summary,
        )

    def test_no_analysis_falls_back_to_self_judged_dialogue(self) -> None:
        prompt, intent = _build_with()
        assert intent == "dialogue"
        assert "応答モードの判定原則（最初にこれで分岐する）" in prompt

    def test_expand_includes_mode_b_and_c_without_decision_principle(self) -> None:
        prompt, _ = _build_with(turn_analysis=self._analysis("expand"))
        assert "## 応答モード（事前分析による決定）" in prompt
        assert "「展開（モード B）」で行うと決定済み" in prompt
        assert "焦点を当てる観点: ツール呼び出し" in prompt
        assert "### モード B: 展開" in prompt
        assert "### モード C: 深掘り / 具体化" in prompt
        assert "### モード A: 誤りの訂正" not in prompt
        assert "応答モードの判定原則" not in prompt

    def test_reinforce_includes_only_mode_a_with_error_summary(self) -> None:
        analysis = self._analysis("reinforce", "レイテンシとレスポンスタイムを混同している")
        prompt, _ = _build_with(turn_analysis=analysis)
        assert "「誤りの訂正（モード A）」で行うと決定済み" in prompt
        assert "検出された誤り: レイテンシとレスポンスタイムを混同している" in prompt
        assert "### モード A: 誤りの訂正" in prompt
        assert "### モード B: 展開" not in prompt

    def test_deepen_includes_only_mode_c(self) -> None:
        prompt, _ = _build_with(turn_analysis=self._analysis("deepen"))
        assert "### モード C: 深掘り / 具体化" in prompt
        assert "### モード A: 誤りの訂正" not in prompt
        assert "### モード B: 展開" not in prompt

    def test_shared_rules_always_present(self) -> None:
        for mode in ("reinforce", "expand", "deepen"):
            prompt, _ = _build_with(turn_analysis=self._analysis(mode))
            assert "## 既出観点の取り扱い（最重要）" in prompt
            assert "## メニュー化の禁止（最重要）" in prompt

    def test_analysis_ignored_for_non_dialogue_intent(self) -> None:
        prompt, intent = build_question_prompt(
            topic="ReAct",
            recent_messages="ユーザー: わかりません",
            plan_fields=_PLAN_FIELDS,
            messages=[HumanMessage(content="わかりません")],
            turn_analysis=self._analysis("expand"),
        )
        assert intent == "unknown_a"
        assert "事前分析による決定" not in prompt


class TestPromptFingerprint:
    def test_is_stable_across_calls(self) -> None:
        assert question._prompt_fingerprint() == question._prompt_fingerprint()
        assert question.PROMPT_FINGERPRINT == question._prompt_fingerprint()

    def test_changes_when_base_text_changes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        before = question._prompt_fingerprint()
        monkeypatch.setattr(question, "QUESTION_PROMPT_BASE", question.QUESTION_PROMPT_BASE + "\n追記")
        assert question._prompt_fingerprint() != before

    def test_changes_when_a_mode_section_changes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        before = question._prompt_fingerprint()
        monkeypatch.setitem(question._MODE_SECTIONS, "exhausted", question.MODE_HINT + "\n追記")
        assert question._prompt_fingerprint() != before

    def test_changes_when_predecided_assembly_changes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        before = question._prompt_fingerprint()
        monkeypatch.setitem(question._PREDECIDED_MODE_LABELS, "expand", "展開（モード B・改）")
        assert question._prompt_fingerprint() != before
