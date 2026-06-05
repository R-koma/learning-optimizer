from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.responses import Response

from api.routes.dialogue_session import get_active_session, get_session_messages
from schemas.dialogue_session import ActiveSessionResponse, SessionMessagesResponse

_USER_ID = "user-123"


def _make_session(
    session_id: UUID | None = None,
    status: str = "in_progress",
    session_type: str = "learning",
    note_id: UUID | None = None,
) -> dict[str, object]:
    return {
        "id": session_id or uuid4(),
        "user_id": _USER_ID,
        "session_type": session_type,
        "status": status,
        "note_id": note_id,
        "started_at": datetime(2026, 1, 1, 0, 0, 0),
        "ended_at": None,
    }


def _make_message(role: str = "user", content: str = "hello", order: int = 1) -> dict[str, object]:
    return {"id": uuid4(), "role": role, "content": content, "message_order": order}


class TestGetActiveSession:
    async def test_returns_204_when_no_active_session(self) -> None:
        mock_db = MagicMock()

        with patch(
            "api.routes.dialogue_session.dialogue_session_repository.find_resumable_by_user",
            new=AsyncMock(return_value=None),
        ):
            result = await get_active_session(current_user_id=_USER_ID, db=mock_db)

        assert isinstance(result, Response)
        assert result.status_code == 204

    async def test_returns_active_session(self) -> None:
        session_id = uuid4()
        session = _make_session(session_id=session_id)
        mock_db = MagicMock()

        with patch(
            "api.routes.dialogue_session.dialogue_session_repository.find_resumable_by_user",
            new=AsyncMock(return_value=session),
        ):
            result = await get_active_session(current_user_id=_USER_ID, db=mock_db)

        assert isinstance(result, ActiveSessionResponse)
        assert result.session_id == session_id
        assert result.session_type == "learning"

    async def test_returns_disconnect_session(self) -> None:
        session = _make_session(status="disconnect", session_type="review")
        mock_db = MagicMock()

        with patch(
            "api.routes.dialogue_session.dialogue_session_repository.find_resumable_by_user",
            new=AsyncMock(return_value=session),
        ):
            result = await get_active_session(current_user_id=_USER_ID, db=mock_db)

        assert isinstance(result, ActiveSessionResponse)
        assert result.status == "disconnect"


class TestGetSessionMessages:
    async def test_raises_404_when_session_not_found(self) -> None:
        mock_db = MagicMock()

        with (
            patch(
                "api.routes.dialogue_session.dialogue_session_repository.find_by_id",
                new=AsyncMock(return_value=None),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_session_messages(session_id=uuid4(), current_user_id=_USER_ID, db=mock_db)

        assert exc_info.value.status_code == 404

    async def test_returns_session_with_messages(self) -> None:
        session_id = uuid4()
        session = _make_session(session_id=session_id)
        messages = [
            _make_message("user", "Pythonを教えて", 1),
            _make_message("assistant", "Pythonはプログラミング言語です", 2),
        ]
        mock_db = MagicMock()

        with (
            patch(
                "api.routes.dialogue_session.dialogue_session_repository.find_by_id",
                new=AsyncMock(return_value=session),
            ),
            patch(
                "api.routes.dialogue_session.dialogue_message_repository.find_by_session_id",
                new=AsyncMock(return_value=messages),
            ),
            patch(
                "api.routes.dialogue_session.dialogue_message_image_repository.find_by_session_id",
                new=AsyncMock(return_value=[]),
            ),
        ):
            result = await get_session_messages(session_id=session_id, current_user_id=_USER_ID, db=mock_db)

        assert isinstance(result, SessionMessagesResponse)
        assert result.session_id == session_id
        assert len(result.messages) == 2
        assert result.messages[0].role == "user"
        assert result.messages[1].role == "assistant"

    async def test_returns_session_with_no_messages(self) -> None:
        session_id = uuid4()
        session = _make_session(session_id=session_id)
        mock_db = MagicMock()

        with (
            patch(
                "api.routes.dialogue_session.dialogue_session_repository.find_by_id",
                new=AsyncMock(return_value=session),
            ),
            patch(
                "api.routes.dialogue_session.dialogue_message_repository.find_by_session_id",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "api.routes.dialogue_session.dialogue_message_image_repository.find_by_session_id",
                new=AsyncMock(return_value=[]),
            ),
        ):
            result = await get_session_messages(session_id=session_id, current_user_id=_USER_ID, db=mock_db)

        assert result.messages == []

    async def test_returns_note_id_when_present(self) -> None:
        session_id = uuid4()
        note_id = uuid4()
        session = _make_session(session_id=session_id, status="completed", note_id=note_id)
        mock_db = MagicMock()

        with (
            patch(
                "api.routes.dialogue_session.dialogue_session_repository.find_by_id",
                new=AsyncMock(return_value=session),
            ),
            patch(
                "api.routes.dialogue_session.dialogue_message_repository.find_by_session_id",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "api.routes.dialogue_session.dialogue_message_image_repository.find_by_session_id",
                new=AsyncMock(return_value=[]),
            ),
        ):
            result = await get_session_messages(session_id=session_id, current_user_id=_USER_ID, db=mock_db)

        assert result.note_id == note_id
