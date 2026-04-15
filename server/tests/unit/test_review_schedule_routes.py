from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from api.routes.review_schedule import complete_review, list_pending_reviews
from schemas.review_schedule import ReviewScheduleUpdate

_USER_ID = "user-123"


def _make_schedule_record(schedule_id: UUID | None = None, note_id: UUID | None = None) -> dict[str, object]:
    return {
        "id": schedule_id or uuid4(),
        "note_id": note_id or uuid4(),
        "review_count": 1,
        "next_review_at": datetime(2026, 4, 17, tzinfo=UTC),
        "last_reviewed_at": None,
        "status": "pending",
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
        "note_topic": "pytest",
        "note_summary": "pytestの概要",
    }


class TestListPendingReviews:
    async def test_returns_pending_list(self) -> None:
        records = [_make_schedule_record(), _make_schedule_record()]
        mock_db = MagicMock()

        with patch(
            "api.routes.review_schedule.review_schedule_repository.find_pending_by_user_id",
            new=AsyncMock(return_value=records),
        ):
            result = await list_pending_reviews(current_user_id=_USER_ID, db=mock_db)

        assert len(result.review_schedules) == 2

    async def test_returns_empty_list_when_no_pending(self) -> None:
        mock_db = MagicMock()

        with patch(
            "api.routes.review_schedule.review_schedule_repository.find_pending_by_user_id",
            new=AsyncMock(return_value=[]),
        ):
            result = await list_pending_reviews(current_user_id=_USER_ID, db=mock_db)

        assert result.review_schedules == []


class TestCompleteReview:
    async def test_complete_returns_updated_schedule(self) -> None:
        schedule_id = uuid4()
        pending_record = _make_schedule_record(schedule_id=schedule_id)
        next_review = datetime(2026, 4, 24, tzinfo=UTC)
        completed_record = {**pending_record, "status": "completed", "next_review_at": next_review}
        mock_db = MagicMock()

        with (
            patch(
                "api.routes.review_schedule.review_schedule_repository.find_pending_by_user_id",
                new=AsyncMock(return_value=[pending_record]),
            ),
            patch("api.routes.review_schedule.calculate_next_review", return_value=next_review),
            patch(
                "api.routes.review_schedule.review_schedule_repository.mark_completed",
                new=AsyncMock(return_value=completed_record),
            ),
        ):
            result = await complete_review(
                schedule_id=schedule_id,
                update_data=ReviewScheduleUpdate(),
                current_user_id=_USER_ID,
                db=mock_db,
            )

        assert result.status == "completed"

    async def test_schedule_not_in_pending_raises_404(self) -> None:
        mock_db = MagicMock()

        with (
            patch(
                "api.routes.review_schedule.review_schedule_repository.find_pending_by_user_id",
                new=AsyncMock(return_value=[]),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await complete_review(
                schedule_id=uuid4(),
                update_data=ReviewScheduleUpdate(),
                current_user_id=_USER_ID,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404
