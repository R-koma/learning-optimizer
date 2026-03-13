from uuid import UUID

from fastapi import APIRouter

from api.dependencies import DB, CurrentUser
from repositories import feedback_repository
from schemas.feedback import FeedbackListResponse

router = APIRouter(prefix="/api/notes/{note_id}/feedbacks", tags=["feedbacks"])


@router.get("", response_model=FeedbackListResponse)
async def list_feedbacks(note_id: UUID, current_user_id: CurrentUser, db: DB):
    records = await feedback_repository.find_by_note_id(db, note_id, current_user_id)
    return FeedbackListResponse(feedbacks=records)
