"""failure_mode をまたいで全 instance に適用する共通 assertion（invariant）。

同じcriterionがファイルに複製されると、片方だけ直したときに生じる食い違いを解決する。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

RUBRIC_DIR = Path(__file__).parent / "datasets" / "rubric"

RUBRIC_SCOPE = "rubric"
FAILURE_MODE_SCOPE = "failure_mode"


def load_rubric(rubric_dir: Path = RUBRIC_DIR) -> list[dict[str, Any]]:
    assertions: list[dict[str, Any]] = []
    for path in sorted(rubric_dir.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        with path.open(encoding="utf-8") as f:
            assertions.extend(yaml.safe_load(f)["assertions"])
    return assertions


def merge_assertions(own: list[dict[str, Any]], rubric: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """failure_mode 固有の assertion に共通 assertion を足し、どちらに属するかを `scope` で残す。

    id が衝突すると `human_verdicts` のラベルがどちらを指すか決まらなくなるので弾く。
    """
    if collisions := sorted({a["id"] for a in own} & {a["id"] for a in rubric}):
        raise ValueError(f"rubric と failure_mode で assertion id が衝突している: {', '.join(collisions)}")
    return [a | {"scope": FAILURE_MODE_SCOPE} for a in own] + [a | {"scope": RUBRIC_SCOPE} for a in rubric]
