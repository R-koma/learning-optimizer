"""汎用・単一 criterion・二値の LLM-as-judge。

golden record の `type: judge` assertion と judge 型 invariant の両方で共用する。
criterion 文字列ひとつを受け取り、出力についてそれが成立しているかを true/false で
判定する（polarity の解釈は呼び出し側）。rationale を先に出させて CoT 効果を得る。
"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from pydantic import BaseModel, Field

from evals._judge_factory import build_judge_llm

_SYSTEM_PROMPT = (
    "あなたは学習対話における AI の出力を評価する厳格な評価者です。\n"
    "与えられた『判定基準（criterion）』が、評価対象の出力について成立しているかを\n"
    "true / false の二値で判定します。\n\n"
    "## ルール\n"
    "- criterion は『ある性質の記述』です。その性質が出力に当てはまるなら holds=true、\n"
    "  当てはまらないなら holds=false とせよ。望ましい・望ましくないの価値判断はしない。\n"
    "- 判定は出力と与えられた文脈（対話履歴・トピック）のみに基づく。憶測で補わない。\n\n"
    "## 出力手順\n"
    "- まず rationale で、criterion を出力に照らして具体的に分析せよ。\n"
    "- その分析を踏まえてから holds を決めよ。結論を先に決めて理由を後付けしてはならない。\n"
)


class CriterionVerdict(BaseModel):
    rationale: str = Field(description="criterion を出力に照らして分析した根拠。これを書いた後に holds を決める")
    holds: bool = Field(description="criterion が出力について成立しているなら true")


@dataclass(frozen=True)
class JudgeOutcome:
    """judge の結果。holds=True は『criterion が成立した』を意味する。"""

    holds: bool
    rationale: str


def _build_user_payload(*, criterion: str, output: str, context: str) -> str:
    return f"## 文脈\n{context}\n\n## 評価対象の出力\n{output}\n\n## 判定基準 (criterion)\n{criterion}"


async def judge_criterion(
    *,
    criterion: str,
    output: str,
    context: str,
    judge_llm: BaseChatModel | None = None,
) -> JudgeOutcome:
    """単一 criterion を judge して成立可否と根拠を返す。"""
    judge = judge_llm or build_judge_llm()
    structured = judge.with_structured_output(CriterionVerdict)
    result = await structured.ainvoke(
        [
            SystemMessage(content=_SYSTEM_PROMPT),
            {"role": "user", "content": _build_user_payload(criterion=criterion, output=output, context=context)},
        ]
    )
    if not isinstance(result, CriterionVerdict):
        raise TypeError(f"judge returned unexpected type: {type(result).__name__}")
    return JudgeOutcome(holds=result.holds, rationale=result.rationale)
