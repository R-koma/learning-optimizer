# P0-1: WebSocket / API の TLS 強制

**優先度**: P0（本番投入前必須）
**対象ブランチ**: `security/tls-enforcement`

---

## 背景

- `client/hooks/use-chat-websocket.ts:80` で WebSocket 接続に JWT を平文 JSON で送信
- `NEXT_PUBLIC_WS_URL` / `NEXT_PUBLIC_API_URL` のデフォルトが `ws://` / `http://`
- 本番環境で TLS 未設定だと JWT が中間者に露出する

## 実装内容

### 1. 起動時バリデーション (Client)

新規ファイル: `client/lib/env-guard.ts`

```typescript
type AppEnv = "development" | "test" | "production";

interface RequiredUrls {
  apiUrl: string;
  wsUrl: string;
  authUrl: string;
}

function assertSecureUrl(name: string, value: string, env: AppEnv): void {
  if (env !== "production") return;
  const insecure = value.startsWith("http://") || value.startsWith("ws://");
  if (insecure) {
    throw new Error(
      `[env-guard] ${name} must use https:// or wss:// in production, got: ${value}`,
    );
  }
}

export function validateClientEnv(): RequiredUrls {
  const env = (process.env.NODE_ENV ?? "development") as AppEnv;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
  const authUrl =
    process.env.NEXT_PUBLIC_BETTER_AUTH_URL ?? "http://localhost:3000";

  assertSecureUrl("NEXT_PUBLIC_API_URL", apiUrl, env);
  assertSecureUrl("NEXT_PUBLIC_WS_URL", wsUrl, env);
  assertSecureUrl("NEXT_PUBLIC_BETTER_AUTH_URL", authUrl, env);

  return { apiUrl, wsUrl, authUrl };
}
```

**呼び出し箇所**: `client/app/layout.tsx` の Server Component 先頭で `validateClientEnv()` を 1 回実行。失敗時は起動時にクラッシュ。

### 2. 起動時バリデーション (Server)

`server/core/config.py` に追加:

```python
import os
from urllib.parse import urlparse

APP_ENV: str = os.getenv("APP_ENV", "development")

def _assert_secure(name: str, url: str) -> None:
    if APP_ENV != "production":
        return
    scheme = urlparse(url).scheme
    if scheme not in ("https", "wss"):
        raise RuntimeError(
            f"[config] {name} must use https/wss in production, got: {url}"
        )

_assert_secure("BETTER_AUTH_URL", BETTER_AUTH_URL)
_assert_secure("JWKS_URL", JWKS_URL)
```

### 3. 本番デプロイ設定

- リバースプロキシ（nginx / Caddy / ALB）で TLS 終端
- WebSocket も同じホストで `wss://` に統一
- `CORS_ORIGINS` / `BETTER_AUTH_URL` を `https://` スキームで設定

## 受け入れ基準

- [ ] `NODE_ENV=production` + `NEXT_PUBLIC_WS_URL=ws://...` でビルドしたコンテナ起動時に即クラッシュする
- [ ] `APP_ENV=production` + `BETTER_AUTH_URL=http://...` で FastAPI が起動失敗する
- [ ] 開発環境（`APP_ENV != production`）では `http://` / `ws://` がそのまま許容される

## テスト方法

```bash
# Server
APP_ENV=production BETTER_AUTH_URL=http://x uv run python -c "import core.config"
# → RuntimeError を期待

# Client
NODE_ENV=production NEXT_PUBLIC_WS_URL=ws://x node -e "require('./client/lib/env-guard').validateClientEnv()"
```
