from langchain_core.messages import HumanMessage, SystemMessage

from graph.llm import llm
from graph.prompts import DEEP_DIVE_SYSTEM_PROMPT
from graph.state import LearningState


async def learning_start(state: LearningState) -> dict:
    """学習フローの開始：トピック抽出 + 深掘りLLMの初期応答"""
    topic = state["topic"]

    user_message = HumanMessage(content=topic)
    response = await llm.ainvoke([SystemMessage(content=DEEP_DIVE_SYSTEM_PROMPT), user_message])

    return {
        "messages": [user_message, response],
        "turn_count": 1,
        "should_generate_note": False,
    }
