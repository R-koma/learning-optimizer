"""観点カバレッジ（covered_aspects）のマージ・整形。

「既出観点の再質問禁止」を直近メッセージの読解だけに頼らせないため、
観点ごとの到達度を state に累積し、毎ターンのプロンプトに注入する。
"""

from collections.abc import Sequence

from graph.output_schemas import AspectObservation
from graph.state import CoveredAspect, ReachedDepth

_DEPTH_ORDER: dict[ReachedDepth, int] = {
    "mentioned": 0,
    "defined": 1,
    "exemplified": 2,
    "applied": 3,
}

DEPTH_LABELS: dict[ReachedDepth, str] = {
    "mentioned": "言及のみ",
    "defined": "定義済み",
    "exemplified": "具体例・動作原理まで説明済み",
    "applied": "応用・他概念との関係まで説明済み",
}


def merge_coverage(
    existing: Sequence[CoveredAspect],
    observations: Sequence[AspectObservation],
) -> list[CoveredAspect]:
    """既存カバレッジへ今ターンの観測をマージする。

    昇格のみ（一度到達した深さを下げない）。観点の並びは既出順を保つ
    （プロンプトの観点選定基準「既出順」がこの並びに依存する）。
    """
    merged: dict[str, ReachedDepth] = {a["aspect"]: a["reached_depth"] for a in existing}
    for obs in observations:
        current = merged.get(obs.aspect)
        if current is None or _DEPTH_ORDER[obs.reached_depth] > _DEPTH_ORDER[current]:
            merged[obs.aspect] = obs.reached_depth
    return [{"aspect": aspect, "reached_depth": depth} for aspect, depth in merged.items()]


def format_covered_aspects(covered: Sequence[CoveredAspect]) -> str:
    """カバレッジをプロンプト注入用の箇条書きに整形する。空なら空文字。"""
    return "\n".join(f"- {a['aspect']}: {a['reached_depth']}（{DEPTH_LABELS[a['reached_depth']]}）" for a in covered)
