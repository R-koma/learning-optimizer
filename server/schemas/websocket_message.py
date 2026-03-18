from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class StartLearningMessage(BaseModel):
    type: Literal["start_learning"]
    topic: str


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


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    detail: str
