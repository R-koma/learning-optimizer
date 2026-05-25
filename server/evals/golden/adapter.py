"""golden record の input を generate_question の実行に橋渡しする。

golden の `conversation_history`（role=system_question / learner）を
`build_question_prompt` が要求する形（messages 列・recent_messages テキスト・
topic・plan_fields）へ変換する。学習プラン情報（learning_goal 等）は golden
input に含まれないため既定値を用いる。
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from evals.golden.schema import GoldenInput, Turn
from graph.llm import llm as default_llm
from graph.prompts import build_question_prompt, format_learning_plan_fields
from graph.state import TargetDepth

_DEFAULT_TARGET_DEPTH: TargetDepth = "recognize"


def _to_message(turn: Turn) -> AIMessage | HumanMessage:
    return AIMessage(content=turn.content) if turn.role == "system_question" else HumanMessage(content=turn.content)


def _display_role(turn: Turn) -> str:
    return "AI" if turn.role == "system_question" else "ユーザー"


def recent_system_questions(record_input: GoldenInput) -> tuple[str, ...]:
    """deterministic check（paraphrase 検出）が参照する過去のシステム質問。"""
    return tuple(t.content for t in record_input.conversation_history if t.role == "system_question")


def build_generate_question_prompt(record_input: GoldenInput) -> tuple[str, str]:
    """golden input から generate_question プロンプトを構築する。"""
    history = record_input.conversation_history
    messages: list[Any] = [_to_message(t) for t in history]
    recent_messages = "\n".join(f"{_display_role(t)}: {t.content}" for t in history)
    plan = record_input.learning_plan
    plan_fields = format_learning_plan_fields(
        learning_goal=plan.learning_goal if plan else None,
        target_depth=plan.target_depth if plan else _DEFAULT_TARGET_DEPTH,
        focus_aspects=plan.focus_aspects if plan else None,
    )
    prompt, intent = build_question_prompt(
        topic=record_input.graph_state.current_topic,
        recent_messages=recent_messages,
        plan_fields=plan_fields,
        messages=messages,
    )
    return prompt, intent


async def generate_question_output(record_input: GoldenInput, *, llm: ChatOpenAI | None = None) -> str:
    """golden input に対して generate_question を実行し、応答テキストを返す。"""
    prompt, _intent = build_generate_question_prompt(record_input)
    effective_llm = llm or default_llm
    response = await effective_llm.ainvoke([SystemMessage(content=prompt)])
    return response.content if isinstance(response.content, str) else str(response.content)
