import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str | None = os.getenv("DATABASE_URL")
BETTER_AUTH_URL: str = os.getenv("BETTER_AUTH_URL", "http://localhost:3000")
JWKS_URL: str = os.getenv("JWKS_URL", f"{BETTER_AUTH_URL}/api/auth/jwks")

# Langfuse（LLM トレース送出）。キー未設定でもアプリは起動できる必要があるため、
# 有無を明示的に持ち、未設定なら送出を丸ごと無効化する。
LANGFUSE_PUBLIC_KEY: str | None = os.getenv("LANGFUSE_PUBLIC_KEY") or None
LANGFUSE_SECRET_KEY: str | None = os.getenv("LANGFUSE_SECRET_KEY") or None
LANGFUSE_BASE_URL: str = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
# Langfuse 側の環境区分。ローカル・CI のトレースが本番と混ざらないよう既定は development。
LANGFUSE_TRACING_ENVIRONMENT: str = os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "development")

# 画像など対話添付の永続化先。AWS 移行（#128）で S3 アダプタを追加する前提で抽象化している。
STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local")
LOCAL_STORAGE_DIR: str = os.getenv("LOCAL_STORAGE_DIR", "storage_data")

# 「今日の復習」の当日判定に使うタイムゾーン。timestamptz をこの暦日に変換して当日を決めるため、
# サーバーの稼働 TZ に依存せずユーザー（日本）の日付境界で集計できる。
REVIEW_TIMEZONE: str = os.getenv("REVIEW_TIMEZONE", "Asia/Tokyo")

# 対話に添付できる画像の制限。OpenAI のプラットフォーム上限は緩いため、コスト・UX 観点でアプリ側が絞る。
MAX_IMAGES_PER_MESSAGE: int = 4
MAX_IMAGE_BYTES: int = 5 * 1024 * 1024
ALLOWED_IMAGE_MIME_TYPES: frozenset[str] = frozenset({"image/jpeg", "image/png", "image/webp"})
