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
4. judge：1 criterion・二値・`{reason, holds}` を返す。クロスファミリのモデル。
5. レコード単位で集約：`must` が満たされ `must_not` が現れていなければ pass。
6. **judge 検証：judge 判定を人間ラベルと突き合わせ、一致（混同行列 or 一致率）を出す。** ← 心臓部。
   `human_verdict` は保存済み `observed_output` へのラベルなので、この突き合わせは
   scoring モードでのみ計算する（regression の再生成出力に人間ラベルは存在しない）。
7. レポート出力：レコード別／assertion 別判定、失敗モード別 pass 率、judge–人間一致を `report/` に書く。

### golden 側の規約

- **judge assertion は pass する instance と fail する instance を各 1 件以上持つ。** 満たせないうちは
  新しい judge assertion を追加しない。fail 側は synthetic でよい（`source: synthetic` を明示する）。
  片方向しか無い assertion は「judge がその向きを検出できるか」を一度も検証していない状態で、
  縮退した judge（常に `holds=true` を返すだけ）でも一致率が稼げてしまう。実測では、負例 2 件だけの
  時点で「常に true」の一致率が 6/9 = 67%、実際の judge は 80〜90% で、差は 1〜2 ラベルしかなかった。
  deterministic assertion は check 関数のユニットテストが両方向を担保するのでこの規則の対象外。
  強制は `tests/unit/evals/test_golden_assertion_coverage.py`。
- **assertion に適用前提があるなら `applies_when` に外出しし、条件を `criterion` に埋めない。**
  適用外の instance は `human_verdicts` に `na` を書く。条件を criterion に埋めると、前提を満たさない
  instance で「記述が当てはまらない」→ `must_not` が pass になり、適用外が合格として TN に計上される
  （FP/FN として現れないので混同行列を見ても異常が見えない）。`applies_when` が input だけの関数なら
  judge に聞かず静的に解決する（regression で N 回再生成しても適用可否は変わらないため）。
- **短絡すると答えが反転する独立条件を、1 criterion に並べない。** judge は先に満たした側だけで
  `holds` を決めて打ち切ることがある（`a1` の複合条件で実測）。判定の基準は連言の有無ではなく、
  **一部だけ読んで正しい答えに達するか**。OR や、主文が偽になる現れ方を言い換えただけの但し書きは
  短絡しても答えが変わらないので許容する。
- **但し書きを消して 1 文に畳むのは改善ではない。** 但し書きは主文の範囲を狭めており、消すと
  主文が広がってより多くを巻き込む。`a2` を「正しかった部分について AI がさらに説明を続けている」の
  1 文にしたところ、judge は「続けている」を**話を進める行為全般**と読み、質問（「さらに深い理解へ
  導く質問を提示している」）も訂正（「より正確な説明を続けている」）も該当と判定した。`a1` では
  主語が曖昧になり、Sonnet が「AI 自身が答えるべき質問ではないので判定対象が存在しない」と結論した。
  実測は Haiku 18/20・Sonnet 19→17/20・Opus 20/20 で、1 文版は明確に悪化した。
  守るべきは文の数ではなく、**主文だけを読んで正しい答えに達する形になっているか**。
- **criterion を精密にして judge が pass に転じたら、まず守備範囲の重複を疑う。**
  `a1` を「焦点の単一性」と「質問の具体性」に割った際、後者を精密にするほど judge は pass を返し、
  人間ラベルの fail と食い違った。調べると、その応答の欠陥（既出内容の再説明要求）は `a3` が既に
  拾っており、曖昧な criterion が `a3` の担当分を吸い込んで**二重計上**していただけだった
  （後者は削除し `a1` に戻した）。**ラベルに合わせて文面を調整する前に、その欠陥を別の assertion が
  既に検出していないか確認する。** n=1 のラベルに文面を寄せ続けるのは criterion の過剰適合で、
  一致率は上がるが検出しているものは増えない。
- **criterion は複数の judge モデルで同じ判定になって初めて「書けている」と言える。**
  モデル間で判定が割れたら、能力差ではなく **criterion の曖昧さ**を疑う。実測では `a1` の
  「回答可能になっている」の閾値（完全性か中核か）が書かれておらず、Haiku=fail / Sonnet=pass /
  Opus=fail と**非単調に**割れた。能力差なら最小のモデルが落ちるはずで、小と大が一致して
  中だけ外れるのは解釈が分かれている証拠。逆に全モデルが一致するなら、それは criterion どおりの
  判定であり、直すべきは criterion の側（`a2` で実測）。切り替えは `--judge-model`。
- **assertion に instance 固有の事実を書かない。** criterion は failure_mode 全体の契約なので、
  特定の trace にしか当てはまらない固有名詞や誤りの中身を埋めると、2 件目の instance を足した
  瞬間に使えなくなる。instance 固有の事実は `rationale` に置く。
  `a4` は「（「OSから独立したメモリ空間」——正しくは…）」と誤りの正解を criterion に埋めていたが、
  外しても judge は自力で不正確な箇所を特定できた（**judge に答えを渡す必要は無かった**）。
- **`input` / `observed_output` / `meta` / `source` は正本 jsonl からの写しで、手で書かない。**
  `evals.golden_yaml.dump_copy_block` で生成する。`tests/unit/evals/test_golden_copy_matches_source.py`
  がバイト一致を保証し、落ちたら写しを再生成する一択。

---

## 4. Section A — 構造チェック（Claude Code がコード読解で確認可）

- [x] golden YAML を読み込む load 関数がある
- [x] scoring / regression をコマンドライン引数等で切り替えられる
- [x] assertion を `type` で deterministic / judge に振り分けるディスパッチがある
- [x] judge は 1 criterion・二値・`{reason, holds}` を返す（曖昧スコアを出すコードになっていない）
- [x] `polarity`（must / must_not）が集約ロジックに反映されている
- [x] **judge 判定を人間ラベルと突き合わせる比較ロジックがある**
- [x] `report/` に結果を書き出す関数がある
- [x] コードが 1 ファイルに収まっている（不要な分割をしていない）

---

## 5. Section B — 挙動チェック（実際に走らせて確認）

- [x] `python eval.py` が golden に対しエラー無く完走する（scoring モード）
- [x] regression モードが完走し、レコード×assertion 別に N 回生成の pass 率が出る
- [x] report に per-record 判定が出る
- [x] report に per-assertion 判定が出る
- [x] report に失敗モード別 pass 率が出る
- [x] **report に judge–人間 一致（混同行列 or 一致率）の実数が出る**
- [x] 決定的チェックは再実行で同じ結果になる（判定が安定）
- [x] エラーになったレコードは握りつぶされず report に出る

---

## 6. Section C — 品質 / アンチパターン回避

- [x] judge が「4.2 / 5」のような曖昧スコアを出していない（pass / fail のみ）
- [x] judge 1 呼び出し = 1 criterion（複数基準を一度に採点していない）
- [x] report に `model` / `prompt_version` が記録されている（再現性）
- [x] judge がクロスファミリ（システムが GPT なら judge は別系統のモデル）
- [x] golden レコードに型付き assertion がある（薄い `input/output/pass` だけになっていない）
- [x] regression モードは本番のプロンプト構築コード（`build_question_prompt` /
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

---

## 9. 決着 — judge は Haiku→Opus の 2 段カスケード（2026-09-05）

**採用: screen（既定 Haiku 4.5）で全件判定し、screen が fail と言った judge assertion だけ
confirm（既定 Opus 5）に回す。** `--judge-model` が screen、`--confirm-judge-model` が confirm、
`--no-cascade` で従来の単一 judge に戻せる。

### 根拠（実測）

Haiku の誤りは全て FP（FN=0、TNR=85%）、Opus は FP=0（TNR=100%）。つまり Haiku が pass と
言ったものは信用でき、fail と言ったものだけ疑わしい。この非対称性がカスケードを成立させる。
`a2` の FP はいずれも「訂正のための記述」を「言い直し・補強」と読む誤りで、4 通りの文面
（下表）で再現するため文面調整では直らない（Haiku の弁別能力の限界）。

| criterion の形 | Haiku 4.5 | Sonnet 5 | Opus 5 |
|---|---|---|---|
| 現行（但し書きあり） | 18/20 | 19/20 | 20/20 |
| 1 文に畳んだ版 | 18/20 | 17/20 | 20/20 |
| 定義または具体例を新たに提示している | FP=2 | — | — |
| 正しく述べた内容を言い直し・補強して解説している | FP=2 | — | — |
| 正しかった部分についてさらに説明を続けている | FP=2 | — | 20/20 |

### 合格条件（総合一致率から方向別へ変更）

総合一致率だけでは「良いものを fail と言う」偏りが 90% の下に隠れる。`calibration_gate()` が
`TPR ≥ 90% かつ TNR ≥ 90%` に加えて **正例レコードが judge 集約で全件 pass** を要求する
（`stage="final"` のときのみ）。`--strict` を付けると scoring モードで final ゲート不合格時に
exit code 1 になる。

### 限界（カスケードが救わないもの）

**screen の FN（欠陥を pass と言う誤り）は confirm に届かない。** confirm はエスカレーション
条件（`should_escalate`: polarity 適用後の verdict が fail）を満たしたときだけ動くため、screen が
pass と誤判定した場合はそのまま最終判定になる。最終判定の TPR ≈ screen の TPR、TNR ≈ confirm の
TNR。scoring の校正ゲートは `stage="screen"` の TPR も出すので、そこが閾値を割ったら
「カスケードでは救えない」旨が failures に出る。

### 決めた際に確認した点

- **判定器を明示しない一致率は意味を持たない。** 同じ golden・同じ criterion でも、judge モデルを
  変えると一致率が変わる（`--judge-model` / `--confirm-judge-model` で切り替え可能）。report の
  `meta.judge`（screen/confirm）に必ず併記する
- `a2` の criterion 自体は変更していない（文面調整では直らないことを確認済みのため）
- judge は temperature 0 でも判定が揺れる（同一入力で `a2` が fail/fail/pass/pass と反転した実測あり）。
  **1〜2 ラベルの差を読まない**
