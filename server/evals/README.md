# Eval Harness

プロンプト改善を数値ドリブンで検証するための評価フレームワーク。

---

## 構成

```
evals/
├── datasets/               # 評価用 JSONL（合成データ、PII なし）
│   ├── note_generation.jsonl      (30件)
│   ├── feedback_generation.jsonl  (20件)
│   ├── question_generation.jsonl  (23件)
│   └── response_analysis.jsonl    (20件)
├── graders/                # 採点ロジック
│   ├── base.py             # GraderResult dataclass
│   ├── note_has_sections.py
│   ├── note_quality_judge.py      # LLM-as-judge（単一 criterion・二値、judge_criterion を共用）
│   ├── question_quality_judge.py  # LLM-as-judge（同上）
│   ├── _criterion_aggregate.py    # rubric 読み込み + 並列 judge_criterion 集約
│   ├── feedback_is_actionable.py
│   ├── dialogue_ended_correctly.py
│   └── response_label_match.py
├── rubrics/
│   ├── note_quality.yaml      # note_quality_judge の criterion 定義
│   └── question_quality.yaml  # question_quality_judge の criterion 定義
├── baselines/              # git 管理対象（比較の基準値）
│   └── note_generation_baseline.json
├── reports/                # .gitignore 対象（実行ごとの出力）
├── runner.py               # eval 実行エンジン
├── compare.py              # 2つの report を比較して回帰検知
└── README.md               # このファイル
```

---

## Grader 一覧

| grader | 対象タスク | 検出内容 | 種別 |
|--------|----------|---------|------|
| `note_has_sections` | note_generation | 必須4セクション（概要/学んだこと/重要なポイント/まだ曖昧な点）の有無 | rule-based |
| `note_quality_judge` | note_generation | 深さ・忠実性・個別性・実用性を criterion ごとに二値判定 | LLM-as-judge |
| `question_quality_judge` | question_generation | 質問の観点重複回避・拡張/補強・受け止めなどを criterion ごとに二値判定 | LLM-as-judge |
| `feedback_is_actionable` | feedback_generation | improvement_points / strength が1件以上あるか | rule-based |
| `dialogue_ended_correctly` | response_analysis | 対話終了判定が正しく機能しているか | rule-based |
| `response_label_match` | response_analysis | LEARNING_END / CONTINUE ラベルの正解一致率 | rule-based |

### LLM-as-judge の判定モデル

各 rubric の criterion は `golden/judge.py::judge_criterion` を共用して 1 criterion = 1 回の judge 呼び出しで二値判定（holds: true/false）する。rubric YAML は `criteria` セクションに criterion 名と性質記述を列挙し、`pass_policy: all` で全 criterion が holds=true のときのみ `passed=True`、`score = passed_count / total` となる。

| rubric | criterion |
|--------|-----------|
| `note_quality.yaml` | `explanatory_depth` / `protege_alignment` / `personalization` / `actionability` |
| `question_quality.yaml` | `avoids_repeated_aspects` / `expands_or_reinforces` / `positive_acknowledgment` / `prompts_re_explanation` / `handles_unknown_appropriately` / `single_question` |

---

## 使い方

### Smoke 実行（先頭5件、LLM コスト小）

```bash
cd server
uv run python -m evals.runner --task note_generation --smoke
uv run python -m evals.runner --task note_generation --smoke --judge   # LLM-as-judge あり
```

### フル実行（全件 x 複数 trial）

```bash
cd server
uv run python -m evals.runner --task note_generation --trials 3 --judge
uv run python -m evals.runner --task feedback_generation --trials 3
uv run python -m evals.runner --task question_generation --trials 3
uv run python -m evals.runner --task response_analysis --trials 3
```

実行後、`evals/reports/<task>_<git_sha>_<timestamp>.json` に結果が保存される。

### Baseline との比較

```bash
cd server
uv run python -m evals.compare \
  --baseline evals/baselines/note_generation_baseline.json \
  --new evals/reports/note_generation_<sha>_<ts>.json

# CI 用（回帰時に exit code 1）
uv run python -m evals.compare \
  --baseline evals/baselines/note_generation_baseline.json \
  --new evals/reports/note_generation_<sha>_<ts>.json \
  --fail-on regressed
```

---

## プロンプト改善の A/B サイクル

```
1. graph/prompts/ 配下の該当モジュールを編集
2. smoke 実行でざっくり確認
   uv run python -m evals.runner --task note_generation --smoke --judge
3. フル実行
   uv run python -m evals.runner --task note_generation --trials 3 --judge
4. baseline と比較
   uv run python -m evals.compare --baseline ... --new ...
5. verdict 確認:
   - improved  -> 採用。PR に prompt-change ラベルを付けて CI 通過を確認
   - neutral   -> ケース別に判断。弱点ケースが改善していれば採用
   - regressed -> 変更を戻す
```

---

## Baseline 更新手順

プロンプト改善が main にマージされた後:

```bash
cd server

# 1. main ブランチで最新コードを使ってフル実行
uv run python -m evals.runner --task note_generation --trials 3 --judge

# 2. baseline を更新
cp evals/reports/note_generation_<sha>_<ts>.json \
   evals/baselines/note_generation_baseline.json

# 3. 別 PR でコミット（プロンプト変更と混ぜない）
git checkout -b chore/update-eval-baselines
git add evals/baselines/
git commit -m "chore: update note_generation eval baseline after prompt improvement"
```

**注意:** baseline 更新は必ず別 PR で行う。プロンプト変更と同一 PR に混ぜると、改善効果の確認ができなくなる。

---

## コスト目安

| 操作 | コスト目安 |
|------|-----------|
| smoke 実行（judge なし、5件） | ~$0.01 |
| smoke 実行（judge あり、5件） | ~$0.05 |
| フル実行（note_generation x 3 trials、judge あり） | ~$2.5 |
| フル実行（4タスク x 3 trials） | ~$7〜10 |
| CI `evals-regression` 1回 | ~$2.5 |

---

## CI 統合

### `evals-smoke`（高速確認）

PR に `prompt-change` ラベルが付いている場合に自動実行。先頭5件のみ。

### `evals-regression`（回帰検知）

`evals-smoke` 通過後に実行。`note_generation` をフル件数 x 3 trials で評価し、`baselines/note_generation_baseline.json` と比較。回帰検出時は CI fail（exit code 1）。

### `golden-gate`（リグレッションゲート）

`prompt-change` ラベル付き PR で実行。golden dataset を評価し、**P0 assertion が 1 件でも fail すると CI fail（exit code 1）**。baseline 比較ではなくハードゲート。

---

## Golden Dataset（assertion ベース評価）

JSONL タスクとは別系統の、**レコード固有の二値 assertion ＋ 普遍 invariant** で
`generate_question` の振る舞いを判定する仕組み。データとスキーマは
`datasets/golden/`（`_TEMPLATE.yaml` / `_invariants.yaml` 参照）。

### 仕組み

- **1 レコード 1 ファイル**（`<category>__<slug>__<NNN>.yaml`）。`id` はファイル名と一致。
- 各 assertion は `polarity`（must / must_not）× `type`（judge / deterministic）。
  - `deterministic`: `checks.py` のレジストリ（`ends_with_question_mark` /
    `contains_any_phrase` / `paraphrases_recent_question`）でコード検証。
  - `judge`: 汎用・単一 criterion・二値の LLM-as-judge（`judge.py`, gpt-4o）。
- `_invariants.yaml` の普遍ルールは全レコードに自動適用される。
- polarity 解釈: `must` は性質成立で pass / `must_not` は性質成立で fail。
- レコードは自身の全 assertion と全 invariant が pass したとき pass。

### 構成

```
evals/golden/
├── schema.py      # GoldenRecord / Assertion / Invariant (Pydantic)
├── loader.py      # YAML ロード・id 検証・status フィルタ
├── checks.py      # deterministic check レジストリ
├── judge.py       # 汎用 LLM-as-judge
├── adapter.py     # golden input -> generate_question 実行
├── evaluator.py   # polarity 適用・record/invariant 評価
├── aggregate.py   # category/priority 集計・P0 ゲート判定
└── runner.py      # 実行エンジン（CLI）
```

### 使い方

```bash
cd server
uv run python -m evals.golden.runner            # 全レコード評価（P0 fail で exit 1）
uv run python -m evals.golden.runner --smoke    # 先頭数件のみ
uv run python -m evals.golden.runner --no-save  # レポート JSON を書かない
```

実行後 `evals/reports/golden_<sha>_<ts>.json` に per-assertion 結果と集計が保存される。
