# Calibration（judge の人手較正）

LLM-as-judge の判定が人間判断とどれくらい一致するかを測る較正タスク。
スコアの「上昇」が真の改善か、それとも judge が甘くなっただけかを切り分けるために使う。

## いつ実行するか

- judge プロンプト（`golden/judge.py::_SYSTEM_PROMPT`）を書き換えた時
- judge モデルを変えた時（`EVALS_JUDGE_PROVIDER` / `EVALS_JUDGE_MODEL`）
- rubric の criterion 文（`rubrics/*.yaml`）を書き換えた時

CI には乗せない（人手ラベルの更新頻度に合わない）。手動較正タスク。

## ファイル構成

```
calibration/
├── schema.py          # HumanLabel Pydantic モデル
├── loader.py          # human_labels/*.jsonl ロード
├── kappa.py           # Cohen's kappa（二値）の純算術実装
├── agreement.py       # CLI 本体（judge 実行 + 集計）
└── human_labels/      # 人手ラベル JSONL（rubric ごとに 1 ファイル）
    ├── note_quality.jsonl       ← 自分で作成（後述）
    └── question_quality.jsonl   ← 自分で作成
```

## ラベル付与の手順

1. `evals/datasets/note_generation.jsonl` から代表 25 件を選ぶ（カテゴリが偏らないように）。
2. 各 case について現行プロンプトでノートを 1 回生成して `output` として固定する。
   judge を回し直すたびに generation を再実行すると非決定性で出力が変わってしまい、
   ラベルとの対応が取れなくなるため、**この `output` を必ず固定**する。
3. 4 つの criterion それぞれについて、人間が holds=true/false を判定。
   1 case あたり 4 行（criterion ごとに 1 行）が生成される（計 100 行）。
4. `human_labels/note_quality.jsonl` に 1 行 1 ラベルで書く。

### スキーマ

```jsonl
{"case_id":"ng-001","criterion_id":"protege_alignment","human_holds":true,"output":"...ノート本文...","context":"## 対話履歴\n...","annotator":"ryoma","annotated_at":"2026-05-28","notes":"任意の補足"}
```

- `case_id`: dataset 側の id を踏襲（必須ではないが追跡用）
- `criterion_id`: `rubrics/note_quality.yaml` の criteria キー名（`explanatory_depth` / `protege_alignment` / `personalization` / `actionability`）
- `output` / `context`: judge を回す時にそのまま渡される。ラベル時点と完全一致させる
- `notes`: 判定で悩んだ理由を書いておくと後で再ラベリング時に役立つ

行頭が `//` の行はコメント扱いでスキップされる。

## 実行

```bash
cd server
uv run python -m evals.calibration.agreement --rubric note_quality
```

出力例:

```
criterion                          n  agreement    kappa   judge%   human%
--------------------------------------------------------------------------
explanatory_depth                 25      0.840    0.660    0.680    0.720
protege_alignment                 25      0.960    0.710    0.920    0.960
personalization                   25      0.760    0.480    0.640    0.720
actionability                     25      0.880    0.730    0.560    0.520
```

### CI で fail させる

`--fail-on-low-kappa` を付けると、いずれかの criterion で `kappa < 0.4` の場合に exit 1 する。
ただしこの CLI は CI に組み込まない前提。

## kappa の解釈

| kappa | 解釈 |
|-------|------|
| < 0.0  | judge と人間が偶然以下の一致（criterion が壊れている） |
| 0.0–0.2 | slight |
| 0.2–0.4 | fair（criterion の見直し推奨） |
| 0.4–0.6 | moderate（実用可だが甘い） |
| 0.6–0.8 | substantial（実用ライン） |
| 0.8–1.0 | almost perfect |

## kappa が低いとき

1. criterion 文（`rubrics/*.yaml`）が曖昧/多義的になっていないかを見直す。
2. 人手ラベル側の判定基準が一貫しているかを再点検（自分で再ラベリング）。
3. judge プロンプト（`golden/judge.py`）に追加ルールが必要か検討。
4. 上記で改善しない場合は judge モデルを変える（`EVALS_JUDGE_MODEL`）。

agreement が高くても kappa が低いケース（base rate skew）に注意:
人間 / judge とも 90% pass する criterion では、kappa が低くても実害は少ない。
逆に pass 率が拮抗（50% 前後）する criterion で kappa が低いと判定が当てにならない。
