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
- モード：保存済み出力の採点（scoring）と、`input` からの再実行採点（regression）の両方。
  regression が本体（プロンプト修正・モデル変更の前後比較ができないと改善ループが回らない。
  scoring だけでは過去の失敗のラベル付けしかできず、修正しても数字が変わらない）。
- 対象外：regular データセット（judge 検証通過後に着手）。Langfuse への score 書き戻し（同上）。コードの過剰分割。

---

## 2. Langfuse と自前の切り分け

原則：**Langfuse を eval の engine にしない。store と viewer として使う。**
判定ロジック（何を良しとするかの定義）は自前、判定結果の保管と観測は Langfuse。

| 機能 | 判断 | 理由 |
|------|------|------|
| Observability | 使う | 既に一本化済み。trace / session が error analysis の一次データ源であり、taxonomy を saturation させる作業は UI が最速 |
| Prompt Management | 使わない | プロンプトは条件分岐を含むコード（`graph/prompts/*.py`）。テンプレート化すると分岐はコードに残りテキストだけが外に出るため、真実の源が二重化して本番と eval の経路が割れる（§6 の「プロンプトを複製しない」と衝突）。git が version 管理・diff・レビュー・ロールバックを既に提供している |
| マネージド evaluator（LLM-as-judge） | 使わない | 「1 item → 1 evaluator → 1 score」のモデル。1 レコードに複数 criterion をぶら下げ `polarity` で集約する本 eval の assertion 構造が載らない |
| Datasets / Annotation Queue | 使わない | golden は YAML + git。**eval の基準が git 履歴と PR レビューを通らずに変わることが最悪の失敗モード**。`rationale` / `exemplar` / assertion 別 `human_verdict` は dataset item の表現力を超える |
| Score API | 後で使う | `report/` の数字を trace に紐付けて時系列比較する用途。ファイル出力だけでは prompt_version / model 間の推移が追えない |

judge–人間一致の突き合わせ（§3-6）は Langfuse に対応機能が無いため自前計算しかない。ここが自前実装の中核。

**Score API の着手時期**：最小構成には含めない。Section E の合格条件は「走って意味のある数字が出る」ことであり、judge が校正されていない段階の数字に履歴比較の価値はない。judge–人間一致が使える水準（20–30 件）に達してから `report/` → Score API の薄いアダプタを足す。

---

## 3. 機能要件（実装すべきもの）

1. golden ファイル（YAML）の読み込み。各ファイルは 1 つの `failure_mode` につき、型付き `assertions`（`type: deterministic | judge`、`criterion`、`polarity: must | must_not`）を 1 回だけ定義し、1 件以上の証拠 `instances`（`input` ＋ `observed_output` ＋ あなたの人間ラベル：インスタンス全体の `pass` と assertion 別 `human_verdicts`）を持つ。
2. 評価対象の出力を用意：2 モードとも実装する。
   - scoring モード：保存済み `observed_output` を採点（judge–人間一致の校正に使う）。
   - regression モード：`input` から `generate_question` を再実行して採点。temperature 0.7 で
     出力が揺れるため、1 レコードにつき N 回（既定 3〜5）生成し assertion 別 pass 率で見る。
3. assertion を `type` で振り分け：`deterministic` → コード関数、`judge` → LLM 呼び出し。
4. judge：1 criterion・二値・`{verdict, reason}` を返す。クロスファミリのモデル。
5. レコード単位で集約：`must` が満たされ `must_not` が現れていなければ pass。
6. **judge 検証：judge 判定を人間ラベルと突き合わせ、一致（混同行列 or 一致率）を出す。** ← 心臓部。
   `human_verdict` は保存済み `observed_output` へのラベルなので、この突き合わせは
   scoring モードでのみ計算する（regression の再生成出力に人間ラベルは存在しない）。
7. レポート出力：レコード別／assertion 別判定、失敗モード別 pass 率、judge–人間一致を `report/` に書く。

---

## 4. Section A — 構造チェック（Claude Code がコード読解で確認可）

- [ ] golden YAML を読み込む load 関数がある
- [ ] scoring / regression をコマンドライン引数等で切り替えられる
- [ ] assertion を `type` で deterministic / judge に振り分けるディスパッチがある
- [ ] judge は 1 criterion・二値・`{verdict, reason}` を返す（曖昧スコアを出すコードになっていない）
- [ ] `polarity`（must / must_not）が集約ロジックに反映されている
- [ ] **judge 判定を人間ラベルと突き合わせる比較ロジックがある**
- [ ] `report/` に結果を書き出す関数がある
- [ ] コードが 1 ファイルに収まっている（不要な分割をしていない）

---

## 5. Section B — 挙動チェック（実際に走らせて確認）

- [ ] `python eval.py` が golden に対しエラー無く完走する（scoring モード）
- [ ] regression モードが完走し、レコード×assertion 別に N 回生成の pass 率が出る
- [ ] report に per-record 判定が出る
- [ ] report に per-assertion 判定が出る
- [ ] report に失敗モード別 pass 率が出る
- [ ] **report に judge–人間 一致（混同行列 or 一致率）の実数が出る**
- [ ] 決定的チェックは再実行で同じ結果になる（判定が安定）
- [ ] エラーになったレコードは握りつぶされず report に出る

---

## 6. Section C — 品質 / アンチパターン回避

- [ ] judge が「4.2 / 5」のような曖昧スコアを出していない（pass / fail のみ）
- [ ] judge 1 呼び出し = 1 criterion（複数基準を一度に採点していない）
- [ ] report に `model` / `prompt_version` が記録されている（再現性）
- [ ] judge がクロスファミリ（システムが GPT なら judge は別系統のモデル）
- [ ] golden レコードに型付き assertion がある（薄い `input/output/pass` だけになっていない）
- [ ] regression モードは本番のプロンプト構築コード（`build_question_prompt` /
      `analyze_dialogue_turn` 等）を import して通す。eval 側にプロンプトを複製すると
      本番との乖離が測れなくなる

---

## 7. Section D — 現段階では「未達で当然」（2 件では検証不能）

> ここは「機構が走ること」だけ確認し、「信頼できること」は件数が揃うまで保留。緑にしない。

- [ ] judge が信頼できる（一致率が十分高い）→ **20–30 件の golden が必要**。今は「一致率の計算が走る」ことのみ確認。
- [ ] 失敗モード率が統計的に意味を持つ → 件数不足。今は「率が算出される」ことのみ確認。
- [ ] taxonomy が網羅的 → error analysis を ~100 trace で saturation させた後。

---

## 8. Section E — 受け入れ基準（executable acceptance / 最終判定）

最小構成として「実装できた」と言える条件：

1. `python eval.py datasets/golden/` が完走し、`report/` に成果物が出力される。
2. その report に次が含まれる：(a) レコード別判定、(b) assertion 別判定、(c) 失敗モード別 pass 率、(d) judge–人間一致の実数。
3. 上記 (d) が stub でなく、**あなたの人間ラベルから実際に計算されている**。
4. 決定的 assertion が 1 つでも存在するなら、それがコードで判定されている。
5. regression モードが完走し、レコード×assertion 別の pass 率（N 回生成）が report に出る。
   ＝プロンプト修正の前後で同じコマンドを叩けば数字で比較できる状態になっている。

> Section A が全緑でも、Section E が満たされなければ「実装できた」ではない。
> 構造の存在ではなく、**走って意味のある数字が出ること**が合格条件。