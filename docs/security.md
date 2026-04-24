# セキュリティポリシー

## 認証アーキテクチャ

### ブラウザ ↔ Next.js
- BetterAuth のデータベースセッション + httpOnly Cookie（BFF 形式）
- Cookie 属性: `HttpOnly; SameSite=Lax; Secure`（本番のみ）
- CSRF 対策: BetterAuth 内蔵 CSRF 保護（`disableCSRFCheck: false`）と `SameSite=Lax` Cookie の組み合わせ

### Next.js ↔ FastAPI
- BetterAuth JWT プラグイン発行の EdDSA JWT を Bearer トークンとして送信
- FastAPI が JWKS エンドポイントで公開鍵を取得し独立検証
- JWT クレーム: `aud=learning-optimizer-api`, `iss=BETTER_AUTH_URL`, `exp`, `iat`, `sub` を必須検証

## CSRF ポリシー

- Next.js `/api/auth/**` は `SameSite=Lax` Cookie と BetterAuth 内蔵 CSRF 保護に依存
- FastAPI はトークン認証のみで Cookie を受け付けない（CSRF リスクなし）
- **カスタム POST エンドポイントを Next.js に追加する場合**: Origin ヘッダー検証または CSRF トークンを必須とすること

## CORS ポリシー

- 許可 Origin: 環境変数 `CORS_ORIGINS`（カンマ区切り、デフォルト `http://localhost:3000`）
- 許可メソッド: `GET, POST, PUT, PATCH, DELETE, OPTIONS`
- 許可ヘッダー: `Authorization, Content-Type`
- `allow_credentials: false`（FastAPI は Cookie 認証を使用しない）

## TLS 要件

本番環境では以下の全 URL が `https://` または `wss://` を使用すること:
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_WS_URL`
- `NEXT_PUBLIC_BETTER_AUTH_URL`
- `BETTER_AUTH_URL`（サーバー側）
- `JWKS_URL`（サーバー側）

`APP_ENV=production` 設定時に FastAPI 起動時バリデーションが実施される。
`NODE_ENV=production` 時に Next.js 起動時バリデーションが実施される。
