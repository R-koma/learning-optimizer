from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NoteResponse(BaseModel):
    id: UUID
    user_id: str
    topic: str
    content: str
    summary: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NoteUpdate(BaseModel):
    topic: str | None = None
    content: str | None = None
    summary: str | None = None
    status: str | None = None


class NoteListResponse(BaseModel):
    notes: list[NoteResponse]
