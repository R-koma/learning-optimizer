from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graph.llm import llm
from graph.prompts import LEARNING_START_PROMPT, REVIEW_SYSTEM_PROMPT
from graph.state import LearningState


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
        prompt = LEARNING_START_PROMPT.format(topic=topic)

    user_message = HumanMessage(content=topic)
    response = await llm.ainvoke([SystemMessage(content=prompt), user_message])

    return {
        "messages": [user_message, response],
        "turn_count": 1,
        "should_generate_note": False,
    }
