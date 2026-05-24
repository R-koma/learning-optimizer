"""Deterministic check レジストリ。

`type: deterministic` の assertion / invariant が参照する純粋関数群。
各 check は「記述された性質が出力について成立しているか」を bool で返す。
must / must_not の解釈は呼び出し側（評価器）が polarity に応じて行う。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

_QUESTION_MARKS = ("?", "？")


@dataclass(frozen=True)
class CheckContext:
    """check に渡す評価対象と文脈。"""

    output: str
    recent_system_questions: tuple[str, ...] = ()
    parameters: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CheckOutcome:
    """check の結果。holds=True は『性質が成立した』を意味する。"""

    holds: bool
    detail: str


def _require_phrases(parameters: Mapping[str, object]) -> list[str]:
    phrases = parameters.get("phrases")
    if not isinstance(phrases, Sequence) or isinstance(phrases, str | bytes):
        raise ValueError("contains_any_phrase requires a 'phrases' list parameter")
    return [str(p) for p in phrases]


def _char_bigrams(text: str) -> set[str]:
    """日本語向けに文字 bigram 集合を作る（形態素解析に依存しない近似）。"""
    compact = "".join(text.split())
    if len(compact) < 2:
        return {compact} if compact else set()
    return {compact[i : i + 2] for i in range(len(compact) - 1)}


def _jaccard(a: str, b: str) -> float:
    ga, gb = _char_bigrams(a), _char_bigrams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def ends_with_question_mark(ctx: CheckContext) -> CheckOutcome:
    holds = ctx.output.rstrip().endswith(_QUESTION_MARKS)
    return CheckOutcome(holds=holds, detail=f"ends_with_question_mark={holds}")


def contains_any_phrase(ctx: CheckContext) -> CheckOutcome:
    phrases = _require_phrases(ctx.parameters)
    matched = [p for p in phrases if p in ctx.output]
    return CheckOutcome(holds=bool(matched), detail=f"matched_phrases={matched}")


def paraphrases_recent_question(ctx: CheckContext) -> CheckOutcome:
    """出力が直近のシステム質問のいずれかと言い換え関係にあるか（Jaccard 近似）。"""
    threshold = float(ctx.parameters.get("threshold", 0.6))  # type: ignore[arg-type]
    scores = [(_jaccard(ctx.output, q), q) for q in ctx.recent_system_questions]
    best = max(scores, default=(0.0, ""))
    holds = best[0] >= threshold
    return CheckOutcome(holds=holds, detail=f"max_jaccard={best[0]:.3f} threshold={threshold}")


_REGISTRY: dict[str, Callable[[CheckContext], CheckOutcome]] = {
    "ends_with_question_mark": ends_with_question_mark,
    "contains_any_phrase": contains_any_phrase,
    "paraphrases_recent_question": paraphrases_recent_question,
}


def available_checks() -> tuple[str, ...]:
    return tuple(_REGISTRY)


def run_check(name: str, ctx: CheckContext) -> CheckOutcome:
    """名前で check を解決して実行する。未登録なら ValueError。"""
    try:
        check = _REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"unknown deterministic check: '{name}' (available: {available_checks()})") from exc
    return check(ctx)
