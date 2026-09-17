"""正本 jsonl の annotate（`pass` / `first_failure` / `note` / `annotated_at`）の読み書き。

書き戻しは対象 1 行の置換に閉じる。`input` / `output` / `meta` / `turn_decision` は golden の
写しとバイト比較されるため、UI からは触れない。

golden は `evals.eval.load_golden_records()` を使わずここで読む。あちらは `status: active` で
絞るが、昇格済み instance との `pass` 不一致は status に関わらず起きる。
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from evals.checks import run_check
from evals.taxonomy import FAILURE_MODES

_EVALS_DIR = Path(__file__).resolve().parents[2]
DEFAULT_JSONL_PATH = _EVALS_DIR / "datasets" / "generate_questions.jsonl"
DEFAULT_GOLDEN_DIR = _EVALS_DIR / "datasets" / "golden"

ANNOTATION_KEYS = ("pass", "first_failure", "note", "annotated_at")

_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_ASSERTION_KEYS = ("id", "type", "polarity", "criterion", "applies_when", "check")


@dataclass(frozen=True)
class Annotation:
    verdict: bool | None
    first_failure: str | None
    note: str


@dataclass(frozen=True)
class GoldenInstance:
    failure_mode: str
    path: Path
    verdict: bool | None


@dataclass(frozen=True)
class DeterministicOutcome:
    assertion_id: str
    failure_mode: str
    check: str
    fails: bool
    detail: str


class AnnotationError(ValueError):
    def __init__(self, problems: list[str]) -> None:
        super().__init__(" / ".join(problems))
        self.problems = problems


def load_records(path: Path = DEFAULT_JSONL_PATH) -> list[dict[str, Any]]:
    return [json.loads(line) for line in _lines(path) if line.strip()]


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def _golden_files(golden_dir: Path) -> Iterator[tuple[Path, dict[str, Any]]]:
    for path in sorted(golden_dir.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        with path.open(encoding="utf-8") as f:
            yield path, yaml.safe_load(f)


def golden_instances(golden_dir: Path = DEFAULT_GOLDEN_DIR) -> dict[str, GoldenInstance]:
    return {
        instance["source_trace_id"]: GoldenInstance(
            failure_mode=data["failure_mode"], path=path, verdict=instance.get("pass")
        )
        for path, data in _golden_files(golden_dir)
        for instance in data["instances"]
    }


def assertions_by_failure_mode(golden_dir: Path = DEFAULT_GOLDEN_DIR) -> dict[str, list[dict[str, Any]]]:
    return {
        data["failure_mode"]: [
            {key: _clean(assertion[key]) for key in _ASSERTION_KEYS if key in assertion}
            for assertion in data["assertions"]
        ]
        for _, data in _golden_files(golden_dir)
    }


def _clean(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


def deterministic_outcomes(output: str, golden_dir: Path = DEFAULT_GOLDEN_DIR) -> list[DeterministicOutcome]:
    """golden の deterministic assertion をこの出力に適用した結果。

    UI は人間が `pass` を選ぶまでこれを表示しない。判定を先に見せると、人間ラベルが実装の写しに
    なり、混同行列（deterministic の outcome も含む）の一致率が自明に 100% になる。
    """
    outcomes: list[DeterministicOutcome] = []
    seen: set[tuple[str, str]] = set()
    for _, data in _golden_files(golden_dir):
        for assertion in data["assertions"]:
            if assertion["type"] != "deterministic":
                continue
            key = (assertion["check"], assertion["polarity"])
            if key in seen:
                continue
            seen.add(key)
            result = run_check(assertion["check"], output)
            outcomes.append(
                DeterministicOutcome(
                    assertion_id=assertion["id"],
                    failure_mode=data["failure_mode"],
                    check=assertion["check"],
                    fails=result.holds if assertion["polarity"] == "must_not" else not result.holds,
                    detail=result.detail,
                )
            )
    return outcomes


def validate_annotation(annotation: Annotation, golden: GoldenInstance | None) -> list[str]:
    problems: list[str] = []
    if annotation.first_failure is not None and annotation.first_failure not in FAILURE_MODES:
        problems.append(
            f"first_failure={annotation.first_failure!r} が evals.taxonomy.FAILURE_MODES に無い"
            f"（候補: {', '.join(sorted(FAILURE_MODES))}）"
        )
    if annotation.verdict is False and annotation.first_failure is None:
        problems.append("pass=false のレコードは first_failure が必須")
    if annotation.verdict is not False and annotation.first_failure is not None:
        problems.append("pass=false 以外のレコードに first_failure は付けられない")
    if golden is not None and golden.verdict != annotation.verdict:
        problems.append(
            f"golden の instance（{golden.path.name}）が pass={golden.verdict!r} なので、"
            f"jsonl 側だけを pass={annotation.verdict!r} に変えられない"
        )
    return problems


def apply_annotation(record: dict[str, Any], annotation: Annotation, *, now: datetime) -> dict[str, Any]:
    return record | {
        "pass": annotation.verdict,
        "first_failure": annotation.first_failure,
        "note": annotation.note,
        "annotated_at": None if annotation.verdict is None else now.strftime(_TIMESTAMP_FORMAT),
    }


def save_annotation(
    path: Path,
    trace_id: str,
    annotation: Annotation,
    *,
    golden_dir: Path = DEFAULT_GOLDEN_DIR,
    now: datetime | None = None,
) -> dict[str, Any]:
    lines = _lines(path)
    index = _index_of(lines, trace_id, path)
    problems = validate_annotation(annotation, golden_instances(golden_dir).get(trace_id))
    if problems:
        raise AnnotationError(problems)

    updated = apply_annotation(json.loads(lines[index]), annotation, now=now or datetime.now(UTC))
    lines[index] = json.dumps(updated, ensure_ascii=False) + "\n"
    _write_atomically(path, "".join(lines))
    return updated


def _index_of(lines: list[str], trace_id: str, path: Path) -> int:
    for index, line in enumerate(lines):
        if line.strip() and json.loads(line)["id"] == trace_id:
            return index
    raise LookupError(f"unknown trace id: {trace_id} not in {path}")


def _write_atomically(path: Path, text: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as tmp:
        tmp.write(text)
        temp_path = Path(tmp.name)
    os.replace(temp_path, path)
