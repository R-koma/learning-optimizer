from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NoteRevisionResponse(BaseModel):
    id: UUID
    note_id: UUID
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NoteRevisionListResponse(BaseModel):
    revisions: list[NoteRevisionResponse]
