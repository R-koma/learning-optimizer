"""人手ラベルのスキーマ定義。

note_quality / question_quality 等の grader が使う rubric の criterion ごとに、
人間が holds=true/false を判定した結果を JSONL で保持する。
judge を回し直すときに生成出力が変わってしまうと比較できなくなるため、
ラベル時点の出力（output）を必ず固定して同梱する。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class HumanLabel(BaseModel):
    """1 件 = 1 (case, criterion) ペアの人手判定。"""

    case_id: str = Field(description="参照する dataset レコードの id（例: ng-001）")
    criterion_id: str = Field(description="rubric の criterion 名（例: protege_alignment）")
    human_holds: bool = Field(description="人間がこの criterion を成立と判定したか")
    output: str = Field(description="ラベル時点の生成出力（ノート本文など）。判定の固定スナップショット")
    context: str = Field(description="judge に渡す文脈（対話履歴など）。output と同様に固定する")
    annotator: str = Field(description="ラベル付与者")
    annotated_at: str = Field(description="ISO8601 日付（YYYY-MM-DD）")
    notes: str | None = Field(default=None, description="判定の補足メモ（任意）")
