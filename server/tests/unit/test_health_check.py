from unittest.mock import AsyncMock, patch

from main import health_check


class TestHealthCheck:
    async def test_returns_ok_when_db_reachable(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value={"check": 1})

        with patch("main.get_pool", new=AsyncMock(return_value=mock_pool)):
            result = await health_check()

        assert result == {"status": "ok", "db": True}

    async def test_returns_error_when_query_raises(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(side_effect=OSError("connection refused"))

        with patch("main.get_pool", new=AsyncMock(return_value=mock_pool)):
            result = await health_check()

        assert result == {"status": "error", "db": False}

    async def test_returns_error_when_get_pool_raises(self) -> None:
        with patch("main.get_pool", new=AsyncMock(side_effect=OSError("pool down"))):
            result = await health_check()

        assert result == {"status": "error", "db": False}

    async def test_returns_error_when_row_is_none(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=None)

        with patch("main.get_pool", new=AsyncMock(return_value=mock_pool)):
            result = await health_check()

        assert result == {"status": "error", "db": False}
