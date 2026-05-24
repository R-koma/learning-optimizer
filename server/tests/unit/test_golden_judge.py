from typing import Any, cast

import pytest
from langchain_openai import ChatOpenAI

from evals.golden.judge import CriterionVerdict, judge_criterion


class _FakeStructured:
    def __init__(self, result: Any) -> None:
        self._result = result

    async def ainvoke(self, _messages: Any) -> Any:
        return self._result


class _FakeJudge:
    """ChatOpenAI の with_structured_output().ainvoke() だけを模した judge ダブル。"""

    def __init__(self, result: Any) -> None:
        self._result = result

    def with_structured_output(self, _schema: Any) -> _FakeStructured:
        return _FakeStructured(self._result)


def _judge(result: Any) -> ChatOpenAI:
    return cast(ChatOpenAI, _FakeJudge(result))


class TestJudgeCriterion:
    async def test_returns_holds_true(self) -> None:
        verdict = CriterionVerdict(rationale="正解を直接説明している", holds=True)
        outcome = await judge_criterion(
            criterion="正解を直接説明してしまっている",
            output="光合成とは光エネルギーを使う反応です。",
            context="topic: 光合成",
            judge_llm=_judge(verdict),
        )
        assert outcome.holds is True
        assert outcome.rationale == "正解を直接説明している"

    async def test_returns_holds_false(self) -> None:
        verdict = CriterionVerdict(rationale="質問で返している", holds=False)
        outcome = await judge_criterion(
            criterion="正解を直接説明してしまっている",
            output="材料には何を使うと思いますか？",
            context="topic: 光合成",
            judge_llm=_judge(verdict),
        )
        assert outcome.holds is False

    async def test_unexpected_type_raises(self) -> None:
        with pytest.raises(TypeError, match="unexpected type"):
            await judge_criterion(
                criterion="c",
                output="o",
                context="ctx",
                judge_llm=_judge("not a verdict"),
            )
