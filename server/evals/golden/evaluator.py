"""golden record の assertion と invariant を評価する。

各 clause（record assertion / invariant）は deterministic check か judge で
「性質が成立したか（holds）」を求め、polarity に応じて pass/fail を決める:
    must     → holds が True なら pass
    must_not → holds が False なら pass
record の判定は、自身の全 assertion と全 invariant が pass したとき pass。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from langchain_core.language_models import BaseChatModel

from evals.golden.adapter import recent_system_questions
from evals.golden.checks import CheckContext, run_check
from evals.golden.judge import judge_criterion
from evals.golden.schema import (
    Assertion,
    AssertionType,
    Difficulty,
    GoldenInput,
    GoldenRecord,
    Invariant,
    Polarity,
    Priority,
)

ClauseSource = Literal["record", "invariant"]


@dataclass(frozen=True)
class AssertionResult:
    source: ClauseSource
    assertion_id: str
    polarity: Polarity
    type: AssertionType
    priority: Priority
    holds: bool
    passed: bool
    detail: str


@dataclass(frozen=True)
class RecordResult:
    record_id: str
    category: str
    difficulty: Difficulty
    priority: Priority
    target: str
    output: str
    results: list[AssertionResult]

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)


def _passed(polarity: Polarity, holds: bool) -> bool:
    return holds if polarity == "must" else not holds


def _build_context_text(record_input: GoldenInput) -> str:
    lines = [f"トピック: {record_input.graph_state.current_topic}", "対話履歴:"]
    for turn in record_input.conversation_history:
        role = "AI" if turn.role == "system_question" else "学習者"
        lines.append(f"  {role}: {turn.content}")
    return "\n".join(lines)


async def _evaluate_clause(
    clause: Assertion | Invariant,
    *,
    output: str,
    record_input: GoldenInput,
    context_text: str,
    judge_llm: BaseChatModel | None,
) -> tuple[bool, str]:
    """clause を評価して (holds, detail) を返す。"""
    if clause.type == "deterministic":
        assert clause.check is not None  # schema が保証
        ctx = CheckContext(
            output=output,
            recent_system_questions=recent_system_questions(record_input),
            parameters=clause.parameters or {},
        )
        outcome = run_check(clause.check, ctx)
        return outcome.holds, outcome.detail
    assert clause.criterion is not None  # schema が保証
    verdict = await judge_criterion(
        criterion=clause.criterion,
        output=output,
        context=context_text,
        judge_llm=judge_llm,
    )
    return verdict.holds, verdict.rationale


async def evaluate_record(
    record: GoldenRecord,
    output: str,
    invariants: list[Invariant],
    *,
    judge_llm: BaseChatModel | None = None,
) -> RecordResult:
    """生成済み output に対して record の assertion と invariant を評価する。"""
    context_text = _build_context_text(record.input)
    results: list[AssertionResult] = []

    for assertion in record.expected_behavior.assertions:
        holds, detail = await _evaluate_clause(
            assertion,
            output=output,
            record_input=record.input,
            context_text=context_text,
            judge_llm=judge_llm,
        )
        results.append(
            AssertionResult(
                source="record",
                assertion_id=assertion.id,
                polarity=assertion.polarity,
                type=assertion.type,
                priority=record.priority,
                holds=holds,
                passed=_passed(assertion.polarity, holds),
                detail=detail,
            )
        )

    for invariant in invariants:
        holds, detail = await _evaluate_clause(
            invariant,
            output=output,
            record_input=record.input,
            context_text=context_text,
            judge_llm=judge_llm,
        )
        results.append(
            AssertionResult(
                source="invariant",
                assertion_id=invariant.id,
                polarity=invariant.polarity,
                type=invariant.type,
                priority=invariant.priority,
                holds=holds,
                passed=_passed(invariant.polarity, holds),
                detail=detail,
            )
        )

    return RecordResult(
        record_id=record.id,
        category=record.category,
        difficulty=record.difficulty,
        priority=record.priority,
        target=record.target,
        output=output,
        results=results,
    )
