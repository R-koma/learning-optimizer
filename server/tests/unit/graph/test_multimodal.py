import base64
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from graph.multimodal import image_attachments_kwargs, image_block_from_bytes, load_image_blocks, text_block
from storage.local import LocalObjectStorage


def test_image_attachments_kwargs_empty_returns_empty_dict() -> None:
    assert image_attachments_kwargs([]) == {}


def test_image_attachments_kwargs_wraps_under_known_key() -> None:
    attachments = [{"storage_key": "k", "mime_type": "image/png"}]
    assert image_attachments_kwargs(attachments) == {"image_attachments": attachments}


def test_image_block_from_bytes_builds_high_detail_data_url() -> None:
    block = image_block_from_bytes(b"abc", "image/png")
    assert block["type"] == "image_url"
    assert block["image_url"]["detail"] == "high"
    assert block["image_url"]["url"] == f"data:image/png;base64,{base64.b64encode(b'abc').decode()}"


def test_text_block_shape() -> None:
    assert text_block("hi") == {"type": "text", "text": "hi"}


async def test_load_image_blocks_reads_from_storage(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path)
    await storage.put("dialogue_images/s/m/0.png", b"img-bytes", "image/png")
    attachments = [{"storage_key": "dialogue_images/s/m/0.png", "mime_type": "image/png"}]
    message = HumanMessage(content="見て", additional_kwargs=image_attachments_kwargs(attachments))

    blocks = await load_image_blocks(message, storage)

    assert len(blocks) == 1
    block = blocks[0]
    assert isinstance(block, dict)
    assert block["image_url"]["url"] == f"data:image/png;base64,{base64.b64encode(b'img-bytes').decode()}"


async def test_load_image_blocks_without_attachments_returns_empty(tmp_path: Path) -> None:
    blocks = await load_image_blocks(HumanMessage(content="text only"), LocalObjectStorage(tmp_path))
    assert blocks == []


async def test_load_image_blocks_ignores_non_human(tmp_path: Path) -> None:
    blocks = await load_image_blocks(AIMessage(content="assistant"), LocalObjectStorage(tmp_path))
    assert blocks == []
