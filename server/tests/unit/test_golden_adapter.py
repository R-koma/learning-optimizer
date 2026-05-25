from typing import Any, cast

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from evals.golden.adapter import (
    build_generate_question_prompt,
    generate_question_output,
    recent_system_questions,
)
from evals.golden.schema import GoldenInput, GraphState, LearnerProfile, LearningPlanContext, Turn


def _input() -> GoldenInput:
    return GoldenInput(
        learner_profile=LearnerProfile(level="undergrad"),
        conversation_history=[
            Turn(role="system_question", content="信頼性とは何ですか？"),
            Turn(role="learner", content="障害が起きても動くこと。"),
            Turn(role="system_question", content="具体例を挙げられますか？"),
            Turn(role="learner", content="RAID で冗長化する。"),
        ],
        graph_state=GraphState(current_topic="信頼性", depth=2),
    )


class _FakeLLM:
    def __init__(self, content: str) -> None:
        self._content = content

    async def ainvoke(self, _messages: Any) -> AIMessage:
        return AIMessage(content=self._content)


class TestRecentSystemQuestions:
    def test_extracts_only_system_questions(self) -> None:
        assert recent_system_questions(_input()) == ("信頼性とは何ですか？", "具体例を挙げられますか？")


class TestBuildPrompt:
    def test_prompt_includes_topic(self) -> None:
        prompt, intent = build_generate_question_prompt(_input())
        assert isinstance(prompt, str)
        assert "信頼性" in prompt
        assert isinstance(intent, str)

    def test_learning_plan_reflected_in_prompt(self) -> None:
        record_input = _input()
        record_input.learning_plan = LearningPlanContext(
            target_depth="apply",
            learning_goal="DDIA の信頼性を体系的に理解する",
        )
        prompt, _ = build_generate_question_prompt(record_input)
        assert "DDIA の信頼性を体系的に理解する" in prompt

    def test_falls_back_when_no_plan(self) -> None:
        # learning_plan 無しでも例外なくプロンプトを構築できる（recognize フォールバック）
        prompt, _ = build_generate_question_prompt(_input())
        assert prompt


class TestGenerateQuestionOutput:
    async def test_returns_llm_text(self) -> None:
        llm = cast(ChatOpenAI, _FakeLLM("ではフォールトの種類は何だと思いますか？"))
        output = await generate_question_output(_input(), llm=llm)
        assert output == "ではフォールトの種類は何だと思いますか？"
