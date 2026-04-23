# P2-2: CSRF 対策の確認と明示化

**優先度**: P2
**対象ブランチ**: `docs/csrf-policy`

---

## 背景

- FastAPI は Bearer トークンのみ受け付けるので API 側の CSRF リスクは低い
- しかし Next.js の `/api/auth/**` は Cookie セッションで動作するため、ここに CSRF 対策が必要
- BetterAuth のデフォルト挙動に依存しており、プロジェクト内で保証が無い

## 実装内容

### 1. BetterAuth の CSRF 設定を明示

`client/lib/auth.ts`:

```typescript
export const auth = betterAuth({
  // ...
  advanced: {
    defaultCookieAttributes: {
      httpOnly: true,
      secure: isProd,
      sameSite: "lax",  // ← Lax で OAuth 外部 IdP リダイレクトとの両立
    },
    disableCSRFCheck: false,  // 明示的に true にしないこと
  },
  trustedOrigins: [
    process.env.BETTER_AUTH_URL ?? "http://localhost:3000",
  ],
});
```

### 2. ドキュメント追記

`docs/security.md`（新規）に以下を記載:

- Next.js `/api/auth/**` は `sameSite=Lax` Cookie と BetterAuth 内蔵 CSRF 保護に依存
- FastAPI はトークン認証のみで Cookie を受け付けない
- カスタム POST エンドポイントを Next.js に追加する場合は、Origin ヘッダ検証または CSRF トークンを必須とする

## 受け入れ基準

- [ ] `trustedOrigins` に本番ドメインが含まれる
- [ ] `docs/security.md` が存在する
- [ ] BetterAuth が CSRF チェックを有効化していることを GitHub のリリースノートで確認
