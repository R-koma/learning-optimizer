import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str | None = os.getenv("DATABASE_URL")
BETTER_AUTH_URL: str = os.getenv("BETTER_AUTH_URL", "http://localhost:3000")
JWKS_URL: str = os.getenv("JWKS_URL", f"{BETTER_AUTH_URL}/api/auth/jwks")
