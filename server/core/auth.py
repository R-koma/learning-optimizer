from typing import Any

import jwt
from jwt import PyJWKClient

from core.config import BETTER_AUTH_URL, JWKS_URL

jwks_client = PyJWKClient(JWKS_URL, cache_jwk_set=True, lifespan=3600)


def verify_jwt(token: str) -> dict[str, Any]:
    """JWKS を使って JWT をローカルで検証し、ペイロードを返す。"""
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload: dict[str, Any] = jwt.decode(
            token,
            signing_key.key,
            algorithms=["EdDSA"],
            audience=BETTER_AUTH_URL,
            issuer=BETTER_AUTH_URL,
        )
    except jwt.ExpiredSignatureError as exc:
        raise ValueError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc

    return payload
