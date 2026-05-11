from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from graph.state import TargetDepth


class StartLearningMessage(BaseModel):
    type: Literal["start_learning"]
    topic: str
    learning_goal: str | None = None
    target_depth: TargetDepth | None = None
    focus_aspects: list[str] | None = None


class StartReviewMessage(BaseModel):
    type: Literal["start_review"]
    note_id: str


class UserMessage(BaseModel):
    type: Literal["user_message"]
    content: str


class EndSessionMessage(BaseModel):
    type: Literal["end_session"]


class AssistantMessage(BaseModel):
    type: Literal["assistant_message"] = "assistant_message"
    content: str


class AssistantMessageChunk(BaseModel):
    type: Literal["assistant_message_chunk"] = "assistant_message_chunk"
    content: str


class AssistantMessageEnd(BaseModel):
    type: Literal["assistant_message_end"] = "assistant_message_end"


class NoteGeneratedMessage(BaseModel):
    type: Literal["note_generated"] = "note_generated"
    note_id: UUID
    topic: str
    summary: str


class FeedbackGeneratedMessage(BaseModel):
    type: Literal["feedback_generated"] = "feedback_generated"
    understanding_level: str
    strength: str
    improvements: str


class SessionEndedMessage(BaseModel):
    type: Literal["session_ended"] = "session_ended"
    session_id: UUID | None = None


class SessionStartedMessage(BaseModel):
    type: Literal["session_started"] = "session_started"
    session_id: UUID
    session_type: Literal["learning", "review"]


class SessionResumedMessage(BaseModel):
    type: Literal["session_resumed"] = "session_resumed"
    session_id: UUID
    session_type: Literal["learning", "review"]


class CancelLastMessageSuccess(BaseModel):
    type: Literal["cancel_last_message_success"] = "cancel_last_message_success"
    cancelled_content: str


class CancelLastMessageError(BaseModel):
    type: Literal["cancel_last_message_error"] = "cancel_last_message_error"
    detail: str


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    detail: str
