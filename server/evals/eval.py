import asyncio
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml

from graph.llm import llm
from graph.prompts.question import PROMPT_VERSION

_GOLDEN_DIR = Path(__file__).parent / "datasets" / "golden"


def load_records() -> Iterator[dict[str, Any]]:
    for path in sorted(_GOLDEN_DIR.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        with path.open(encoding="utf-8") as f:
            record = yaml.safe_load(f)
        if record.get("status") == "active":
            yield record


async def main() -> None:
    print(f"model={llm.model_name} temperature={llm.temperature}")
    print(f"prompt_version={PROMPT_VERSION}")

    for record in load_records():
        print("=" * 100)
        for assertion in record["assertions"]:
            assertion_id = assertion["id"]
            print(assertion_id)
        print("-" * 100)
        print("LLMの出力（observed_output / 人間ラベル: fail）:")
        for instance in record["instances"]:
            observed_output = instance["observed_output"]
            print(observed_output)
        print("-" * 100)
        print(record)


if __name__ == "__main__":
    asyncio.run(main())
