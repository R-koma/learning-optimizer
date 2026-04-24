import os
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

APP_ENV: str = os.getenv("APP_ENV", "development")
DATABASE_URL: str | None = os.getenv("DATABASE_URL")
BETTER_AUTH_URL: str = os.getenv("BETTER_AUTH_URL", "http://localhost:3000")
JWKS_URL: str = os.getenv("JWKS_URL", f"{BETTER_AUTH_URL}/api/auth/jwks")
API_AUDIENCE: str = os.getenv("API_AUDIENCE", "learning-optimizer-api")
JWT_ISSUER: str = os.getenv("JWT_ISSUER", BETTER_AUTH_URL)


def _assert_secure(name: str, url: str) -> None:
    if APP_ENV != "production":
        return
    scheme = urlparse(url).scheme
    if scheme not in ("https", "wss"):
        raise RuntimeError(f"[config] {name} must use https/wss in production, got: {url}")


_assert_secure("BETTER_AUTH_URL", BETTER_AUTH_URL)
_assert_secure("JWKS_URL", JWKS_URL)
