from typing import Any

from langchain_core.messages import SystemMessage

from core.database import get_pool
from graph.llm import llm_structured
from graph.model import FeedbackOutput
from graph.prompts import ANALYZE_RESPONSE_PROMPT, GENERATE_FEEDBACK_PROMPT
from graph.state import LearningState
from observability.llm import measured_ainvoke
from observability.tracing import build_trace_context
from repositories import feedback_repository, note_repository, review_schedule_repository
from services.review_scheduler import calculate_next_review


async def generate_feedback(state: LearningState) -> dict[str, Any]:
    """会話履歴を分析し、理解度評価を生成してDBに保存"""

    pool = await get_pool()
    topic = state["topic"]
    trace_ctx = build_trace_context(state)

    conversation_history = "\n".join(
        f"{'ユーザー' if msg.type == 'human' else 'AI'}: {msg.content}" for msg in state["messages"]
    )
    analyze_prompt = ANALYZE_RESPONSE_PROMPT.format(
        topic=topic,
        conversation_history=conversation_history,
    )
    analysis_result = await measured_ainvoke(
        runnable=llm_structured,
        messages=[SystemMessage(content=analyze_prompt)],
        context=trace_ctx,
        node_name="generate_feedback",
    )
    analysis = analysis_result.content

    note_id = state["note_id"]

    feedback_prompt = GENERATE_FEEDBACK_PROMPT.format(topic=topic, analysis=analysis)
    structured_llm = llm_structured.with_structured_output(FeedbackOutput)

    async with pool.acquire() as conn:
        note = await note_repository.find_by_id(conn, note_id, state["user_id"])
        if not note:
            raise RuntimeError(f"Note {note_id} not found")
        note_text = f"トピック: {note['topic']}\n\n{note['content']}"

        feedback_data = await measured_ainvoke(
            runnable=structured_llm,
            messages=[
                SystemMessage(content=feedback_prompt),
                {"role": "user", "content": note_text},
            ],
            context=trace_ctx,
            node_name="generate_feedback",
        )

        if not isinstance(feedback_data, FeedbackOutput):
            raise RuntimeError("LLM did not return structured FeedbackOutput")

        await feedback_repository.insert(
            conn=conn,
            note_id=note_id,
            dialogue_session_id=state["dialogue_session_id"],
            understanding_level=feedback_data.understanding_level,
            strength="\n".join(feedback_data.strength),
            improvements="\n".join(feedback_data.improvement_points),
        )

        existing_schedule = await review_schedule_repository.find_by_note_id(conn=conn, note_id=note_id)
        current_review_count: int = existing_schedule["review_count"] if existing_schedule else 0

        next_review_at = calculate_next_review(current_review_count=current_review_count)

        if existing_schedule:
            await review_schedule_repository.update_schedule(
                conn=conn,
                note_id=note_id,
                review_count=current_review_count + 1,
                next_review_at=next_review_at,
            )
        else:
            await review_schedule_repository.insert(conn=conn, note_id=note_id, next_review_at=next_review_at)

    return {}
