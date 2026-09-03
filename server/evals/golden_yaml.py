"""golden instance の「写し」を正本 jsonl から機械生成する。

日本語本文に folded scalar（`>` / `>-`）を使うと、折り返し位置に原文に無い半角空白が入る。
`yaml.safe_dump` は folded を出さないので正確側から入り、複数行だけ `|` にして読みやすさを足す。
"""

from __future__ import annotations

from typing import Any

import yaml

COPY_KEYS: tuple[str, ...] = ("source", "meta", "input", "observed_output")


class _BlockDumper(yaml.SafeDumper):
    pass


def _represent_str(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


_BlockDumper.add_representer(str, _represent_str)


def copy_fields(source_record: dict[str, Any]) -> dict[str, Any]:
    """jsonl レコードから、golden instance が写しとして持つフィールドだけを抜き出す。"""
    return {
        "source": source_record["source"],
        "meta": source_record["meta"],
        "input": source_record["input"],
        "observed_output": source_record["output"],
    }


def dump_copy_block(source_record: dict[str, Any], *, indent: int = 4) -> str:
    """写しフィールドを golden YAML へ貼れる形（既定は instance 直下の 4 スペース）で文字列化する。"""
    text = yaml.dump(
        copy_fields(source_record),
        Dumper=_BlockDumper,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=10**9,
    )
    pad = " " * indent
    return "".join(f"{pad}{line}\n" if line else "\n" for line in text.splitlines())
