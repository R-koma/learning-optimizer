"""Golden dataset 評価の実行エンジン。

Usage:
    uv run python -m evals.golden.runner            # 全レコード評価
    uv run python -m evals.golden.runner --smoke    # 先頭数件のみ
    uv run python -m evals.golden.runner --no-save  # レポート JSON を書かない

P0 assertion が 1 件でも fail するか、評価中にエラーが出た場合は exit code 1。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from evals.golden.adapter import generate_question_output
from evals.golden.aggregate import summarize
from evals.golden.evaluator import evaluate_record
from evals.golden.loader import load_golden_records, load_invariants

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent.parent / "reports"
SMOKE_MAX_RECORDS = 5


@dataclass
class GoldenReport:
    run_at: str
    git_sha: str
    smoke: bool
    n_records: int
    n_passed_records: int
    pass_rate: float
    gate_passed: bool
    by_category: dict[str, float] = field(default_factory=dict)
    failed_by_priority: dict[str, int] = field(default_factory=dict)
    p0_failures: list[dict[str, Any]] = field(default_factory=list)
    records: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _save_report(report: GoldenReport) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = REPORTS_DIR / f"golden_{report.git_sha}_{timestamp}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(asdict(report), f, ensure_ascii=False, indent=2)
    return path


async def run_golden(
    *,
    smoke: bool = False,
    save_report: bool = True,
    llm: ChatOpenAI | None = None,
    judge_llm: BaseChatModel | None = None,
) -> GoldenReport:
    records = load_golden_records()
    invariants = load_invariants()
    if smoke:
        records = records[:SMOKE_MAX_RECORDS]

    record_results = []
    errors: list[dict[str, str]] = []
    for record in records:
        try:
            output = await generate_question_output(record.input, llm=llm)
            record_results.append(await evaluate_record(record, output, invariants, judge_llm=judge_llm))
        except Exception as exc:
            logger.exception("golden record failed: record_id=%s", record.id)
            errors.append({"record_id": record.id, "error": f"{type(exc).__name__}: {exc}"})

    summary = summarize(record_results)
    report = GoldenReport(
        run_at=datetime.now(UTC).isoformat(),
        git_sha=_git_sha(),
        smoke=smoke,
        n_records=summary.n_records,
        n_passed_records=summary.n_passed_records,
        pass_rate=summary.pass_rate,
        gate_passed=summary.gate_passed and not errors,
        by_category=summary.by_category,
        failed_by_priority=summary.failed_by_priority,
        p0_failures=[asdict(f) for f in summary.p0_failures],
        records=[asdict(r) for r in record_results],
        errors=errors,
    )
    if save_report:
        logger.info("golden report saved: %s", _save_report(report))
    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Golden dataset eval runner")
    parser.add_argument("--smoke", action="store_true", help=f"run only first {SMOKE_MAX_RECORDS} records")
    parser.add_argument("--no-save", action="store_true", help="skip writing report JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = _parse_args(argv)
    report = asyncio.run(run_golden(smoke=args.smoke, save_report=not args.no_save))
    print(
        json.dumps(
            {
                "n_records": report.n_records,
                "n_passed_records": report.n_passed_records,
                "pass_rate": round(report.pass_rate, 3),
                "gate_passed": report.gate_passed,
                "failed_by_priority": report.failed_by_priority,
                "p0_failures": report.p0_failures,
                "errors": report.errors,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report.gate_passed else 1


if __name__ == "__main__":
    sys.exit(main())
