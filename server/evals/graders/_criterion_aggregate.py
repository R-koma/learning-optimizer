"""rubric YAML から criterion を読み、judge_criterion を並列実行して集約する共通ロジック。

note_quality_judge / question_quality_judge から共用する。
1 観点 1 回の judge 呼び出しによる二値判定の集約に閉じる。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from langchain_core.language_models import BaseChatModel

from evals._judge_factory import build_judge_llm
from evals.golden.judge import judge_criterion
from evals.graders.base import GraderResult

PassPolicy = Literal["all"]


@dataclass(frozen=True)
class Rubric:
    criteria: dict[str, str]  # name -> criterion text
    pass_policy: PassPolicy


def load_rubric(path: Path) -> Rubric:
    with path.open(encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)
    criteria_block = raw.get("criteria")
    if not isinstance(criteria_block, dict) or not criteria_block:
        raise ValueError(f"rubric {path} must define non-empty 'criteria'")
    criteria: dict[str, str] = {}
    for name, body in criteria_block.items():
        if isinstance(body, dict):
            criterion = body.get("criterion")
        else:
            criterion = body
        if not isinstance(criterion, str) or not criterion.strip():
            raise ValueError(f"rubric {path}: criterion for {name!r} must be a non-empty string")
        criteria[str(name)] = criterion.strip()
    policy = raw.get("pass_policy", "all")
    if policy != "all":
        raise ValueError(f"rubric {path}: unsupported pass_policy {policy!r} (only 'all' is implemented)")
    return Rubric(criteria=criteria, pass_policy="all")


async def grade_by_criteria(
    *,
    rubric: Rubric,
    output: str,
    context: str,
    grader_name: str,
    judge_llm: BaseChatModel | None,
) -> GraderResult:
    """rubric の各 criterion を並列に judge し、集約結果を GraderResult として返す。"""
    judge = judge_llm or build_judge_llm()

    names = list(rubric.criteria.keys())
    verdicts = await asyncio.gather(
        *(
            judge_criterion(criterion=rubric.criteria[name], output=output, context=context, judge_llm=judge)
            for name in names
        )
    )

    per_criterion: dict[str, dict[str, Any]] = {}
    passed_count = 0
    for name, verdict in zip(names, verdicts, strict=True):
        per_criterion[name] = {"holds": verdict.holds, "rationale": verdict.rationale}
        if verdict.holds:
            passed_count += 1

    total = len(names)
    score = passed_count / total
    all_passed = passed_count == total
    failed = [name for name, v in zip(names, verdicts, strict=True) if not v.holds]
    reason = "all criteria hold" if all_passed else f"failed criteria: {', '.join(failed)}"

    return GraderResult(
        grader_name=grader_name,
        score=score,
        passed=all_passed,
        reason=reason,
        metadata={
            "passed_count": passed_count,
            "total": total,
            "pass_policy": rubric.pass_policy,
            "criteria": per_criterion,
        },
    )
