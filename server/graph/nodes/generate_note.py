import asyncio
import logging
import uuid
from typing import Any
from uuid import UUID

from langchain_core.messages import SystemMessage

from core.database import get_pool
from graph.llm import llm_structured
from graph.output_schemas import AspectMap, NoteContent
from graph.prompts import GENERATE_ASPECT_MAP_PROMPT, GENERATE_NOTE_PROMPT
from graph.state import LearningState
from observability.llm import measured_ainvoke
from observability.tracing import TraceContext, build_trace_context
from repositories import note_repository

logger = logging.getLogger(__name__)


async def _generate_aspect_map_background(
    note_id: UUID,
    conversation_text: str,
    trace_context: TraceContext,
) -> None:
    aspect_llm = llm_structured.with_structured_output(AspectMap)
    try:
        aspect_result: Any = await measured_ainvoke(
            runnable=aspect_llm,
            messages=[
                SystemMessage(content=GENERATE_ASPECT_MAP_PROMPT),
                {"role": "user", "content": conversation_text},
            ],
            context=trace_context,
            node_name="generate_aspect_map",
        )
    except Exception:
        logger.warning("aspect map generation failed for note %s", note_id, exc_info=True)
        return

    if not isinstance(aspect_result, AspectMap):
        logger.warning("aspect map generation returned unexpected type for note %s", note_id)
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        await note_repository.update_aspect_map(conn, note_id, aspect_result.model_dump_json())


async def generate_note(state: LearningState) -> dict[str, Any]:
    """会話内容からノートを生成し DB に保存。観点マップは後追いで生成する"""

    conversation_text = ""
    for msg in state["messages"]:
        role = "ユーザー" if msg.type == "human" else "アシスタント"
        conversation_text += f"{role}: {msg.content}\n"

    trace_context = build_trace_context(state)

    note_llm = llm_structured.with_structured_output(NoteContent)
    note_result: Any = await measured_ainvoke(
        runnable=note_llm,
        messages=[
            SystemMessage(content=GENERATE_NOTE_PROMPT),
            {"role": "user", "content": conversation_text},
        ],
        context=trace_context,
        node_name="generate_note",
    )
    if not isinstance(note_result, NoteContent):
        raise RuntimeError("LLM did not return structured NoteContent output")

    note_id = uuid.uuid4()
    pool = await get_pool()

    async with pool.acquire() as conn:
        await note_repository.insert(
            conn=conn,
            note_id=note_id,
            user_id=state["user_id"],
            topic=note_result.topic,
            content=note_result.content,
            summary=note_result.summary,
            aspect_map=None,
        )

    asyncio.create_task(_generate_aspect_map_background(note_id, conversation_text, trace_context))

    return {
        "note_id": note_id,
    }


__all__ = ["generate_note"]
