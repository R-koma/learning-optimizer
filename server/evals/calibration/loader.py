"""human_labels/*.jsonl のロード。"""

from __future__ import annotations

from pathlib import Path

from evals.calibration.schema import HumanLabel

HUMAN_LABELS_DIR = Path(__file__).parent / "human_labels"


def load_labels(rubric_name: str) -> list[HumanLabel]:
    """human_labels/<rubric_name>.jsonl を読み込んで HumanLabel のリストを返す。"""
    path = HUMAN_LABELS_DIR / f"{rubric_name}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"human labels not found: {path}")
    labels: list[HumanLabel] = []
    with path.open(encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith("//"):
                continue
            try:
                labels.append(HumanLabel.model_validate_json(line))
            except Exception as exc:
                raise ValueError(f"{path}:{lineno} invalid label record: {exc}") from exc
    return labels
