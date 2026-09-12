"""正本 jsonl と golden の値空間・構造の不変条件。

`failure_mode` / `first_failure` / `source` は自由文字列なので、レジストリ（`evals.taxonomy`）に
無い値が入れば表記ゆれとして集計が割れる。構造側は regression の忠実度に直結する
（本番の `messages` と 1:1 でない履歴で再実行すると別のターンを測る）。
"""

from __future__ import annotations

import glob
import json
from pathlib import Path
from typing import Any

import yaml

from evals.taxonomy import FAILURE_MODES, SOURCES
from evals.tools.capture import CAPTURED_BY

_DATASETS_DIR = Path(__file__).resolve().parents[3] / "evals" / "datasets"
_GOLDEN_DIR = _DATASETS_DIR / "golden"
_JSONL_PATH = _DATASETS_DIR / "generate_questions.jsonl"


def _records() -> list[dict[str, Any]]:
    with _JSONL_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _golden_files() -> list[tuple[str, dict[str, Any]]]:
    files = []
    for path in sorted(glob.glob(str(_GOLDEN_DIR / "*.yaml"))):
        if Path(path).name.startswith("_"):
            continue
        with open(path, encoding="utf-8") as f:
            files.append((path, yaml.safe_load(f)))
    return files


def test_golden_failure_modes_are_registered() -> None:
    problems = [
        f"{path}: failure_mode={data['failure_mode']!r} が evals.taxonomy.FAILURE_MODES に無い"
        for path, data in _golden_files()
        if data["failure_mode"] not in FAILURE_MODES
    ]
    assert not problems, "\n".join(problems)


def test_golden_filename_matches_failure_mode() -> None:
    problems = [
        f"{path}: ファイル名と failure_mode={data['failure_mode']!r} が一致しない"
        for path, data in _golden_files()
        if Path(path).stem != data["failure_mode"]
    ]
    assert not problems, "\n".join(problems)


def test_first_failure_values_are_registered() -> None:
    problems = [
        f"{record['id']}: first_failure={record['first_failure']!r} が FAILURE_MODES に無い"
        for record in _records()
        if record["first_failure"] is not None and record["first_failure"] not in FAILURE_MODES
    ]
    assert not problems, "\n".join(problems)


def test_source_values_are_registered() -> None:
    problems = [
        f"{record['id']}: source={record['source']!r} が evals.taxonomy.SOURCES に無い"
        for record in _records()
        if record["source"] not in SOURCES
    ]
    assert not problems, "\n".join(problems)


def test_failed_records_name_the_failure_mode() -> None:
    problems = [
        f"{record['id']}: pass=false なのに first_failure が無い"
        for record in _records()
        if record["pass"] is False and record["first_failure"] is None
    ]
    assert not problems, "\n".join(problems)


def test_capture_derived_history_is_the_complete_prefix() -> None:
    """capture 由来レコードの履歴は本番の `messages` と 1:1 になっている。

    条件は「先頭が user のトピック発話」＋「`turn`（対象応答の message_order）が履歴長 +1」。
    手で転記したレコードはこれを満たさない（トピック発話や learning_start の応答が欠けている）ので、
    regression は capture 由来以外をスキップする。

    role の厳密な交互は要求しない。応答生成前に切断されたターンなど、本番が実際に連続した user
    メッセージを残すことがあり（capture が warning で知らせる）、それは忠実な写しとして正しい。
    """
    problems: list[str] = []
    for record in _records():
        if record["meta"].get("captured_by") != CAPTURED_BY:
            continue
        history = record["input"]["conversation_history"]
        if not history or history[0]["role"] != "user":
            problems.append(f"{record['id']}: 履歴の先頭が user のトピック発話でない")
        if record["turn"] != len(history) + 1:
            problems.append(f"{record['id']}: turn={record['turn']} が履歴長 {len(history)} と整合しない")
        if record["input"]["graph_state"].get("topic") != history[0]["content"]:
            problems.append(f"{record['id']}: topic と履歴先頭の本文が一致しない")
    assert not problems, "\n".join(problems)
