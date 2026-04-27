from evals.graders.base import GraderResult

REQUIRED_SECTIONS: tuple[str, ...] = ("概要", "学んだこと", "重要なポイント", "まだ曖昧な点")


def grade(note_content: str) -> GraderResult:
    missing = [s for s in REQUIRED_SECTIONS if s not in note_content]
    score = (len(REQUIRED_SECTIONS) - len(missing)) / len(REQUIRED_SECTIONS)
    return GraderResult(
        grader_name="note_has_sections",
        score=score,
        passed=len(missing) == 0,
        reason=f"missing sections: {missing}" if missing else "all sections present",
        metadata={"missing_sections": missing, "required_sections": list(REQUIRED_SECTIONS)},
    )
