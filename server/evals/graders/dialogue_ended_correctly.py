from evals.graders.base import GraderResult

LEARNING_END_SIGNAL = "LEARNING_END"


def grade(*, response_content: str, expected_label: str) -> GraderResult:
    """Check if response is correctly formatted for the expected label.

    expected_label = "LEARNING_END": response.content.strip() must equal exactly "LEARNING_END"
    expected_label = "CONTINUE":     response.content.strip() must NOT equal "LEARNING_END"
    """
    stripped = response_content.strip()
    is_end_signal = stripped == LEARNING_END_SIGNAL

    if expected_label == LEARNING_END_SIGNAL:
        passed = is_end_signal
        reason = (
            "response is exactly 'LEARNING_END'"
            if passed
            else f"expected exact 'LEARNING_END' but got: {stripped[:80]!r}"
        )
    elif expected_label == "CONTINUE":
        passed = not is_end_signal
        reason = (
            "response is a continuation (not LEARNING_END)"
            if passed
            else "response is LEARNING_END but expected continuation"
        )
    else:
        return GraderResult(
            grader_name="dialogue_ended_correctly",
            score=0.0,
            passed=False,
            reason=f"unknown expected_label: {expected_label}",
            metadata={"expected_label": expected_label},
        )

    return GraderResult(
        grader_name="dialogue_ended_correctly",
        score=1.0 if passed else 0.0,
        passed=passed,
        reason=reason,
        metadata={"expected_label": expected_label, "is_end_signal": is_end_signal},
    )
