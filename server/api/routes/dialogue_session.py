from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from api.dependencies import DB, CurrentUser
from repositories import (
    dialogue_message_repository,
    dialogue_session_repository,
    feedback_repository,
    note_repository,
)
from schemas.dialogue_session import (
    ActiveSessionResponse,
    DialogueMessageData,
    FeedbackData,
    NoteStatusResponse,
    SessionMessagesResponse,
)

router = APIRouter(prefix="/api/dialogue-sessions", tags=["dialogue-sessions"])


@router.get("/active", response_model=ActiveSessionResponse | None)
async def get_active_session(
    current_user_id: CurrentUser,
    db: DB,
) -> Response | ActiveSessionResponse:
    session = await dialogue_session_repository.find_resumable_by_user(db, current_user_id)
    if not session:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return ActiveSessionResponse(
        session_id=session["id"],
        session_type=session["session_type"],
        status=session["status"],
        started_at=session["started_at"],
    )


@router.get("/{session_id}/messages", response_model=SessionMessagesResponse)
async def get_session_messages(
    session_id: UUID,
    current_user_id: CurrentUser,
    db: DB,
) -> SessionMessagesResponse:
    session = await dialogue_session_repository.find_by_id(db, session_id, current_user_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    messages = await dialogue_message_repository.find_by_session_id(db, session_id)

    return SessionMessagesResponse(
        session_id=session["id"],
        session_type=session["session_type"],
        status=session["status"],
        note_id=session["note_id"],
        messages=[
            DialogueMessageData(
                role=m["role"],
                content=m["content"],
                message_order=m["message_order"],
            )
            for m in messages
        ],
    )


@router.get("/{session_id}/note-status", response_model=NoteStatusResponse)
async def get_note_status(
    session_id: UUID,
    current_user_id: CurrentUser,
    db: DB,
) -> NoteStatusResponse:
    session = await dialogue_session_repository.find_by_id(db, session_id, current_user_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    response = NoteStatusResponse(
        status=session["status"],
        session_type=session["session_type"],
    )

    if session["status"] != "completed" or session["note_id"] is None:
        return response

    if session["session_type"] == "learning":
        note = await note_repository.find_by_id(db, session["note_id"], current_user_id)
        if note:
            response.note_id = note["id"]
            response.topic = note["topic"]
            response.summary = note["summary"] or ""
    else:
        note = await note_repository.find_by_id(db, session["note_id"], current_user_id)
        if note:
            response.note_id = note["id"]
            response.topic = note["topic"]
            response.summary = note["summary"] or ""
        feedbacks = await feedback_repository.find_by_note_id(db, session["note_id"], current_user_id)
        if feedbacks:
            latest = feedbacks[-1]
            response.feedback = FeedbackData(
                understanding_level=latest["understanding_level"],
                strength=latest["strength"],
                improvements=latest["improvements"],
            )

    return response
