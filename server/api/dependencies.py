from collections.abc import AsyncGenerator
from typing import Annotated

import asyncpg
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.auth import verify_jwt
from core.database import get_pool

security = HTTPBearer()
BearerCredentials = Annotated[HTTPAuthorizationCredentials, Security(security)]


async def get_current_user(credentials: BearerCredentials) -> str:
    """Authorizationヘッダー (Bearerトークン) からJWTを取得し、検証する"""
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = verify_jwt(token)
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return user_id
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from None


async def get_db() -> AsyncGenerator[asyncpg.Connection]:
    """プールからコネクションを取得してリクエスト単位で管理する"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


CurrentUser = Annotated[str, Depends(get_current_user)]
DB = Annotated[asyncpg.Connection, Depends(get_db)]
