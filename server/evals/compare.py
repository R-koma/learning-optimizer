"""Compare two EvalReport JSONs and detect regressions or improvements.

Usage:
    uv run python -m evals.compare \\
      --baseline evals/baselines/note_generation_baseline.json \\
      --new evals/reports/note_generation_<sha>_<ts>.json

    # Fail with exit code 1 when regressed (for CI):
    uv run python -m evals.compare \\
      --baseline evals/baselines/note_generation_baseline.json \\
      --new evals/reports/note_generation_<sha>_<ts>.json \\
      --fail-on regressed
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True)
class CompareResult:
    task: str
    baseline_summary: dict[str, float]
    new_summary: dict[str, float]
    delta: dict[str, float]
    case_regressions: list[dict[str, Any]]
    case_improvements: list[dict[str, Any]]
    verdict: Literal["improved", "regressed", "neutral"]


def _load_report(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def _mean_score_for_case(case_result: dict[str, Any]) -> float:
    grader_results = case_result.get("grader_results", [])
    if not grader_results:
        return 0.0
    return sum(float(gr["score"]) for gr in grader_results) / len(grader_results)


def compare(
    baseline_path: Path,
    new_path: Path,
    *,
    threshold: float = 0.02,
    case_threshold: float = 0.1,
) -> CompareResult:
    """Compare two EvalReport JSONs.

    Args:
        baseline_path: Path to the baseline report JSON.
        new_path: Path to the new report JSON.
        threshold: Minimum delta (grader-level) to count as regression. Default 0.02.
        case_threshold: Minimum score drop (case-level) to flag as regression. Default 0.1.

    Returns:
        CompareResult with verdict "improved", "regressed", or "neutral".
    """
    baseline = _load_report(baseline_path)
    new = _load_report(new_path)

    baseline_summary: dict[str, float] = baseline.get("summary", {})
    new_summary: dict[str, float] = new.get("summary", {})

    all_graders = set(baseline_summary) | set(new_summary)
    delta: dict[str, float] = {}
    for grader in all_graders:
        b = baseline_summary.get(grader, 0.0)
        n = new_summary.get(grader, 0.0)
        delta[grader] = round(n - b, 6)

    has_regression = any(d < -threshold for d in delta.values())
    has_improvement = any(d > threshold for d in delta.values())

    if has_regression:
        verdict: Literal["improved", "regressed", "neutral"] = "regressed"
    elif has_improvement:
        verdict = "improved"
    else:
        verdict = "neutral"

    baseline_cases: dict[str, dict[str, Any]] = {
        cr["case_id"]: cr for cr in baseline.get("case_results", []) if cr.get("trial", 0) == 0
    }
    new_cases: dict[str, dict[str, Any]] = {
        cr["case_id"]: cr for cr in new.get("case_results", []) if cr.get("trial", 0) == 0
    }

    case_regressions: list[dict[str, Any]] = []
    case_improvements: list[dict[str, Any]] = []

    for case_id in set(baseline_cases) | set(new_cases):
        b_score = _mean_score_for_case(baseline_cases.get(case_id, {}))
        n_score = _mean_score_for_case(new_cases.get(case_id, {}))
        diff = round(n_score - b_score, 6)
        entry = {"case_id": case_id, "baseline_score": b_score, "new_score": n_score, "delta": diff}
        if diff < -case_threshold:
            case_regressions.append(entry)
        elif diff > case_threshold:
            case_improvements.append(entry)

    case_regressions.sort(key=lambda x: x["delta"])
    case_improvements.sort(key=lambda x: -x["delta"])

    return CompareResult(
        task=new.get("task", baseline.get("task", "unknown")),
        baseline_summary=baseline_summary,
        new_summary=new_summary,
        delta=delta,
        case_regressions=case_regressions,
        case_improvements=case_improvements,
        verdict=verdict,
    )


def _print_report(result: CompareResult, *, threshold: float) -> None:
    print(f"\n=== Eval Comparison: {result.task} ===")
    print(f"Verdict: {result.verdict.upper()}\n")

    print("Grader Summary:")
    all_graders = sorted(set(result.baseline_summary) | set(result.new_summary))
    for grader in all_graders:
        b = result.baseline_summary.get(grader, 0.0)
        n = result.new_summary.get(grader, 0.0)
        d = result.delta.get(grader, 0.0)
        marker = ""
        if d < -threshold:
            marker = " <- REGRESSED"
        elif d > threshold:
            marker = " <- improved"
        print(f"  {grader:40s}  baseline={b:.4f}  new={n:.4f}  delta={d:+.4f}{marker}")

    if result.case_regressions:
        print("\nCase Regressions:")
        for cr in result.case_regressions:
            print(f"  {cr['case_id']:20s}  {cr['baseline_score']:.4f} -> {cr['new_score']:.4f}  ({cr['delta']:+.4f})")

    if result.case_improvements:
        print("\nCase Improvements:")
        for ci in result.case_improvements:
            print(f"  {ci['case_id']:20s}  {ci['baseline_score']:.4f} -> {ci['new_score']:.4f}  ({ci['delta']:+.4f})")

    print()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two EvalReport JSONs")
    parser.add_argument("--baseline", required=True, type=Path, help="path to baseline report JSON")
    parser.add_argument("--new", required=True, type=Path, dest="new_report", help="path to new report JSON")
    parser.add_argument("--threshold", type=float, default=0.02, help="grader-level regression threshold")
    parser.add_argument("--case-threshold", type=float, default=0.1, help="case-level regression threshold")
    parser.add_argument(
        "--fail-on",
        choices=["regressed", "regressed-or-neutral"],
        dest="fail_on",
        help="exit with code 1 when verdict matches",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = compare(
        args.baseline,
        args.new_report,
        threshold=args.threshold,
        case_threshold=args.case_threshold,
    )
    _print_report(result, threshold=args.threshold)

    if args.fail_on == "regressed" and result.verdict == "regressed":
        return 1
    if args.fail_on == "regressed-or-neutral" and result.verdict in ("regressed", "neutral"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
