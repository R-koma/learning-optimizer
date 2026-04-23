# P3-2: 将来の移行候補（メモ）

**優先度**: 参考
**対象ブランチ**: なし（検討項目）

---

本ドキュメントは本仕様書シリーズの必須項目ではないが、中長期の方針として記録する。

## 検討項目

### Opaque Access Token + Introspection

- JWT 失効が困難な問題（stateless ゆえログアウト後も `exp` まで有効）に対する恒久解
- BetterAuth が DB セッションを持っているので `/api/auth/session` をサーバサイド introspection として使う構成に寄せる
- トレードオフ: FastAPI → Next.js への往復が増えるが、即時失効・権限変更が可能になる

### mTLS or 共有シークレット

- Next.js → FastAPI を内部ネットワーク通信として閉じる BFF 寄りへの移行
- 現状のハイブリッド（JWT + JWKS）から、純粋なパターン A への移行候補
- デプロイ上の複雑さは増えるが、攻撃面を削減できる

### Refresh Token Rotation

- 現状 `/api/auth/token` 再発行で代替しているが、リフレッシュ境界を明示化する
- 長期セッション Cookie とは別に、短命 access / 回転型 refresh を導入
- BetterAuth jwt プラグインの拡張 or 独自実装

### Rate Limiting

- `/api/auth/**` と `/ws/chat` にレート制限（IP 単位、ユーザ単位）
- ブルートフォース攻撃・クレデンシャルスタッフィング対策
- 実装候補: Next.js middleware、FastAPI `slowapi`、リバースプロキシ層

### セッション一括失効機構

- 管理画面からユーザのセッションを強制終了できる機構
- JWT のブラックリスト or opaque token への切替が前提

## 意思決定のトリガー

以下のいずれかが発生したときに P3-2 を再検討:

- ユーザ数が 1000 を超えた
- セキュリティインシデント（トークン漏洩等）が発生した
- 認証まわりに対する監査要件が追加された
- マルチテナント化（組織アカウント等）の要件が出た
