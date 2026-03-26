# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

Learning Optimizer は「プロテジェ効果」（教えることで学ぶ）を活用した AI 学習アプリケーション。ユーザーが LLM エージェントとの対話を通じて学習し、自動でノート・フィードバック・復習スケジュールが生成される。

## 開発コマンド

### フロントエンド（client/）
```bash
cd client
npm install
npm run dev
npm run build
npm run lint 
```

### バックエンド（server/）
```bash
cd server
uv sync
uv run fastapi dev main.py
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description" 
uv run ruff check . 
uv run ruff format .
```

### データベース
PostgreSQL が必要。デフォルト接続: `postgresql://dev:dev@localhost:5432/learning_optimizer`

## アーキテクチャ

### 全体構成
- **client/**: Next.js 16（App Router）+ React 19 + TypeScript
- **server/**: Python 3.13 + FastAPI + LangGraph
- **DB**: PostgreSQL（asyncpg で非同期アクセス）
- **認証**: BetterAuth（クライアント側）→ JWT + JWKS（サーバー側で検証）
- **リアルタイム通信**: WebSocket（`ws://localhost:8000/ws/chat`）

### 認証フロー
BetterAuth が Next.js の API ルート（`/api/auth/[...all]`）で OAuth/セッション管理を担当。サーバーへの API 呼び出しには BetterAuth の `/api/auth/token` エンドポイントから取得した JWT を Authorization ヘッダーに付与。サーバー側は JWKS エンドポイントから公開鍵を取得して EdDSA 署名を検証する。

### LangGraph ワークフロー（server/graph/）
学習セッションのコア処理を LangGraph で実装:

```
learning_start → learning_dialogue（3ターン繰り返し）→ generate_note → generate_feedback → END
```

- **learning_start**: トピックを受け取り最初の質問を生成
- **learning_dialogue**: 対話ループ（3ターンまたは LEARNING_END で終了）
- **generate_note**: 会話からノートを自動生成（`with_structured_output` で Pydantic モデルへ）
- **generate_feedback**: 理解度評価（high/medium/low）を生成し復習スケジュールを作成

レビューセッションは同じグラフを使うが、既存ノートの内容を含むプロンプトで開始し、generate_note をスキップする。

### データアクセスパターン
- **リポジトリパターン**: `server/repositories/` に SQL-first で実装（ORM 不使用、asyncpg で直接 SQL 実行）
- **依存性注入**: FastAPI の `Depends()` で認証（`CurrentUser`）と DB プール（`DB`）を注入

### フロントエンドのパターン
- **WebSocket Hook**: `client/hooks/use-chat-websocket.ts` が接続ライフサイクル・メッセージ型振り分け・セッション状態を管理
- **UIコンポーネント**: shadcn/ui ベース（`client/components/ui/`）
- **API呼び出し**: `client/lib/api.ts` の `fetchAPI()` ユーティリティが JWT を自動付与

### 復習スケジュール（エビングハウス忘却曲線）
`server/services/review_scheduler.py` で実装。間隔: `[1, 3, 7, 14, 30, 60]` 日。理解度が high なら次の間隔へ、low なら前の間隔へ戻る。

## DB テーブル構成
主要テーブル: `notes`, `dialogue_sessions`, `dialogue_messages`, `feedbacks`, `review_schedules`。BetterAuth 管理テーブル（`user`, `account`, `session` 等）も同一 DB に存在。外部キー制約によるカスケード削除あり。

## コード規約

### Python（Ruff）
- 行長: 119文字
- ターゲット: Python 3.13
- ルール: E, W, F, I, B, UP（pyflakes, isort, bugbear, pyupgrade）

### TypeScript
- ESLint + Prettier
- strict モード

## 環境変数

### client/.env.local
`NEXT_PUBLIC_API_URL`, `DATABASE_URL`, `BETTER_AUTH_SECRET`, `BETTER_AUTH_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`

### server/.env
`DATABASE_URL`, `OPENAI_API_KEY`, `BETTER_AUTH_URL`, `JWKS_URL`
