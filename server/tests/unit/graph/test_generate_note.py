from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from langchain_core.messages import HumanMessage

from graph.output_schemas import NoteCategory, NoteContent
from graph.state import LearningState

SESSION_ID = UUID("00000000-0000-0000-0000-000000000002")
USER_ID = "user-abc"

FAKE_NOTE_CONTENT = NoteContent(topic="Pythonの基礎", content="本文", summary="要約")


async def _fake_measured(*, runnable: Any, messages: Any, **_kwargs: Any) -> Any:
    """observability/DB を経由する measured_ainvoke の代わりに runnable を直接呼ぶ"""
    return await runnable.ainvoke(messages)


def _make_structured_mock(category_result: object) -> MagicMock:
    """with_structured_output(NoteContent | NoteCategory) を振り分けるモックを返す"""

    def _route(schema: type) -> AsyncMock:
        if schema is NoteCategory:
            return AsyncMock(ainvoke=AsyncMock(return_value=category_result))
        return AsyncMock(ainvoke=AsyncMock(return_value=FAKE_NOTE_CONTENT))

    return MagicMock(side_effect=_route)


def _make_state(**overrides: object) -> LearningState:
    base: dict[str, object] = {
        "user_id": USER_ID,
        "dialogue_session_id": SESSION_ID,
        "messages": [HumanMessage(content="Pythonとは何ですか？")],
        "topic": "Pythonの基礎",
        "turn_count": 3,
        "should_generate_note": True,
        "session_type": "learning",
    }
    base.update(overrides)
    return cast(LearningState, base)


def _mock_pool() -> tuple[MagicMock, AsyncMock]:
    conn = AsyncMock()
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__ = AsyncMock(return_value=conn)
    acquire_cm.__aexit__ = AsyncMock(return_value=False)
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=acquire_cm)
    return pool, conn


class TestGenerateNoteCategory:
    async def test_category_estimated_and_passed_to_insert(self) -> None:
        pool, _ = _mock_pool()

        with (
            patch("graph.nodes.generate_note.get_pool", AsyncMock(return_value=pool)),
            patch("graph.nodes.generate_note.measured_ainvoke", _fake_measured),
            patch("graph.nodes.generate_note.llm_structured") as mock_llm,
            patch(
                "graph.nodes.generate_note.note_repository.find_categories_by_user_id",
                AsyncMock(return_value=["数学"]),
            ),
            patch("graph.nodes.generate_note.note_repository.insert", AsyncMock()) as mock_insert,
            patch("graph.nodes.generate_note._generate_aspect_map_background", MagicMock()),
            patch("graph.nodes.generate_note.asyncio.create_task", MagicMock()),
        ):
            mock_llm.with_structured_output = _make_structured_mock(NoteCategory(category="プログラミング"))

            from graph.nodes.generate_note import generate_note

            await generate_note(_make_state())

        _, kwargs = mock_insert.call_args
        assert kwargs["category"] == "プログラミング"

    async def test_insert_called_with_none_when_category_llm_fails(self) -> None:
        pool, _ = _mock_pool()

        def _route(schema: type) -> AsyncMock:
            if schema is NoteCategory:
                return AsyncMock(ainvoke=AsyncMock(side_effect=RuntimeError("boom")))
            return AsyncMock(ainvoke=AsyncMock(return_value=FAKE_NOTE_CONTENT))

        with (
            patch("graph.nodes.generate_note.get_pool", AsyncMock(return_value=pool)),
            patch("graph.nodes.generate_note.measured_ainvoke", _fake_measured),
            patch("graph.nodes.generate_note.llm_structured") as mock_llm,
            patch(
                "graph.nodes.generate_note.note_repository.find_categories_by_user_id",
                AsyncMock(return_value=[]),
            ),
            patch("graph.nodes.generate_note.note_repository.insert", AsyncMock()) as mock_insert,
            patch("graph.nodes.generate_note._generate_aspect_map_background", MagicMock()),
            patch("graph.nodes.generate_note.asyncio.create_task", MagicMock()),
        ):
            mock_llm.with_structured_output = MagicMock(side_effect=_route)

            from graph.nodes.generate_note import generate_note

            await generate_note(_make_state())

        _, kwargs = mock_insert.call_args
        assert kwargs["category"] is None

    async def test_insert_called_with_none_when_category_blank(self) -> None:
        pool, _ = _mock_pool()

        with (
            patch("graph.nodes.generate_note.get_pool", AsyncMock(return_value=pool)),
            patch("graph.nodes.generate_note.measured_ainvoke", _fake_measured),
            patch("graph.nodes.generate_note.llm_structured") as mock_llm,
            patch(
                "graph.nodes.generate_note.note_repository.find_categories_by_user_id",
                AsyncMock(return_value=[]),
            ),
            patch("graph.nodes.generate_note.note_repository.insert", AsyncMock()) as mock_insert,
            patch("graph.nodes.generate_note._generate_aspect_map_background", MagicMock()),
            patch("graph.nodes.generate_note.asyncio.create_task", MagicMock()),
        ):
            mock_llm.with_structured_output = _make_structured_mock(NoteCategory(category="   "))

            from graph.nodes.generate_note import generate_note

            await generate_note(_make_state())

        _, kwargs = mock_insert.call_args
        assert kwargs["category"] is None
