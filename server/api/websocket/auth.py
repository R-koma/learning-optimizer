from fastapi import WebSocket, WebSocketException, status

from core.auth import verify_jwt


async def authenticate_websocket(websocket: WebSocket) -> str:
    """WebSocket 接続時に JWT を検証し、user_id を返す"""
    token = websocket.query_params.get("token")
    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    try:
        payload = verify_jwt(token)
        user_id = payload.get("sub")
        if not user_id:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        return user_id
    except ValueError:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION) from None
