"""LLM が生成したテキストの性質を判定する deterministic check レジストリ。

判定ロジック自体は pure function で再現可能だが、検査対象（output）は
temperature 0.7 の LLM 生成テキストなので出力そのものは非決定的。
1 回の判定は安定していても、複数回生成した際の pass 率を見る前提は
eval 側（regression モード）が担う。ここでは判定ロジックのみを持つ。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

_GENERIC_PROMPT_PHRASES: tuple[str, ...] = (
    "もう少し詳しく",
    "さらに詳しく",
    "掘り下げてみませんか",
    "考えてみませんか",
)


@dataclass(frozen=True)
class CheckOutcome:
    holds: bool
    detail: str


def contains_generic_prompt_phrase(output: str) -> CheckOutcome:
    """対象を特定しない一般化した促し（「もっと詳しく」「掘り下げてみませんか」等）を含むか。"""
    matched = [p for p in _GENERIC_PROMPT_PHRASES if p in output]
    return CheckOutcome(holds=bool(matched), detail=f"matched_phrases={matched}")


_REGISTRY: dict[str, Callable[[str], CheckOutcome]] = {
    "contains_generic_prompt_phrase": contains_generic_prompt_phrase,
}


def run_check(name: str, output: str) -> CheckOutcome:
    """check 名で登録済み関数を解決して実行する。未登録なら fail-fast で ValueError。"""
    try:
        check = _REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"unknown deterministic check: {name!r} (available: {tuple(_REGISTRY)})") from exc
    return check(output)
