# CLAUDE.md

## プロジェクト概要

Learning Optimizer は「プロテジェ効果」（教えることで学ぶ）を活用した AI 学習アプリケーション。ユーザーが LLM エージェントとの対話を通じて学習し、自動でノート・フィードバック・復習スケジュールが生成される。

## ローカル開発環境のセットアップ

```bash
# DB のみ起動（推奨）
make dev-db          # docker compose up -d

# サーバーとクライアントを別ターミナルで起動
make dev-server      # cd server && uv run fastapi dev main.py
make dev-client      # cd client && npm run dev

# フルスタックを Docker で起動
docker compose up
```

初回セットアップ:
```bash
cd server && uv sync
uv run alembic upgrade head   # BetterAuth テーブルを先に適用してから実行すること（後述）
cd ../client && npm install
```

## 開発コマンド

### バックエンド（server/）
```bash
uv run fastapi dev main.py           # 開発サーバー起動
uv run alembic upgrade head          # マイグレーション適用
uv run alembic revision --autogenerate -m "description"  # マイグレーション生成
uv run ruff check . --fix            # Lint（自動修正あり）
uv run ruff format .                 # フォーマット
uv run mypy .                        # 型チェック
```

### フロントエンド（client/）
```bash
npm run dev          # 開発サーバー起動
npm run build        # ビルド
npm run lint         # ESLint
npx tsc --noEmit     # 型チェック
npx prettier --write # フォーマット（pre-commit で自動実行）
```

### ADR（アーキテクチャ決定記録）
```bash
make adr name=your-decision-title    # docs/adr/ に連番ファイルを生成
```

## テスト

### バックエンド（pytest + pytest-asyncio）
```bash
cd server
uv run pytest                                  # 全テスト実行
uv run pytest --cov=. --cov-report=term        # カバレッジ付き
uv run pytest tests/unit/test_note_routes.py   # 特定ファイルのみ
```

- テストは `server/tests/unit/` に配置
- **カバレッジ目標: 60%**
- DB を使うテストは実 PostgreSQL に接続（モック禁止）
- `asyncio_mode = "auto"` のため `@pytest.mark.asyncio` 不要

### フロントエンド（Vitest）
```bash
cd client
npm run test          # 一回実行
npm run test:watch    # ウォッチモード
```

- テストは `client/__tests__/` に配置

## CI パイプライン（GitHub Actions）

PR マージ前に以下がすべて通る必要がある:
- `server-lint`: ruff check / format
- `server-typecheck`: mypy（strict モード）
- `server-test`: pytest（実 DB 使用）
- `client-lint`: eslint + tsc --noEmit
- `client-test`: vitest
- `secret-scan`: Gitleaks によるシークレットスキャン

## アーキテクチャ

### 全体構成
- **client/**: Next.js 16（App Router）+ React 19 + TypeScript
- **server/**: Python 3.13 + FastAPI + LangGraph
- **DB**: PostgreSQL 17（asyncpg で非同期アクセス）
- **認証**: BetterAuth（クライアント側）→ JWT + JWKS（サーバー側で EdDSA 検証）
- **リアルタイム通信**: WebSocket（`ws://localhost:8000/ws/chat`）

### LangGraph ワークフロー（server/graph/）
```
learning_start → learning_dialogue（最大3ターン or LEARNING_END）→ generate_note → generate_feedback → END
```
レビューセッションは同じグラフを使い、既存ノート内容をプロンプトに含め `generate_note` をスキップする。

### データアクセスパターン
- **リポジトリパターン**: `server/repositories/` に SQL-first で実装（ORM 不使用、asyncpg で直接 SQL）
- **依存性注入**: FastAPI の `Depends()` で `CurrentUser`（JWT 検証済み）と `DB`（コネクションプール）を注入

### フロントエンドのパターン
- **WebSocket Hook**: `client/hooks/use-chat-websocket.ts` が接続ライフサイクル・メッセージ型振り分けを管理
- **API 呼び出し**: `client/lib/api.ts` の `fetchAPI()` が JWT を自動付与

## コード規約

### Python（Ruff + mypy strict）
- 行長: 119 文字
- ターゲット: Python 3.13
- ルール: E, W, F, I, B, UP
- mypy strict モード（`pydantic.mypy` プラグイン使用）

### TypeScript
- ESLint + Prettier（`.ts`/`.tsx` は commit 時に自動フォーマット）
- strict モード

### pre-commit フック
commit 時に自動実行（`uv run pre-commit install` で有効化）:
- ruff check + format（server/）
- mypy（server/）
- prettier（client/ の .ts/.tsx）

## 環境変数

### server/.env
```
DATABASE_URL=postgresql://learning_optimizer:localdev@localhost:5432/learning_optimizer
OPENAI_API_KEY=...
BETTER_AUTH_URL=http://localhost:3000
JWKS_URL=http://localhost:3000/api/auth/jwks
```

### client/.env.local
```
NEXT_PUBLIC_API_URL=http://localhost:8000
DATABASE_URL=postgresql://learning_optimizer:localdev@localhost:5432/learning_optimizer
BETTER_AUTH_SECRET=...
BETTER_AUTH_URL=http://localhost:3000
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

## 注意事項

- **マイグレーション順序**: `alembic upgrade head` の前に `client/better-auth_migrations/*.sql` を適用すること（BetterAuth テーブルへの外部キー制約があるため）
- **DB テーブル**: `notes`, `dialogue_sessions`, `dialogue_messages`, `feedbacks`, `review_schedules` が主要テーブル。BetterAuth 管理テーブル（`user`, `account`, `session` 等）も同一 DB に存在し、外部キー制約によるカスケード削除あり
- **LangGraph の永続化**: `langgraph-checkpoint-postgres` を使用。セッション状態は DB に保存される
