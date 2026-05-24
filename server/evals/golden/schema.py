"""Golden record / invariants の Pydantic スキーマ。

YAML を読み込む境界で fail-fast に検証する。未知フィールドは禁止し、
type と criterion/check の整合（judge⇒criterion 必須 / deterministic⇒check 必須）
を model レベルで保証する。
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

Polarity = Literal["must", "must_not"]
AssertionType = Literal["judge", "deterministic"]
Status = Literal["draft", "active", "deprecated", "quarantined"]
EvalLevel = Literal["node", "turn", "trajectory"]
Difficulty = Literal["easy", "medium", "hard"]
Priority = Literal["P0", "P1", "P2"]
TurnRole = Literal["system_question", "learner"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _require_type_field(obj: _Strict, type_: AssertionType, criterion: str | None, check: str | None) -> None:
    """type=judge は criterion、type=deterministic は check を必須にする共通検証。"""
    if type_ == "judge" and not criterion:
        raise ValueError(f"{obj.__class__.__name__}: type=judge requires a non-empty 'criterion'")
    if type_ == "deterministic" and not check:
        raise ValueError(f"{obj.__class__.__name__}: type=deterministic requires a non-empty 'check'")


class LearnerProfile(_Strict):
    level: str


class Turn(_Strict):
    role: TurnRole
    content: str


class GraphState(_Strict):
    current_topic: str
    depth: int


class GoldenInput(_Strict):
    learner_profile: LearnerProfile
    conversation_history: list[Turn]
    graph_state: GraphState


class Assertion(_Strict):
    """レコード固有の期待。judge は criterion、deterministic は check を持つ。"""

    id: str
    polarity: Polarity
    type: AssertionType
    criterion: str | None = None
    check: str | None = None
    parameters: dict[str, object] | None = None

    @model_validator(mode="after")
    def _check_type_fields(self) -> Assertion:
        _require_type_field(self, self.type, self.criterion, self.check)
        return self


class ExpectedBehavior(_Strict):
    assertions: list[Assertion]
    exemplar: str | None = None


class GoldenRecord(_Strict):
    """1 ファイル = 1 golden record。"""

    id: str
    schema_version: int
    status: Status
    eval_level: EvalLevel
    target: str
    category: str
    difficulty: Difficulty
    priority: Priority
    source: str
    tags: list[str]
    input: GoldenInput
    expected_behavior: ExpectedBehavior
    rationale: str
    created_at: str
    verified_by: str
    last_reviewed_at: str
    # CAPTURE 段階の記述項目（finalize 後も記録として残る）。
    observed_output: str | None = None
    capture_note: str | None = None

    @field_validator("created_at", "last_reviewed_at", mode="before")
    @classmethod
    def _date_to_str(cls, value: object) -> object:
        # YAML は素の日付を datetime.date にパースするため ISO 文字列へ正規化する。
        return value.isoformat() if isinstance(value, date) else value


class Invariant(_Strict):
    """全レコードに自動適用される普遍ルール。"""

    id: str
    polarity: Polarity
    type: AssertionType
    priority: Priority
    criterion: str | None = None
    check: str | None = None
    parameters: dict[str, object] | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _check_type_fields(self) -> Invariant:
        _require_type_field(self, self.type, self.criterion, self.check)
        return self


class InvariantsFile(_Strict):
    schema_version: int
    invariants: list[Invariant]
