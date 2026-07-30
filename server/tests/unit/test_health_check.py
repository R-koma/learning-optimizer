from unittest.mock import AsyncMock, patch

from main import health_check


class TestHealthCheck:
    async def test_returns_ok_when_db_reachable(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value={"check": 1})

        with (
            patch("main.get_pool", new=AsyncMock(return_value=mock_pool)),
            patch("main.is_tracing_enabled", return_value=True),
        ):
            result = await health_check()

        assert result == {"status": "ok", "db": True, "tracing": True}

    async def test_returns_error_when_query_raises(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(side_effect=OSError("connection refused"))

        with (
            patch("main.get_pool", new=AsyncMock(return_value=mock_pool)),
            patch("main.is_tracing_enabled", return_value=True),
        ):
            result = await health_check()

        assert result == {"status": "error", "db": False, "tracing": True}

    async def test_returns_error_when_get_pool_raises(self) -> None:
        with (
            patch("main.get_pool", new=AsyncMock(side_effect=OSError("pool down"))),
            patch("main.is_tracing_enabled", return_value=True),
        ):
            result = await health_check()

        assert result == {"status": "error", "db": False, "tracing": True}

    async def test_returns_error_when_row_is_none(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=None)

        with (
            patch("main.get_pool", new=AsyncMock(return_value=mock_pool)),
            patch("main.is_tracing_enabled", return_value=True),
        ):
            result = await health_check()

        assert result == {"status": "error", "db": False, "tracing": True}

    async def test_tracing_disabled_does_not_degrade_status(self) -> None:
        """キー未設定でも status は ok。観測の不在でヘルスチェックを落とさない。"""
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value={"check": 1})

        with (
            patch("main.get_pool", new=AsyncMock(return_value=mock_pool)),
            patch("main.is_tracing_enabled", return_value=False),
        ):
            result = await health_check()

        assert result == {"status": "ok", "db": True, "tracing": False}
