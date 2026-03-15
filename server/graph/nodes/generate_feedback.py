from langchain_core.messages import SystemMessage

from core.database import get_pool
from graph.llm import llm_structured
from graph.model import FeedbackOutput
from graph.prompts import GENERATE_FEEDBACK_PROMPT
from graph.state import LearningState
from repositories import feedback_repository, note_repository, review_schedule_repository
from services.review_scheduler import calculate_next_review


async def generate_feedback(state: LearningState) -> dict:
    """ノート内容から理解度評価を生成しDBに保存"""

    pool = await get_pool()
    note_id = state["note_id"]

    note = await note_repository.find_by_id(pool, note_id, state["user_id"])

    note_text = f"トピック: {note['topic']}\n\n{note['content']}"

    structured_llm = llm_structured.with_structured_output(FeedbackOutput)
    feedback_data = await structured_llm.ainvoke(
        [
            SystemMessage(content=GENERATE_FEEDBACK_PROMPT),
            {"role": "user", "content": note_text},
        ]
    )

    await feedback_repository.insert(
        conn=pool,
        note_id=note_id,
        dialogue_session_id=state["dialogue_session_id"],
        understanding_level=feedback_data.understanding_level,
        strength="\n".join(feedback_data.strength),
        improvements="\n".join(feedback_data.improvement_points),
    )

    existing_schedule = await review_schedule_repository.find_by_note_id(conn=pool, note_id=note_id)
    current_review_count = existing_schedule["review_count"] if existing_schedule else 0

    next_review_at = calculate_next_review(
        current_review_count=current_review_count,
        understanding_level=feedback_data.understanding_level,
    )

    if existing_schedule:
        await review_schedule_repository.update_schedule(
            conn=pool,
            note_id=note_id,
            review_count=current_review_count + 1,
            next_review_at=next_review_at,
        )
    else:
        await review_schedule_repository.insert(conn=pool, note_id=note_id, next_review_at=next_review_at)

    return {}
