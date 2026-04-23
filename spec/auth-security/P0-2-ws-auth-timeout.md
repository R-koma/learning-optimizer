# P0-2: WebSocket 認証メッセージのタイムアウト

**優先度**: P0（本番投入前必須）
**対象ブランチ**: `security/ws-auth-timeout`

---

## 背景

- `server/api/websocket/auth.py:10` で `websocket.receive_text()` を無制限待機
- 未認証状態の接続を大量保持して DoS にできる
- 認証メッセージが来る前の TCP コネクションが無限に滞留する

## 実装内容

`server/api/websocket/auth.py` を改修:

```python
import asyncio
import json

from fastapi import WebSocket

from core.auth import verify_jwt

AUTH_TIMEOUT_SECONDS = 5.0


async def authenticate_websocket(websocket: WebSocket) -> str:
    try:
        raw = await asyncio.wait_for(
            websocket.receive_text(),
            timeout=AUTH_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
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
```

## 受け入れ基準

- [ ] 5 秒以内に `authenticate` メッセージを送らない接続は `code=4008` でクローズされる
- [ ] 既存の正常系（起動直後に `authenticate` を送る）は挙動変化なし

## テスト方法

`server/tests/unit/test_websocket_auth.py` に以下を追加:

```python
async def test_authenticate_websocket_times_out():
    # FastAPI TestClient の WebSocketTestSession で
    # authenticate メッセージを送らず 6 秒待機 → close code=4008 を検証
    ...
```
