import asyncio
import logging
import uuid
from typing import Any

from langchain_core.messages import SystemMessage

from core.database import get_pool
from graph.llm import llm_structured
from graph.model import AspectMap, NoteContent
from graph.prompts import GENERATE_ASPECT_MAP_PROMPT, GENERATE_NOTE_PROMPT
from graph.state import LearningState
from observability.llm import measured_ainvoke
from observability.tracing import build_trace_context
from repositories import note_repository

logger = logging.getLogger(__name__)


async def generate_note(state: LearningState) -> dict[str, Any]:
    """会話内容からノートと観点マップを並列生成し DB に保存"""

    conversation_text = ""
    for msg in state["messages"]:
        role = "ユーザー" if msg.type == "human" else "アシスタント"
        conversation_text += f"{role}: {msg.content}\n"

    trace_context = build_trace_context(state)

    note_llm = llm_structured.with_structured_output(NoteContent)
    aspect_llm = llm_structured.with_structured_output(AspectMap)

    note_task = measured_ainvoke(
        runnable=note_llm,
        messages=[
            SystemMessage(content=GENERATE_NOTE_PROMPT),
            {"role": "user", "content": conversation_text},
        ],
        context=trace_context,
        node_name="generate_note",
    )
    aspect_task = measured_ainvoke(
        runnable=aspect_llm,
        messages=[
            SystemMessage(content=GENERATE_ASPECT_MAP_PROMPT),
            {"role": "user", "content": conversation_text},
        ],
        context=trace_context,
        node_name="generate_aspect_map",
    )

    results = await asyncio.gather(
        note_task,
        aspect_task,
        return_exceptions=True,
    )
    note_result: Any = results[0]
    aspect_result: Any = results[1]

    if isinstance(note_result, BaseException):
        raise note_result
    if not isinstance(note_result, NoteContent):
        raise RuntimeError("LLM did not return structured NoteContent output")

    aspect_payload: str | None = None
    if isinstance(aspect_result, AspectMap):
        aspect_payload = aspect_result.model_dump_json()
    else:
        logger.warning(
            "aspect map generation failed; persisting note without aspect_map: %r",
            aspect_result,
        )

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
            aspect_map=aspect_payload,
        )

    return {
        "note_id": note_id,
    }


__all__ = ["generate_note"]
