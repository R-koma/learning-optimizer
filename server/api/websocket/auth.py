import asyncio
import json

from fastapi import WebSocket

from core.auth import verify_jwt

AUTH_TIMEOUT_SECONDS = 5.0


async def authenticate_websocket(websocket: WebSocket) -> str:
    """接続後、最初のメッセージで JWT を検証し user_id を返す。失敗時は接続を閉じる。"""
    try:
        raw = await asyncio.wait_for(
            websocket.receive_text(),
            timeout=AUTH_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        await websocket.close(code=4008, reason="Authentication timeout")
        raise ValueError("Authentication timeout") from None

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        await websocket.close(code=4001, reason="Invalid message format")
        raise ValueError("Invalid message format") from None

    if data.get("type") != "authenticate" or not data.get("token"):
        await websocket.close(code=4001, reason="First message must be authenticate")
        raise ValueError("First message must be authenticate")

    try:
        payload = verify_jwt(data["token"])
        user_id: str | None = payload.get("sub")
        if not user_id:
            await websocket.close(code=4003, reason="Invalid token")
            raise ValueError("Invalid token")
        return user_id
    except ValueError:
        await websocket.close(code=4003, reason="Invalid token")
        raise
