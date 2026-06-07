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


class PendingReviewListResponse(ReviewScheduleListResponse):
    # 当日（REVIEW_TIMEZONE 基準）に復習を完了した件数。進捗バーの分子に使う。
    # 完了済みは next_review_at が未来に進み review_schedules からは消えるため、別途数えて返す。
    completed_today: int


class ReviewScheduleUpdate(BaseModel):
    pass
