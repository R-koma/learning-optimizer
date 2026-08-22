import asyncio
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from graph.llm import llm
from graph.prompts.question import PROMPT_VERSION

_GOLDEN_DIR = Path(__file__).parent / "datasets" / "golden"
_JSONL_PATH = Path(__file__).parent / "datasets" / "generate_questions.jsonl"


@dataclass(frozen=True)
class SourceTrace:
    meta: dict[str, Any]
    input: dict[str, Any]
    observed_output: str


def load_golden_records() -> Iterator[dict[str, Any]]:
    for path in sorted(_GOLDEN_DIR.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        with path.open(encoding="utf-8") as f:
            record = yaml.safe_load(f)
        if record.get("status") == "active":
            yield record


def get_source_trace(trace_id: str) -> SourceTrace:
    with _JSONL_PATH.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            record: dict[str, Any] = json.loads(line)
            if record["id"] != trace_id:
                continue
            return SourceTrace(meta=record["meta"], input=record["input"], observed_output=record["output"])
    raise ValueError(f"unknown source_trace_id: {trace_id} not in {_JSONL_PATH}")


async def main() -> None:
    print(f"model={llm.model_name} temperature={llm.temperature}")
    print(f"prompt_version={PROMPT_VERSION}")

    for record in load_golden_records():
        print("=" * 100)
        for instance in record["instances"]:
            trace = get_source_trace(instance["source_trace_id"])
            print(trace)
        print("-" * 100)


if __name__ == "__main__":
    asyncio.run(main())
