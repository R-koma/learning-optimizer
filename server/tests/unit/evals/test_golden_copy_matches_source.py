"""golden instance の写しが正本 jsonl とバイト一致することを保証する。

正本は jsonl で、golden YAML の `meta` / `input` / `observed_output` はレビュー用の写し。
落ちたときの対処は `evals.golden_yaml.dump_copy_block` で写しを再生成する一択にする
（どちらが正しいかの判断を毎回発生させないため）。

正規化して比較しない。段落境界の消失のような本物のドリフトも一緒に見えなくなるうえ、
日本語では空白 1 個がトークン境界を動かす。
"""

from __future__ import annotations

import glob
import json
from pathlib import Path
from typing import Any

import yaml

from evals.golden_yaml import COPY_KEYS, copy_fields

_DATASETS_DIR = Path(__file__).resolve().parents[3] / "evals" / "datasets"
_GOLDEN_DIR = _DATASETS_DIR / "golden"
_JSONL_PATH = _DATASETS_DIR / "generate_questions.jsonl"


def _load_source_records() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    with open(_JSONL_PATH, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                record: dict[str, Any] = json.loads(line)
                records[record["id"]] = record
    return records


def _load_golden_files() -> list[dict[str, Any]]:
    files = []
    for path in sorted(glob.glob(str(_GOLDEN_DIR / "*.yaml"))):
        if Path(path).name.startswith("_"):
            continue
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        data["_path"] = path
        files.append(data)
    return files


def test_golden_copy_matches_source() -> None:
    sources = _load_source_records()
    mismatches: list[str] = []
    for data in _load_golden_files():
        for instance in data["instances"]:
            expected = copy_fields(sources[instance["source_trace_id"]])
            for key in COPY_KEYS:
                if instance.get(key) != expected[key]:
                    mismatches.append(
                        f"{data['_path']}: instance={instance['source_trace_id']} field={key} "
                        f"copy={instance.get(key)!r} source={expected[key]!r}"
                    )
    assert not mismatches, "\n".join(mismatches)
