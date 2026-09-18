"""annotate UI の書き戻しと検証。

正本 jsonl は capture が追記した 1 行 = 1 レコードのテキストで、UI が書いてよいのは
`pass` / `first_failure` / `note` / `annotated_at` だけ。対象外の行が 1 バイトでも動くと
`test_golden_copy_matches_source` の写し比較が落ちるため、行単位の保持をここで固定する。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from evals.tools.annotate.store import (
    Annotation,
    AnnotationError,
    assertions_by_failure_mode,
    deterministic_outcomes,
    golden_instances,
    load_records,
    save_annotation,
)

_NOW = datetime(2026, 9, 17, 6, 20, 14, tzinfo=UTC)


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
        "input": {"conversation_history": [{"role": "user", "content": "説明です"}], "graph_state": {"topic": "T"}},
        "output": "応答です",
        "pass": None,
        "first_failure": None,
        "note": "",
        "annotated_at": None,
    }
    return record | overrides


@pytest.fixture
def jsonl_path(tmp_path: Path) -> Path:
    path = tmp_path / "generate_questions.jsonl"
    records = [_record("rec-a"), _record("rec-b"), _record("rec-c")]
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    return path


@pytest.fixture
def golden_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "golden"
    directory.mkdir()
    (directory / "self_answered_question.yaml").write_text(
        "failure_mode: self_answered_question\n"
        "schema_version: 2\n"
        "status: active\n"
        "assertions:\n"
        "  - id: a1\n"
        "    type: judge\n"
        "    polarity: must_not\n"
        "    criterion: >\n"
        "      AI が自分の質問の答えを先に述べている。\n"
        "  - id: a5\n"
        "    type: deterministic\n"
        "    check: contains_generic_prompt_phrase\n"
        "    check_fingerprint: a9bd66a88432\n"
        "    polarity: must_not\n"
        "    criterion: >\n"
        "      一般化した促しを含んでいる。\n"
        "instances:\n"
        "  - source_trace_id: rec-c\n"
        "    pass: false\n"
        "    human_verdicts:\n"
        "      a1: fail\n"
        "      a5: pass\n",
        encoding="utf-8",
    )
    (directory / "_TEMPLATE.yaml").write_text("failure_mode: ignored\n", encoding="utf-8")
    return directory


def _empty_rubric(tmp_path: Path) -> Path:
    directory = tmp_path / "rubric"
    directory.mkdir(exist_ok=True)
    return directory


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def test_save_leaves_other_lines_byte_identical(jsonl_path: Path, golden_dir: Path) -> None:
    before = _lines(jsonl_path)

    save_annotation(
        jsonl_path,
        "rec-b",
        Annotation(verdict=False, first_failure="self_answered_question", note="負例"),
        golden_dir=golden_dir,
        now=_NOW,
    )

    after = _lines(jsonl_path)
    assert after[0] == before[0]
    assert after[2] == before[2]
    assert after[1] != before[1]


def test_save_writes_only_the_annotation_fields(jsonl_path: Path, golden_dir: Path) -> None:
    before = json.loads(_lines(jsonl_path)[0])

    save_annotation(
        jsonl_path,
        "rec-a",
        Annotation(verdict=False, first_failure="self_answered_question", note="負例"),
        golden_dir=golden_dir,
        now=_NOW,
    )

    after = json.loads(_lines(jsonl_path)[0])
    assert after["pass"] is False
    assert after["first_failure"] == "self_answered_question"
    assert after["note"] == "負例"
    assert after["annotated_at"] == "2026-09-17T06:20:14Z"
    untouched = [k for k in before if k not in {"pass", "first_failure", "note", "annotated_at"}]
    assert all(after[k] == before[k] for k in untouched)
    assert list(after) == list(before)


def test_save_keeps_the_record_unannotated_when_the_verdict_is_deferred(jsonl_path: Path, golden_dir: Path) -> None:
    save_annotation(
        jsonl_path,
        "rec-a",
        Annotation(verdict=True, first_failure=None, note="正例"),
        golden_dir=golden_dir,
        now=_NOW,
    )

    save_annotation(
        jsonl_path,
        "rec-a",
        Annotation(verdict=None, first_failure=None, note="判断保留"),
        golden_dir=golden_dir,
        now=_NOW,
    )

    record = json.loads(_lines(jsonl_path)[0])
    assert record["pass"] is None
    assert record["annotated_at"] is None
    assert record["note"] == "判断保留"


def test_unknown_trace_id_raises_lookup_error(jsonl_path: Path, golden_dir: Path) -> None:
    with pytest.raises(LookupError):
        save_annotation(
            jsonl_path,
            "missing",
            Annotation(verdict=True, first_failure=None, note=""),
            golden_dir=golden_dir,
            now=_NOW,
        )


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        (Annotation(verdict=False, first_failure="typo_mode", note=""), "FAILURE_MODES"),
        (Annotation(verdict=False, first_failure=None, note=""), "first_failure"),
        (Annotation(verdict=True, first_failure="self_answered_question", note=""), "first_failure"),
        (Annotation(verdict=None, first_failure="self_answered_question", note=""), "first_failure"),
    ],
)
def test_invalid_annotations_are_rejected(
    jsonl_path: Path, golden_dir: Path, annotation: Annotation, expected: str
) -> None:
    before = jsonl_path.read_bytes()

    with pytest.raises(AnnotationError) as exc:
        save_annotation(jsonl_path, "rec-a", annotation, golden_dir=golden_dir, now=_NOW)

    assert any(expected in problem for problem in exc.value.problems)
    assert jsonl_path.read_bytes() == before


def test_promoted_records_cannot_diverge_from_the_golden_label(jsonl_path: Path, golden_dir: Path) -> None:
    with pytest.raises(AnnotationError) as exc:
        save_annotation(
            jsonl_path,
            "rec-c",
            Annotation(verdict=True, first_failure=None, note=""),
            golden_dir=golden_dir,
            now=_NOW,
        )

    assert any("self_answered_question.yaml" in problem for problem in exc.value.problems)


def test_promoted_records_accept_the_matching_label(jsonl_path: Path, golden_dir: Path) -> None:
    save_annotation(
        jsonl_path,
        "rec-c",
        Annotation(verdict=False, first_failure="self_answered_question", note="昇格済み"),
        golden_dir=golden_dir,
        now=_NOW,
    )

    assert json.loads(_lines(jsonl_path)[2])["pass"] is False


def test_load_records_preserves_file_order(jsonl_path: Path) -> None:
    assert [r["id"] for r in load_records(jsonl_path)] == ["rec-a", "rec-b", "rec-c"]


def test_golden_instances_skip_underscore_files(golden_dir: Path) -> None:
    instances = golden_instances(golden_dir)

    assert set(instances) == {"rec-c"}
    assert instances["rec-c"].failure_mode == "self_answered_question"
    assert instances["rec-c"].verdict is False


def test_assertions_are_grouped_by_failure_mode(golden_dir: Path, tmp_path: Path) -> None:
    assertions = assertions_by_failure_mode(golden_dir, _empty_rubric(tmp_path))

    assert set(assertions) == {"self_answered_question"}
    a1, a5 = assertions["self_answered_question"]
    assert a1 == {
        "scope": "failure_mode",
        "id": "a1",
        "type": "judge",
        "polarity": "must_not",
        "criterion": "AI が自分の質問の答えを先に述べている。",
    }
    assert a5["check"] == "contains_generic_prompt_phrase"


def test_deterministic_outcomes_report_whether_the_output_fails(golden_dir: Path, tmp_path: Path) -> None:
    outcomes = deterministic_outcomes("もっと詳しく教えてください", golden_dir, _empty_rubric(tmp_path))

    assert [(o.assertion_id, o.fails) for o in outcomes] == [("a5", True)]
    assert "もっと詳しく" in outcomes[0].detail


def test_deterministic_outcomes_pass_for_a_specific_question(golden_dir: Path, tmp_path: Path) -> None:
    outcomes = deterministic_outcomes("その仕組みはどう動きますか？", golden_dir, _empty_rubric(tmp_path))

    assert [o.fails for o in outcomes] == [False]


def test_deterministic_outcomes_include_rubric_assertions(golden_dir: Path, tmp_path: Path) -> None:
    """rubric へ移した check が UI の食い違い警告から落ちないことを固定する。

    golden 側だけを見る実装に戻すと、deterministic assertion が 0 件になり警告が静かに死ぬ。
    """
    rubric_dir = tmp_path / "rubric"
    rubric_dir.mkdir(exist_ok=True)
    (rubric_dir / "common.yaml").write_text(
        "schema_version: 1\n"
        "assertions:\n"
        "  - id: r2\n"
        "    type: deterministic\n"
        "    check: contains_generic_prompt_phrase\n"
        "    polarity: must_not\n"
        "    criterion: >\n"
        "      一般化した促し。\n",
        encoding="utf-8",
    )

    outcomes = deterministic_outcomes("もっと詳しく教えてください", golden_dir, rubric_dir)

    assert [(o.assertion_id, o.fails) for o in outcomes] == [("r2", True)]
