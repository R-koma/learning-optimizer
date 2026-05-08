from evals.graders.base import GraderResult

REQUIRED_H2_SECTIONS: tuple[str, ...] = ("学んだこと", "重要なポイント")
REQUIRED_CALLOUT_LABEL: str = "まだ曖昧な点"


def _has_h2(content: str, name: str) -> bool:
    return f"## {name}" in content


def _has_ambiguity_callout(content: str) -> bool:
    """blockquote callout `> **まだ曖昧な点**` の存在を検出する。

    曖昧な点が一切ない場合は省略可なので、callout が存在しなければ
    暗黙的に「曖昧な点なし」と解釈し、欠落とは扱わない。
    """
    needle = f"> **{REQUIRED_CALLOUT_LABEL}**"
    return needle in content


def grade(note_content: str) -> GraderResult:
    missing_h2 = [s for s in REQUIRED_H2_SECTIONS if not _has_h2(note_content, s)]
    has_callout = _has_ambiguity_callout(note_content)

    total_checks = len(REQUIRED_H2_SECTIONS)
    score = (total_checks - len(missing_h2)) / total_checks
    passed = len(missing_h2) == 0

    reason_parts: list[str] = []
    if missing_h2:
        reason_parts.append(f"missing h2 sections: {missing_h2}")
    reason_parts.append(f"ambiguity callout: {'present' if has_callout else 'absent (allowed if no ambiguities)'}")

    return GraderResult(
        grader_name="note_has_sections",
        score=score,
        passed=passed,
        reason="; ".join(reason_parts),
        metadata={
            "missing_h2_sections": missing_h2,
            "required_h2_sections": list(REQUIRED_H2_SECTIONS),
            "has_ambiguity_callout": has_callout,
        },
    )
