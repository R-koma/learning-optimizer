import json
from typing import Any, cast

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from evals.golden.judge import CriterionVerdict
from evals.golden.runner import run_golden


class _FakeLLM:
    def __init__(self, content: str) -> None:
        self._content = content

    async def ainvoke(self, _messages: Any) -> AIMessage:
        return AIMessage(content=self._content)


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


class TestRunGolden:
    async def test_runs_over_shipped_records(self) -> None:
        report = await run_golden(
            save_report=False,
            llm=cast(ChatOpenAI, _FakeLLM("では次に何が起きると思いますか？")),
            judge_llm=cast(ChatOpenAI, _FakeJudge(False)),
        )
        assert report.n_records >= 4
        assert len(report.records) == report.n_records
        assert report.errors == []
        assert isinstance(report.gate_passed, bool)

    async def test_report_is_json_serializable(self) -> None:
        from dataclasses import asdict

        report = await run_golden(
            save_report=False,
            llm=cast(ChatOpenAI, _FakeLLM("どう考えますか？")),
            judge_llm=cast(ChatOpenAI, _FakeJudge(False)),
        )
        # 例外なくシリアライズできること
        json.dumps(asdict(report), ensure_ascii=False)

    async def test_smoke_limits_records(self) -> None:
        report = await run_golden(
            smoke=True,
            save_report=False,
            llm=cast(ChatOpenAI, _FakeLLM("なぜですか？")),
            judge_llm=cast(ChatOpenAI, _FakeJudge(False)),
        )
        assert report.smoke is True
        assert report.n_records <= 5
