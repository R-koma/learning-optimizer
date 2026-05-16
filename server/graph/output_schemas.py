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


class DialogueAnalysis(BaseModel):
    """対話分析結果（generate_feedback の前段で生成される構造化データ）。"""

    accurate_understanding: list[str] = Field(
        default_factory=list,
        description="ユーザーが正しく理解・説明できている概念。各項目は1文で具体的に",
    )
    misconceptions: list[str] = Field(
        default_factory=list,
        description="誤解・用語の混同。「○○と△△を混同している」「○○を△△の意味で使っている」のように具体的に",
    )
    ambiguous_expressions: list[str] = Field(
        default_factory=list,
        description="曖昧な表現。何が曖昧で、正確にはどう表現すべきかを示す",
    )
    unmentioned_concepts: list[str] = Field(
        default_factory=list,
        description="このトピックで言及されるべきだが触れられていない概念",
    )
    depth_level: Literal["surface", "principle", "applied"] = Field(
        ...,
        description="理解の深さ。surface=表面的な暗記 / principle=原理の理解 / applied=応用レベル",
    )

    def to_markdown(self) -> str:
        def _fmt(items: list[str]) -> str:
            return "\n".join(f"- {x}" for x in items) if items else "- （該当なし）"

        depth_label = {"surface": "表面的な暗記", "principle": "原理の理解", "applied": "応用レベル"}[self.depth_level]
        return (
            f"### 正確な理解\n{_fmt(self.accurate_understanding)}\n\n"
            f"### 誤解・用語の混同\n{_fmt(self.misconceptions)}\n\n"
            f"### 曖昧な表現\n{_fmt(self.ambiguous_expressions)}\n\n"
            f"### 未言及の重要概念\n{_fmt(self.unmentioned_concepts)}\n\n"
            f"### 理解の深さ\n- {depth_label}"
        )
