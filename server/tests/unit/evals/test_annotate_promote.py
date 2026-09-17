"""golden への昇格（写しの生成と人間ラベルの追記）。

golden YAML は読み込んで書き直さない。`>` の折り返しやコメントが pyyaml の round-trip で
落ちるため、既存の assertion 定義や他の instance を壊す。追記だけに閉じることをここで固定する。
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from evals.golden_yaml import copy_fields
from evals.tools.annotate.store import (
    Promotion,
    PromotionError,
    default_verified_by,
    promote_to_golden,
)

_TODAY = date(2026, 9, 18)

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
"""


def _record(trace_id: str, **overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": trace_id,
        "schema_version": 3,
        "source": "real",
        "session": "2026-09-17-session",
        "dialogue_session_id": None,
        "turn": 3,
        "captured_at": "2026-09-17T06:00:00Z",
        "meta": {"model": "gpt-4.1-nano", "prompt_version": "generate_question@v4"},
        "input": {
            "conversation_history": [{"role": "user", "content": "トピック"}],
            "graph_state": {"topic": "トピック"},
        },
        "output": "その仕組みはどう動きますか？",
        "pass": False,
        "first_failure": "self_answered_question",
        "note": "負例",
        "annotated_at": "2026-09-18T00:00:00Z",
    }
    return record | overrides


@pytest.fixture
def jsonl_path(tmp_path: Path) -> Path:
    path = tmp_path / "generate_questions.jsonl"
    records = [_record("rec-fail"), _record("rec-good", **{"pass": True, "first_failure": None, "note": "正例"})]
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    return path


def _golden(tmp_path: Path, instances: str) -> Path:
    directory = tmp_path / "golden"
    directory.mkdir(exist_ok=True)
    path = directory / "self_answered_question.yaml"
    path.write_text(_HEADER + instances, encoding="utf-8")
    return directory


@pytest.fixture
def golden_dir(tmp_path: Path) -> Path:
    return _golden(
        tmp_path,
        "instances:\n"
        "  - source_trace_id: existing\n"
        "    source: synthetic\n"
        "    pass: true\n"
        "    human_verdicts:\n"
        "      a1: pass\n"
        "      a2: na\n"
        "    rationale: |\n"
        "      既存の instance。\n"
        "    verified_by: R-koma\n"
        "    created_at: 2026-08-31\n",
    )


def _promotion(**overrides: Any) -> Promotion:
    values: dict[str, Any] = {
        "failure_mode": "self_answered_question",
        "human_verdicts": {"a1": "fail", "a2": "na"},
        "rationale": "質問の答えを先に述べている。",
        "verified_by": "R-koma",
    }
    return Promotion(**(values | overrides))


def test_promotion_appends_without_touching_existing_content(
    jsonl_path: Path, golden_dir: Path, tmp_path: Path
) -> None:
    path = golden_dir / "self_answered_question.yaml"
    before = path.read_text(encoding="utf-8")

    promote_to_golden(jsonl_path, golden_dir, "rec-fail", _promotion(), today=_TODAY)

    after = path.read_text(encoding="utf-8")
    assert after.startswith(before)


def test_promoted_instance_round_trips_as_a_copy_of_the_source(jsonl_path: Path, golden_dir: Path) -> None:
    promote_to_golden(jsonl_path, golden_dir, "rec-fail", _promotion(), today=_TODAY)

    data = yaml.safe_load((golden_dir / "self_answered_question.yaml").read_text(encoding="utf-8"))
    instance = data["instances"][-1]
    source = json.loads(jsonl_path.read_text(encoding="utf-8").splitlines()[0])
    assert instance["source_trace_id"] == "rec-fail"
    assert {key: instance[key] for key in copy_fields(source)} == copy_fields(source)
    assert instance["pass"] is False
    assert instance["human_verdicts"] == {"a1": "fail", "a2": "na"}
    assert instance["verified_by"] == "R-koma"
    assert instance["created_at"] == _TODAY
    assert data["assertions"][0]["id"] == "a1"


def test_multiline_rationale_is_written_as_a_block_scalar(jsonl_path: Path, golden_dir: Path) -> None:
    promote_to_golden(jsonl_path, golden_dir, "rec-fail", _promotion(rationale="1 行目。\n2 行目。"), today=_TODAY)

    text = (golden_dir / "self_answered_question.yaml").read_text(encoding="utf-8")
    assert "    rationale: |-\n      1 行目。\n      2 行目。\n" in text


def test_promotion_works_on_a_file_with_no_instances_yet(jsonl_path: Path, tmp_path: Path) -> None:
    golden_dir = _golden(tmp_path, "instances: []\n")

    promote_to_golden(jsonl_path, golden_dir, "rec-fail", _promotion(), today=_TODAY)

    data = yaml.safe_load((golden_dir / "self_answered_question.yaml").read_text(encoding="utf-8"))
    assert [i["source_trace_id"] for i in data["instances"]] == ["rec-fail"]


def test_a_positive_record_may_be_promoted_with_no_failing_verdict(jsonl_path: Path, golden_dir: Path) -> None:
    promote_to_golden(
        jsonl_path,
        golden_dir,
        "rec-good",
        _promotion(human_verdicts={"a1": "pass", "a2": "na"}, rationale="正例。"),
        today=_TODAY,
    )

    data = yaml.safe_load((golden_dir / "self_answered_question.yaml").read_text(encoding="utf-8"))
    assert data["instances"][-1]["pass"] is True


@pytest.mark.parametrize(
    ("trace_id", "promotion", "expected"),
    [
        ("rec-fail", _promotion(failure_mode="accurate_multi_concept_overexplain"), "golden ファイルが無い"),
        ("rec-fail", _promotion(human_verdicts={"a1": "fail"}), "a2"),
        ("rec-fail", _promotion(human_verdicts={"a1": "fail", "a2": "na", "a9": "pass"}), "a9"),
        ("rec-fail", _promotion(human_verdicts={"a1": "maybe", "a2": "na"}), "maybe"),
        ("rec-fail", _promotion(human_verdicts={"a1": "na", "a2": "na"}), "applies_when"),
        ("rec-fail", _promotion(human_verdicts={"a1": "pass", "a2": "na"}), "fail が 1 つも無い"),
        ("rec-good", _promotion(human_verdicts={"a1": "fail", "a2": "na"}), "pass=true"),
        ("rec-fail", _promotion(rationale="  "), "rationale"),
        ("rec-fail", _promotion(verified_by=""), "verified_by"),
        ("existing", _promotion(), "unknown trace id"),
    ],
)
def test_invalid_promotions_are_rejected(
    jsonl_path: Path, golden_dir: Path, trace_id: str, promotion: Promotion, expected: str
) -> None:
    path = golden_dir / "self_answered_question.yaml"
    before = path.read_bytes()

    with pytest.raises((PromotionError, LookupError)) as exc:
        promote_to_golden(jsonl_path, golden_dir, trace_id, promotion, today=_TODAY)

    problems = getattr(exc.value, "problems", [str(exc.value)])
    assert any(expected in problem for problem in problems), problems
    assert path.read_bytes() == before


def test_an_unannotated_record_cannot_be_promoted(tmp_path: Path, golden_dir: Path) -> None:
    jsonl_path = tmp_path / "unannotated.jsonl"
    record = _record("rec-todo", **{"pass": None, "first_failure": None, "annotated_at": None})
    jsonl_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    with pytest.raises(PromotionError) as exc:
        promote_to_golden(jsonl_path, golden_dir, "rec-todo", _promotion(), today=_TODAY)

    assert any("annotate" in problem for problem in exc.value.problems)


def test_a_record_cannot_be_promoted_twice(jsonl_path: Path, golden_dir: Path) -> None:
    promote_to_golden(jsonl_path, golden_dir, "rec-fail", _promotion(), today=_TODAY)

    with pytest.raises(PromotionError) as exc:
        promote_to_golden(jsonl_path, golden_dir, "rec-fail", _promotion(), today=_TODAY)

    assert any("既に golden" in problem for problem in exc.value.problems)


def test_default_verified_by_reuses_the_existing_reviewer(golden_dir: Path) -> None:
    assert default_verified_by(golden_dir) == "R-koma"
