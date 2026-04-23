# P2-1: BetterAuth Cookie 設定の明示化

**優先度**: P2
**対象ブランチ**: `security/explicit-cookies`

---

## 背景

- `client/lib/auth.ts` で Cookie 属性が未指定。BetterAuth デフォルトに依存
- 本番で `secure: true` が確実に立つ保証がコード上に無い

## 実装内容

`client/lib/auth.ts`:

```typescript
const isProd = process.env.NODE_ENV === "production";

export const auth = betterAuth({
  database: new Pool({ connectionString: process.env.DATABASE_URL }),
  emailAndPassword: { enabled: true },
  socialProviders: {
    google: {
      clientId: process.env.GOOGLE_CLIENT_ID as string,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET as string,
    },
  },
  advanced: {
    defaultCookieAttributes: {
      httpOnly: true,
      secure: isProd,
      sameSite: "lax",
    },
    useSecureCookies: isProd,
  },
  session: {
    expiresIn: 60 * 60 * 24 * 7,     // 7 days
    updateAge: 60 * 60 * 24,          // 1 day
    cookieCache: { enabled: true, maxAge: 5 * 60 },
  },
  plugins: [jwt({ jwt: { audience: "learning-optimizer-api", expirationTime: "15m" } })],
});
```

※ オプションキー名は BetterAuth の実際のバージョンに合わせて要調整。実装前に `node_modules/better-auth` 内の型定義を確認すること。

## 受け入れ基準

- [ ] 本番相当ビルドで `Set-Cookie` に `Secure; HttpOnly; SameSite=Lax` が含まれる
- [ ] ログインセッションが 7 日間維持される
- [ ] `/api/auth/token` が 15 分有効の JWT を返す

## テスト方法

```bash
curl -i -X POST http://localhost:3000/api/auth/sign-in/email \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"..."}' \
  | grep -i "set-cookie"
```
