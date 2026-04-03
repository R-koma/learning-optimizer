from langchain_core.messages import SystemMessage

from graph.llm import llm
from graph.prompts import DEEP_DIVE_SYSTEM_PROMPT, REVIEW_SYSTEM_PROMPT
from graph.state import LearningState

LEARNING_END_SIGNAL = "LEARNING_END"


async def learning_dialogue(state: LearningState) -> dict:
    """深掘りLLMとの対話継続"""
    session_type = state.get("session_type", "learning")

    if session_type == "review":
        prompt = REVIEW_SYSTEM_PROMPT.format(
            topic=state["topic"],
            content=state.get("note_content", ""),
            summary=state.get("note_summary", ""),
        )
    else:
        prompt = DEEP_DIVE_SYSTEM_PROMPT

    system_message = SystemMessage(content=prompt)
    all_messages = [system_message] + state["messages"]

    response = await llm.ainvoke(all_messages)

    turn_count = state["turn_count"] + 1
    should_generate_note = response.content.strip() == LEARNING_END_SIGNAL

    return {
        "messages": [response],
        "turn_count": turn_count,
        "should_generate_note": should_generate_note,
    }
