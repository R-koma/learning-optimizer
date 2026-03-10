from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.auth import verify_jwt
from core.database import get_pool

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),  # noqa: B008
) -> str:
    """Authorizationヘッダー (Bearerトークン) からJWTを取得し、検証する"""
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = verify_jwt(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return user_id
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


async def get_db():
    """DBコネクションプールを返す"""
    return await get_pool()
