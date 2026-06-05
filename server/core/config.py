import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str | None = os.getenv("DATABASE_URL")
BETTER_AUTH_URL: str = os.getenv("BETTER_AUTH_URL", "http://localhost:3000")
JWKS_URL: str = os.getenv("JWKS_URL", f"{BETTER_AUTH_URL}/api/auth/jwks")

# 画像など対話添付の永続化先。AWS 移行（#128）で S3 アダプタを追加する前提で抽象化している。
STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local")
LOCAL_STORAGE_DIR: str = os.getenv("LOCAL_STORAGE_DIR", "storage_data")

# 対話に添付できる画像の制限。OpenAI のプラットフォーム上限は緩いため、コスト・UX 観点でアプリ側が絞る。
MAX_IMAGES_PER_MESSAGE: int = 4
MAX_IMAGE_BYTES: int = 5 * 1024 * 1024
ALLOWED_IMAGE_MIME_TYPES: frozenset[str] = frozenset({"image/jpeg", "image/png", "image/webp"})
