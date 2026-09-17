"""judge assertion が pass / fail 両方向の instance を持つことを保証する。

片方向しか無い assertion は「judge がその向きを検出できるか」を一度も検証していない。
縮退した judge（常に holds=true を返すだけ）でも一致率が稼げてしまう。

未充足のものは `_KNOWN_SINGLE_DIRECTION` に列挙する。充足したのに列挙が残っている場合も
落とすので、負債が解消されたら必ず外れる。

rubric の assertion は全 failure_mode に適用されるため、両方向は golden 全体で満たせばよい
（failure_mode ごとに要求すると、その観点が出ない失敗モードで必ず落ちる）。
"""

from __future__ import annotations

import glob
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from evals.rubric import RUBRIC_SCOPE, load_rubric, merge_assertions

_GOLDEN_DIR = Path(__file__).resolve().parents[3] / "evals" / "datasets" / "golden"

_KNOWN_SINGLE_DIRECTION: set[tuple[str, str]] = {
    ("accurate_multi_concept_overexplain", "a1"),
    ("accurate_multi_concept_overexplain", "a4"),
}


def _judge_verdicts_by_assertion() -> dict[tuple[str, str], set[str]]:
    verdicts: dict[tuple[str, str], set[str]] = defaultdict(set)
    for path in sorted(glob.glob(str(_GOLDEN_DIR / "*.yaml"))):
        if Path(path).name.startswith("_"):
            continue
        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f)
        assertions = merge_assertions(data["assertions"], load_rubric())
        judge = {a["id"]: a for a in assertions if a["type"] == "judge"}
        for instance in data["instances"]:
            for assertion_id, verdict in instance["human_verdicts"].items():
                if assertion_id not in judge:
                    continue
                # rubric は failure_mode をまたいで適用されるので、カバレッジも全体で 1 つと数える
                owner = RUBRIC_SCOPE if judge[assertion_id]["scope"] == RUBRIC_SCOPE else data["failure_mode"]
                verdicts[owner, assertion_id].add(verdict)
    return verdicts


def test_judge_assertions_have_both_directions() -> None:
    verdicts = _judge_verdicts_by_assertion()
    satisfied = {key for key, values in verdicts.items() if {"pass", "fail"} <= values}

    missing = sorted(set(verdicts) - satisfied - _KNOWN_SINGLE_DIRECTION)
    assert not missing, "pass / fail 両方向の instance が無い judge assertion: " + ", ".join(
        f"{fm}.{aid} ({sorted(verdicts[fm, aid])})" for fm, aid in missing
    )

    resolved = sorted(_KNOWN_SINGLE_DIRECTION & satisfied)
    assert not resolved, "両方向を満たしたので _KNOWN_SINGLE_DIRECTION から外すこと: " + ", ".join(
        f"{fm}.{aid}" for fm, aid in resolved
    )

    stale = sorted(_KNOWN_SINGLE_DIRECTION - set(verdicts))
    assert not stale, "存在しない assertion が _KNOWN_SINGLE_DIRECTION に残っている: " + ", ".join(
        f"{fm}.{aid}" for fm, aid in stale
    )
