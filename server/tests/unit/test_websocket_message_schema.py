import base64

import pytest
from pydantic import TypeAdapter, ValidationError

from core import config
from schemas.websocket_message import ImageAttachment, IncomingMessage, UserMessage

_adapter: TypeAdapter[IncomingMessage] = TypeAdapter(IncomingMessage)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def test_user_message_without_images_parses() -> None:
    msg = _adapter.validate_python({"type": "user_message", "content": "hi"})
    assert isinstance(msg, UserMessage)
    assert msg.images is None


def test_user_message_with_image_parses() -> None:
    msg = _adapter.validate_python(
        {
            "type": "user_message",
            "content": "見て",
            "images": [{"mime_type": "image/png", "data": _b64(b"x")}],
        }
    )
    assert isinstance(msg, UserMessage)
    assert msg.images is not None
    assert msg.images[0].mime_type == "image/png"


def test_rejects_unsupported_mime() -> None:
    with pytest.raises(ValidationError):
        ImageAttachment(mime_type="image/gif", data=_b64(b"x"))  # type: ignore[arg-type]


def test_rejects_invalid_base64() -> None:
    with pytest.raises(ValidationError, match="valid base64"):
        ImageAttachment(mime_type="image/png", data="!!!not base64!!!")


def test_rejects_empty_image() -> None:
    with pytest.raises(ValidationError, match="empty"):
        ImageAttachment(mime_type="image/png", data=_b64(b""))


def test_rejects_oversized_image() -> None:
    oversized = _b64(b"a" * (config.MAX_IMAGE_BYTES + 1))
    with pytest.raises(ValidationError, match="exceeds"):
        ImageAttachment(mime_type="image/png", data=oversized)


def test_rejects_too_many_images() -> None:
    images = [{"mime_type": "image/png", "data": _b64(b"x")}] * (config.MAX_IMAGES_PER_MESSAGE + 1)
    with pytest.raises(ValidationError, match="at most"):
        _adapter.validate_python({"type": "user_message", "content": "hi", "images": images})
