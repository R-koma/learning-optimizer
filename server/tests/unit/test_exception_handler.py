import json

from starlette.requests import Request

from main import unhandled_exception_handler


def _make_request(method: str = "GET", path: str = "/api/notes") -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
    }
    return Request(scope)


class TestUnhandledExceptionHandler:
    async def test_returns_500_with_generic_detail(self) -> None:
        response = await unhandled_exception_handler(_make_request(), RuntimeError("boom"))

        assert response.status_code == 500
        assert json.loads(bytes(response.body)) == {"detail": "Internal server error"}

    async def test_does_not_leak_exception_message(self) -> None:
        secret = "sensitive-internal-detail"
        response = await unhandled_exception_handler(_make_request(), ValueError(secret))

        assert secret not in bytes(response.body).decode()
