from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from evals.golden import (
    Assertion,
    GoldenRecord,
    load_golden_records,
    load_invariants,
)
from evals.golden.loader import GOLDEN_DIR


def _write_yaml(path: Path, data: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _record_dict(record_id: str, *, status: str = "active") -> dict[str, object]:
    return {
        "id": record_id,
        "schema_version": 2,
        "status": status,
        "eval_level": "node",
        "target": "generate_question",
        "category": "premature_definition",
        "difficulty": "easy",
        "priority": "P0",
        "source": "hand_authored",
        "tags": ["topic:test"],
        "input": {
            "learner_profile": {"level": "undergrad"},
            "conversation_history": [
                {"role": "system_question", "content": "Q?"},
                {"role": "learner", "content": "A"},
            ],
            "graph_state": {"current_topic": "t", "depth": 1},
        },
        "expected_behavior": {
            "assertions": [
                {"id": "a1", "polarity": "must", "type": "judge", "criterion": "c"},
            ],
        },
        "rationale": "r",
        "created_at": "2026-05-22",
        "verified_by": "ryoma",
        "last_reviewed_at": "2026-05-22",
    }


class TestAssertionSchema:
    def test_judge_requires_criterion(self) -> None:
        with pytest.raises(ValidationError, match="criterion"):
            Assertion(id="a1", polarity="must", type="judge")

    def test_deterministic_requires_check(self) -> None:
        with pytest.raises(ValidationError, match="check"):
            Assertion(id="a1", polarity="must", type="deterministic")

    def test_deterministic_with_check_is_valid(self) -> None:
        a = Assertion(id="a1", polarity="must", type="deterministic", check="ends_with_question_mark")
        assert a.check == "ends_with_question_mark"

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            Assertion(id="a1", polarity="must", type="judge", criterion="c", typo="x")  # type: ignore[call-arg]


class TestLoadGoldenRecords:
    def test_loads_shipped_records(self) -> None:
        records = load_golden_records()
        assert len(records) >= 4
        assert all(isinstance(r, GoldenRecord) for r in records)
        assert all(r.status == "active" for r in records)
        ids = {r.id for r in records}
        assert "circular_question__ddia-reliability-repeated-prompt__001" in ids

    def test_skips_underscore_files(self) -> None:
        ids = {r.id for r in load_golden_records()}
        assert not any(i.startswith("_") for i in ids)

    def test_shipped_records_have_learning_plan(self) -> None:
        for r in load_golden_records():
            assert r.input.learning_plan is not None, f"{r.id} missing learning_plan"
            assert r.input.learning_plan.target_depth in ("recognize", "explain", "apply")

    def test_learning_plan_is_optional(self, tmp_path: Path) -> None:
        # learning_plan を持たないレコードも後方互換でロードできる
        _write_yaml(tmp_path / "rec_active.yaml", _record_dict("rec_active"))
        record = load_golden_records(tmp_path)[0]
        assert record.input.learning_plan is None

    def test_id_must_match_filename(self, tmp_path: Path) -> None:
        _write_yaml(tmp_path / "mismatch.yaml", _record_dict("not_mismatch"))
        with pytest.raises(ValueError, match="does not match filename"):
            load_golden_records(tmp_path)

    def test_status_filter_excludes_draft(self, tmp_path: Path) -> None:
        _write_yaml(tmp_path / "rec_active.yaml", _record_dict("rec_active"))
        _write_yaml(tmp_path / "rec_draft.yaml", _record_dict("rec_draft", status="draft"))
        ids = {r.id for r in load_golden_records(tmp_path)}
        assert ids == {"rec_active"}

    def test_empty_statuses_returns_all(self, tmp_path: Path) -> None:
        _write_yaml(tmp_path / "rec_active.yaml", _record_dict("rec_active"))
        _write_yaml(tmp_path / "rec_draft.yaml", _record_dict("rec_draft", status="draft"))
        ids = {r.id for r in load_golden_records(tmp_path, statuses=())}
        assert ids == {"rec_active", "rec_draft"}


class TestLoadInvariants:
    def test_loads_shipped_invariants(self) -> None:
        invariants = load_invariants()
        ids = {inv.id for inv in invariants}
        assert "inv_no_full_answer" in ids
        assert "inv_ends_with_question" in ids

    def test_deterministic_invariants_have_check(self) -> None:
        invariants = load_invariants()
        for inv in invariants:
            if inv.type == "deterministic":
                assert inv.check, f"{inv.id} missing check"
            else:
                assert inv.criterion, f"{inv.id} missing criterion"

    def test_invariants_file_path_resolves(self) -> None:
        assert (GOLDEN_DIR / "_invariants.yaml").exists()
