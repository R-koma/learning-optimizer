from typing import Any, cast

from langchain_openai import ChatOpenAI

from evals.golden.evaluator import evaluate_record
from evals.golden.judge import CriterionVerdict
from evals.golden.schema import (
    Assertion,
    ExpectedBehavior,
    GoldenInput,
    GoldenRecord,
    GraphState,
    Invariant,
    LearnerProfile,
    Turn,
)


class _FakeStructured:
    def __init__(self, result: Any) -> None:
        self._result = result

    async def ainvoke(self, _messages: Any) -> Any:
        return self._result


class _FakeJudge:
    def __init__(self, holds: bool) -> None:
        self._result = CriterionVerdict(rationale="fake", holds=holds)

    def with_structured_output(self, _schema: Any) -> _FakeStructured:
        return _FakeStructured(self._result)


def _judge(holds: bool) -> ChatOpenAI:
    return cast(ChatOpenAI, _FakeJudge(holds))


def _ends_q(aid: str = "a1") -> Assertion:
    return Assertion(id=aid, polarity="must", type="deterministic", check="ends_with_question_mark")


def _make_record(assertions: list[Assertion], *, priority: str = "P0", category: str = "cat") -> GoldenRecord:
    return GoldenRecord(
        id="cat__slug__001",
        schema_version=2,
        status="active",
        eval_level="node",
        target="generate_question",
        category=category,
        difficulty="easy",
        priority=cast(Any, priority),
        source="hand_authored",
        tags=[],
        input=GoldenInput(
            learner_profile=LearnerProfile(level="undergrad"),
            conversation_history=[
                Turn(role="system_question", content="前の質問: 信頼性とは何ですか？"),
                Turn(role="learner", content="障害が起きても動くこと。"),
            ],
            graph_state=GraphState(current_topic="信頼性", depth=1),
        ),
        expected_behavior=ExpectedBehavior(assertions=assertions),
        rationale="r",
        created_at="2026-05-22",
        verified_by="ryoma",
        last_reviewed_at="2026-05-22",
    )


class TestDeterministicPolarity:
    async def test_must_passes_when_property_holds(self) -> None:
        rec = _make_record([_ends_q()])
        result = await evaluate_record(rec, "次は何だと思いますか？", [])
        assert result.passed is True
        assert result.results[0].holds is True

    async def test_must_not_fails_when_property_holds(self) -> None:
        rec = _make_record(
            [
                Assertion(
                    id="a1",
                    polarity="must_not",
                    type="deterministic",
                    check="contains_any_phrase",
                    parameters={"phrases": ["丸投げ"]},
                )
            ]
        )
        result = await evaluate_record(rec, "あとは丸投げします。", [])
        assert result.results[0].holds is True
        assert result.results[0].passed is False
        assert result.passed is False


class TestJudgePolarity:
    async def test_must_judge_pass(self) -> None:
        rec = _make_record([Assertion(id="a1", polarity="must", type="judge", criterion="深掘りしている")])
        result = await evaluate_record(rec, "なぜそう思いますか？", [], judge_llm=_judge(True))
        assert result.passed is True

    async def test_must_not_judge_fail(self) -> None:
        rec = _make_record([Assertion(id="a1", polarity="must_not", type="judge", criterion="正解を説明している")])
        result = await evaluate_record(rec, "答えはこうです。", [], judge_llm=_judge(True))
        assert result.results[0].passed is False
        assert result.passed is False


class TestInvariants:
    async def test_invariant_failure_fails_record(self) -> None:
        rec = _make_record([_ends_q()])
        invariant = Invariant(
            id="inv_ends_with_question",
            polarity="must",
            type="deterministic",
            priority="P1",
            check="ends_with_question_mark",
        )
        # output は ? で終わらないため、自身の a1 と invariant の両方が落ちる
        result = await evaluate_record(rec, "説明で終わる文。", [invariant])
        assert result.passed is False
        inv_result = next(r for r in result.results if r.source == "invariant")
        assert inv_result.assertion_id == "inv_ends_with_question"
        assert inv_result.priority == "P1"
        assert inv_result.passed is False

    async def test_assertion_priority_overrides_record(self) -> None:
        assertion = Assertion(
            id="a1", polarity="must", type="deterministic", check="ends_with_question_mark", priority="P1"
        )
        rec = _make_record([assertion], priority="P0")
        result = await evaluate_record(rec, "終わりですか？", [])
        assert result.results[0].priority == "P1"

    async def test_invariant_priority_preserved(self) -> None:
        rec = _make_record(
            [Assertion(id="a1", polarity="must", type="deterministic", check="ends_with_question_mark")],
            priority="P2",
        )
        invariant = Invariant(
            id="inv_x", polarity="must", type="deterministic", priority="P0", check="ends_with_question_mark"
        )
        result = await evaluate_record(rec, "終わりですか？", [invariant])
        record_assertion = next(r for r in result.results if r.source == "record")
        invariant_assertion = next(r for r in result.results if r.source == "invariant")
        assert record_assertion.priority == "P2"
        assert invariant_assertion.priority == "P0"
        assert result.passed is True
