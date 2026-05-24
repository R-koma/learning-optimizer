"""Golden dataset 評価のスキーマとローダ。

golden record は `evals/datasets/golden/<category>__<slug>__<NNN>.yaml` に
1 レコード 1 ファイルで置かれ、全レコードに `_invariants.yaml` の普遍ルールが
自動適用される。詳細は `evals/datasets/golden/_TEMPLATE.yaml` を参照。
"""

from evals.golden.loader import load_golden_records, load_invariants
from evals.golden.schema import (
    Assertion,
    ExpectedBehavior,
    GoldenInput,
    GoldenRecord,
    Invariant,
    InvariantsFile,
)

__all__ = [
    "Assertion",
    "ExpectedBehavior",
    "GoldenInput",
    "GoldenRecord",
    "Invariant",
    "InvariantsFile",
    "load_golden_records",
    "load_invariants",
]
