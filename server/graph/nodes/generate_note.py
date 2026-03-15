import uuid

from langchain_core.messages import SystemMessage

from core.database import get_pool
from graph.llm import llm_structured
from graph.model import NoteContent
from graph.prompts import GENERATE_NOTE_PROMPT
from graph.state import LearningState
from repositories import note_repository


async def generate_note(state: LearningState) -> dict:
    """会話内容からノートを自動生成してDBに保存"""

    conversation_text = ""
    for msg in state["messages"]:
        role = "ユーザー" if msg.type == "human" else "アシスタント"
        conversation_text += f"{role}: {msg.content}\n"

    structured_llm = llm_structured.with_structured_output(NoteContent)
    note_data = await structured_llm.ainvoke(
        [
            SystemMessage(content=GENERATE_NOTE_PROMPT),
            {"role": "user", "content": conversation_text},
        ]
    )

    note_id = uuid.uuid4()
    pool = await get_pool()

    await note_repository.insert(
        conn=pool,
        note_id=note_id,
        user_id=state["user_id"],
        topic=note_data.topic,
        content=note_data.content,
        summary=note_data.summary,
    )

    return {
        "note_id": note_id,
    }
