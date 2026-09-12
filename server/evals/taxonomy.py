"""失敗モードの正本。

`failure_mode`（golden のファイル名とフィールド）と `first_failure`（jsonl の annotation）は
どちらも自由文字列で、表記ゆれが入ると集計が静かに割れる。ここを唯一の値空間にして
`tests/unit/evals/test_dataset_invariants.py` が強制する。

網羅的な taxonomy を今作らないのは意図的（`todo.md` Section D: error analysis が ~100 trace で
saturation してから）。ここは「今ある値を固定し、追加を PR レビューに通す」ためだけにある。
"""

from __future__ import annotations

FAILURE_MODES: dict[str, str] = {
    "accurate_multi_concept_overexplain": "誤りのない複数観点の列挙に対し、AI が全観点へ解説を被せる",
    "self_answered_question": "AI が自分の質問の答えを同じ応答内で先に述べてしまう",
}

# jsonl レコードの `source`。real = 本番 LLM の実出力、rerun = eval の regression 再実行、
# handwritten = 人が書いた応答（正例の理想応答など）
SOURCES: frozenset[str] = frozenset({"real", "rerun", "handwritten"})
