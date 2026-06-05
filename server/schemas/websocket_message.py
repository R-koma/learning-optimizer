import base64
import binascii
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from core import config
from graph.state import TargetDepth


class ImageAttachment(BaseModel):
    mime_type: Literal["image/jpeg", "image/png", "image/webp"]
    data: str  # base64（data URL プレフィックスは含めない）

    @field_validator("data")
    @classmethod
    def _validate_decoded_size(cls, value: str) -> str:
        try:
            decoded = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("data must be valid base64") from exc
        if len(decoded) == 0:
            raise ValueError("image is empty")
        if len(decoded) > config.MAX_IMAGE_BYTES:
            raise ValueError(f"image exceeds {config.MAX_IMAGE_BYTES} bytes")
        return value


class StartLearningMessage(BaseModel):
    type: Literal["start_learning"]
    topic: str
    learning_goal: str | None = None
    target_depth: TargetDepth | None = None
    focus_aspects: list[str] | None = None


class StartReviewMessage(BaseModel):
    type: Literal["start_review"]
    note_id: UUID


class ResumeSessionMessage(BaseModel):
    type: Literal["resume_session"]
    session_id: UUID


class UserMessage(BaseModel):
    type: Literal["user_message"]
    content: str
    images: list[ImageAttachment] | None = None

    @field_validator("images")
    @classmethod
    def _validate_image_count(cls, value: list[ImageAttachment] | None) -> list[ImageAttachment] | None:
        if value and len(value) > config.MAX_IMAGES_PER_MESSAGE:
            raise ValueError(f"at most {config.MAX_IMAGES_PER_MESSAGE} images per message")
        return value


class CancelLastMessageRequest(BaseModel):
    type: Literal["cancel_last_message"]


class EndSessionMessage(BaseModel):
    type: Literal["end_session"]


IncomingMessage = Annotated[
    StartLearningMessage
    | StartReviewMessage
    | ResumeSessionMessage
    | UserMessage
    | CancelLastMessageRequest
    | EndSessionMessage,
    Field(discriminator="type"),
]


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
