from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from api.dependencies import DB, CurrentUser
from repositories import (
    dialogue_session_repository,
    feedback_repository,
    note_repository,
)
from schemas.dialogue_session import FeedbackData, NoteStatusResponse

router = APIRouter(prefix="/api/dialogue-sessions", tags=["dialogue-sessions"])


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
        feedbacks = await feedback_repository.find_by_note_id(db, session["note_id"], current_user_id)
        if feedbacks:
            latest = feedbacks[-1]
            response.note_id = session["note_id"]
            response.feedback = FeedbackData(
                understanding_level=latest["understanding_level"],
                strength=latest["strength"],
                improvements=latest["improvements"],
            )

    return response
