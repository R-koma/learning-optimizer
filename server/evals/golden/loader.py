"""golden record / invariants を YAML から読み込む。

- `_` 始まりのファイルはテンプレ / 設定として除外する。
- `id` フィールドはファイル名（拡張子なし）と一致していなければならない。
- 既定では `status: active` のレコードのみ返す（draft / deprecated は測定に含めない）。
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import yaml

from evals.golden.schema import GoldenRecord, Invariant, InvariantsFile

GOLDEN_DIR = Path(__file__).parent.parent / "datasets" / "golden"
INVARIANTS_FILENAME = "_invariants.yaml"
_DEFAULT_STATUSES: tuple[str, ...] = ("active",)


def _load_yaml(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name}: expected a YAML mapping, got {type(data).__name__}")
    return data


def load_invariants(path: Path | None = None) -> list[Invariant]:
    """`_invariants.yaml` を読み込んで invariant のリストを返す。"""
    invariants_path = path or (GOLDEN_DIR / INVARIANTS_FILENAME)
    parsed = InvariantsFile.model_validate(_load_yaml(invariants_path))
    return parsed.invariants


def load_golden_records(
    directory: Path | None = None,
    *,
    statuses: Iterable[str] = _DEFAULT_STATUSES,
) -> list[GoldenRecord]:
    """golden record を読み込む。

    Args:
        directory: golden ディレクトリ。省略時は同梱の datasets/golden。
        statuses: 採用する status。空イテラブルを渡すと全 status を返す。

    Raises:
        ValueError: id がファイル名と一致しない、または YAML 検証に失敗した場合。
    """
    golden_dir = directory or GOLDEN_DIR
    allowed = tuple(statuses)
    records: list[GoldenRecord] = []
    for path in sorted(golden_dir.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        record = GoldenRecord.model_validate(_load_yaml(path))
        expected_id = path.stem
        if record.id != expected_id:
            raise ValueError(f"{path.name}: id '{record.id}' does not match filename stem '{expected_id}'")
        if allowed and record.status not in allowed:
            continue
        records.append(record)
    return records
