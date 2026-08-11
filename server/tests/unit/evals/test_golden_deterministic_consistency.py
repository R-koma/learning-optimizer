"""golden の deterministic assertion が、実際の check 関数の判定と矛盾しないことを保証する。

過去に「主導的な質問が1つだけである」assertion が疑問符ベースの実装と人間ラベルで
恒常的に矛盾していた（#292 で削除）。同じ問題を二度と golden にコミットしないための回帰テスト。
"""

from __future__ import annotations

import glob
from pathlib import Path
from typing import Any

import yaml

from evals.checks import run_check

_GOLDEN_DIR = Path(__file__).resolve().parents[3] / "evals" / "datasets" / "golden"


def _passed(polarity: str, holds: bool) -> bool:
    return holds if polarity == "must" else not holds


def _load_golden_files() -> list[dict[str, Any]]:
    files = []
    for path in sorted(glob.glob(str(_GOLDEN_DIR / "*.yaml"))):
        if Path(path).name.startswith("_"):
            continue
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        data["_path"] = path
        files.append(data)
    return files


def test_deterministic_assertions_match_human_verdicts() -> None:
    mismatches: list[str] = []
    for data in _load_golden_files():
        deterministic = {a["id"]: a for a in data["assertions"] if a["type"] == "deterministic"}
        if not deterministic:
            continue
        for instance in data["instances"]:
            for assertion_id, assertion in deterministic.items():
                outcome = run_check(assertion["check"], instance["observed_output"])
                expected = "pass" if _passed(assertion["polarity"], outcome.holds) else "fail"
                actual = instance["human_verdicts"][assertion_id]
                if expected != actual:
                    mismatches.append(
                        f"{data['_path']}: instance={instance['source_trace_id']} "
                        f"assertion={assertion_id} check says {expected!r}, human_verdicts says {actual!r} "
                        f"({outcome.detail})"
                    )
    assert not mismatches, "\n".join(mismatches)
