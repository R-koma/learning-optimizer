import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Literal, cast
from uuid import UUID

import asyncpg
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import AIMessageChunk, HumanMessage, RemoveMessage
from pydantic import BaseModel, TypeAdapter, ValidationError

from api.websocket.auth import authenticate_websocket
from core.database import get_pool
from repositories import (
    dialogue_message_repository,
    dialogue_session_repository,
    feedback_repository,
    note_repository,
)
from schemas.websocket_message import (
    AssistantMessageChunk,
    AssistantMessageEnd,
    CancelLastMessageError,
    CancelLastMessageRequest,
    CancelLastMessageSuccess,
    EndSessionMessage,
    ErrorMessage,
    FeedbackGeneratedMessage,
    IncomingMessage,
    NoteGeneratedMessage,
    ResumeSessionMessage,
    SessionEndedMessage,
    SessionResumedMessage,
    SessionStartedMessage,
    StartLearningMessage,
    StartReviewMessage,
    UserMessage,
)

logger = logging.getLogger(__name__)

_STREAMING_NODES = {"learning_start", "learning_dialogue"}
MIN_TURNS_BEFORE_NOTE = 3

_incoming_adapter: TypeAdapter[IncomingMessage] = TypeAdapter(IncomingMessage)


@dataclass
class SessionContext:
    session_id: UUID
    config: dict[str, Any]
    session_type: Literal["learning", "review"]
    message_order: int
    is_session_ended: bool = False


@dataclass
class Deps:
    pool: asyncpg.Pool
    graph: Any
    websocket: WebSocket
    user_id: str


async def _generate_note_background(
    pool: asyncpg.Pool,
    graph: Any,
    config: dict[str, Any],
    session_id: UUID,
) -> None:
    try:
        result = await graph.ainvoke(None, config=config)
        # learning は generate_note で新規 note_id が state に設定される
        # review は start_review 時点で既存 note_id が state に注入されている
        generated_note_id: UUID | None = result.get("note_id")
        async with pool.acquire() as conn:
            if generated_note_id is not None:
                await dialogue_session_repository.update_note_id(conn, session_id, generated_note_id)
            else:
                await dialogue_session_repository.update_status(conn, session_id, "completed")
    except Exception:
        logger.exception("Background note generation failed for session %s", session_id)
        async with pool.acquire() as conn:
            await dialogue_session_repository.update_status(conn, session_id, "failed")


async def _stream_ai_response(graph: Any, input: Any, config: dict[str, Any], websocket: WebSocket) -> str:
    ai_content = ""
    async for msg, metadata in graph.astream(input, config, stream_mode="messages"):
        node = metadata.get("langgraph_node", "")
        if isinstance(msg, AIMessageChunk) and node in _STREAMING_NODES and msg.content:
            chunk = str(msg.content)
            ai_content += chunk
            await websocket.send_text(AssistantMessageChunk(content=chunk).model_dump_json())
    await websocket.send_text(AssistantMessageEnd().model_dump_json())
    return ai_content


async def _start_session(
    *,
    session_type: Literal["learning", "review"],
    deps: Deps,
    initial_state: dict[str, Any],
    first_user_content: str,
) -> SessionContext:
    """セッション作成・SessionStarted 送信・初期 user/assistant メッセージ保存までを共通化。"""
    session_id = uuid.uuid4()
    config = {"configurable": {"thread_id": str(session_id)}}

    message_order = 1
    async with deps.pool.acquire() as conn:
        await dialogue_session_repository.abandon_active_by_user(conn, deps.user_id)
        await dialogue_session_repository.create(
            conn=conn,
            session_id=session_id,
            user_id=deps.user_id,
            session_type=session_type,
        )
        await dialogue_message_repository.insert(conn, session_id, "user", first_user_content, message_order)

    await deps.websocket.send_text(
        SessionStartedMessage(session_id=session_id, session_type=session_type).model_dump_json()
    )

    initial_state["dialogue_session_id"] = str(session_id)

    ai_msg = await _stream_ai_response(deps.graph, initial_state, config, deps.websocket)
    message_order += 1
    async with deps.pool.acquire() as conn:
        await dialogue_message_repository.insert(conn, session_id, "assistant", ai_msg, message_order)

    return SessionContext(
        session_id=session_id,
        config=config,
        session_type=session_type,
        message_order=message_order,
    )


async def _finalize_session(result: dict[str, Any], ctx: SessionContext, deps: Deps) -> list[BaseModel]:
    """ノート生成完了時にクライアントへ送るメッセージ列を返す（送信順）。"""
    outgoing: list[BaseModel] = []
    note_id: UUID | None = result.get("note_id")
    if note_id is None:
        return outgoing

    async with deps.pool.acquire() as conn:
        await dialogue_session_repository.update_note_id(conn, ctx.session_id, note_id)

        if ctx.session_type == "review":
            feedbacks = await feedback_repository.find_by_note_id(conn, note_id, deps.user_id)
            if feedbacks:
                latest = feedbacks[-1]
                outgoing.append(
                    FeedbackGeneratedMessage(
                        understanding_level=latest["understanding_level"],
                        strength=latest["strength"],
                        improvements=latest["improvements"],
                    )
                )

        note = await note_repository.find_by_id(conn, note_id, deps.user_id)
    if note:
        outgoing.append(
            NoteGeneratedMessage(
                note_id=note_id,
                topic=note["topic"],
                summary=note["summary"] or "",
            )
        )
    return outgoing


async def _handle_start_learning(msg: StartLearningMessage, deps: Deps) -> SessionContext:
    initial_state: dict[str, Any] = {
        "user_id": deps.user_id,
        "topic": msg.topic,
        "turn_count": 0,
        "should_generate_note": False,
        "session_type": "learning",
    }
    if msg.learning_goal and msg.learning_goal.strip():
        initial_state["learning_goal"] = msg.learning_goal.strip()
    if msg.target_depth is not None:
        initial_state["target_depth"] = msg.target_depth
    if msg.focus_aspects:
        cleaned_aspects = [a.strip() for a in msg.focus_aspects if a and a.strip()]
        if cleaned_aspects:
            initial_state["focus_aspects"] = cleaned_aspects

    return await _start_session(
        session_type="learning",
        deps=deps,
        initial_state=initial_state,
        first_user_content=msg.topic,
    )


async def _handle_start_review(msg: StartReviewMessage, deps: Deps) -> SessionContext | None:
    async with deps.pool.acquire() as conn:
        note = await note_repository.find_by_id(conn, msg.note_id, deps.user_id)
    if not note:
        await deps.websocket.send_text(ErrorMessage(detail="Note not found").model_dump_json())
        return None

    initial_state: dict[str, Any] = {
        "user_id": deps.user_id,
        "note_id": msg.note_id,
        "topic": note["topic"],
        "note_content": note["content"],
        "note_summary": note["summary"] or "",
        "turn_count": 0,
        "should_generate_note": False,
        "session_type": "review",
    }
    return await _start_session(
        session_type="review",
        deps=deps,
        initial_state=initial_state,
        first_user_content=note["topic"],
    )


async def _handle_resume_session(msg: ResumeSessionMessage, deps: Deps) -> SessionContext | None:
    async with deps.pool.acquire() as conn:
        existing = await dialogue_session_repository.find_by_id(conn, msg.session_id, deps.user_id)
    if not existing:
        await deps.websocket.send_text(ErrorMessage(detail="Session not found").model_dump_json())
        return None

    if existing["status"] not in ("in_progress", "disconnect"):
        await deps.websocket.send_text(ErrorMessage(detail="Session is not resumable").model_dump_json())
        return None

    if existing["session_type"] not in ("learning", "review"):
        await deps.websocket.send_text(ErrorMessage(detail="Invalid session type").model_dump_json())
        return None

    resumed_session_type = cast(Literal["learning", "review"], existing["session_type"])
    config = {"configurable": {"thread_id": str(msg.session_id)}}

    async with deps.pool.acquire() as conn:
        if existing["status"] == "disconnect":
            await dialogue_session_repository.update_status(conn, msg.session_id, "in_progress")
        last_order = await conn.fetchval(
            "SELECT COALESCE(MAX(message_order), 0) FROM dialogue_messages WHERE dialogue_session_id = $1",
            str(msg.session_id),
        )
    message_order = int(last_order or 0)

    await deps.websocket.send_text(
        SessionResumedMessage(
            session_id=msg.session_id,
            session_type=resumed_session_type,
        ).model_dump_json()
    )

    return SessionContext(
        session_id=msg.session_id,
        config=config,
        session_type=resumed_session_type,
        message_order=message_order,
    )


async def _handle_user_message(msg: UserMessage, ctx: SessionContext, deps: Deps) -> SessionContext:
    ctx.message_order += 1
    async with deps.pool.acquire() as conn:
        await dialogue_message_repository.insert(conn, ctx.session_id, "user", msg.content, ctx.message_order)

    await deps.graph.aupdate_state(
        ctx.config,
        {"messages": [HumanMessage(content=msg.content)]},
    )

    ai_msg = await _stream_ai_response(deps.graph, None, ctx.config, deps.websocket)
    ctx.message_order += 1
    async with deps.pool.acquire() as conn:
        await dialogue_message_repository.insert(conn, ctx.session_id, "assistant", ai_msg, ctx.message_order)

    state = await deps.graph.aget_state(ctx.config)
    result = state.values

    if not result.get("should_generate_note"):
        return ctx

    if result.get("turn_count", 0) < MIN_TURNS_BEFORE_NOTE:
        await deps.graph.aupdate_state(ctx.config, {"should_generate_note": False})
        return ctx

    ctx.is_session_ended = True
    async with deps.pool.acquire() as conn:
        await dialogue_session_repository.update_status(conn, ctx.session_id, "completed")

    for payload in await _finalize_session(result, ctx, deps):
        await deps.websocket.send_text(payload.model_dump_json())

    await deps.websocket.send_text(SessionEndedMessage().model_dump_json())
    return ctx


async def _handle_cancel_last_message(ctx: SessionContext, deps: Deps) -> SessionContext:
    if ctx.is_session_ended:
        await deps.websocket.send_text(CancelLastMessageError(detail="Session already ended").model_dump_json())
        return ctx

    if ctx.message_order < 4:
        await deps.websocket.send_text(CancelLastMessageError(detail="No cancellable message").model_dump_json())
        return ctx

    state = await deps.graph.aget_state(ctx.config)
    messages_in_state = state.values["messages"]

    last_ai = messages_in_state[-1]
    last_human = messages_in_state[-2]
    cancelled_content = str(last_human.content)

    await deps.graph.aupdate_state(
        ctx.config,
        {
            "messages": [
                RemoveMessage(id=last_ai.id),
                RemoveMessage(id=last_human.id),
            ],
            "turn_count": state.values["turn_count"] - 1,
        },
    )

    async with deps.pool.acquire() as conn:
        await dialogue_message_repository.delete_last_n(conn, ctx.session_id, 2)
    ctx.message_order -= 2

    await deps.websocket.send_text(CancelLastMessageSuccess(cancelled_content=cancelled_content).model_dump_json())
    return ctx


async def _handle_end_session(ctx: SessionContext | None, deps: Deps) -> None:
    if ctx is not None:
        ctx.is_session_ended = True
        await deps.graph.aupdate_state(ctx.config, {"should_generate_note": True}, as_node="learning_dialogue")
        async with deps.pool.acquire() as conn:
            await dialogue_session_repository.update_status(conn, ctx.session_id, "generate_note")
        asyncio.create_task(_generate_note_background(deps.pool, deps.graph, ctx.config, ctx.session_id))

    await deps.websocket.send_text(SessionEndedMessage(session_id=ctx.session_id if ctx else None).model_dump_json())


router = APIRouter()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        user_id = await authenticate_websocket(websocket)
    except ValueError:
        return

    deps = Deps(
        pool=await get_pool(),
        graph=websocket.app.state.graph,
        websocket=websocket,
        user_id=user_id,
    )

    ctx: SessionContext | None = None

    try:
        while True:
            user_input = await websocket.receive_text()

            try:
                msg = _incoming_adapter.validate_json(user_input)
            except ValidationError:
                await websocket.send_text(ErrorMessage(detail="Invalid message format").model_dump_json())
                continue

            if isinstance(msg, StartLearningMessage):
                ctx = await _handle_start_learning(msg, deps)
            elif isinstance(msg, StartReviewMessage):
                new_ctx = await _handle_start_review(msg, deps)
                if new_ctx is not None:
                    ctx = new_ctx
            elif isinstance(msg, ResumeSessionMessage):
                new_ctx = await _handle_resume_session(msg, deps)
                if new_ctx is not None:
                    ctx = new_ctx
            elif isinstance(msg, UserMessage):
                if ctx is None:
                    await websocket.send_text(ErrorMessage(detail="Session not started").model_dump_json())
                    continue
                ctx = await _handle_user_message(msg, ctx, deps)
            elif isinstance(msg, CancelLastMessageRequest):
                if ctx is None:
                    await websocket.send_text(CancelLastMessageError(detail="Session not started").model_dump_json())
                    continue
                ctx = await _handle_cancel_last_message(ctx, deps)
            elif isinstance(msg, EndSessionMessage):
                await _handle_end_session(ctx, deps)
                break

    except WebSocketDisconnect:
        if ctx is not None:
            async with deps.pool.acquire() as conn:
                await dialogue_session_repository.update_status(conn, ctx.session_id, "disconnect")
    except Exception:
        logger.exception(
            "WebSocket handler crashed",
            extra={"session_id": str(ctx.session_id) if ctx else None},
        )
        if ctx is not None:
            async with deps.pool.acquire() as conn:
                await dialogue_session_repository.update_status(conn, ctx.session_id, "failed")
        await websocket.send_text(ErrorMessage(detail="Internal error").model_dump_json())
