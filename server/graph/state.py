from typing import Annotated, Literal, NotRequired
from uuid import UUID

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from graph.output_schemas import ResponseMode

TargetDepth = Literal["recognize", "explain", "apply"]

# DialogueAnalysis.depth_level（surface / principle / applied）との対応:
# surface ≒ mentioned〜defined / principle ≒ exemplified / applied ≒ applied。
# こちらは観点単位の到達度なので、発話から判定しやすい4段階（言及→定義→具体例→応用）を使う。
ReachedDepth = Literal["mentioned", "defined", "exemplified", "applied"]


class CoveredAspect(TypedDict):
    aspect: str
    reached_depth: ReachedDepth


class TurnAnalysisRecord(TypedDict):
    """事前分析のうち、プロンプトに注入された決定内容だけを残す記録。

    `DialogueTurnAnalysis` をそのまま持たず TypedDict に落とすのは、チェックポイントの
    シリアライズ経路を素の dict に揃えるため（`CoveredAspect` と同じ扱い）。
    `observations` は `covered_aspects` へマージ済みなので含めない。
    """

    response_mode: ResponseMode
    selected_aspect: str
    error_summary: str


class LearningState(TypedDict):
    user_id: str
    dialogue_session_id: UUID
    note_id: UUID
    messages: Annotated[list[BaseMessage], add_messages]
    topic: str
    turn_count: int
    should_generate_note: bool
    session_type: str
    note_content: NotRequired[str]
    note_summary: NotRequired[str]
    prior_improvements: NotRequired[str]
    learning_goal: NotRequired[str]
    target_depth: NotRequired[TargetDepth]
    focus_aspects: NotRequired[list[str]]
    # 旧チェックポイントには存在しないため NotRequired。読む側は state.get() で欠損許容する
    covered_aspects: NotRequired[list[CoveredAspect]]
    # 「直近ターンの」事前分析結果。covered_aspects と違い累積せず毎ターン置き換わる。
    # 事前分析を行わなかったターン（dialogue intent 以外・分析失敗）は None を書き込む。
    # 前ターンの値が残ると、チェックポイント履歴を辿る eval エクスポートが別ターンの
    # 決定内容を取り違えるため、値が無いことも明示的に記録する必要がある。
    turn_analysis: NotRequired[TurnAnalysisRecord | None]
