"""対話メッセージへの画像添付を LLM 向けの content ブロックへ変換する補助。

画像参照（storage_key + mime）は HumanMessage の `additional_kwargs["image_attachments"]`
に持たせる方針。state（= チェックポイント）には base64 を載せず軽量参照のみを保持し、
LLM 呼び出しの直前にストレージから読み出して base64 data URL を構築する（issue #136 D2/D9）。
"""

import base64
from typing import Any

from langchain_core.messages import BaseMessage

from storage.base import ObjectStorage

_ATTACHMENTS_KEY = "image_attachments"


def image_attachments_kwargs(attachments: list[dict[str, str]]) -> dict[str, Any]:
    """HumanMessage に渡す additional_kwargs を組み立てる。

    attachments は {"storage_key": ..., "mime_type": ...} の並び。空なら空 dict を返し、
    余計なキーをメッセージに載せない。
    """
    if not attachments:
        return {}
    return {_ATTACHMENTS_KEY: attachments}


# LangChain の HumanMessage.content は str | list[str | dict[Any, Any]]。dict のキー/値は
# 不変なので、content ブロックは dict[Any, Any] として組み立てる。
ContentBlock = dict[Any, Any]


def text_block(text: str) -> ContentBlock:
    return {"type": "text", "text": text}


def image_block_from_bytes(data: bytes, mime_type: str) -> ContentBlock:
    b64 = base64.b64encode(data).decode()
    # detail=high: コードや図中の文字を読む必要があるため低解像度では不足する。
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime_type};base64,{b64}", "detail": "high"},
    }


async def load_image_blocks(message: BaseMessage, storage: ObjectStorage) -> list[str | ContentBlock]:
    """メッセージに紐づく画像参照をストレージから読み出し、image_url ブロック列を返す。"""
    if message.type != "human":
        return []
    attachments = message.additional_kwargs.get(_ATTACHMENTS_KEY) or []
    blocks: list[str | ContentBlock] = []
    for att in attachments:
        data = await storage.get(att["storage_key"])
        blocks.append(image_block_from_bytes(data, att["mime_type"]))
    return blocks
