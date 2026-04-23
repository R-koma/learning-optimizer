# P1-1: JWT の `aud` / `iss` を分離

**優先度**: P1
**対象ブランチ**: `security/jwt-audience`

---

## 背景

- `server/core/auth.py:19-20` で `audience` と `issuer` を同じ `BETTER_AUTH_URL` に設定
- BetterAuth jwt プラグイン発行の JWT は汎用で、API 専用の境界が無い
- 本来 `aud` は「トークン受信側（FastAPI）」、`iss` は「発行者（Next.js/BetterAuth）」で分離すべき

## 実装内容

### 1. BetterAuth jwt プラグインに audience を指定

`client/lib/auth.ts`:

```typescript
import { betterAuth } from "better-auth";
import { jwt } from "better-auth/plugins";
import { Pool } from "pg";

const API_AUDIENCE = "learning-optimizer-api";
const JWT_ISSUER = process.env.BETTER_AUTH_URL ?? "http://localhost:3000";

export const auth = betterAuth({
  database: new Pool({ connectionString: process.env.DATABASE_URL }),
  emailAndPassword: { enabled: true },
  socialProviders: {
    google: {
      clientId: process.env.GOOGLE_CLIENT_ID as string,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET as string,
    },
  },
  plugins: [
    jwt({
      jwt: {
        audience: API_AUDIENCE,
        issuer: JWT_ISSUER,
        expirationTime: "15m",
      },
    }),
  ],
});
```

※ `better-auth/plugins` の `jwt()` オプション名は公式ドキュメント要確認。名前が異なれば発行レスポンスを実機で確認して合わせる。

### 2. FastAPI 検証側を分離

`server/core/config.py`:

```python
API_AUDIENCE: str = os.getenv("API_AUDIENCE", "learning-optimizer-api")
JWT_ISSUER: str = os.getenv("JWT_ISSUER", BETTER_AUTH_URL)
```

`server/core/auth.py`:

```python
payload: dict[str, Any] = jwt.decode(
    token,
    signing_key.key,
    algorithms=["EdDSA"],
    audience=API_AUDIENCE,
    issuer=JWT_ISSUER,
    options={"require": ["exp", "iat", "sub", "aud", "iss"]},
)
```

### 3. 環境変数の追加

- `server/.env`, `docker-compose.yml` に `API_AUDIENCE=learning-optimizer-api`, `JWT_ISSUER=${BETTER_AUTH_URL}`

## 受け入れ基準

- [ ] `/api/auth/token` が返す JWT のペイロードに `aud: "learning-optimizer-api"` が含まれる
- [ ] 旧 `aud` の JWT は FastAPI で 401 になる
- [ ] `iss` / `aud` / `exp` / `iat` / `sub` のいずれかが欠けた JWT は 401 になる

## テスト方法

```python
# server/tests/unit/test_auth.py
def test_verify_jwt_rejects_wrong_audience(valid_signing_key):
    token = build_jwt(aud="other-service", ...)
    with pytest.raises(ValueError, match="Invalid token"):
        verify_jwt(token)
```

## ロールアウト戦略（3 段階 PR）

1. **PR #1 (Server)**: `API_AUDIENCE` 未設定時は旧挙動（`aud=iss=BETTER_AUTH_URL`）を許容するフォールバックを実装
2. **PR #2 (Client)**: BetterAuth に `audience` を設定、サーバ側で `API_AUDIENCE` を有効化
3. **PR #3 (Cleanup)**: サーバ側フォールバックを削除
