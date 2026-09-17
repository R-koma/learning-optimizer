"""昇格済み instance の `human_verdicts` 付け直し。

criterion を変えた後の付け直しと付け間違いの修正のために、この 1 ブロックだけを差し替える。
criterion 本文はここでは触らない（判定の基準そのものなので PR レビューを通す）。
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from evals.tools.annotate.store import VerdictError, update_verdicts

_HEADER = """\
failure_mode: self_answered_question
schema_version: 2
status: active

assertions:
  - id: a1
    type: judge
    polarity: must_not
    criterion: >
      AI が自分の質問の答えを先に述べている。
  - id: a2
    type: judge
    polarity: must_not
    applies_when: >
      直前の説明に事実誤認が含まれている。
    criterion: >
      不正確な表現を訂正せず追認している。
instances:
  - source_trace_id: first
    source: real
    observed_output: 応答 1
    pass: false
    human_verdicts:
      a1: fail
      a2: na
    rationale: |
      1 件目。
    verified_by: R-koma
    created_at: 2026-08-31

  - source_trace_id: second
    source: real
    observed_output: 応答 2
    pass: true
    human_verdicts:
      a1: pass
      a2: na
    rationale: |
      2 件目。
    verified_by: R-koma
    created_at: 2026-09-01
"""


@pytest.fixture
def golden_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "golden"
    directory.mkdir()
    (directory / "self_answered_question.yaml").write_text(_HEADER, encoding="utf-8")
    return directory


def _text(golden_dir: Path) -> str:
    return (golden_dir / "self_answered_question.yaml").read_text(encoding="utf-8")


def test_only_the_targeted_verdict_block_changes(golden_dir: Path) -> None:
    before = _text(golden_dir)

    update_verdicts(golden_dir, "first", {"a1": "fail", "a2": "fail"})

    after = _text(golden_dir)
    assert after.replace("      a2: fail\n", "      a2: na\n", 1) == before


def test_the_other_instance_keeps_its_verdicts(golden_dir: Path) -> None:
    update_verdicts(golden_dir, "first", {"a1": "fail", "a2": "fail"})

    data = yaml.safe_load(_text(golden_dir))
    assert data["instances"][0]["human_verdicts"] == {"a1": "fail", "a2": "fail"}
    assert data["instances"][1]["human_verdicts"] == {"a1": "pass", "a2": "na"}
    assert data["instances"][1]["rationale"] == "2 件目。\n"


def test_verdicts_are_written_in_the_declared_assertion_order(golden_dir: Path) -> None:
    update_verdicts(golden_dir, "first", {"a2": "fail", "a1": "fail"})

    assert "    human_verdicts:\n      a1: fail\n      a2: fail\n    rationale: |\n" in _text(golden_dir)


def test_the_last_instance_can_be_relabelled(golden_dir: Path) -> None:
    update_verdicts(golden_dir, "second", {"a1": "pass", "a2": "pass"})

    data = yaml.safe_load(_text(golden_dir))
    assert data["instances"][1]["human_verdicts"] == {"a1": "pass", "a2": "pass"}
    assert data["instances"][1]["verified_by"] == "R-koma"


def test_criterion_and_assertions_are_untouched(golden_dir: Path) -> None:
    update_verdicts(golden_dir, "first", {"a1": "fail", "a2": "fail"})

    data = yaml.safe_load(_text(golden_dir))
    assert [a["id"] for a in data["assertions"]] == ["a1", "a2"]
    assert data["assertions"][1]["applies_when"].strip() == "直前の説明に事実誤認が含まれている。"


@pytest.mark.parametrize(
    ("trace_id", "verdicts", "expected"),
    [
        ("first", {"a1": "fail"}, "a2"),
        ("first", {"a1": "fail", "a2": "na", "a9": "pass"}, "a9"),
        ("first", {"a1": "maybe", "a2": "na"}, "maybe"),
        ("first", {"a1": "na", "a2": "na"}, "applies_when"),
        ("first", {"a1": "pass", "a2": "pass"}, "fail が 1 つも無い"),
        ("second", {"a1": "fail", "a2": "na"}, "pass=true"),
        ("missing", {"a1": "fail", "a2": "na"}, "golden に無い"),
    ],
)
def test_invalid_relabelling_is_rejected(
    golden_dir: Path, trace_id: str, verdicts: dict[str, str], expected: str
) -> None:
    before = (golden_dir / "self_answered_question.yaml").read_bytes()

    with pytest.raises(VerdictError) as exc:
        update_verdicts(golden_dir, trace_id, verdicts)

    assert any(expected in problem for problem in exc.value.problems), exc.value.problems
    assert (golden_dir / "self_answered_question.yaml").read_bytes() == before
