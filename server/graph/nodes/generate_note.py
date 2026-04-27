import uuid
from typing import Any

from langchain_core.messages import SystemMessage

from core.database import get_pool
from graph.llm import llm_structured
from graph.model import NoteContent
from graph.prompts import GENERATE_NOTE_PROMPT
from graph.state import LearningState
from observability.llm import measured_ainvoke
from observability.tracing import build_trace_context
from repositories import note_repository


async def generate_note(state: LearningState) -> dict[str, Any]:
    """会話内容からノートを自動生成してDBに保存"""

    conversation_text = ""
    for msg in state["messages"]:
        role = "ユーザー" if msg.type == "human" else "アシスタント"
        conversation_text += f"{role}: {msg.content}\n"

    structured_llm = llm_structured.with_structured_output(NoteContent)
    note_data = await measured_ainvoke(
        runnable=structured_llm,
        messages=[
            SystemMessage(content=GENERATE_NOTE_PROMPT),
            {"role": "user", "content": conversation_text},
        ],
        context=build_trace_context(state),
        node_name="generate_note",
    )

    if not isinstance(note_data, NoteContent):
        raise RuntimeError("LLM did not return structured NoteContent output")

    note_id = uuid.uuid4()
    pool = await get_pool()

    async with pool.acquire() as conn:
        await note_repository.insert(
            conn=conn,
            note_id=note_id,
            user_id=state["user_id"],
            topic=note_data.topic,
            content=note_data.content,
            summary=note_data.summary,
        )

    return {
        "note_id": note_id,
    }
