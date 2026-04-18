import json
import uuid
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage, RemoveMessage

from api.websocket.auth import authenticate_websocket
from core.database import get_pool
from repositories import (
    dialogue_message_repository,
    dialogue_session_repository,
    feedback_repository,
    note_repository,
)
from schemas.websocket_message import (
    AssistantMessage,
    CancelLastMessageError,
    CancelLastMessageSuccess,
    ErrorMessage,
    FeedbackGeneratedMessage,
    NoteGeneratedMessage,
    SessionEndedMessage,
)

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
                session_id = uuid.uuid4()
                config = {"configurable": {"thread_id": str(session_id)}}
                session_type = "learning"

                await dialogue_session_repository.create(
                    conn=pool,
                    session_id=session_id,
                    user_id=user_id,
                    session_type="learning",
                )

                initial_state = {
                    "user_id": user_id,
                    "dialogue_session_id": str(session_id),
                    "topic": data["topic"],
                    "turn_count": 0,
                    "should_generate_note": False,
                    "session_type": "learning",
                }
                result: dict[str, Any] = await graph.ainvoke(initial_state, config=config)

                message_order += 1
                await dialogue_message_repository.insert(pool, session_id, "user", data["topic"], message_order)

                ai_msg: str = str(result["messages"][-1].content)
                message_order += 1
                await dialogue_message_repository.insert(pool, session_id, "assistant", ai_msg, message_order)

                await websocket.send_text(AssistantMessage(content=ai_msg).model_dump_json())

            elif data["type"] == "start_review":
                note_id = UUID(data["note_id"])

                note = await note_repository.find_by_id(pool, note_id, user_id)
                if not note:
                    await websocket.send_text(ErrorMessage(detail="Note not found").model_dump_json())
                    continue

                session_id = uuid.uuid4()
                config = {"configurable": {"thread_id": str(session_id)}}
                session_type = "review"

                await dialogue_session_repository.create(
                    conn=pool,
                    session_id=session_id,
                    user_id=user_id,
                    session_type="review",
                )

                initial_state = {
                    "user_id": user_id,
                    "dialogue_session_id": str(session_id),
                    "note_id": note_id,
                    "topic": note["topic"],
                    "note_content": note["content"],
                    "note_summary": note["summary"] or "",
                    "turn_count": 0,
                    "should_generate_note": False,
                    "session_type": "review",
                }
                result = await graph.ainvoke(initial_state, config=config)

                message_order += 1
                await dialogue_message_repository.insert(pool, session_id, "user", note["topic"], message_order)

                ai_msg = str(result["messages"][-1].content)
                message_order += 1
                await dialogue_message_repository.insert(pool, session_id, "assistant", ai_msg, message_order)

                await websocket.send_text(AssistantMessage(content=ai_msg).model_dump_json())

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
                result = await graph.ainvoke(None, config=config)

                ai_msg = str(result["messages"][-1].content)
                message_order += 1
                await dialogue_message_repository.insert(pool, session_id, "assistant", ai_msg, message_order)

                if result.get("should_generate_note"):
                    turn_count = result.get("turn_count", 0)
                    if turn_count < 3:
                        await graph.aupdate_state(config, {"should_generate_note": False})
                        await websocket.send_text(AssistantMessage(content=ai_msg).model_dump_json())
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

                    await websocket.send_text(SessionEndedMessage().model_dump_json())
                else:
                    await websocket.send_text(AssistantMessage(content=ai_msg).model_dump_json())

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
                if config:
                    await graph.aupdate_state(config, {"should_generate_note": True}, as_node="learning_dialogue")
                    result = await graph.ainvoke(None, config=config)

                    if session_id:
                        await dialogue_session_repository.update_status(pool, session_id, "completed")

                    if session_type == "learning":
                        end_note_id: UUID | None = result.get("note_id")
                        if end_note_id is not None:
                            if session_id:
                                await dialogue_session_repository.update_note_id(pool, session_id, end_note_id)
                            note = await note_repository.find_by_id(pool, end_note_id, user_id)
                            if note:
                                await websocket.send_text(
                                    NoteGeneratedMessage(
                                        note_id=end_note_id,
                                        topic=note["topic"],
                                        summary=note["summary"] or "",
                                    ).model_dump_json()
                                )
                    else:
                        end_review_note_id: UUID | None = result.get("note_id")
                        if end_review_note_id is not None:
                            feedbacks = await feedback_repository.find_by_note_id(pool, end_review_note_id, user_id)
                            if feedbacks:
                                latest = feedbacks[-1]
                                await websocket.send_text(
                                    FeedbackGeneratedMessage(
                                        understanding_level=latest["understanding_level"],
                                        strength=latest["strength"],
                                        improvements=latest["improvements"],
                                    ).model_dump_json()
                                )
                elif session_id:
                    await dialogue_session_repository.update_status(pool, session_id, "completed")

                await websocket.send_text(SessionEndedMessage().model_dump_json())
                break

    except WebSocketDisconnect:
        if session_id:
            await dialogue_session_repository.update_status(pool, session_id, "disconnect")
    except Exception as e:
        if session_id:
            await dialogue_session_repository.update_status(pool, session_id, "failed")
        await websocket.send_text(ErrorMessage(detail=str(e)).model_dump_json())
