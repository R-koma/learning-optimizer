from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class StartLearningMessage(BaseModel):
    type: Literal["start_learning"]
    topic: str


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


class CancelLastMessageSuccess(BaseModel):
    type: Literal["cancel_last_message_success"] = "cancel_last_message_success"
    cancelled_content: str


class CancelLastMessageError(BaseModel):
    type: Literal["cancel_last_message_error"] = "cancel_last_message_error"
    detail: str


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    detail: str
