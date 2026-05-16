from langchain_core.messages import AIMessage, HumanMessage

from graph.prompts.question import (
    MODE_DIALOGUE,
    MODE_HINT,
    MODE_UNKNOWN_A,
    MODE_UNKNOWN_B,
    MODE_UNKNOWN_C,
    build_question_prompt,
    classify_user_intent,
)

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
        assert "応答モード（この順で判断する）" in prompt
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
