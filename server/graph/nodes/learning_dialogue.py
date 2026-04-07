from langchain_core.messages import SystemMessage

from graph.llm import llm
from graph.prompts import GENERATE_QUESTION_PROMPT, REVIEW_SYSTEM_PROMPT
from graph.state import LearningState

LEARNING_END_SIGNAL = "LEARNING_END"


async def learning_dialogue(state: LearningState) -> dict:
    """対話継続: ファシリテーターとして説明を促す（評価はしない）"""
    session_type = state.get("session_type", "learning")
    topic = state["topic"]

    if session_type == "review":
        prompt = REVIEW_SYSTEM_PROMPT.format(
            topic=topic,
            content=state.get("note_content", ""),
            summary=state.get("note_summary", ""),
        )
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

    recent_messages = "\n".join(
        f"{'ユーザー' if msg.type == 'human' else 'AI'}: {msg.content}" for msg in state["messages"][-6:]
    )
    question_prompt = GENERATE_QUESTION_PROMPT.format(
        topic=topic,
        recent_messages=recent_messages,
    )
    response = await llm.ainvoke([SystemMessage(content=question_prompt)])

    turn_count = state["turn_count"] + 1

    return {
        "messages": [response],
        "turn_count": turn_count,
        "should_generate_note": False,
    }
