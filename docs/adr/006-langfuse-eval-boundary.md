# ADR-006: Langfuse は eval の store / viewer に限定し、判定ロジックは自前に持つ

## Status

Accepted（2026-09-14 時点の運用を記録。決定自体は 2026-08 の eval 設計時）

## Context

`generate_question` の振る舞いを評価する eval（`server/evals/`）を作るにあたり、既に LLM 観測を
一本化している Langfuse の機能（Prompt Management / マネージド evaluator / Datasets・Annotation Queue /
Score API）をどこまで使うかを決める必要があった。

eval の判定は「1 レコードに複数の型付き assertion（`deterministic | judge`）を用い、
`polarity`（`must | must_not`）で集約する」構造で、assertion ごとに人間ラベル `human_verdicts` と
`rationale` / `exemplar` を持つ。judge の信頼性は、この人間ラベルとの一致（混同行列・方向別 TPR/TNR）で測る。

## Decision

**Langfuse を eval の engine にしない。store と viewer として使う。**
何を良しとするかの定義（golden・criterion・集約）は自前のコードと YAML に置き、
判定結果の保管と観測だけを Langfuse に委ねる。

| 機能 | 判断 |
|------|------|
| Observability（trace / session） | 使う |
| Prompt Management | 使わない |
| マネージド evaluator（LLM-as-judge） | 使わない |
| Datasets / Annotation Queue | 使わない |
| Score API | 後で使う（judge 校正後に `report/` → Score API の薄いアダプタを足す） |

## Reasons

- **Observability**: 既に一本化済み。trace / session が error analysis の一次データ源であり、taxonomy を
  saturation させる作業は UI が最速
- **Prompt Management を使わない**: プロンプトは条件分岐を含むコード（`graph/prompts/*.py`）。
  テンプレート化すると分岐はコードに残りテキストだけが外に出るため、本番と eval の経路が割れる。regression モードは本番のプロンプト構築コードを import して通す方針（eval 側にプロンプトを複製しない）と衝突する。git が version 管理・diff・レビュー・ロールバックを既に提供している
- **マネージド evaluator を使わない**: 「1 item → 1 evaluator → 1 score」のモデルで、1 レコードに複数
  criterion をぶら下げ `polarity` で集約する assertion 構造が載らない
- **Datasets / Annotation Queue を使わない**: golden は YAML + git。**eval の基準が git 履歴と
  PR レビューを通らずに変わることが最悪の失敗モード**。`rationale` / `exemplar` / assertion 別
  `human_verdicts` は dataset item の表現力を超える
- **Score API は後で**: `report/` の数字を trace に紐付けて時系列比較する用途だが、judge が校正されて
  いない段階の数字に履歴比較の価値はない。judge–人間一致が使える水準（golden 20〜30 件）に達してから
- judge–人間一致の突き合わせは Langfuse に対応機能が無いため自前計算しかない。ここが自前実装の中核

## Consequences

- 判定ロジックの変更は必ずコードか golden YAML の diff として PR に現れる
- Langfuse 側で使う機能は trace の閲覧と（将来の）score の保管に限られ、Langfuse の UI 上で eval の基準を編集する経路は存在しない
- golden の規約と judge の決定は `server/evals/README.md` に置く。Langfuse の Hobby プランは 30 日でデータアクセスが切れるため、eval のデータは正本 jsonl（`evals/datasets/`）に capture で残す
