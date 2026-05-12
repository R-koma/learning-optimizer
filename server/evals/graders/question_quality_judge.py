from pathlib import Path
from typing import Any

import yaml
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from evals.graders.base import GraderResult

RUBRIC_PATH = Path(__file__).parent.parent / "rubrics" / "question_quality.yaml"


class QuestionQualityScore(BaseModel):
    avoids_repeated_aspects: int = Field(ge=1, le=5)
    expands_to_uncovered: int = Field(ge=1, le=5)
    acknowledges_coverage: int = Field(ge=1, le=5)
    single_question: int = Field(ge=1, le=5)
    rationale: str = Field(description="採点理由を簡潔に")


def _load_rubric() -> dict[str, Any]:
    with RUBRIC_PATH.open(encoding="utf-8") as f:
        loaded: dict[str, Any] = yaml.safe_load(f)
    return loaded


def _build_judge_prompt(rubric: dict[str, Any]) -> str:
    rubric_lines: list[str] = []
    for axis, body in rubric["rubric"].items():
        rubric_lines.append(f"- {axis} ({body['scale']}): {body['description']}")
    rubric_text = "\n".join(rubric_lines)
    return (
        "あなたは学習対話における AI 質問の品質を評価する厳格な評価者です。\n"
        "学習者の発話に含まれる『観点（aspect）』を見抜き、\n"
        "AI の次質問がそれらをどう扱っているかを評価します。\n\n"
        "## 評価軸（各 1-5 点、5 が最高）\n"
        f"{rubric_text}\n\n"
        "## 評価ルール\n"
        "- ユーザー発話に複数の観点が含まれている場合（例: 信頼性・スケーラビリティ・メンテナンス性を一度に説明）、\n"
        "  AI 質問がそのうちの 1 つを再度問い直しているなら avoids_repeated_aspects を 1-2 にする。\n"
        "- ユーザー発話の観点を要約復唱せず無視して別観点に飛んでいる場合、acknowledges_coverage を 1-2 にする。\n"
        "- 質問が複数（疑問符が複数）含まれていれば single_question を 1-2 にする。\n"
        "- 未カバーの新規観点、もしくは既出観点同士の関係・対比・トレードオフへ展開していれば、\n"
        "  expands_to_uncovered を 4-5 にする。単一観点の表面的な深掘りに留まれば 2-3。\n"
        "- 単一観点のユーザー発話の場合は acknowledges_coverage を 3 とし、減点しない（該当しないため）。\n"
    )


async def grade(
    *,
    user_message: str,
    ai_question: str,
    topic: str,
    judge_llm: ChatOpenAI | None = None,
) -> GraderResult:
    rubric = _load_rubric()
    judge = judge_llm or ChatOpenAI(model="gpt-4o", temperature=0)  # type: ignore[call-arg]
    structured_judge = judge.with_structured_output(QuestionQualityScore)

    user_payload = (
        f"## トピック\n{topic}\n\n## ユーザー発話\n{user_message}\n\n## AI が生成した次の質問\n{ai_question}"
    )
    result = await structured_judge.ainvoke(
        [
            SystemMessage(content=_build_judge_prompt(rubric)),
            {"role": "user", "content": user_payload},
        ]
    )
    if not isinstance(result, QuestionQualityScore):
        return GraderResult(
            grader_name="question_quality_judge",
            score=0.0,
            passed=False,
            reason=f"judge returned unexpected type: {type(result).__name__}",
        )

    total = (
        result.avoids_repeated_aspects
        + result.expands_to_uncovered
        + result.acknowledges_coverage
        + result.single_question
    )
    max_score = int(rubric["max_score"])
    pass_threshold = int(rubric["pass_threshold"])
    return GraderResult(
        grader_name="question_quality_judge",
        score=total / max_score,
        passed=total >= pass_threshold,
        reason=result.rationale,
        metadata={
            "avoids_repeated_aspects": result.avoids_repeated_aspects,
            "expands_to_uncovered": result.expands_to_uncovered,
            "acknowledges_coverage": result.acknowledges_coverage,
            "single_question": result.single_question,
            "total": total,
            "max_score": max_score,
            "pass_threshold": pass_threshold,
        },
    )
