from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from evals import runner
from evals.runner import EvalReport, _load_dataset, run_eval
from graph.model import FeedbackOutput, NoteContent


def _make_structured_llm_returning(value: Any) -> MagicMock:
    """Build a mock that mimics ChatOpenAI: with_structured_output(...).ainvoke -> value."""
    mock_llm = MagicMock()
    structured = MagicMock()
    structured.ainvoke = AsyncMock(return_value=value)
    mock_llm.with_structured_output = MagicMock(return_value=structured)
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="分析結果: 良い理解です"))
    return mock_llm


def _make_llm_returning(content: str) -> MagicMock:
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content=content))
    return mock_llm


def test_load_dataset_smoke_truncates() -> None:
    cases = _load_dataset("note_generation", smoke=True)
    assert len(cases) <= 5
    assert all("id" in c for c in cases)


def test_load_dataset_full() -> None:
    cases = _load_dataset("note_generation", smoke=False)
    assert len(cases) >= 30


def test_load_dataset_response_analysis_has_labels() -> None:
    cases = _load_dataset("response_analysis", smoke=False)
    labels = {c["expected_label"] for c in cases}
    assert labels == {"LEARNING_END", "CONTINUE"}


@pytest.mark.asyncio
async def test_run_eval_note_generation_smoke(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "REPORTS_DIR", tmp_path)
    note = NoteContent(
        topic="テスト",
        summary="要約",
        content="## 概要\nx\n## 学んだこと\ny\n## 重要なポイント\nz\n## まだ曖昧な点\nw",
    )
    structured_mock = _make_structured_llm_returning(note)
    report: EvalReport = await run_eval(
        "note_generation",
        smoke=True,
        save_report=False,
        llm_structured=structured_mock,
    )
    assert report.task == "note_generation"
    assert report.smoke is True
    assert report.n_cases <= 5
    assert "note_has_sections" in report.summary
    assert report.summary["note_has_sections"] == 1.0


@pytest.mark.asyncio
async def test_run_eval_feedback_generation_smoke(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "REPORTS_DIR", tmp_path)
    fb = FeedbackOutput(
        understanding_level="medium",
        strength=["s1"],
        improvement_points=["i1"],
    )
    structured_mock = _make_structured_llm_returning(fb)
    report = await run_eval(
        "feedback_generation",
        smoke=True,
        save_report=False,
        llm_structured=structured_mock,
    )
    assert "feedback_is_actionable" in report.summary
    assert report.summary["feedback_is_actionable"] == 1.0


@pytest.mark.asyncio
async def test_run_eval_response_analysis_smoke(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "REPORTS_DIR", tmp_path)
    llm_mock = _make_llm_returning("LEARNING_END")
    report = await run_eval(
        "response_analysis",
        smoke=True,
        save_report=False,
        llm=llm_mock,
    )
    assert "dialogue_ended_correctly" in report.summary
    assert "response_label_match" in report.summary
    assert report.n_cases == 5


@pytest.mark.asyncio
async def test_run_eval_question_generation_smoke(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "REPORTS_DIR", tmp_path)
    llm_mock = _make_llm_returning("もう少し詳しく教えてもらえますか？")
    report = await run_eval(
        "question_generation",
        smoke=True,
        save_report=False,
        llm=llm_mock,
    )
    assert "question_generation_smoke" in report.summary
    assert report.summary["question_generation_smoke"] == 1.0


@pytest.mark.asyncio
async def test_run_eval_writes_report_json(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "REPORTS_DIR", tmp_path)
    note = NoteContent(
        topic="テスト",
        summary="要約",
        content="## 概要\nx\n## 学んだこと\ny\n## 重要なポイント\nz\n## まだ曖昧な点\nw",
    )
    structured_mock = _make_structured_llm_returning(note)
    await run_eval(
        "note_generation",
        smoke=True,
        save_report=True,
        llm_structured=structured_mock,
    )
    files = list(tmp_path.glob("note_generation_*.json"))
    assert len(files) == 1


@pytest.mark.asyncio
async def test_run_eval_records_error_per_case(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "REPORTS_DIR", tmp_path)
    failing_structured = MagicMock()
    failing = MagicMock()
    failing.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))
    failing_structured.with_structured_output = MagicMock(return_value=failing)
    report = await run_eval(
        "note_generation",
        smoke=True,
        save_report=False,
        llm_structured=failing_structured,
    )
    assert all(cr["error"] is not None for cr in report.case_results)
