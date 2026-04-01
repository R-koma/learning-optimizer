import json
import uuid
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage

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
    ErrorMessage,
    FeedbackGeneratedMessage,
    NoteGeneratedMessage,
    SessionEndedMessage,
)

router = APIRouter()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        user_id = await authenticate_websocket(websocket)
    except ValueError:
        return

    graph = websocket.app.state.graph
    pool = await get_pool()

    session_id = None
    config = None
    message_order = 0
    session_type = "learning"

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
                result = await graph.ainvoke(initial_state, config=config)

                message_order += 1
                await dialogue_message_repository.insert(pool, session_id, "user", data["topic"], message_order)

                ai_msg = result["messages"][-1].content
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

                ai_msg = result["messages"][-1].content
                message_order += 1
                await dialogue_message_repository.insert(pool, session_id, "assistant", ai_msg, message_order)

                await websocket.send_text(AssistantMessage(content=ai_msg).model_dump_json())

            elif data["type"] == "user_message":
                if not config:
                    await websocket.send_text(ErrorMessage(detail="Session not started").model_dump_json())
                    continue

                message_order += 1
                await dialogue_message_repository.insert(pool, session_id, "user", data["content"], message_order)

                await graph.aupdate_state(
                    config,
                    {"messages": [HumanMessage(content=data["content"])]},
                )
                result = await graph.ainvoke(None, config=config)

                ai_msg = result["messages"][-1].content
                message_order += 1
                await dialogue_message_repository.insert(pool, session_id, "assistant", ai_msg, message_order)

                if result.get("should_generate_note"):
                    await dialogue_session_repository.update_status(pool, session_id, "completed")

                    if session_type == "learning":
                        note_id = result.get("note_id")
                        if note_id:
                            await dialogue_session_repository.update_note_id(pool, session_id, note_id)
                            note = await note_repository.find_by_id(pool, note_id, user_id)
                            await websocket.send_text(
                                NoteGeneratedMessage(
                                    note_id=str(note_id),
                                    topic=note["topic"],
                                    summary=note["summary"],
                                ).model_dump_json()
                            )
                    else:
                        review_note_id = result.get("note_id")
                        if review_note_id:
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

            elif data["type"] == "end_session":
                if config:
                    await graph.aupdate_state(config, {"should_generate_note": True}, as_node="learning_dialogue")
                    result = await graph.ainvoke(None, config=config)

                    if session_id:
                        await dialogue_session_repository.update_status(pool, session_id, "completed")

                    if session_type == "learning":
                        note_id = result.get("note_id")
                        if note_id:
                            if session_id:
                                await dialogue_session_repository.update_note_id(pool, session_id, note_id)
                            note = await note_repository.find_by_id(pool, note_id, user_id)
                            await websocket.send_text(
                                NoteGeneratedMessage(
                                    note_id=str(note_id),
                                    topic=note["topic"],
                                    summary=note["summary"],
                                ).model_dump_json()
                            )
                    else:
                        review_note_id = result.get("note_id")
                        if review_note_id:
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
