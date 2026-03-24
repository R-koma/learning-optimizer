from typing import Annotated
from uuid import UUID

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class LearningState(TypedDict):
    user_id: str
    dialogue_session_id: UUID
    note_id: UUID
    messages: Annotated[list[BaseMessage], add_messages]
    topic: str
    turn_count: int
    should_generate_note: bool
    session_type: str
    note_content: str
    note_summary: str
