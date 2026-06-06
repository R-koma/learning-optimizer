from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from api.routes.note_revision import list_note_revisions

_USER_ID = "user-123"


def _make_revision_record() -> dict[str, object]:
    return {
        "id": uuid4(),
        "note_id": uuid4(),
        "content": "- 復習で深まった点",
        "created_at": datetime(2026, 6, 1),
    }


class TestListNoteRevisions:
    async def test_returns_revisions(self) -> None:
        records = [_make_revision_record(), _make_revision_record()]
        mock_db = MagicMock()

        with patch(
            "api.routes.note_revision.note_revision_repository.find_by_note_id",
            new=AsyncMock(return_value=records),
        ):
            result = await list_note_revisions(note_id=uuid4(), current_user_id=_USER_ID, db=mock_db)

        assert len(result.revisions) == 2

    async def test_returns_empty_list(self) -> None:
        mock_db = MagicMock()

        with patch(
            "api.routes.note_revision.note_revision_repository.find_by_note_id",
            new=AsyncMock(return_value=[]),
        ):
            result = await list_note_revisions(note_id=uuid4(), current_user_id=_USER_ID, db=mock_db)

        assert result.revisions == []
