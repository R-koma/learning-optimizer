from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReviewScheduleResponse(BaseModel):
    id: UUID
    note_id: UUID
    review_count: int
    next_review_at: datetime
    last_reviewed_at: datetime | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewScheduleWithNoteResponse(ReviewScheduleResponse):
    note_topic: str
    note_summary: str


class ReviewScheduleListResponse(BaseModel):
    review_schedules: list[ReviewScheduleWithNoteResponse]


class ReviewScheduleUpdate(BaseModel):
    pass
