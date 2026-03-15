from typing import Literal

from pydantic import BaseModel, Field


class NoteContent(BaseModel):
    topic: str = Field(..., description="学習トピック")
    content: str = Field(..., description="ノート本文")
    summary: str = Field(..., description="ノート要約")


class FeedbackOutput(BaseModel):
    understanding_level: Literal["low", "medium", "high"] = Field(..., description="ユーザーの回答から理解度を算出")
    strength: list[str] = Field(..., description="良かった点")
    improvement_points: list[str] = Field(..., description="改善点")
