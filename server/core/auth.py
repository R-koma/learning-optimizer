import logging
from typing import Any

import jwt
from jwt import PyJWKClient

from core.config import API_AUDIENCE, JWKS_URL, JWT_ISSUER

logger = logging.getLogger(__name__)
jwks_client = PyJWKClient(JWKS_URL, cache_jwk_set=True, lifespan=3600)


def verify_jwt(token: str) -> dict[str, Any]:
    """JWKS を使って JWT をローカルで検証し、ペイロードを返す。"""
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
