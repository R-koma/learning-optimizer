"""Unit tests for evals/compare.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evals.compare import compare, main


def _make_report(
    task: str = "note_generation",
    summary: dict[str, float] | None = None,
    case_results: list[dict[str, Any]] | None = None,
    *,
    git_sha: str = "abc1234",
) -> dict[str, Any]:
    return {
        "task": task,
        "run_at": "2026-04-28T03:00:00+00:00",
        "git_sha": git_sha,
        "n_cases": len(case_results) if case_results else 0,
        "n_trials": 1,
        "smoke": True,
        "judge_enabled": False,
        "summary": summary or {},
        "case_results": case_results or [],
    }


def _grader_result(name: str, score: float) -> dict[str, Any]:
    return {"grader_name": name, "score": score, "passed": score >= 0.5, "reason": "test"}


def _case_result(case_id: str, scores: dict[str, float], *, trial: int = 0) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "trial": trial,
        "grader_results": [_grader_result(k, v) for k, v in scores.items()],
        "error": None,
    }


def _write_report(tmp_path: Path, name: str, data: dict[str, Any]) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class TestVerdictLogic:
    def test_neutral_when_all_deltas_within_threshold(self, tmp_path: Path) -> None:
        summary = {"note_has_sections": 1.0, "note_quality_judge": 0.76}
        b = _write_report(tmp_path, "baseline.json", _make_report(summary=summary))
        n = _write_report(tmp_path, "new.json", _make_report(summary=summary))
        result = compare(b, n)
        assert result.verdict == "neutral"
        assert all(d == 0.0 for d in result.delta.values())

    def test_improved_when_all_graders_increase(self, tmp_path: Path) -> None:
        baseline = {"note_has_sections": 0.8, "note_quality_judge": 0.70}
        new = {"note_has_sections": 0.9, "note_quality_judge": 0.85}
        b = _write_report(tmp_path, "baseline.json", _make_report(summary=baseline))
        n = _write_report(tmp_path, "new.json", _make_report(summary=new))
        result = compare(b, n)
        assert result.verdict == "improved"
        assert result.delta["note_has_sections"] == pytest.approx(0.1)
        assert result.delta["note_quality_judge"] == pytest.approx(0.15)

    def test_regressed_when_one_grader_drops_beyond_threshold(self, tmp_path: Path) -> None:
        baseline = {"note_has_sections": 1.0, "note_quality_judge": 0.80}
        new = {"note_has_sections": 1.0, "note_quality_judge": 0.70}
        b = _write_report(tmp_path, "baseline.json", _make_report(summary=baseline))
        n = _write_report(tmp_path, "new.json", _make_report(summary=new))
        result = compare(b, n, threshold=0.02)
        assert result.verdict == "regressed"

    def test_neutral_when_drop_is_within_threshold(self, tmp_path: Path) -> None:
        baseline = {"note_quality_judge": 0.80}
        new = {"note_quality_judge": 0.79}  # delta = -0.01, under threshold 0.02
        b = _write_report(tmp_path, "baseline.json", _make_report(summary=baseline))
        n = _write_report(tmp_path, "new.json", _make_report(summary=new))
        result = compare(b, n, threshold=0.02)
        assert result.verdict == "neutral"

    def test_regressed_takes_precedence_over_improvement(self, tmp_path: Path) -> None:
        baseline = {"grader_a": 0.9, "grader_b": 0.5}
        new = {"grader_a": 0.6, "grader_b": 0.9}  # grader_a regressed, grader_b improved
        b = _write_report(tmp_path, "baseline.json", _make_report(summary=baseline))
        n = _write_report(tmp_path, "new.json", _make_report(summary=new))
        result = compare(b, n, threshold=0.02)
        assert result.verdict == "regressed"


class TestCaseLevelAnalysis:
    def test_case_regression_detected(self, tmp_path: Path) -> None:
        b_cases = [_case_result("ng-001", {"note_quality_judge": 0.80})]
        n_cases = [_case_result("ng-001", {"note_quality_judge": 0.60})]
        b = _write_report(tmp_path, "baseline.json", _make_report(summary={}, case_results=b_cases))
        n = _write_report(tmp_path, "new.json", _make_report(summary={}, case_results=n_cases))
        result = compare(b, n, case_threshold=0.1)
        assert len(result.case_regressions) == 1
        assert result.case_regressions[0]["case_id"] == "ng-001"
        assert result.case_regressions[0]["delta"] == pytest.approx(-0.2)

    def test_case_improvement_detected(self, tmp_path: Path) -> None:
        b_cases = [_case_result("ng-004", {"note_quality_judge": 0.65})]
        n_cases = [_case_result("ng-004", {"note_quality_judge": 0.85})]
        b = _write_report(tmp_path, "baseline.json", _make_report(summary={}, case_results=b_cases))
        n = _write_report(tmp_path, "new.json", _make_report(summary={}, case_results=n_cases))
        result = compare(b, n, case_threshold=0.1)
        assert len(result.case_improvements) == 1
        assert result.case_improvements[0]["case_id"] == "ng-004"

    def test_case_within_threshold_not_flagged(self, tmp_path: Path) -> None:
        b_cases = [_case_result("ng-002", {"note_quality_judge": 0.80})]
        n_cases = [_case_result("ng-002", {"note_quality_judge": 0.75})]  # delta = -0.05
        b = _write_report(tmp_path, "baseline.json", _make_report(summary={}, case_results=b_cases))
        n = _write_report(tmp_path, "new.json", _make_report(summary={}, case_results=n_cases))
        result = compare(b, n, case_threshold=0.1)
        assert result.case_regressions == []
        assert result.case_improvements == []

    def test_only_trial_0_used_for_case_comparison(self, tmp_path: Path) -> None:
        b_cases = [
            _case_result("ng-001", {"note_quality_judge": 0.80}, trial=0),
            _case_result("ng-001", {"note_quality_judge": 0.50}, trial=1),
        ]
        n_cases = [
            _case_result("ng-001", {"note_quality_judge": 0.90}, trial=0),
            _case_result("ng-001", {"note_quality_judge": 0.20}, trial=1),
        ]
        b = _write_report(tmp_path, "baseline.json", _make_report(summary={}, case_results=b_cases))
        n = _write_report(tmp_path, "new.json", _make_report(summary={}, case_results=n_cases))
        result = compare(b, n, case_threshold=0.05)
        # Only trial=0 is considered: 0.80 -> 0.90 = improvement
        assert len(result.case_improvements) == 1
        assert result.case_improvements[0]["delta"] == pytest.approx(0.1)


class TestCLI:
    def test_exit_0_when_neutral(self, tmp_path: Path) -> None:
        summary = {"note_has_sections": 1.0}
        b = _write_report(tmp_path, "baseline.json", _make_report(summary=summary))
        n = _write_report(tmp_path, "new.json", _make_report(summary=summary))
        code = main(["--baseline", str(b), "--new", str(n)])
        assert code == 0

    def test_exit_0_when_improved_and_fail_on_regressed(self, tmp_path: Path) -> None:
        b = _write_report(tmp_path, "baseline.json", _make_report(summary={"g": 0.7}))
        n = _write_report(tmp_path, "new.json", _make_report(summary={"g": 0.9}))
        code = main(["--baseline", str(b), "--new", str(n), "--fail-on", "regressed"])
        assert code == 0

    def test_exit_1_when_regressed_and_fail_on_regressed(self, tmp_path: Path) -> None:
        b = _write_report(tmp_path, "baseline.json", _make_report(summary={"g": 0.9}))
        n = _write_report(tmp_path, "new.json", _make_report(summary={"g": 0.7}))
        code = main(["--baseline", str(b), "--new", str(n), "--fail-on", "regressed"])
        assert code == 1

    def test_exit_1_when_neutral_and_fail_on_regressed_or_neutral(self, tmp_path: Path) -> None:
        summary = {"g": 0.8}
        b = _write_report(tmp_path, "baseline.json", _make_report(summary=summary))
        n = _write_report(tmp_path, "new.json", _make_report(summary=summary))
        code = main(["--baseline", str(b), "--new", str(n), "--fail-on", "regressed-or-neutral"])
        assert code == 1

    def test_exit_0_without_fail_on_even_when_regressed(self, tmp_path: Path) -> None:
        b = _write_report(tmp_path, "baseline.json", _make_report(summary={"g": 0.9}))
        n = _write_report(tmp_path, "new.json", _make_report(summary={"g": 0.7}))
        code = main(["--baseline", str(b), "--new", str(n)])
        assert code == 0
