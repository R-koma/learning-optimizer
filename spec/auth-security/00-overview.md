# 認証セキュリティ改善 全体仕様

**文書バージョン**: 1.0
**作成日**: 2026-04-23
**対象ブランチ**: `main` から派生する改善ブランチ群
**想定実施順**: P0 → P1 → P2 → P3

---

## 背景

2026-04-23 時点の認証実装調査結果に基づき、以下の改善を段階的に実施する。

現状構成:
- ブラウザ ↔ Next.js: BetterAuth のデータベースセッション + httpOnly Cookie（BFF 形）
- Next.js ↔ FastAPI: BetterAuth JWT プラグイン発行の EdDSA JWT を FastAPI が JWKS で独立検証（外部 IdP 形）

総合評価: 🟡 要改善

---

## 全体方針

- **破壊的変更を避ける**: 既存の `/api/auth/token` エンドポイントや `fetchAPI` シグネチャは維持
- **段階的ロールアウト**: P0 / P1 は本番投入前に必須、P2 / P3 は順次
- **検証方法の明記**: 各項目に「実装内容」「受け入れ基準」「テスト方法」を記載
- **読み取り専用調査の延長**: この仕様書の作成時点ではコード変更は行わない

---

## 実装順序とブランチ戦略

| 順序 | 項目 | ブランチ | PR タイトル案 |
|---|---|---|---|
| 1 | P0-1 TLS 強制 | `security/tls-enforcement` | `feat(security): enforce https/wss in production` |
| 2 | P0-2 WS タイムアウト | `security/ws-auth-timeout` | `fix(ws): add authentication timeout to websocket` |
| 3 | P1-1 aud/iss 分離 | `security/jwt-audience` | `feat(auth): separate JWT audience for API` |
| 4 | P1-2 エラー汎化 | `security/generic-401` | `fix(auth): mask jwt verification details` |
| 5 | P1-3 CORS 厳格化 | `security/strict-cors` | `fix(cors): restrict methods and headers` |
| 6 | P2-1 Cookie 明示 | `security/explicit-cookies` | `feat(auth): explicit cookie attributes` |
| 7 | P2-2 CSRF ドキュメント | `docs/csrf-policy` | `docs(security): document csrf posture` |
| 8 | P3-1 トークンキャッシュ | `perf/token-cache` | `perf(api): cache jwt within expiry window` |

各 PR は独立してレビュー・マージ可能な粒度にする。P1-1 のみロールアウト戦略（フォールバック → 切替 → 削除）の 3 段階 PR になる。

---

## 本番投入前チェックリスト

- [ ] P0-1 / P0-2 完了
- [ ] 本番環境変数レビュー: `CORS_ORIGINS`, `BETTER_AUTH_URL`, `JWKS_URL`, `NEXT_PUBLIC_*_URL` がすべて https/wss
- [ ] BetterAuth のバージョン固定（`package.json` の `^` を外すか、`package-lock.json` をコミット済み確認）
- [ ] Gitleaks CI が通っている
- [ ] `/api/auth/jwks` が **公開鍵のみ** 返すことを curl で確認
- [ ] ログイン → ノート作成 → ログアウトの E2E が本番 URL で通る
- [ ] セキュリティヘッダ（HSTS, X-Content-Type-Options, X-Frame-Options, CSP）がリバースプロキシで付与されている

---

## 未確認事項（実装前に要リサーチ）

1. **`better-auth/plugins` の `jwt()` の正確なオプション名**（`jwt.audience` / `jwt.issuer` / `jwt.expirationTime`）
   - 調査方法: `node_modules/better-auth/dist/plugins/jwt/*.d.ts` を読む
2. **`advanced.defaultCookieAttributes` / `trustedOrigins` / `disableCSRFCheck` の API 安定性**
   - 調査方法: BetterAuth GitHub のリリースノート
3. **Next.js 16 の Server Component 間での `Map` 共有スコープ**
   - 調査方法: `next start` の実行モデル（プロセス / ワーカー）を Next.js 公式ドキュメントで確認
4. **現行 `/api/auth/token` が返す JWT の実ペイロード**
   - 調査方法: ローカル環境で curl し、`jwt.io` でデコード
