from pathlib import Path

import pytest

from storage.local import LocalObjectStorage


async def test_put_then_get_roundtrips_bytes(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path)
    await storage.put("a/b/c.png", b"hello", "image/png")

    assert await storage.get("a/b/c.png") == b"hello"


async def test_put_creates_nested_directories(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path)
    await storage.put("dialogue_images/session/0.jpg", b"x", "image/jpeg")

    assert (tmp_path / "dialogue_images" / "session" / "0.jpg").read_bytes() == b"x"


async def test_delete_is_idempotent(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path)
    await storage.put("k.png", b"x", "image/png")

    await storage.delete("k.png")
    await storage.delete("k.png")  # 既に無くても例外を出さない

    assert not (tmp_path / "k.png").exists()


@pytest.mark.parametrize("key", ["../escape.png", "a/../../escape.png"])
async def test_rejects_path_traversal(tmp_path: Path, key: str) -> None:
    storage = LocalObjectStorage(tmp_path)
    with pytest.raises(ValueError, match="Invalid storage key"):
        await storage.put(key, b"x", "image/png")
