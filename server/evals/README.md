# Eval Harness

プロンプト改善を数値ドリブンで検証するための評価フレームワーク。

---

## 構成

```
evals/
├── datasets/               # 評価用 JSONL（合成データ、PII なし）
│   ├── note_generation.jsonl      (30件)
│   ├── feedback_generation.jsonl  (20件)
│   ├── question_generation.jsonl  (15件)
│   └── response_analysis.jsonl    (20件)
├── graders/                # 採点ロジック
│   ├── base.py             # GraderResult dataclass
│   ├── note_has_sections.py
│   ├── note_quality_judge.py      # LLM-as-judge (gpt-4o)
│   ├── feedback_is_actionable.py
│   ├── dialogue_ended_correctly.py
│   └── response_label_match.py
├── rubrics/
│   └── note_quality.yaml   # note_quality_judge の採点基準
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
| `note_quality_judge` | note_generation | 深さ・忠実性・個別性・実用性を4観点でスコアリング | LLM-as-judge |
| `feedback_is_actionable` | feedback_generation | improvement_points / strength が1件以上あるか | rule-based |
| `dialogue_ended_correctly` | response_analysis | 対話終了判定が正しく機能しているか | rule-based |
| `response_label_match` | response_analysis | LEARNING_END / CONTINUE ラベルの正解一致率 | rule-based |

### `note_quality_judge` の観点（各1〜5点、合計20点満点）

| 観点 | 説明 |
|------|------|
| `explanatory_depth` | ユーザーの理解がどれだけ深く記録されているか |
| `protege_alignment` | 実際の対話内容と一致しているか（ハルシネーション検出） |
| `personalization` | ユーザー固有の表現・誤解が反映されているか |
| `actionability` | 次回の学習につながる「曖昧な点」が具体的か |

合格閾値: 12点以上（score = 合計 / 20）

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
1. prompts.py を編集
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
