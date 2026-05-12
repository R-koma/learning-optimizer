from typing import Literal

from pydantic import BaseModel, Field


class NoteContent(BaseModel):
    topic: str = Field(..., description="学習トピック")
    content: str = Field(..., description="ノート本文")
    summary: str = Field(..., description="ノート要約")


class AspectNode(BaseModel):
    name: str = Field(..., description="観点名（短い名詞句）")
    summary: str = Field(..., description="この観点について対話で扱われた内容の1〜2文要約")
    coverage: Literal["covered", "partial", "uncovered"] = Field(
        ...,
        description="対話でのカバー度。covered=ユーザーが自分の言葉で説明できた / "
        "partial=触れたが理解が浅い・曖昧 / uncovered=言及なし（重要な隣接観点として明示）",
    )
    children: list["AspectNode"] = Field(
        default_factory=list,
        description="サブ観点。最大 2 階層まで（ルート→子→孫）。それ以上深くしない",
    )


class AspectMap(BaseModel):
    root: str = Field(..., description="トピック名（ノートの topic と一致させる）")
    aspects: list[AspectNode] = Field(
        ...,
        description="ルート直下の観点リスト。3〜7 項目を目安に、対話で実際に扱われた観点を中心に構成する",
    )


class FeedbackOutput(BaseModel):
    understanding_level: Literal["low", "medium", "high"] = Field(..., description="ユーザーの回答から理解度を算出")
    strength: list[str] = Field(..., description="良かった点")
    improvement_points: list[str] = Field(..., description="改善点")
