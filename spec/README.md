# spec/

Learning Optimizer の仕様書・改善計画を格納するディレクトリ。

## 認証セキュリティ改善

2026-04-23 時点の認証実装調査（ハイブリッド構成: BetterAuth Cookie セッション + EdDSA JWT + FastAPI JWKS 検証）に基づく改善仕様書。

| ファイル | 内容 | 優先度 |
|---|---|---|
| [auth-security/00-overview.md](./auth-security/00-overview.md) | 全体方針・実装順序・チェックリスト | - |
| [auth-security/P0-1-tls-enforcement.md](./auth-security/P0-1-tls-enforcement.md) | WebSocket / API の TLS 強制 | P0 |
| [auth-security/P0-2-ws-auth-timeout.md](./auth-security/P0-2-ws-auth-timeout.md) | WebSocket 認証メッセージのタイムアウト | P0 |
| [auth-security/P1-1-jwt-audience.md](./auth-security/P1-1-jwt-audience.md) | JWT の `aud` / `iss` を分離 | P1 |
| [auth-security/P1-2-generic-error.md](./auth-security/P1-2-generic-error.md) | エラーメッセージの情報漏洩防止 | P1 |
| [auth-security/P1-3-strict-cors.md](./auth-security/P1-3-strict-cors.md) | CORS の厳格化 | P1 |
| [auth-security/P2-1-explicit-cookies.md](./auth-security/P2-1-explicit-cookies.md) | BetterAuth Cookie 設定の明示化 | P2 |
| [auth-security/P2-2-csrf-posture.md](./auth-security/P2-2-csrf-posture.md) | CSRF 対策の確認と明示化 | P2 |
| [auth-security/P3-1-token-cache.md](./auth-security/P3-1-token-cache.md) | トークン取得のキャッシュ | P3 |
| [auth-security/P3-2-future-work.md](./auth-security/P3-2-future-work.md) | 将来の移行候補 | - |

## 関連ドキュメント

- [../docs/adr/](../docs/adr/) — アーキテクチャ決定記録（ADR）
- [../CLAUDE.md](../CLAUDE.md) — プロジェクト全体の開発ガイド
