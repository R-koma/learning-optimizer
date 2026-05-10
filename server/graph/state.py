from typing import Annotated, Literal, NotRequired
from uuid import UUID

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

TargetDepth = Literal["recognize", "explain", "apply"]
TARGET_DEPTH_VALUES: tuple[TargetDepth, ...] = ("recognize", "explain", "apply")


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
    learning_goal: NotRequired[str]
    target_depth: NotRequired[TargetDepth]
    focus_aspects: NotRequired[list[str]]
