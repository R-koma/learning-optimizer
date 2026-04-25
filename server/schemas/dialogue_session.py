from uuid import UUID

from pydantic import BaseModel


class FeedbackData(BaseModel):
    understanding_level: str
    strength: str
    improvements: str


class NoteStatusResponse(BaseModel):
    status: str
    session_type: str
    note_id: UUID | None = None
    topic: str | None = None
    summary: str | None = None
    feedback: FeedbackData | None = None
