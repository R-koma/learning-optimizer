"""judge と人手ラベルの一致率（agreement / Cohen's kappa）を計測する CLI。

Usage:
    uv run python -m evals.calibration.agreement --rubric note_quality
    uv run python -m evals.calibration.agreement --rubric question_quality --limit 50

`human_labels/<rubric>.jsonl` のラベルを読み込み、各レコードについて固定 output と
固定 context を使って judge_criterion を呼ぶ。同じ criterion ごとに集計して
n / agreement / kappa / judge_pass_rate / human_pass_rate を表示する。

CI には乗せない。judge プロンプト or judge モデルを変えた時に手動で実行する較正タスク。
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from evals._judge_factory import build_judge_llm
from evals.calibration.kappa import BinaryAgreement, compute_binary_agreement
from evals.calibration.loader import load_labels
from evals.calibration.schema import HumanLabel
from evals.golden.judge import judge_criterion
from evals.graders._criterion_aggregate import load_rubric

RUBRIC_DIR = Path(__file__).parent.parent / "rubrics"
KAPPA_WARN_THRESHOLD = 0.4

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CriterionAgreement:
    criterion_id: str
    agreement: BinaryAgreement


async def _judge_label(label: HumanLabel, criterion_text: str) -> bool:
    judge = build_judge_llm()
    verdict = await judge_criterion(
        criterion=criterion_text,
        output=label.output,
        context=label.context,
        judge_llm=judge,
    )
    return verdict.holds


def _group_by_criterion(labels: list[HumanLabel]) -> dict[str, list[HumanLabel]]:
    grouped: dict[str, list[HumanLabel]] = defaultdict(list)
    for label in labels:
        grouped[label.criterion_id].append(label)
    return dict(grouped)


async def compute_agreement(rubric_name: str, *, limit: int | None = None) -> list[CriterionAgreement]:
    rubric = load_rubric(RUBRIC_DIR / f"{rubric_name}.yaml")
    labels = load_labels(rubric_name)
    if limit is not None:
        labels = labels[:limit]
    if not labels:
        raise ValueError(f"no human labels found for {rubric_name!r}")

    grouped = _group_by_criterion(labels)
    unknown = sorted(c for c in grouped if c not in rubric.criteria)
    if unknown:
        raise ValueError(f"unknown criterion_id(s) in labels: {unknown}")

    results: list[CriterionAgreement] = []
    for criterion_id, criterion_text in rubric.criteria.items():
        bucket = grouped.get(criterion_id, [])
        if not bucket:
            logger.warning("no labels for criterion %r; skipping", criterion_id)
            continue
        judge_verdicts = await asyncio.gather(*(_judge_label(lbl, criterion_text) for lbl in bucket))
        agreement = compute_binary_agreement(
            judge=list(judge_verdicts),
            human=[lbl.human_holds for lbl in bucket],
        )
        results.append(CriterionAgreement(criterion_id=criterion_id, agreement=agreement))
    return results


def _format_table(results: list[CriterionAgreement]) -> str:
    header = f"{'criterion':<32} {'n':>4} {'agreement':>10} {'kappa':>8} {'judge%':>8} {'human%':>8}"
    lines = [header, "-" * len(header)]
    for r in results:
        a = r.agreement
        lines.append(
            f"{r.criterion_id:<32} {a.n:>4} {a.agreement:>10.3f} {a.kappa:>8.3f} "
            f"{a.judge_pass_rate:>8.3f} {a.human_pass_rate:>8.3f}"
        )
    return "\n".join(lines)


def _has_low_kappa(results: list[CriterionAgreement]) -> bool:
    return any(r.agreement.kappa < KAPPA_WARN_THRESHOLD for r in results)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="compute judge / human label agreement")
    parser.add_argument("--rubric", required=True, help="rubric 名（例: note_quality）")
    parser.add_argument("--limit", type=int, default=None, help="先頭 N 件のみ評価")
    parser.add_argument(
        "--fail-on-low-kappa",
        action="store_true",
        help=f"いずれかの criterion で kappa < {KAPPA_WARN_THRESHOLD} なら exit 1",
    )
    return parser.parse_args()


async def main_async() -> int:
    args = _parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    results = await compute_agreement(args.rubric, limit=args.limit)
    print(_format_table(results))
    if args.fail_on_low_kappa and _has_low_kappa(results):
        print(
            f"\nWARNING: kappa < {KAPPA_WARN_THRESHOLD} on at least one criterion. "
            "Re-draft criterion text or re-label.",
            file=sys.stderr,
        )
        return 1
    return 0


def main() -> None:
    sys.exit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
