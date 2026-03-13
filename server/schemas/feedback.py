from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FeedbackResponse(BaseModel):
    id: UUID
    note_id: UUID
    dialogue_session_id: UUID
    understanding_level: str
    strength: str
    improvements: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackListResponse(BaseModel):
    feedbacks: list[FeedbackResponse]
