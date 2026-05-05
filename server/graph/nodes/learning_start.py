from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graph.llm import llm
from graph.prompts import LEARNING_PLANNER_PROMPT, REVIEW_SYSTEM_PROMPT
from graph.state import LearningState
from observability.llm import measured_ainvoke
from observability.tracing import build_trace_context


async def learning_start(state: LearningState) -> dict[str, Any]:
    """学習フローの開始：トピック抽出 + 深掘りLLMの初期応答"""
    topic = state["topic"]
    session_type = state.get("session_type", "learning")

    if session_type == "review":
        prompt = REVIEW_SYSTEM_PROMPT.format(
            topic=topic,
            content=state.get("note_content"),
            summary=state.get("note_summary"),
        )
    else:
        prompt = LEARNING_PLANNER_PROMPT

    user_message = HumanMessage(content=topic)
    response = await measured_ainvoke(
        runnable=llm,
        messages=[SystemMessage(content=prompt), user_message],
        context=build_trace_context(state),
        node_name="learning_start",
    )

    return {
        "messages": [user_message, response],
        "turn_count": 1,
        "should_generate_note": False,
    }
