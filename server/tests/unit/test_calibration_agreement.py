"""evals.calibration.agreement.compute_agreement の集計挙動テスト。

judge_criterion をモックして、criterion ごとに人手ラベルと突き合わせる集計が
正しく動作することを確認する。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from evals.calibration import agreement, loader
from evals.calibration.agreement import _format_table, _has_low_kappa, compute_agreement
from evals.calibration.kappa import BinaryAgreement
from evals.golden.judge import JudgeOutcome


@pytest.fixture
def setup_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    rubric_dir = tmp_path / "rubrics"
    labels_dir = tmp_path / "labels"
    rubric_dir.mkdir()
    labels_dir.mkdir()
    monkeypatch.setattr(agreement, "RUBRIC_DIR", rubric_dir)
    monkeypatch.setattr(loader, "HUMAN_LABELS_DIR", labels_dir)
    (rubric_dir / "note_quality.yaml").write_text(
        "criteria:\n"
        "  explanatory_depth:\n    criterion: 'crit-explanatory'\n"
        "  protege_alignment:\n    criterion: 'crit-alignment'\n"
        "pass_policy: all\n",
        encoding="utf-8",
    )
    return labels_dir


def _label(case: str, criterion: str, human: bool) -> str:
    return (
        f'{{"case_id":"{case}","criterion_id":"{criterion}","human_holds":{str(human).lower()},'
        '"output":"o","context":"c","annotator":"r","annotated_at":"2026-05-28"}'
    )


async def test_compute_agreement_groups_by_criterion(
    setup_paths: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (setup_paths / "note_quality.jsonl").write_text(
        "\n".join(
            [
                _label("c1", "explanatory_depth", True),
                _label("c2", "explanatory_depth", False),
                _label("c1", "protege_alignment", True),
                _label("c2", "protege_alignment", True),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(agreement, "build_judge_llm", lambda: AsyncMock())

    # judge_criterion は criterion 文字列で振り分けて返す
    async def fake_judge_criterion(*, criterion: str, output: str, context: str, judge_llm: object) -> JudgeOutcome:
        # explanatory: 人間と完全一致, alignment: 全 False を返して disagreement
        if criterion == "crit-explanatory":
            # 順序保証: c1=True, c2=False と同じ
            return JudgeOutcome(holds=fake_judge_criterion.exp_seq.pop(0), rationale="r")  # type: ignore[attr-defined]
        return JudgeOutcome(holds=False, rationale="r")

    fake_judge_criterion.exp_seq = [True, False]  # type: ignore[attr-defined]
    monkeypatch.setattr(agreement, "judge_criterion", fake_judge_criterion)

    results = await compute_agreement("note_quality")

    by_id = {r.criterion_id: r.agreement for r in results}
    assert by_id["explanatory_depth"].n == 2
    assert by_id["explanatory_depth"].agreement == 1.0
    assert by_id["protege_alignment"].n == 2
    # judge=[F,F], human=[T,T] → agreement=0
    assert by_id["protege_alignment"].agreement == 0.0


async def test_compute_agreement_raises_on_unknown_criterion(
    setup_paths: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (setup_paths / "note_quality.jsonl").write_text(
        _label("c1", "nonexistent_axis", True) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(agreement, "build_judge_llm", lambda: AsyncMock())

    with pytest.raises(ValueError, match="unknown criterion_id"):
        await compute_agreement("note_quality")


def test_format_table_contains_columns() -> None:
    from evals.calibration.agreement import CriterionAgreement

    results = [
        CriterionAgreement(
            criterion_id="explanatory_depth",
            agreement=BinaryAgreement(n=25, agreement=0.84, kappa=0.66, judge_pass_rate=0.68, human_pass_rate=0.72),
        )
    ]
    table = _format_table(results)
    assert "criterion" in table
    assert "kappa" in table
    assert "explanatory_depth" in table
    assert "25" in table


def test_has_low_kappa_detects_below_threshold() -> None:
    from evals.calibration.agreement import CriterionAgreement

    high = CriterionAgreement(
        criterion_id="a",
        agreement=BinaryAgreement(n=10, agreement=0.9, kappa=0.7, judge_pass_rate=0.5, human_pass_rate=0.5),
    )
    low = CriterionAgreement(
        criterion_id="b",
        agreement=BinaryAgreement(n=10, agreement=0.6, kappa=0.2, judge_pass_rate=0.5, human_pass_rate=0.5),
    )
    assert _has_low_kappa([high, low]) is True
    assert _has_low_kappa([high]) is False


async def test_compute_agreement_empty_labels_raises(
    setup_paths: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (setup_paths / "note_quality.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setattr(agreement, "build_judge_llm", lambda: AsyncMock())

    with pytest.raises(ValueError, match="no human labels"):
        await compute_agreement("note_quality")
