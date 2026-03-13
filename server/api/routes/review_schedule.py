from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from api.dependencies import DB, CurrentUser
from repositories import review_schedule_repository
from schemas.review_schedule import (
    ReviewScheduleListResponse,
    ReviewScheduleResponse,
    ReviewScheduleUpdate,
)
from services.review_scheduler import calculate_next_review

router = APIRouter(prefix="/api/review-schedules", tags=["Review Schedules"])


router.get("", response_model=ReviewScheduleListResponse)


async def list_pending_reviews(current_user_id: CurrentUser, db: DB):
    records = await review_schedule_repository.find_pending_by_user_id(db, current_user_id)
    return ReviewScheduleListResponse(review_schedules=records)


@router.patch("/{schedule_id}", response_model=ReviewScheduleResponse)
async def complete_review(schedule_id: UUID, update_data: ReviewScheduleUpdate, current_user_id: CurrentUser, db: DB):
    pending_schedules = await review_schedule_repository.find_pending_by_user_id(db, current_user_id)
    target_schedule = next((s for s in pending_schedules if s["id"] == schedule_id), None)

    if not target_schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending review schedule not found")

    next_review_at = calculate_next_review(
        current_review_count=target_schedule["review_count"], understanding_level=update_data.understanding_level
    )

    updated_record = await review_schedule_repository.mark_completed(
        db, schedule_id=schedule_id, user_id=current_user_id, next_review_at=next_review_at
    )

    return updated_record
