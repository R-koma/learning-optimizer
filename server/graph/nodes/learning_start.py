from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graph.llm import llm
from graph.prompts import LEARNING_PLANNER_PROMPT, format_learning_plan_fields
from graph.state import LearningState


async def learning_start(state: LearningState) -> dict[str, Any]:
    """学習フローの開始：学習プランに基づく深掘り LLM の初期応答"""
    topic = state["topic"]
    plan_fields = format_learning_plan_fields(
        learning_goal=state.get("learning_goal"),
        focus_aspects=state.get("focus_aspects"),
    )
    prompt = LEARNING_PLANNER_PROMPT.format(topic=topic, **plan_fields)

    user_message = HumanMessage(content=topic)
    response = await llm.ainvoke([SystemMessage(content=prompt), user_message])

    return {
        "messages": [user_message, response],
        "turn_count": 1,
        "should_generate_note": False,
    }
