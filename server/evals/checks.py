"""LLM が生成したテキストの性質を判定する deterministic check レジストリ。

判定ロジック自体は pure function で再現可能だが、検査対象（output）は
temperature 0.7 の LLM 生成テキストなので出力そのものは非決定的。
1 回の判定は安定していても、複数回生成した際の pass 率を見る前提は
eval 側（regression モード）が担う。ここでは判定ロジックと、その同一性を
表す fingerprint だけを持つ。
"""

from __future__ import annotations

import hashlib
import inspect
import sys
from collections.abc import Callable
from dataclasses import dataclass
from types import FunctionType

_GENERIC_PROMPT_PHRASES: tuple[str, ...] = (
    "もっと詳しく",
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

_FINGERPRINT_DATA_TYPES = (str, bytes, int, float, tuple, frozenset, list, set, dict)


def _resolve(name: str) -> Callable[[str], CheckOutcome]:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"unknown deterministic check: {name!r} (available: {tuple(_REGISTRY)})") from exc


def _implementation_parts(fn: FunctionType, seen: set[str]) -> list[str]:
    if fn.__qualname__ in seen:
        return []
    seen.add(fn.__qualname__)

    module = sys.modules[fn.__module__]
    parts = [inspect.getsource(fn)]
    # co_names は関数本体が参照するグローバル名。同一モジュールの定数とヘルパー関数だけを
    # 拾うことで、builtin・型・他モジュールからの import は自然に外れる。
    for name in sorted(fn.__code__.co_names):
        referent = getattr(module, name, None)
        if isinstance(referent, _FINGERPRINT_DATA_TYPES):
            parts.append(f"{name}={referent!r}")
        elif inspect.isfunction(referent) and referent.__module__ == fn.__module__:
            parts.extend(_implementation_parts(referent, seen))
    return parts


def check_fingerprint(name: str) -> str:
    """check の実装（関数本体 + 参照する定数・ヘルパー）の内容ハッシュ。"""
    fn = _resolve(name)
    if not isinstance(fn, FunctionType):
        raise ValueError(f"cannot fingerprint check {name!r}: not a plain function ({type(fn).__name__})")
    return hashlib.sha256("\x00".join(_implementation_parts(fn, set())).encode()).hexdigest()[:12]


def run_check(name: str, output: str) -> CheckOutcome:
    """check 名で登録済み関数を解決して実行する。未登録なら fail-fast で ValueError。"""
    return _resolve(name)(output)
