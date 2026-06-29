# 最小構成 Eval 実装 — 要件定義 & 受け入れチェックリスト

`generate_question` の振る舞いを評価する最小構成 eval の definition-of-done。

---

## 0. このドキュメントの使い方（最初に読む）

- これは「最小構成の eval が実装できているか」の判定基準。
- **重要な前提：チェックが全部緑でも「eval が正しく振る舞いを測れている」ことは保証しない。**
  構造（ファイル・関数が存在する）と挙動（実際に動いて正しい数字を出す）は別物。
  - **Section A（構造）** = Claude Code がコード読解で確認できる。
  - **Section B/C（挙動・品質）** = 実際に `python eval.py` を走らせて確認する。Claude Code の読解だけで緑にしない。
- 2 件しか golden が無い現段階では検証できない項目がある。**Section D** に隔離し、false-green を防ぐ。
- 最終判定は **Section E（executable acceptance）**。ここが満たされて初めて「最小構成が実装できた」と言える。

---

## 1. スコープ

- 対象：`generate_question` の質問振る舞いの評価。
- 構成：`eval.py`（1 ファイル）＋ `datasets/golden/*.yaml` ＋ `report/`。
- 対象外：regular データセット（judge 検証通過後に着手）。コードの過剰分割。

---

## 2. 機能要件（実装すべきもの）

1. golden レコード（YAML）の読み込み。各レコードは `input` ＋ 型付き `assertions`（`type: deterministic | judge`、`criterion`、`polarity: must | must_not`）＋ あなたの人間ラベル（`pass` と assertion 別判定）を持つ。
2. 評価対象の出力を用意：保存済み `observed_output` を使う（最小）／ `input` から `generate_question` を再実行する（回帰モード、+α）。
3. assertion を `type` で振り分け：`deterministic` → コード関数、`judge` → LLM 呼び出し。
4. judge：1 criterion・二値・`{verdict, reason}` を返す。クロスファミリのモデル。
5. レコード単位で集約：`must` が満たされ `must_not` が現れていなければ pass。
6. **judge 検証：judge 判定を人間ラベルと突き合わせ、一致（混同行列 or 一致率）を出す。** ← 心臓部。
7. レポート出力：レコード別／assertion 別判定、失敗モード別 pass 率、judge–人間一致を `report/` に書く。

---

## 3. Section A — 構造チェック（Claude Code がコード読解で確認可）

- [ ] golden YAML を読み込む load 関数がある
- [ ] assertion を `type` で deterministic / judge に振り分けるディスパッチがある
- [ ] judge は 1 criterion・二値・`{verdict, reason}` を返す（曖昧スコアを出すコードになっていない）
- [ ] `polarity`（must / must_not）が集約ロジックに反映されている
- [ ] **judge 判定を人間ラベルと突き合わせる比較ロジックがある**
- [ ] `report/` に結果を書き出す関数がある
- [ ] コードが 1 ファイルに収まっている（不要な分割をしていない）

---

## 4. Section B — 挙動チェック（実際に走らせて確認）

- [ ] `python eval.py` が golden に対しエラー無く完走する
- [ ] report に per-record 判定が出る
- [ ] report に per-assertion 判定が出る
- [ ] report に失敗モード別 pass 率が出る
- [ ] **report に judge–人間 一致（混同行列 or 一致率）の実数が出る**
- [ ] 決定的チェックは再実行で同じ結果になる（判定が安定）
- [ ] エラーになったレコードは握りつぶされず report に出る

---

## 5. Section C — 品質 / アンチパターン回避

- [ ] judge が「4.2 / 5」のような曖昧スコアを出していない（pass / fail のみ）
- [ ] judge 1 呼び出し = 1 criterion（複数基準を一度に採点していない）
- [ ] report に `model` / `prompt_version` が記録されている（再現性）
- [ ] judge がクロスファミリ（システムが GPT なら judge は別系統のモデル）
- [ ] golden レコードに型付き assertion がある（薄い `input/output/pass` だけになっていない）

---

## 6. Section D — 現段階では「未達で当然」（2 件では検証不能）

> ここは「機構が走ること」だけ確認し、「信頼できること」は件数が揃うまで保留。緑にしない。

- [ ] judge が信頼できる（一致率が十分高い）→ **20–30 件の golden が必要**。今は「一致率の計算が走る」ことのみ確認。
- [ ] 失敗モード率が統計的に意味を持つ → 件数不足。今は「率が算出される」ことのみ確認。
- [ ] taxonomy が網羅的 → error analysis を ~100 trace で saturation させた後。

---

## 7. Section E — 受け入れ基準（executable acceptance / 最終判定）

最小構成として「実装できた」と言える条件：

1. `python eval.py datasets/golden/` が完走し、`report/` に成果物が出力される。
2. その report に次が含まれる：(a) レコード別判定、(b) assertion 別判定、(c) 失敗モード別 pass 率、(d) judge–人間一致の実数。
3. 上記 (d) が stub でなく、**あなたの人間ラベルから実際に計算されている**。
4. 決定的 assertion が 1 つでも存在するなら、それがコードで判定されている。

> Section A が全緑でも、Section E が満たされなければ「実装できた」ではない。
> 構造の存在ではなく、**走って意味のある数字が出ること**が合格条件。