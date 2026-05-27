"""evals.calibration.loader.load_labels のテスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.calibration import loader
from evals.calibration.loader import load_labels


@pytest.fixture
def labels_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(loader, "HUMAN_LABELS_DIR", tmp_path)
    return tmp_path


def _write(path: Path, *lines: str) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_load_labels_parses_jsonl(labels_dir: Path) -> None:
    _write(
        labels_dir / "note_quality.jsonl",
        '{"case_id":"ng-001","criterion_id":"protege_alignment","human_holds":true,'
        '"output":"note","context":"ctx","annotator":"ryoma","annotated_at":"2026-05-28"}',
        '{"case_id":"ng-002","criterion_id":"personalization","human_holds":false,'
        '"output":"n","context":"c","annotator":"ryoma","annotated_at":"2026-05-28","notes":"hard"}',
    )

    labels = load_labels("note_quality")

    assert len(labels) == 2
    assert labels[0].case_id == "ng-001"
    assert labels[0].human_holds is True
    assert labels[1].notes == "hard"


def test_load_labels_skips_blank_and_comment_lines(labels_dir: Path) -> None:
    _write(
        labels_dir / "note_quality.jsonl",
        "// header comment",
        "",
        '{"case_id":"ng-001","criterion_id":"x","human_holds":true,'
        '"output":"o","context":"c","annotator":"r","annotated_at":"2026-05-28"}',
        "",
    )

    labels = load_labels("note_quality")

    assert len(labels) == 1


def test_load_labels_raises_on_missing_file(labels_dir: Path) -> None:
    with pytest.raises(FileNotFoundError, match="note_quality.jsonl"):
        load_labels("note_quality")


def test_load_labels_raises_on_invalid_record(labels_dir: Path) -> None:
    _write(labels_dir / "note_quality.jsonl", '{"case_id":"x"}')

    with pytest.raises(ValueError, match="invalid label record"):
        load_labels("note_quality")
