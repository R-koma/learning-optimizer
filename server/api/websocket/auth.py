import json

from fastapi import WebSocket

from core.auth import verify_jwt


async def authenticate_websocket(websocket: WebSocket) -> str:
    """接続後、最初のメッセージで JWT を検証し user_id を返す。失敗時は接続を閉じる。"""
    raw = await websocket.receive_text()

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
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4003, reason="Invalid token")
            raise ValueError("Invalid token")
        return user_id
    except ValueError:
        await websocket.close(code=4003, reason="Invalid token")
        raise
