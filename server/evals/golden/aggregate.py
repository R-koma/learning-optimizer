"""record 評価結果を集計し、リリースゲート判定（P0 fail で不合格）を出す。"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field

from evals.golden.evaluator import RecordResult


@dataclass(frozen=True)
class FailedAssertion:
    record_id: str
    assertion_id: str
    source: str
    priority: str
    detail: str


@dataclass(frozen=True)
class Summary:
    n_records: int
    n_passed_records: int
    pass_rate: float
    by_category: dict[str, float] = field(default_factory=dict)
    failed_by_priority: dict[str, int] = field(default_factory=dict)
    p0_failures: list[FailedAssertion] = field(default_factory=list)

    @property
    def gate_passed(self) -> bool:
        """P0 の assertion 失敗が 1 件も無ければゲート合格。"""
        return not self.p0_failures


def summarize(record_results: list[RecordResult]) -> Summary:
    n_records = len(record_results)
    n_passed = sum(1 for r in record_results if r.passed)

    category_pass: dict[str, list[float]] = defaultdict(list)
    failed_by_priority: dict[str, int] = defaultdict(int)
    p0_failures: list[FailedAssertion] = []

    for record in record_results:
        category_pass[record.category].append(1.0 if record.passed else 0.0)
        for assertion in record.results:
            if assertion.passed:
                continue
            failed_by_priority[assertion.priority] += 1
            if assertion.priority == "P0":
                p0_failures.append(
                    FailedAssertion(
                        record_id=record.record_id,
                        assertion_id=assertion.assertion_id,
                        source=assertion.source,
                        priority=assertion.priority,
                        detail=assertion.detail,
                    )
                )

    return Summary(
        n_records=n_records,
        n_passed_records=n_passed,
        pass_rate=(n_passed / n_records) if n_records else 0.0,
        by_category={cat: statistics.mean(scores) for cat, scores in category_pass.items()},
        failed_by_priority=dict(failed_by_priority),
        p0_failures=p0_failures,
    )
