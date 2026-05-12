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
    expands_or_reinforces: int = Field(ge=1, le=5)
    positive_acknowledgment: int = Field(ge=1, le=5)
    prompts_re_explanation: int = Field(ge=1, le=5)
    handles_unknown_appropriately: int = Field(ge=1, le=5)
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
        "- 質問が複数（疑問符が複数）含まれていれば single_question を 1-2 にする。\n"
        "\n"
        "### expands_or_reinforces の評価\n"
        "- ユーザー説明が target_depth に対して十分:\n"
        "  未カバー観点・観点間関係・トレードオフへ展開していれば 4-5、単一観点の表面的な深掘りなら 2-3。\n"
        "- ユーザー説明が不十分（具体例なし・誤りあり等）:\n"
        "  AI が観点を補強（より正確な定義 / 具体例 / 応用場面のいずれか）していれば 4-5。\n"
        "  補強せず別観点に飛んでいれば 1-2。\n"
        "\n"
        "### positive_acknowledgment の評価\n"
        "- 「良い整理ですね」「重要な軸を押さえています」のような自然なポジティブ受け止めがあれば 4-5。\n"
        "- まったく受け止めず即座に質問に入っているなら 2-3。\n"
        "- 「100点です」「完璧」のような断定的評価があれば 1-2（減点対象）。\n"
        "- 単一観点の短い発話に対して受け止めがなくても、自然な対話の範疇なら 3-4 で許容。\n"
        "\n"
        "### prompts_re_explanation の評価\n"
        "- ユーザー説明が target_depth に対して不十分（補強が必要）と判定できる場合:\n"
        "  AI が補強後に「改めて自分の言葉で説明してみてください」のような再説明促しをしていれば 4-5。\n"
        "  補強のみで再説明を促していなければ 2-3。補強自体がなければ 1-2。\n"
        "- ユーザー説明が十分で補強モード非該当の場合: 該当しないため 3 とする（減点しない）。\n"
        "\n"
        "### handles_unknown_appropriately の評価\n"
        "- ユーザー発話に「わかりません」「知りません」「よくわからない」が含まれていない場合:\n"
        "  3 とする（該当しないため減点しない）。\n"
        "- 含まれている場合:\n"
        "  - 直前の AI 質問の答えを LLM 側が具体的に提示している（定義 / 動作原理 / 具体例）なら 4-5。\n"
        "  - 「どの観点について？」「どこから始めますか？」のように同じ質問を別形で問い直していたら 1-2。\n"
        "  - トピック冒頭の不知に対して、基礎レベルに下げて具体例で導入できていれば 4-5。\n"
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
        + result.expands_or_reinforces
        + result.positive_acknowledgment
        + result.prompts_re_explanation
        + result.handles_unknown_appropriately
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
            "expands_or_reinforces": result.expands_or_reinforces,
            "positive_acknowledgment": result.positive_acknowledgment,
            "prompts_re_explanation": result.prompts_re_explanation,
            "handles_unknown_appropriately": result.handles_unknown_appropriately,
            "single_question": result.single_question,
            "total": total,
            "max_score": max_score,
            "pass_threshold": pass_threshold,
        },
    )
