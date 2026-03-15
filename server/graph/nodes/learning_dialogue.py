from langchain_core.messages import SystemMessage

from graph.llm import llm
from graph.prompts import DEEP_DIVE_SYSTEM_PROMPT
from graph.state import LearningState

MAX_TURNS = 3
LEARNING_END_SIGNAL = "LEARNING_END"


async def learning_dialogue(state: LearningState) -> dict:
    """深掘りLLMとの対話継続"""
    system_message = SystemMessage(content=DEEP_DIVE_SYSTEM_PROMPT)
    all_messages = [system_message] + state["messages"]

    response = await llm.ainvoke(all_messages)

    turn_count = state["turn_count"] + 1
    should_generate_note = turn_count >= MAX_TURNS or response.content.strip() == LEARNING_END_SIGNAL

    return {
        "messages": [response],
        "turn_count": turn_count,
        "should_generate_note": should_generate_note,
    }
