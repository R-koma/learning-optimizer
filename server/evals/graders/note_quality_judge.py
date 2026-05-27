"""ノート品質を criterion ごとの二値判定で評価する grader。

各 criterion は rubrics/note_quality.yaml で定義され、判定は
golden/judge.py の judge_criterion を共用する（単一 criterion・二値）。
pass_policy='all' のため、全 criterion が holds=True のときのみ passed=True。
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.language_models import BaseChatModel

from evals.graders._criterion_aggregate import grade_by_criteria, load_rubric
from evals.graders.base import GraderResult

RUBRIC_PATH = Path(__file__).parent.parent / "rubrics" / "note_quality.yaml"
GRADER_NAME = "note_quality_judge"


async def grade(
    *,
    note_content: str,
    conversation_text: str,
    judge_llm: BaseChatModel | None = None,
) -> GraderResult:
    rubric = load_rubric(RUBRIC_PATH)
    return await grade_by_criteria(
        rubric=rubric,
        output=note_content,
        context=f"## 対話履歴\n{conversation_text}",
        grader_name=GRADER_NAME,
        judge_llm=judge_llm,
    )
