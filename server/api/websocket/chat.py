import asyncio
import json
import logging
import uuid
from typing import Any, Literal, cast
from uuid import UUID

import asyncpg
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import AIMessageChunk, HumanMessage, RemoveMessage

from api.websocket.auth import authenticate_websocket
from core.database import get_pool
from graph.state import TARGET_DEPTH_VALUES
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
    CancelLastMessageSuccess,
    ErrorMessage,
    FeedbackGeneratedMessage,
    NoteGeneratedMessage,
    SessionEndedMessage,
    SessionResumedMessage,
    SessionStartedMessage,
)

logger = logging.getLogger(__name__)

_STREAMING_NODES = {"learning_start", "learning_dialogue"}


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
        if generated_note_id is not None:
            await dialogue_session_repository.update_note_id(pool, session_id, generated_note_id)
        else:
            await dialogue_session_repository.update_status(pool, session_id, "completed")
    except Exception:
        logger.exception("Background note generation failed for session %s", session_id)
        await dialogue_session_repository.update_status(pool, session_id, "failed")


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
    user_id: str,
    pool: asyncpg.Pool,
    graph: Any,
    websocket: WebSocket,
    initial_state: dict[str, Any],
    first_user_content: str,
) -> tuple[UUID, dict[str, Any], int]:
    """セッション作成・SessionStarted 送信・初期 user/assistant メッセージ保存までを共通化。

    戻り値: (session_id, config, message_order)
    """
    await dialogue_session_repository.abandon_active_by_user(pool, user_id)

    session_id = uuid.uuid4()
    config = {"configurable": {"thread_id": str(session_id)}}

    await dialogue_session_repository.create(
        conn=pool,
        session_id=session_id,
        user_id=user_id,
        session_type=session_type,
    )

    await websocket.send_text(
        SessionStartedMessage(session_id=session_id, session_type=session_type).model_dump_json()
    )

    initial_state["dialogue_session_id"] = str(session_id)

    message_order = 1
    await dialogue_message_repository.insert(pool, session_id, "user", first_user_content, message_order)

    ai_msg = await _stream_ai_response(graph, initial_state, config, websocket)
    message_order += 1
    await dialogue_message_repository.insert(pool, session_id, "assistant", ai_msg, message_order)

    return session_id, config, message_order


router = APIRouter()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        user_id = await authenticate_websocket(websocket)
    except ValueError:
        return

    graph = websocket.app.state.graph
    pool = await get_pool()

    session_id: UUID | None = None
    config: dict[str, Any] | None = None
    message_order: int = 0
    session_type: str = "learning"
    is_session_ended: bool = False

    try:
        while True:
            user_input = await websocket.receive_text()
            data = json.loads(user_input)

            if data["type"] == "start_learning":
                session_type = "learning"
                is_session_ended = False

                initial_state: dict[str, Any] = {
                    "user_id": user_id,
                    "topic": data["topic"],
                    "turn_count": 0,
                    "should_generate_note": False,
                    "session_type": "learning",
                }

                learning_goal = data.get("learning_goal")
                if isinstance(learning_goal, str) and learning_goal.strip():
                    initial_state["learning_goal"] = learning_goal.strip()

                target_depth = data.get("target_depth")
                if target_depth in TARGET_DEPTH_VALUES:
                    initial_state["target_depth"] = target_depth

                focus_aspects = data.get("focus_aspects")
                if isinstance(focus_aspects, list):
                    cleaned_aspects = [a.strip() for a in focus_aspects if isinstance(a, str) and a.strip()]
                    if cleaned_aspects:
                        initial_state["focus_aspects"] = cleaned_aspects

                session_id, config, message_order = await _start_session(
                    session_type="learning",
                    user_id=user_id,
                    pool=pool,
                    graph=graph,
                    websocket=websocket,
                    initial_state=initial_state,
                    first_user_content=data["topic"],
                )

            elif data["type"] == "start_review":
                note_id = UUID(data["note_id"])

                note = await note_repository.find_by_id(pool, note_id, user_id)
                if not note:
                    await websocket.send_text(ErrorMessage(detail="Note not found").model_dump_json())
                    continue

                session_type = "review"
                is_session_ended = False

                initial_state = {
                    "user_id": user_id,
                    "note_id": note_id,
                    "topic": note["topic"],
                    "note_content": note["content"],
                    "note_summary": note["summary"] or "",
                    "turn_count": 0,
                    "should_generate_note": False,
                    "session_type": "review",
                }

                session_id, config, message_order = await _start_session(
                    session_type="review",
                    user_id=user_id,
                    pool=pool,
                    graph=graph,
                    websocket=websocket,
                    initial_state=initial_state,
                    first_user_content=note["topic"],
                )

            elif data["type"] == "resume_session":
                resume_id = UUID(data["session_id"])
                existing = await dialogue_session_repository.find_by_id(pool, resume_id, user_id)
                if not existing:
                    await websocket.send_text(ErrorMessage(detail="Session not found").model_dump_json())
                    continue

                if existing["status"] not in ("in_progress", "disconnect"):
                    await websocket.send_text(ErrorMessage(detail="Session is not resumable").model_dump_json())
                    continue

                if existing["status"] == "disconnect":
                    await dialogue_session_repository.update_status(pool, resume_id, "in_progress")

                session_id = resume_id
                if existing["session_type"] not in ("learning", "review"):
                    await websocket.send_text(ErrorMessage(detail="Invalid session type").model_dump_json())
                    continue
                resumed_session_type = cast(Literal["learning", "review"], existing["session_type"])
                session_type = resumed_session_type
                config = {"configurable": {"thread_id": str(session_id)}}
                is_session_ended = False

                last_order = await pool.fetchval(
                    "SELECT COALESCE(MAX(message_order), 0) FROM dialogue_messages WHERE dialogue_session_id = $1",
                    str(session_id),
                )
                message_order = int(last_order or 0)

                await websocket.send_text(
                    SessionResumedMessage(
                        session_id=session_id,
                        session_type=resumed_session_type,
                    ).model_dump_json()
                )

            elif data["type"] == "user_message":
                if not config or not session_id:
                    await websocket.send_text(ErrorMessage(detail="Session not started").model_dump_json())
                    continue

                message_order += 1
                await dialogue_message_repository.insert(pool, session_id, "user", data["content"], message_order)

                await graph.aupdate_state(
                    config,
                    {"messages": [HumanMessage(content=data["content"])]},
                )

                ai_msg = await _stream_ai_response(graph, None, config, websocket)
                message_order += 1
                await dialogue_message_repository.insert(pool, session_id, "assistant", ai_msg, message_order)

                state = await graph.aget_state(config)
                result = state.values

                if result.get("should_generate_note"):
                    turn_count = result.get("turn_count", 0)
                    if turn_count < 3:
                        await graph.aupdate_state(config, {"should_generate_note": False})
                        continue
                    is_session_ended = True
                    await dialogue_session_repository.update_status(pool, session_id, "completed")

                    if session_type == "learning":
                        generated_note_id: UUID | None = result.get("note_id")
                        if generated_note_id is not None:
                            await dialogue_session_repository.update_note_id(pool, session_id, generated_note_id)
                            note = await note_repository.find_by_id(pool, generated_note_id, user_id)
                            if note:
                                await websocket.send_text(
                                    NoteGeneratedMessage(
                                        note_id=generated_note_id,
                                        topic=note["topic"],
                                        summary=note["summary"] or "",
                                    ).model_dump_json()
                                )
                    else:
                        review_note_id: UUID | None = result.get("note_id")
                        if review_note_id is not None:
                            await dialogue_session_repository.update_note_id(pool, session_id, review_note_id)
                            feedbacks = await feedback_repository.find_by_note_id(pool, review_note_id, user_id)
                            if feedbacks:
                                latest = feedbacks[-1]
                                await websocket.send_text(
                                    FeedbackGeneratedMessage(
                                        understanding_level=latest["understanding_level"],
                                        strength=latest["strength"],
                                        improvements=latest["improvements"],
                                    ).model_dump_json()
                                )
                            updated_note = await note_repository.find_by_id(pool, review_note_id, user_id)
                            if updated_note:
                                await websocket.send_text(
                                    NoteGeneratedMessage(
                                        note_id=review_note_id,
                                        topic=updated_note["topic"],
                                        summary=updated_note["summary"] or "",
                                    ).model_dump_json()
                                )

                    await websocket.send_text(SessionEndedMessage().model_dump_json())

            elif data["type"] == "cancel_last_message":
                if not config or not session_id:
                    await websocket.send_text(CancelLastMessageError(detail="Session not started").model_dump_json())
                    continue

                if is_session_ended:
                    await websocket.send_text(CancelLastMessageError(detail="Session already ended").model_dump_json())
                    continue

                if message_order < 4:
                    await websocket.send_text(
                        CancelLastMessageError(detail="No cancellable message").model_dump_json()
                    )
                    continue

                state = await graph.aget_state(config)
                messages_in_state = state.values["messages"]

                last_ai = messages_in_state[-1]
                last_human = messages_in_state[-2]
                cancelled_content: str = str(last_human.content)

                await graph.aupdate_state(
                    config,
                    {
                        "messages": [
                            RemoveMessage(id=last_ai.id),
                            RemoveMessage(id=last_human.id),
                        ],
                        "turn_count": state.values["turn_count"] - 1,
                    },
                )

                await dialogue_message_repository.delete_last_n(pool, session_id, 2)
                message_order -= 2

                await websocket.send_text(
                    CancelLastMessageSuccess(cancelled_content=cancelled_content).model_dump_json()
                )

            elif data["type"] == "end_session":
                is_session_ended = True
                if config and session_id:
                    await graph.aupdate_state(config, {"should_generate_note": True}, as_node="learning_dialogue")
                    await dialogue_session_repository.update_status(pool, session_id, "generate_note")
                    asyncio.create_task(_generate_note_background(pool, graph, config, session_id))
                elif session_id:
                    await dialogue_session_repository.update_status(pool, session_id, "completed")

                await websocket.send_text(SessionEndedMessage(session_id=session_id).model_dump_json())
                break

    except WebSocketDisconnect:
        if session_id:
            await dialogue_session_repository.update_status(pool, session_id, "disconnect")
    except Exception as e:
        if session_id:
            await dialogue_session_repository.update_status(pool, session_id, "failed")
        await websocket.send_text(ErrorMessage(detail=str(e)).model_dump_json())
