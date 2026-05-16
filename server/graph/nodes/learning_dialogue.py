from typing import Any

from langchain_core.messages import SystemMessage

from graph.llm import llm
from graph.prompts import (
    REVIEW_SYSTEM_PROMPT,
    build_question_prompt,
    format_learning_plan_fields,
)
from graph.state import LearningState
from observability.llm import measured_ainvoke
from observability.tracing import build_trace_context

LEARNING_END_SIGNAL = "LEARNING_END"


async def learning_dialogue(state: LearningState) -> dict[str, Any]:
    """対話継続: ファシリテーターとして説明を促す（評価はしない）"""
    session_type = state.get("session_type", "learning")
    topic = state["topic"]
    trace_ctx = build_trace_context(state)

    if session_type == "review":
        prompt = REVIEW_SYSTEM_PROMPT.format(
            topic=topic,
            content=state.get("note_content", ""),
            summary=state.get("note_summary", ""),
        )
        system_message = SystemMessage(content=prompt)
        all_messages = [system_message, *state["messages"]]
        response = await measured_ainvoke(
            runnable=llm,
            messages=all_messages,
            context=trace_ctx,
            node_name="learning_dialogue",
        )

        turn_count = state["turn_count"] + 1
        content = response.content
        should_generate_note = isinstance(content, str) and content.strip() == LEARNING_END_SIGNAL

        return {
            "messages": [response],
            "turn_count": turn_count,
            "should_generate_note": should_generate_note,
        }

    recent_messages = "\n".join(
        f"{'ユーザー' if msg.type == 'human' else 'AI'}: {msg.content}" for msg in state["messages"][-6:]
    )
    plan_fields = format_learning_plan_fields(
        learning_goal=state.get("learning_goal"),
        target_depth=state.get("target_depth") or "recognize",
        focus_aspects=state.get("focus_aspects"),
    )
    question_prompt, _intent = build_question_prompt(
        topic=topic,
        recent_messages=recent_messages,
        plan_fields=plan_fields,
        messages=state["messages"],
    )
    response = await measured_ainvoke(
        runnable=llm,
        messages=[SystemMessage(content=question_prompt)],
        context=trace_ctx,
        node_name="learning_dialogue",
    )

    turn_count = state["turn_count"] + 1

    return {
        "messages": [response],
        "turn_count": turn_count,
        "should_generate_note": False,
    }
