"""evals.graders._criterion_aggregate の集約挙動テスト。

judge_criterion をモックして、rubric の各 criterion が並列評価され
pass_policy='all' で集約されることを確認する。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from evals.golden.judge import JudgeOutcome
from evals.graders import _criterion_aggregate
from evals.graders._criterion_aggregate import Rubric, grade_by_criteria, load_rubric


@pytest.fixture
def rubric_path(tmp_path: Path) -> Path:
    path = tmp_path / "rubric.yaml"
    path.write_text(
        "criteria:\n"
        "  a:\n"
        "    criterion: 'criterion A'\n"
        "  b:\n"
        "    criterion: 'criterion B'\n"
        "  c:\n"
        "    criterion: 'criterion C'\n"
        "pass_policy: all\n",
        encoding="utf-8",
    )
    return path


def test_load_rubric_parses_criteria(rubric_path: Path) -> None:
    rubric = load_rubric(rubric_path)
    assert rubric.criteria == {"a": "criterion A", "b": "criterion B", "c": "criterion C"}
    assert rubric.pass_policy == "all"


def test_load_rubric_rejects_empty_criteria(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("criteria: {}\npass_policy: all\n", encoding="utf-8")
    with pytest.raises(ValueError, match="non-empty"):
        load_rubric(path)


def test_load_rubric_rejects_unsupported_policy(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(
        "criteria:\n  a:\n    criterion: 'x'\npass_policy: majority\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unsupported pass_policy"):
        load_rubric(path)


async def test_grade_all_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    rubric = Rubric(
        criteria={"a": "criterion A", "b": "criterion B"},
        pass_policy="all",
    )
    mock_judge = AsyncMock(
        side_effect=[
            JudgeOutcome(holds=True, rationale="rA"),
            JudgeOutcome(holds=True, rationale="rB"),
        ]
    )
    monkeypatch.setattr(_criterion_aggregate, "judge_criterion", mock_judge)

    result = await grade_by_criteria(
        rubric=rubric,
        output="out",
        context="ctx",
        grader_name="g",
        judge_llm=AsyncMock(),
    )

    assert result.passed is True
    assert result.score == 1.0
    assert result.metadata["passed_count"] == 2
    assert result.metadata["total"] == 2
    assert result.metadata["criteria"]["a"]["holds"] is True
    assert result.metadata["criteria"]["a"]["rationale"] == "rA"
    assert result.reason == "all criteria hold"


async def test_grade_partial_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    rubric = Rubric(
        criteria={"a": "criterion A", "b": "criterion B", "c": "criterion C", "d": "criterion D"},
        pass_policy="all",
    )
    mock_judge = AsyncMock(
        side_effect=[
            JudgeOutcome(holds=True, rationale="rA"),
            JudgeOutcome(holds=False, rationale="rB"),
            JudgeOutcome(holds=True, rationale="rC"),
            JudgeOutcome(holds=False, rationale="rD"),
        ]
    )
    monkeypatch.setattr(_criterion_aggregate, "judge_criterion", mock_judge)

    result = await grade_by_criteria(
        rubric=rubric,
        output="out",
        context="ctx",
        grader_name="g",
        judge_llm=AsyncMock(),
    )

    assert result.passed is False
    assert result.score == 0.5
    assert result.metadata["passed_count"] == 2
    assert "b" in result.reason and "d" in result.reason


async def test_grade_invokes_judge_in_parallel(monkeypatch: pytest.MonkeyPatch) -> None:
    rubric = Rubric(criteria={"a": "A", "b": "B", "c": "C"}, pass_policy="all")
    mock_judge = AsyncMock(return_value=JudgeOutcome(holds=True, rationale="r"))
    monkeypatch.setattr(_criterion_aggregate, "judge_criterion", mock_judge)

    await grade_by_criteria(
        rubric=rubric,
        output="out",
        context="ctx",
        grader_name="g",
        judge_llm=AsyncMock(),
    )

    assert mock_judge.call_count == 3
    criteria_passed = sorted(call.kwargs["criterion"] for call in mock_judge.call_args_list)
    assert criteria_passed == ["A", "B", "C"]
