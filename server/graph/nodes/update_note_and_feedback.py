from typing import Any

from langchain_core.messages import SystemMessage

from core.database import get_pool
from graph.llm import llm_structured
from graph.model import FeedbackOutput, NoteContent
from graph.prompts import ANALYZE_RESPONSE_PROMPT, GENERATE_FEEDBACK_PROMPT, UPDATE_NOTE_PROMPT
from graph.state import LearningState
from repositories import feedback_repository, note_repository, review_schedule_repository
from services.review_scheduler import calculate_next_review


async def update_note_and_feedback(state: LearningState) -> dict[str, Any]:
    """復習対話の内容で既存ノートを上書き更新し、フィードバックを UPSERT する"""

    pool = await get_pool()
    note_id = state["note_id"]
    user_id = state["user_id"]

    conversation_history = "\n".join(
        f"{'ユーザー' if msg.type == 'human' else 'AI'}: {msg.content}" for msg in state["messages"]
    )

    async with pool.acquire() as conn:
        existing_note = await note_repository.find_by_id(conn, note_id, user_id)
        if not existing_note:
            raise RuntimeError(f"Note {note_id} not found")

        topic = existing_note["topic"]

        update_note_prompt = UPDATE_NOTE_PROMPT.format(
            topic=topic,
            summary=existing_note["summary"] or "",
            content=existing_note["content"],
            conversation_history=conversation_history,
        )
        note_structured_llm = llm_structured.with_structured_output(NoteContent)
        revised_note = await note_structured_llm.ainvoke([SystemMessage(content=update_note_prompt)])
        if not isinstance(revised_note, NoteContent):
            raise RuntimeError("LLM did not return structured NoteContent output")

        await note_repository.update(
            conn=conn,
            note_id=note_id,
            user_id=user_id,
            content=revised_note.content,
            summary=revised_note.summary,
        )

        analyze_prompt = ANALYZE_RESPONSE_PROMPT.format(
            topic=topic,
            conversation_history=conversation_history,
        )
        analysis_result = await llm_structured.ainvoke([SystemMessage(content=analyze_prompt)])
        analysis = analysis_result.content

        note_text = f"トピック: {topic}\n\n{revised_note.content}"
        feedback_prompt = GENERATE_FEEDBACK_PROMPT.format(topic=topic, analysis=analysis)
        feedback_structured_llm = llm_structured.with_structured_output(FeedbackOutput)
        feedback_data = await feedback_structured_llm.ainvoke(
            [
                SystemMessage(content=feedback_prompt),
                {"role": "user", "content": note_text},
            ]
        )
        if not isinstance(feedback_data, FeedbackOutput):
            raise RuntimeError("LLM did not return structured FeedbackOutput")

        await feedback_repository.upsert_for_note(
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
