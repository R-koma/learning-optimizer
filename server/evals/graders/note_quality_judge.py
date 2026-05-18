from pathlib import Path
from typing import Any

import yaml
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from evals.graders.base import GraderResult

RUBRIC_PATH = Path(__file__).parent.parent / "rubrics" / "note_quality.yaml"


class NoteQualityScore(BaseModel):
    rationale: str = Field(
        description="各評価軸を対話履歴とノートに照らして 1 つずつ分析した根拠。これを書いた後にスコアを付与する"
    )
    explanatory_depth: int = Field(ge=1, le=5)
    protege_alignment: int = Field(ge=1, le=5)
    personalization: int = Field(ge=1, le=5)
    actionability: int = Field(ge=1, le=5)


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
        "あなたは学習ノートの品質を評価する厳格な評価者です。\n\n"
        "## 評価軸（各 1-5 点、5 が最高）\n"
        f"{rubric_text}\n\n"
        "## 評価ルール\n"
        "- 対話内容に基づかない記述（ハルシネーション）は protege_alignment を 1-2 に下げる\n"
        "- ノート構造: 『リード段落 → ## 学んだこと → ## 重要なポイント → "
        "> **まだ曖昧な点** の blockquote callout（曖昧な点なしなら省略可）』。"
        "崩れていれば explanatory_depth を下げる\n"
        "- ユーザーの実際の発言と無関係な一般論ばかりなら personalization を 1-2 に下げる\n"
        "- 「まだ曖昧な点」blockquote が存在するのに内容が空・曖昧で具体性がなければ actionability を 1-2 に下げる\n\n"
        "## 出力手順\n"
        "- まず rationale で各評価軸を対話履歴とノートに照らして 1 つずつ分析せよ。\n"
        "- その分析を踏まえてから各軸のスコアを付与せよ。スコアを先に決めて理由を後付けしてはならない。\n"
    )


async def grade(
    *,
    note_content: str,
    conversation_text: str,
    judge_llm: ChatOpenAI | None = None,
) -> GraderResult:
    rubric = _load_rubric()
    judge = judge_llm or ChatOpenAI(model="gpt-4o", temperature=0)  # type: ignore[call-arg]
    structured_judge = judge.with_structured_output(NoteQualityScore)

    user_payload = f"## 対話履歴\n{conversation_text}\n\n## 生成されたノート\n{note_content}"
    result = await structured_judge.ainvoke(
        [
            SystemMessage(content=_build_judge_prompt(rubric)),
            {"role": "user", "content": user_payload},
        ]
    )
    if not isinstance(result, NoteQualityScore):
        return GraderResult(
            grader_name="note_quality_judge",
            score=0.0,
            passed=False,
            reason=f"judge returned unexpected type: {type(result).__name__}",
        )

    total = result.explanatory_depth + result.protege_alignment + result.personalization + result.actionability
    max_score = int(rubric["max_score"])
    pass_threshold = int(rubric["pass_threshold"])
    return GraderResult(
        grader_name="note_quality_judge",
        score=total / max_score,
        passed=total >= pass_threshold,
        reason=result.rationale,
        metadata={
            "explanatory_depth": result.explanatory_depth,
            "protege_alignment": result.protege_alignment,
            "personalization": result.personalization,
            "actionability": result.actionability,
            "total": total,
            "max_score": max_score,
            "pass_threshold": pass_threshold,
        },
    )
