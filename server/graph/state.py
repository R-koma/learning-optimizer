from typing import Annotated, Literal, NotRequired
from uuid import UUID

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

TargetDepth = Literal["recognize", "explain", "apply"]

# DialogueAnalysis.depth_level（surface / principle / applied）との対応:
# surface ≒ mentioned〜defined / principle ≒ exemplified / applied ≒ applied。
# こちらは観点単位の到達度なので、発話から判定しやすい4段階（言及→定義→具体例→応用）を使う。
ReachedDepth = Literal["mentioned", "defined", "exemplified", "applied"]


class CoveredAspect(TypedDict):
    aspect: str
    reached_depth: ReachedDepth


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
