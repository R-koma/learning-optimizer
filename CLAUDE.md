# CLAUDE.md

## プロジェクト概要

「プロテジェ効果」（教えることで学ぶ）を活用した AI 学習アプリ。ユーザーが LLM と対話しながら学習し、ノート・フィードバック・復習スケジュールが自動生成される。

- **client/**: Next.js 16 (App Router) + React 19 + TypeScript
- **server/**: Python 3.13 + FastAPI + LangGraph
- **DB**: PostgreSQL 17（asyncpg で非同期アクセス、ORM 不使用）
- **認証**: BetterAuth（client）→ JWT + JWKS（server で EdDSA 検証）
- **リアルタイム**: WebSocket `ws://localhost:8000/ws/chat`

---

## 開発コマンド

### バックエンド（`server/`）
```bash
uv run fastapi dev main.py                                    # 開発サーバー
uv run alembic upgrade head                                   # マイグレーション適用
uv run alembic revision --autogenerate -m "description"       # マイグレーション生成
uv run ruff check . --fix && uv run ruff format .             # Lint + フォーマット
uv run mypy .                                                 # 型チェック（strict）
uv run pytest                                                 # テスト全実行
uv run pytest --cov=. --cov-report=term                      # カバレッジ付き
```

> **Note:** eval ハーネスは再構築中。`evals/` には現在データ資産のみ（`datasets/`・`rubrics/`）が残り、実行コードは未実装。

### フロントエンド（`client/`）
```bash
npm run dev              # 開発サーバー
npm run build            # ビルド
npm run lint             # ESLint
npx tsc --noEmit         # 型チェック
npm run test             # Vitest（一回実行）
npm run test:watch       # ウォッチモード
```

### その他
```bash
make adr name=your-title  # docs/adr/ にアーキテクチャ決定記録を生成
make test-db              # テスト用 DB 起動
```

---

## ディレクトリ構成

```text
server/
├── main.py                    # FastAPI エントリーポイント・lifespan
├── api/
│   ├── routes/                # REST エンドポイント（note, feedback, review_schedule, dialogue_session）
│   ├── websocket/chat.py      # WebSocket ハンドラ
│   └── dependencies.py        # CurrentUser, DB (Depends 注入)
├── core/
│   ├── auth.py                # JWT / JWKS 検証
│   ├── config.py              # 環境変数
│   └── database.py            # asyncpg コネクションプール
├── graph/                     # LangGraph ワークフロー
│   ├── builder.py             # グラフ定義・route_after_dialogue
│   ├── state.py               # LearningState TypedDict
│   ├── nodes/                 # learning_start, learning_dialogue, generate_note, generate_feedback, update_note_and_feedback
│   └── prompts/               # タスク別プロンプト（learning_planner, analysis, note, feedback, review, question）
├── observability/             # langfuse_tracing.py（Langfuse へのトレース送出）
├── repositories/              # SQL-first データアクセス（asyncpg 直接）
├── schemas/                   # Pydantic モデル（リクエスト/レスポンス）
├── storage/                   # 対話添付のオブジェクトストレージ抽象（local 実装、S3 は #128 で追加）
├── services/review_scheduler.py
├── migrations/                # Alembic（env.py, versions/）
├── evals/                     # データ資産のみ（datasets/・rubrics/）。ハーネスは再構築中
└── tests/
    ├── unit/                  # pytest + 実 DB（モック禁止）
    └── integration/

client/
├── app/
│   ├── (auth)/                # sign-in, sign-up
│   ├── (main)/                # dashboard, learn, notes/[id], review/[noteId]
│   └── api/                   # Next.js Route Handlers（auth/[...all], upload-avatar）
├── context/                   # navbar-slot-context.tsx（ナビバー差し込み）
├── components/
│   ├── chat/                  # chat-input など
│   ├── layout/                # sidebar, navbar, main-layout-client
│   ├── notes/
│   └── ui/                   # shadcn/ui コンポーネント
├── hooks/use-chat-websocket.ts # WebSocket ライフサイクル管理
├── lib/
│   ├── api.ts                 # fetchAPI()（JWT 自動付与）
│   ├── auth.ts / auth-client.ts
│   └── utils.ts
└── __tests__/                 # Vitest テスト
```

---

## アーキテクチャ詳細

### LangGraph ワークフロー

```
learning_start → learning_dialogue（対話継続中はループ）
  ├─ session_type="learning" → generate_note → generate_feedback → END
  └─ session_type="review"   → update_note_and_feedback → END
```

- 分岐は `graph/builder.py` の `route_after_dialogue` が担当：`should_generate_note` が立つまで `learning_dialogue` をループ、立った後 `session_type` で `generate_note` / `update_note_and_feedback` に分岐
- レビューセッション: 既存ノートをプロンプトに注入し、`update_note_and_feedback` でノート・フィードバックを更新（`generate_note` / `generate_feedback` は通らない）
- `interrupt_before=["learning_dialogue"]` でユーザー入力待ちのため毎ターン中断する（再開はチェックポイントから）
- ノードスパン・LLM 生成の計測は Langfuse が自動で行う（`observability/langfuse_tracing.py`）。詳細は「Langfuse トレース」節
- グラフ状態は `langgraph-checkpoint-postgres` で DB に永続化
- `LearningState` は `session_type`（`"learning"` / `"review"`）で分岐

### API エンドポイント

| Method | Path | 用途 |
|--------|------|------|
| GET | `/api/health` | ヘルスチェック |
| GET/PATCH | `/api/notes` | ノート取得・更新 |
| GET | `/api/feedbacks` | フィードバック取得 |
| GET | `/api/review-schedules` | 復習スケジュール |
| GET | `/api/dialogue-sessions` | セッション一覧 |
| WS | `/ws/chat` | チャット WebSocket |

### データアクセスパターン

- リポジトリパターン（`repositories/`）: SQL を直接記述、asyncpg で実行
- 依存性注入: `CurrentUser`（JWT 検証済みユーザー ID）と `DB`（コネクション）を `Depends()` で注入
- ORM 不使用、`asyncpg.Record` を直接扱う
- リポジトリ関数の接続引数は `core.database.DBConnection`（`Connection | PoolConnectionProxy`）を使う。`pool.acquire()` が返すのは `Connection` の非サブクラスである `PoolConnectionProxy` のため、両方を受け取れる必要がある（`Pool` を直接渡さず、必ず `acquire()` してから渡す）

### 画像添付（マルチモーダル）

- 対話の `user_message` に画像（JPEG/PNG/WebP・最大4枚・各5MB）を添付できる。クライアントは送信前に長辺2048pxへ縮小し base64 で送る（`client/lib/image.ts`）
- バイナリは `storage/`（dev: ローカルFS、本番: S3 は #128）に保存し、参照メタは `dialogue_message_images` テーブルに持つ。state（チェックポイント）には base64 を載せず storage_key 参照のみ保持し、LLM 呼び出し直前にストレージから読んで base64 data URL を組む（`graph/multimodal.py`）
- LLM へは最新ユーザーメッセージの画像のみ `image_url`（detail=high）ブロックで渡す（会話履歴はプロンプト本文に文字列化されるため）。ノート/フィードバック生成には画像を渡さない
- 履歴の画像は `GET /api/dialogue-sessions/{id}/images/{image_id}` で配信（Bearer 認証必須のためフロントは `fetchImageObjectURL()` で取得）
- 環境変数: `STORAGE_BACKEND`（既定 `local`）・`LOCAL_STORAGE_DIR`（既定 `storage_data`）
- 音声・動画は対象外（音声は #41）

### Langfuse トレース

- 送出は `observability/langfuse_tracing.py` に閉じている。クライアントは `main.py` の lifespan で `init_tracing()` / `shutdown_tracing()`（後者を省くと終了間際のトレースがバッチ送出されずに落ちる）
- 粒度は **1ターン＝1 trace・1対話セッション＝1 Langfuse session**。グラフは `interrupt_before` で毎ターン中断するため、実行の切れ目がそのままターンの境界になる
- グラフ実行は `traced_graph_run()` で自前の root span に包む。LangGraph の実行をそのまま root にすると trace の入出力が `LearningState` 丸ごと（かつ再開ターンでは入力 `None`）になり、一覧・評価器から読めないため。root span にはユーザー発話と応答だけを載せる
- `CallbackHandler` は root span が active な間に生成する必要がある（生成時点の trace context を引き継ぐため）。`build_graph_config()` が返す config に callbacks は入っておらず、`traced_graph_run()` が実行時に足す
- trace 名（`respond-to-user` 等）はダッシュボード・評価器の参照キーになるため、ID やターン番号を混ぜない。変更は破壊的変更として扱う
- `aget_state` / `aupdate_state` はノードを実行しないので callbacks を付けない（付けると中身のない trace が量産される）
- 環境変数: `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`（未設定なら送出は自動的に無効）・`LANGFUSE_BASE_URL`・`LANGFUSE_TRACING_ENVIRONMENT`（既定 `development`）
- **LLM 観測は Langfuse に一本化している**（自前実装の DB テーブル `run_traces` と `measured_node` / `measured_ainvoke` は廃止）。ノードのレイテンシもトークン数も Langfuse 側にしか無いので、集計・eval のデータ源は Langfuse API を使う
- ノードが LLM を複数回呼ぶ場合（`generate_note` は3回、`update_note_and_feedback` は4回、`learning_dialogue` は dialogue intent 時のみ turn_analysis 分を含め2回）だけ `config={"run_name": "..."}` で呼び出しを識別する（`generate-note-content` / `estimate-category` / `analyze-dialogue` / `turn-analysis` など）。1ノード1呼び出しの対話ノードには付けない（ノードスパン名と二重になる）

### フロントエンドのパターン

- `use-chat-websocket.ts`: 接続ライフサイクル・メッセージ型振り分けを一元管理
- `fetchAPI()`: 全 REST 呼び出しはここを経由（JWT ヘッダー付与、エラーハンドリング）
- `NavbarSlotContext`: レイアウト内でナビバーに動的コンテンツを挿入するポータルパターン
- チャットのメッセージ本文は `Markdown` の `variant="chat"`（`remark-breaks` で単一改行を保持・`rehype-highlight` でコードをハイライト）で描画。ストリーミング中は `closeOpenCodeFence()` で未閉じフェンスを補ってから渡す（`notes`/`review` の `default`/`article` variant とは別系統）
- コピーは各メッセージ単位（`MessageCopyButton` が `msg.content` 全文をコピー）。未フェンスの貼り付けコードでも全文コピーできるよう、コードブロック単位ではなくメッセージ単位にしている

---

## テスト

| 種別 | 場所 | フレームワーク | カバレッジ目標 |
|------|------|--------------|--------------|
| バックエンド unit | `server/tests/unit/` | pytest | 75% |
| バックエンド integration | `server/tests/integration/` | pytest | - |
| フロントエンド | `client/__tests__/` | Vitest | - |

- `asyncio_mode = "auto"` のため `@pytest.mark.asyncio` 不要
- DB を使うテストは実 PostgreSQL に接続（モック禁止）
- テスト用 DB: `make test-db`

---

## CI（GitHub Actions）

PR マージ前に全通過が必須:

- `server-lint`: ruff check / format
- `server-typecheck`: mypy（strict）
- `server-test`: pytest（実 DB）
- `client-lint`: eslint + `tsc --noEmit`
- `client-test`: vitest
- `secret-scan`: Gitleaks

---

## コード規約

### コメント（言語共通）
- **不要なコメントを書かない**。不要なコメント = コードを読めば分かるもの（処理・シグネチャ・ノード名の言い換え）。
- コメント・docstring に書いてよいのは「**なぜ**そうするか」「**制約・前提**」「コードから読み取れない**非自明な意図**」だけ。
- 例: `# learning パス`（ノード名で自明）や「LLM を呼んで応答を返す」（シグネチャの言い換え）は削除対象。
  一方「終了は外部の `_handle_end_session` が制御するため常に False」（理由）や「値はプロンプト本文と一致させる」（制約）は残す。
- 判断に迷ったら書かない。コメントで補うより、命名と関数分割でコード自体を読めるようにする。

### Python（Ruff + mypy strict）
- 行長: 119 文字、Python 3.13 ターゲット
- ルール: E, W, F, I, B, UP
- `pydantic.mypy` プラグイン使用

### TypeScript
- ESLint + Prettier（`.ts`/`.tsx` はコミット時に自動フォーマット）
- strict モード

### pre-commit フック（`uv run pre-commit install` で有効化）
- ruff check + format（server/）
- mypy（server/）
- prettier（client/ の .ts/.tsx）

---

## 注意事項（ハマりポイント）

> **このセクションの育て方**: 実装中に、コードを読むだけでは分からない制約・ライブラリの癖・型の落とし穴（例: 下記の asyncpg Pool/Connection 型不一致）に直面し、それを考慮して実装・修正したときは、その教訓をここへ追記することを提案する。判断基準は「コードから読み取れることは書かない。『なぜ』『制約』だけ書く」。これにより、以降の実装が同じ問題を最初から考慮できるようにする。

- **マイグレーション順序**: `alembic upgrade head` の前に `client/better-auth_migrations/*.sql` を適用すること（外部キー制約あり）
- **BetterAuth スキーマは静的SQLで `auth.ts` と自動同期しない**: `client/better-auth_migrations/*.sql` は生成時点のスナップショット。`client/lib/auth.ts` のプラグイン（例: `jwt()` は `jwks` テーブルを要求）を追加・変更したら `npx @better-auth/cli generate --config lib/auth.ts` で再生成してコミットすること。漏れると新環境で `relation "jwks"/"user" does not exist` になる（過去に `jwks` 欠落で認証が落ちた）
- **スタック状セッション**: サーバー起動時に `reset_stuck_generations()` が自動実行される（`main.py` の `lifespan` 参照）
- **LangGraph 永続化**: チェックポイントは DB に保存されるため、ローカル開発中にスキーマ変更するとチェックポイントとの不整合が起きる場合がある
- **DB テーブル**: `notes`, `dialogue_sessions`, `dialogue_messages`, `feedbacks`, `review_schedules` が主要テーブル。BetterAuth テーブル（`user`, `account`, `session` 等）も同一 DB に存在し、外部キー制約によるカスケード削除あり
- **CORS**: `CORS_ORIGINS` 環境変数でカンマ区切りで複数指定可能（デフォルト `http://localhost:3000`）
- **ストリーミング対象ノード内の内部 LLM 呼び出しには `INTERNAL_LLM_TAG` を付ける**: WebSocket の `_stream_ai_response` は `stream_mode="messages"` を「ノード名が `_STREAMING_NODES` に含まれるか」だけでフィルタするため、対象ノード（例: `learning_dialogue`）の中で行う structured output 等の追加 LLM 呼び出しの出力（生 JSON）もそのままクライアントへ流れてしまう。内部呼び出しの runnable に `.with_config(tags=[INTERNAL_LLM_TAG])`（`graph/llm.py`）を付与すること。chat.py 側がこのタグ付きチャンクを除外する
- **「今日」の暦日判定はユーザーTZで行う**: 復習スケジュールの時刻列は `TIMESTAMPTZ`（UTC 保持）。「今日復習を完了した件数」のような暦日集計を `last_reviewed_at::date = CURRENT_DATE` でやるとサーバーの稼働 TZ 次第で日付境界がずれる。`(last_reviewed_at AT TIME ZONE $tz)::date = (NOW() AT TIME ZONE $tz)::date` のようにユーザーTZ（`REVIEW_TIMEZONE`、既定 `Asia/Tokyo`）へ変換してから比較する。なお「期限到来済みか」の判定（`next_review_at <= NOW()`）は瞬間の前後比較なので TZ 非依存で問題ない。暦日に丸める集計だけが TZ 依存。
- **復習完了はダッシュボードに残さず消す**: ダッシュボード（`GET /api/review-schedules`）は `next_review_at <= NOW()` かつ `status IN ('pending','overdue')` の未到来分だけを返す。実際の復習完了（review セッションの `update_note_and_feedback` → `_advance_review_schedule`）で `next_review_at` が将来へ進むと自動的に一覧から消える。フロントで「開いた＝復習済み」のような疑似状態を持って表示を残さない（次回到来まで非表示が正）。当日の進捗バーに必要な「当日完了件数」は一覧から消えるため `completed_today` として別途集計して返している
