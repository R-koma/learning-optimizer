import asyncio
import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, Field

from evals.checks import run_check
from graph.llm import llm, llm_judge
from graph.prompts.question import PROMPT_VERSION
from graph.state import LearningState

logger = logging.getLogger(__name__)

_GOLDEN_DIR = Path(__file__).parent / "datasets" / "golden"
_JSONL_PATH = Path(__file__).parent / "datasets" / "generate_questions.jsonl"

_JUDGE_MAX_ATTEMPTS = 3
_EVAL_USER_ID = "eval-regression"
_NOT_APPLICABLE = "na"

JUDGE_PROMPT = """\
## 役割
あなたは、学習支援 AI の応答を評価する専門家です。

## 評価対象
学習者と AI の会話履歴、および直近の AI 応答が与えられます。
判定するのは「直近の AI 応答」だけです。

## 学習トピック
{topic}

## 会話履歴
{conversation}

## 直近の AI 応答（判定対象）
{observed_output}

## 判定基準
次の記述が、直近の AI 応答について成り立っているかを判定してください。

{criterion}

## 注意事項
- 記述が成り立つなら holds=true、成り立たないなら holds=false を返してください。
- 応答の良し悪しは判断しません。記述が事実として当てはまるかだけを見ます。
- reason を先に書き、その reason に基づいて holds を決めてください。
- reason は 1〜2 文で、応答のどの箇所を根拠にしたかを引用してください。
- reason と holds は必ず両方とも出力してください。
"""


class JudgeResult(BaseModel):
    reason: str = Field(..., description="判定の根拠。1〜2文で、応答のどの箇所を根拠にしたかを引用する")
    holds: bool = Field(..., description="判定基準の記述が、判定対象の応答について成り立っているか")


@dataclass(frozen=True)
class SourceTrace:
    turn: int
    meta: dict[str, Any]
    input: dict[str, Any]
    observed_output: str


@dataclass(frozen=True)
class AssertionOutcome:
    assertion_id: str
    assertion_type: str
    polarity: str
    holds: bool | None
    verdict: str
    human_verdict: str
    detail: str

    @property
    def applicable(self) -> bool:
        return self.verdict != _NOT_APPLICABLE

    @property
    def agrees(self) -> bool:
        return self.applicable and self.verdict == self.human_verdict


def load_golden_records() -> Iterator[dict[str, Any]]:
    for path in sorted(_GOLDEN_DIR.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        with path.open(encoding="utf-8") as f:
            record = yaml.safe_load(f)
        if record.get("status") == "active":
            yield record


def get_source_trace(trace_id: str) -> SourceTrace:
    with _JSONL_PATH.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            record: dict[str, Any] = json.loads(line)
            if record["id"] != trace_id:
                continue
            return SourceTrace(
                turn=record["turn"],
                meta=record["meta"],
                input=record["input"],
                observed_output=record["output"],
            )
    raise ValueError(f"unknown source_trace_id: {trace_id} not in {_JSONL_PATH}")


def to_state(trace: SourceTrace) -> LearningState:
    graph_state = trace.input["graph_state"]
    messages: list[BaseMessage] = [
        AIMessage(content=m["content"]) if m["role"] == "assistant" else HumanMessage(content=m["content"])
        for m in trace.input["conversation_history"]
    ]
    state: LearningState = {
        "user_id": _EVAL_USER_ID,
        "dialogue_session_id": uuid4(),
        "note_id": uuid4(),
        "messages": messages,
        "topic": graph_state["topic"],
        "turn_count": trace.turn,
        "should_generate_note": False,
        "session_type": "learning",
    }
    if graph_state.get("learning_goal"):
        state["learning_goal"] = graph_state["learning_goal"]
    if graph_state.get("focus_aspects"):
        state["focus_aspects"] = graph_state["focus_aspects"]
    if graph_state.get("covered_aspects"):
        state["covered_aspects"] = graph_state["covered_aspects"]
    return state


def to_verdict(polarity: str, holds: bool) -> str:
    if polarity == "must":
        return "pass" if holds else "fail"
    if polarity == "must_not":
        return "fail" if holds else "pass"
    raise ValueError(f"unknown polarity: {polarity!r} (expected 'must' or 'must_not')")


def format_conversation(conversation_history: list[dict[str, str]]) -> str:
    return "\n".join(f"{turn['role']}: {turn['content']}" for turn in conversation_history)


async def judge_by_llm(assertion: dict[str, Any], trace: SourceTrace) -> JudgeResult:
    prompt = JUDGE_PROMPT.format(
        topic=trace.input["graph_state"]["topic"],
        conversation=format_conversation(trace.input["conversation_history"]),
        observed_output=trace.observed_output,
        criterion=assertion["criterion"].strip(),
    )
    runnable = llm_judge.with_structured_output(JudgeResult)

    last_error: Exception | None = None
    for attempt in range(1, _JUDGE_MAX_ATTEMPTS + 1):
        try:
            result = await runnable.ainvoke([HumanMessage(content=prompt)])
        except Exception as exc:
            last_error = exc
            logger.warning("judge attempt %d/%d failed for %s", attempt, _JUDGE_MAX_ATTEMPTS, assertion["id"])
            continue
        if isinstance(result, JudgeResult):
            return result
        last_error = RuntimeError(f"judge returned {type(result).__name__}")

    raise RuntimeError(
        f"judge failed for assertion {assertion['id']} after {_JUDGE_MAX_ATTEMPTS} attempts"
    ) from last_error


async def evaluate_assertion(
    assertion: dict[str, Any], trace: SourceTrace, human_verdicts: dict[str, str]
) -> AssertionOutcome:
    human_verdict = human_verdicts[assertion["id"]]
    if human_verdict == _NOT_APPLICABLE:
        return AssertionOutcome(
            assertion_id=assertion["id"],
            assertion_type=assertion["type"],
            polarity=assertion["polarity"],
            holds=None,
            verdict=_NOT_APPLICABLE,
            human_verdict=human_verdict,
            detail=f"applies_when: {assertion.get('applies_when', '').strip()}",
        )

    if assertion["type"] == "judge":
        judged = await judge_by_llm(assertion, trace)
        holds, detail = judged.holds, judged.reason
    elif assertion["type"] == "deterministic":
        outcome = run_check(assertion["check"], trace.observed_output)
        holds, detail = outcome.holds, outcome.detail
    else:
        raise ValueError(f"unknown assertion type: {assertion['type']!r} (expected 'judge' or 'deterministic')")

    return AssertionOutcome(
        assertion_id=assertion["id"],
        assertion_type=assertion["type"],
        polarity=assertion["polarity"],
        holds=holds,
        verdict=to_verdict(assertion["polarity"], holds),
        human_verdict=human_verdict,
        detail=detail,
    )


async def evaluate_instance(record: dict[str, Any], instance: dict[str, Any]) -> list[AssertionOutcome]:
    trace = get_source_trace(instance["source_trace_id"])
    return list(
        await asyncio.gather(*(evaluate_assertion(a, trace, instance["human_verdicts"]) for a in record["assertions"]))
    )


def format_output(record: dict[str, Any], instance: dict[str, Any], outcomes: list[AssertionOutcome]) -> None:
    print("=" * 100)
    print(f"failure_mode={record['failure_mode']}  source_trace_id={instance['source_trace_id']}")
    print("-" * 100)
    for outcome in outcomes:
        mark = "-- " if not outcome.applicable else ("OK " if outcome.agrees else "NG ")
        print(
            f"{mark}{outcome.assertion_id}  {outcome.assertion_type:<13} {outcome.polarity:<8} "
            f"holds={str(outcome.holds):<5} judge={outcome.verdict:<4} human={outcome.human_verdict}"
        )
        print(f"      {outcome.detail}")
    print()


def validate(outcomes: list[AssertionOutcome]) -> None:
    scored = [o for o in outcomes if o.applicable]
    skipped = len(outcomes) - len(scored)
    tp = sum(1 for o in scored if o.human_verdict == "fail" and o.verdict == "fail")
    fn = sum(1 for o in scored if o.human_verdict == "fail" and o.verdict == "pass")
    fp = sum(1 for o in scored if o.human_verdict == "pass" and o.verdict == "fail")
    tn = sum(1 for o in scored if o.human_verdict == "pass" and o.verdict == "pass")
    agreed = tp + tn
    total = len(scored)

    print("=" * 100)
    print(f"judge–人間一致: {agreed}/{total}" + (f" ({agreed / total:.0%})" if total else ""))
    print(f"  適用外（applies_when を満たさず採点対象外）: {skipped} 件")
    print(f"  TP={tp} TN={tn} FP={fp} FN={fn}   （陽性 = 人間ラベル fail）")
    print(f"  TPR={tp / (tp + fn):.0%}" if tp + fn else "  TPR=n/a")
    print(f"  TNR={tn / (tn + fp):.0%}" if tn + fp else "  TNR=n/a")


async def main() -> None:
    print(f"model={llm.model_name} temperature={llm.temperature}")
    print(f"judge={llm_judge.model} prompt_version={PROMPT_VERSION}\n")

    all_outcomes: list[AssertionOutcome] = []
    for record in load_golden_records():
        for instance in record["instances"]:
            outcomes = await evaluate_instance(record, instance)
            format_output(record, instance, outcomes)
            all_outcomes.extend(outcomes)

    validate(all_outcomes)


if __name__ == "__main__":
    asyncio.run(main())
