from evals.golden.aggregate import summarize
from evals.golden.evaluator import AssertionResult, RecordResult


def _assertion(*, passed: bool, priority: str = "P0", aid: str = "a1") -> AssertionResult:
    return AssertionResult(
        source="record",
        assertion_id=aid,
        polarity="must",
        type="judge",
        priority=priority,  # type: ignore[arg-type]
        holds=passed,
        passed=passed,
        detail="d",
    )


def _record(record_id: str, category: str, assertions: list[AssertionResult]) -> RecordResult:
    return RecordResult(
        record_id=record_id,
        category=category,
        difficulty="easy",
        priority="P0",
        target="generate_question",
        output="o",
        results=assertions,
    )


class TestSummarize:
    def test_all_pass_gate_passed(self) -> None:
        results = [_record("r1", "catA", [_assertion(passed=True)])]
        summary = summarize(results)
        assert summary.n_records == 1
        assert summary.n_passed_records == 1
        assert summary.pass_rate == 1.0
        assert summary.gate_passed is True
        assert summary.p0_failures == []

    def test_p0_failure_blocks_gate(self) -> None:
        results = [_record("r1", "catA", [_assertion(passed=False, priority="P0")])]
        summary = summarize(results)
        assert summary.gate_passed is False
        assert len(summary.p0_failures) == 1
        assert summary.p0_failures[0].record_id == "r1"
        assert summary.failed_by_priority == {"P0": 1}

    def test_p1_failure_does_not_block_gate(self) -> None:
        results = [_record("r1", "catA", [_assertion(passed=False, priority="P1")])]
        summary = summarize(results)
        assert summary.gate_passed is True
        assert summary.failed_by_priority == {"P1": 1}

    def test_by_category_pass_rate(self) -> None:
        results = [
            _record("r1", "catA", [_assertion(passed=True)]),
            _record("r2", "catA", [_assertion(passed=False, priority="P1")]),
            _record("r3", "catB", [_assertion(passed=True)]),
        ]
        summary = summarize(results)
        assert summary.by_category["catA"] == 0.5
        assert summary.by_category["catB"] == 1.0

    def test_empty_results(self) -> None:
        summary = summarize([])
        assert summary.n_records == 0
        assert summary.pass_rate == 0.0
        assert summary.gate_passed is True
