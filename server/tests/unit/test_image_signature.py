import pytest

from core.image_signature import detect_image_mime


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (b"\x89PNG\r\n\x1a\n" + b"rest", "image/png"),
        (b"\xff\xd8\xff\xe0\x00\x10JFIF", "image/jpeg"),
        (b"RIFF\x24\x00\x00\x00WEBPVP8 ", "image/webp"),
    ],
)
def test_detects_known_signatures(data: bytes, expected: str) -> None:
    assert detect_image_mime(data) == expected


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"not an image",
        b"RIFF\x00\x00\x00\x00AVI ",  # RIFF だが WEBP ではない
        b"GIF89a",  # 非対応形式
        b"RIFF",  # WebP 判定に必要な長さに満たない
    ],
)
def test_returns_none_for_unknown(data: bytes) -> None:
    assert detect_image_mime(data) is None
