from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from api.routes.note import delete_note, get_note, list_notes, update_note
from schemas.note import NoteUpdate

_USER_ID = "user-123"


def _make_note_record(note_id: UUID | None = None, user_id: str = _USER_ID) -> dict[str, object]:
    return {
        "id": note_id or uuid4(),
        "user_id": user_id,
        "topic": "pytest",
        "content": "pytestの使い方",
        "summary": "テスト概要",
        "status": "active",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
        "review_count": 0,
    }


class TestListNotes:
    async def test_returns_note_list(self) -> None:
        records = [_make_note_record(), _make_note_record()]
        mock_db = MagicMock()

        with patch("api.routes.note.note_repository.find_by_user_id", new=AsyncMock(return_value=records)):
            result = await list_notes(current_user_id=_USER_ID, db=mock_db)

        assert len(result.notes) == 2

    async def test_returns_empty_list_when_no_notes(self) -> None:
        mock_db = MagicMock()

        with patch("api.routes.note.note_repository.find_by_user_id", new=AsyncMock(return_value=[])):
            result = await list_notes(current_user_id=_USER_ID, db=mock_db)

        assert result.notes == []


class TestGetNote:
    async def test_note_found_returns_note(self) -> None:
        note_id = uuid4()
        record = _make_note_record(note_id=note_id)
        mock_db = MagicMock()

        with patch("api.routes.note.note_repository.find_by_id", new=AsyncMock(return_value=record)):
            result = await get_note(note_id=note_id, current_user_id=_USER_ID, db=mock_db)

        assert result.id == note_id

    async def test_note_not_found_raises_404(self) -> None:
        mock_db = MagicMock()

        with (
            patch("api.routes.note.note_repository.find_by_id", new=AsyncMock(return_value=None)),
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_note(note_id=uuid4(), current_user_id=_USER_ID, db=mock_db)

        assert exc_info.value.status_code == 404


class TestUpdateNote:
    async def test_update_returns_updated_note(self) -> None:
        note_id = uuid4()
        record = _make_note_record(note_id=note_id)
        record["topic"] = "updated topic"
        mock_db = MagicMock()
        note_data = NoteUpdate(topic="updated topic")

        with patch("api.routes.note.note_repository.update", new=AsyncMock(return_value=record)):
            result = await update_note(note_id=note_id, note_data=note_data, current_user_id=_USER_ID, db=mock_db)

        assert result.topic == "updated topic"

    async def test_update_not_found_raises_404(self) -> None:
        mock_db = MagicMock()
        note_data = NoteUpdate(topic="updated topic")

        with (
            patch("api.routes.note.note_repository.update", new=AsyncMock(return_value=None)),
            pytest.raises(HTTPException) as exc_info,
        ):
            await update_note(note_id=uuid4(), note_data=note_data, current_user_id=_USER_ID, db=mock_db)

        assert exc_info.value.status_code == 404


class TestDeleteNote:
    async def test_delete_success_returns_none(self) -> None:
        mock_db = MagicMock()

        with patch("api.routes.note.note_repository.delete", new=AsyncMock(return_value=True)):
            await delete_note(note_id=uuid4(), current_user_id=_USER_ID, db=mock_db)

    async def test_delete_not_found_raises_404(self) -> None:
        mock_db = MagicMock()

        with (
            patch("api.routes.note.note_repository.delete", new=AsyncMock(return_value=False)),
            pytest.raises(HTTPException) as exc_info,
        ):
            await delete_note(note_id=uuid4(), current_user_id=_USER_ID, db=mock_db)

        assert exc_info.value.status_code == 404
