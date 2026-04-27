from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GraderResult:
    grader_name: str
    score: float
    passed: bool
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)
