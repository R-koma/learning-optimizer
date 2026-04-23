# P1-2: エラーメッセージの情報漏洩防止

**優先度**: P1
**対象ブランチ**: `security/generic-401`

---

## 背景

- `server/core/auth.py:25` で PyJWT 内部エラーを `f"Invalid token: {exc}"` のまま返す
- `server/api/dependencies.py:28` でそれを `HTTPException.detail` に伝搬
- 攻撃者に「exp 切れ / 署名誤り / aud 誤り」等の情報を与えてしまう

## 実装内容

`server/core/auth.py`:

```python
import logging
from typing import Any

import jwt
from jwt import PyJWKClient

from core.config import API_AUDIENCE, JWT_ISSUER, JWKS_URL

logger = logging.getLogger(__name__)
jwks_client = PyJWKClient(JWKS_URL, cache_jwk_set=True, lifespan=3600)


def verify_jwt(token: str) -> dict[str, Any]:
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload: dict[str, Any] = jwt.decode(
            token,
            signing_key.key,
            algorithms=["EdDSA"],
            audience=API_AUDIENCE,
            issuer=JWT_ISSUER,
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
    except jwt.ExpiredSignatureError:
        logger.info("JWT rejected: expired")
        raise ValueError("Token expired") from None
    except jwt.InvalidTokenError as exc:
        logger.warning("JWT rejected: %s", exc)
        raise ValueError("Invalid token") from None

    return payload
```

`server/api/dependencies.py`:

```python
async def get_current_user(credentials: BearerCredentials) -> str:
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = verify_jwt(token)
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return user_id
    except ValueError:
        raise HTTPException(status_code=401, detail="Not authenticated") from None
```

## 受け入れ基準

- [ ] 期限切れ JWT でも 401 `{"detail":"Not authenticated"}` のみ返る
- [ ] サーバログには `JWT rejected: expired` 等が記録される
- [ ] 正常系の 200 レスポンスは従来通り

## テスト方法

```python
def test_expired_token_returns_generic_401(client, expired_token):
    r = client.get("/api/notes", headers={"Authorization": f"Bearer {expired_token}"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Not authenticated"
```
